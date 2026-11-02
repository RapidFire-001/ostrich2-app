"""Desktop interface for the Ostrich 2.0 memory programmer."""
import os
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from serial.tools import list_ports
from ostrich2 import Ostrich2


class App:
    def __init__(self, root):
        self.root = root
        root.title('Ostrich 2 • Memory programmer')
        root.geometry('880x850')
        root.minsize(800, 790)
        self.events = queue.Queue()
        self.busy = False
        self.controls = []
        self.ranges = []
        self.map_port = None
        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure('.', font=('Segoe UI', 10))
        style.configure('Title.TLabel', font=('Segoe UI', 23, 'bold'))
        style.configure('TButton', padding=(12, 7))
        outer = ttk.Frame(root, padding=24)
        outer.pack(fill='both', expand=True)
        ttk.Label(outer, text='Ostrich 2', style='Title.TLabel').pack(anchor='w')
        ttk.Label(outer, text='Read, back up and program your EPROM emulator.').pack(anchor='w', pady=(2, 18))
        connection = ttk.LabelFrame(outer, text='USB device', padding=12)
        connection.pack(fill='x')
        self.port = tk.StringVar(value=Ostrich2.default_device())
        self.ports = ttk.Combobox(connection, textvariable=self.port, width=18)
        self.ports.pack(side='left', padx=(0, 10))
        self.controls.append(self.ports)
        self.button(connection, 'Refresh ports', self.refresh).pack(side='left')
        self.button(connection, 'Check device', self.info).pack(side='right')
        self.button(connection, 'Read device', self.read_device).pack(side='right', padx=8)
        self.refresh()
        memory = ttk.LabelFrame(outer, text='Memory transfer', padding=14)
        memory.pack(fill='x', pady=16)
        self.start = tk.StringVar(value='0x0000')
        self.end = tk.StringVar(value='0x1fff')
        for row, (label, variable) in enumerate([('Start address', self.start), ('End address (inclusive)', self.end)]):
            ttk.Label(memory, text=label).grid(row=row, column=0, sticky='w', pady=5)
            entry = ttk.Entry(memory, textvariable=variable, width=20)
            entry.grid(row=row, column=1, sticky='w', padx=16, pady=5)
            self.controls.append(entry)
        ttk.Label(memory, text='Use hex (0x1000) or decimal. Writes start at the start address.').grid(row=2, column=0, columnspan=3, sticky='w', pady=(4, 12))
        self.button(memory, 'Read to file…', self.read_file).grid(row=3, column=0, sticky='w')
        self.button(memory, 'Write file to device…', self.write_file).grid(row=3, column=1, sticky='w', padx=16)
        self.button(memory, 'Erase range…', self.erase_range).grid(row=3, column=2, sticky='w')
        self.button(memory, 'Erase whole device…', self.erase_device).grid(row=4, column=0, columnspan=2, sticky='w', pady=(10, 0))
        bank_frame = ttk.Frame(outer)
        bank_frame.pack(fill='x')
        ttk.Label(bank_frame, text='Bank').pack(side='left')
        self.bank = tk.StringVar(value='0')
        bank_entry = ttk.Combobox(bank_frame, values=list(range(9)), textvariable=self.bank, width=4, state='readonly')
        bank_entry.pack(side='left', padx=10)
        self.controls.append(bank_entry)
        self.button(bank_frame, 'Apply bank', self.set_bank).pack(side='left')
        ttk.Label(bank_frame, text='Sets I/O and emulation bank; saved on device.').pack(side='left', padx=12)
        map_frame = ttk.LabelFrame(outer, text='Device memory • 512 KiB address space', padding=12)
        map_frame.pack(fill='x', pady=(16, 0))
        self.bank_status = tk.StringVar(value='Device banks: unknown — click Check device')
        ttk.Label(map_frame, textvariable=self.bank_status).pack(anchor='w')
        self.map = tk.Canvas(map_frame, height=54, background='#f0f3f7', highlightthickness=0)
        self.map.pack(fill='x', pady=6)
        self.map.bind('<Configure>', lambda event: self.draw_map())
        self.memory_status = tk.StringVar(value='Existing contents unknown. Blue = read; green = written this session.')
        ttk.Label(map_frame, textvariable=self.memory_status, wraplength=790).pack(anchor='w')
        self.locations = ttk.Treeview(map_frame, columns=('action', 'file', 'range', 'size', 'bank'), show='headings', height=3)
        for column, title, width in [('action', 'Operation', 85), ('file', 'File', 190), ('range', 'Device address (inclusive)', 210), ('size', 'Bytes', 85), ('bank', 'I/O bank', 65)]:
            self.locations.heading(column, text=title)
            self.locations.column(column, width=width)
        self.locations.pack(fill='x', pady=(8, 0))
        self.locations.bind('<<TreeviewSelect>>', self.select_range)
        self.status = tk.StringVar(value='Ready — select your device COM port.')
        ttk.Label(outer, textvariable=self.status).pack(anchor='w', pady=(16, 5))
        self.progress = ttk.Progressbar(outer, maximum=100)
        self.progress.pack(fill='x')
        self.log = tk.Text(outer, height=8, font=('Consolas', 10), state='disabled', wrap='word')
        self.log.pack(fill='both', expand=True, pady=(12, 0))
        self.append('Connect the Ostrich over USB, then click Check device.\nBack up memory before writing a file.')
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.after(80, self.poll)

    def button(self, parent, text, command):
        button = ttk.Button(parent, text=text, command=lambda: self.guard(command))
        self.controls.append(button)
        return button

    def guard(self, command):
        try:
            if not self.busy:
                command()
        except Exception as error:
            messagebox.showerror('Ostrich 2', str(error), parent=self.root)

    def refresh(self):
        self.ports['values'] = [p.device for p in list_ports.comports()]

    def append(self, text):
        self.log.configure(state='normal')
        self.log.insert('end', text + '\n')
        self.log.see('end')
        self.log.configure(state='disabled')

    def run(self, title, operation):
        port = self.port.get().strip()
        if not port:
            raise ValueError('Select or enter a COM port first.')
        if self.map_port != port:
            self.map_port = port
            self.ranges.clear()
            self.locations.delete(*self.locations.get_children())
            self.memory_status.set('Existing contents unknown. Blue = read; green = written this session.')
            self.bank_status.set('Device banks: unknown — click Check device')
            self.draw_map()
        self.busy = True
        self.status.set(title + '…')
        self.progress['value'] = 0
        for control in self.controls:
            control.state(['disabled'])
        def worker():
            try:
                device = Ostrich2(port)
                try:
                    result = operation(device)
                finally:
                    device.disconnect()
                self.events.put(('done', result))
            except Exception as error:
                self.events.put(('error', str(error)))
        threading.Thread(target=worker, daemon=True).start()

    def poll(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == 'progress':
                    self.progress['value'] = value
                    continue
                if kind == 'banks':
                    io, emu = value
                    self.bank_status.set(f'{self.map_port} • I/O bank: {io} • Emulation bank: {emu}')
                    continue
                if kind == 'memory':
                    self.record_memory(*value)
                    continue
                if kind == 'snapshot':
                    self.show_snapshot(*value)
                    continue
                self.busy = False
                for control in self.controls:
                    control.state(['!disabled'])
                if kind == 'done':
                    self.status.set('Completed')
                    self.progress['value'] = 100
                    self.append(value)
                else:
                    self.status.set('Operation failed — see details below.')
                    self.append('Error: ' + value)
                    messagebox.showerror('Operation failed', value, parent=self.root)
        except queue.Empty:
            pass
        self.root.after(80, self.poll)

    def info(self):
        def operation(device):
            typ, version, ident = device.version()
            vendor, serial = device.serial_number()
            io, emu = device.get_io_bank(), device.get_emulation_bank()
            self.events.put(('banks', (io, emu)))
            return (f'Device connected: type {typ}, version {version}, ID {ident}\n'
                    f'Vendor {vendor} • Serial {serial}\n'
                    f'I/O bank: {io} • Emulation bank: {emu}')
        self.run('Checking device', operation)

    def read_file(self):
        start, end = int(self.start.get(), 0), int(self.end.get(), 0)
        Ostrich2._validate_range(start, end)
        filename = filedialog.asksaveasfilename(parent=self.root, title='Save memory backup', defaultextension='.bin', filetypes=[('Binary file', '*.bin'), ('All files', '*.*')])
        if not filename:
            return
        def operation(device):
            # Save only a complete transfer; keep existing backup on failure.
            bank = device.get_io_bank()
            data = bytearray()
            for block in device.read_memory(start, end):
                data.extend(block)
                self.events.put(('progress', len(data) * 100 / (end - start + 1)))
            Path(filename).write_bytes(data)
            self.events.put(('memory', ('Read', filename, start, end, bank)))
            return f'Read {len(data):,} bytes to {filename}'
        self.run('Reading memory', operation)

    def read_device(self):
        def operation(device):
            bank = device.get_io_bank()
            # Bank 8 exposes all 512 KiB; banks 0–7 expose one 64 KiB window.
            size = 0x80000 if bank == 8 else 0x10000
            data = bytearray()
            for block in device.read_memory(0, size-1):
                data.extend(block)
                self.events.put(('progress', len(data)*100/size))
            if len(data) != size:
                raise IOError('Device returned incomplete memory data.')
            self.events.put(('snapshot', (bytes(data), bank)))
            self.events.put(('memory', ('Read', '(device snapshot)', 0, size-1, bank)))
            return f'Read device: {size:,} bytes from I/O bank {bank}. Opened memory viewer.'
        self.run('Reading device', operation)

    def show_snapshot(self, data, bank):
        window = tk.Toplevel(self.root)
        window.title(f'Ostrich memory • bank {bank} • {len(data):,} bytes')
        window.geometry('850x650')
        frame = ttk.Frame(window, padding=14)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text=f'I/O bank {bank} • 0x00000–0x{len(data)-1:05X} • {len(data):,} bytes read').pack(anchor='w')
        ff = data.count(255)
        ttk.Label(frame, text=f'FF bytes: {ff:,} • Other bytes: {len(data)-ff:,}. Raw contents do not identify tune names.').pack(anchor='w', pady=(4, 10))
        def save():
            filename = filedialog.asksaveasfilename(parent=window, title='Save device snapshot', initialfile=f'ostrich-bank-{bank}.bin', defaultextension='.bin', filetypes=[('Binary file', '*.bin'), ('All files', '*.*')])
            if filename:
                try:
                    Path(filename).write_bytes(data)
                except OSError as error:
                    messagebox.showerror('Save failed', str(error), parent=window)
        ttk.Button(frame, text='Save snapshot as BIN…', command=save).pack(anchor='w', pady=(0, 10))
        ttk.Label(frame, text='Address     Hex bytes                                         Text').pack(anchor='w')
        holder = ttk.Frame(frame)
        holder.pack(fill='both', expand=True)
        text = tk.Text(holder, wrap='none', font=('Consolas', 10))
        scroll = ttk.Scrollbar(holder, orient='vertical', command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        text.pack(side='left', fill='both', expand=True)
        lines = []
        for address in range(0, len(data), 16):
            block = data[address:address+16]
            ascii_text = ''.join(chr(b) if 32 <= b < 127 else '.' for b in block)
            lines.append(f'{address:05X}   {block.hex(" ").upper():47}   {ascii_text}')
        text.insert('1.0', '\n'.join(lines))
        text.configure(state='disabled')

    def write_file(self):
        start = int(self.start.get(), 0)
        filename = filedialog.askopenfilename(parent=self.root, title='Choose binary file to write', filetypes=[('Binary file', '*.bin'), ('All files', '*.*')])
        if not filename:
            return
        data = Path(filename).read_bytes()
        Ostrich2._validate_range(start, start + len(data) - 1)
        if start % 256 or len(data) % 256:
            raise ValueError('Start address and file size must be multiples of 256 bytes.')
        if not messagebox.askyesno('Write device memory?', f'Write {len(data):,} bytes from {Path(filename).name}\nto {self.port.get()} at {start:#x}?\n\nThis overwrites device memory. Make a backup first.', parent=self.root):
            return
        def operation(device):
            bank = device.get_io_bank()
            count = 0
            for size in device.write_memory(data, start):
                count += size
                self.events.put(('memory', ('Written', filename, start, start + count - 1, bank)))
                self.events.put(('progress', count * 100 / len(data)))
            return f'Wrote {count:,} bytes from {filename}'
        self.run('Writing memory', operation)

    def set_bank(self):
        bank = int(self.bank.get())
        if not 0 <= bank <= 8:
            raise ValueError('Bank must be between 0 and 8.')
        def operation(device):
            device.set_io_bank(bank)
            device.set_emulation_bank(bank, True)
            device.set_emulation_bank(bank, False)
            self.events.put(('banks', (device.get_io_bank(), device.get_emulation_bank())))
            return f'Applied bank {bank} for I/O and emulation.'
        self.run('Setting bank', operation)

    def erase_range(self):
        start, end = int(self.start.get(), 0), int(self.end.get(), 0)
        Ostrich2._validate_range(start, end)
        if start % 256 or (end + 1) % 256:
            raise ValueError('Erase requires complete 256-byte pages. Start must be a multiple of 256 and end must end in FF (for example 0x0000–0x1fff).')
        if not messagebox.askyesno('Erase device memory?',
                f'Overwrite {end-start+1:,} bytes at 0x{start:05X}–0x{end:05X}\non {self.port.get()} with FF bytes?\n\nThis removes the tune data in this range. Back it up first.\nDo not erase while the device is being used to run an engine.', parent=self.root):
            return
        def operation(device):
            bank = device.get_io_bank()
            data = b'\xff' * (end-start+1)
            count = 0
            for size in device.write_memory(data, start):
                count += size
                self.events.put(('memory', ('Erased', '(FF fill)', start, start+count-1, bank)))
                self.events.put(('progress', count * 100 / len(data)))
            # Confirm the full range before reporting a successful erase.
            offset = 0
            for block in device.read_memory(start, end):
                if block != data[offset:offset+len(block)]:
                    raise IOError('Erase verification failed. Device contents may be partially erased.')
                offset += len(block)
            if offset != len(data):
                raise IOError('Erase verification returned an incomplete range.')
            return f'Erased and verified 0x{start:05X}–0x{end:05X} ({len(data):,} bytes), I/O bank {bank}.'
        self.run('Erasing memory', operation)

    def select_range(self, event=None):
        if self.busy:
            return
        selected = self.locations.selection()
        if not selected:
            return
        record = next((r for r in self.ranges if r['item'] == selected[0]), None)
        if record:
            self.start.set(f'0x{record["start"]:05X}')
            self.end.set(f'0x{record["end"]:05X}')

    def erase_device(self):
        if not messagebox.askyesno('Erase the whole Ostrich?',
                f'Erase ALL 512 KiB on {self.port.get()}, across every memory bank?\n\nAll tunes will be overwritten with FF bytes. Back up first.\nDo not proceed while the device is running an engine.', parent=self.root):
            return
        def operation(device):
            original_bank = device.get_io_bank()
            primary_error = None
            try:
                # Bank 8 enables the full address space; emulation banks stay unchanged.
                device.set_io_bank(8)
                if device.get_io_bank() != 8:
                    raise IOError('Could not select full-memory I/O mode. Erase was not started.')
                size = 0x80000
                data = b'\xff' * size
                count = 0
                for written in device.write_memory(data, 0):
                    count += written
                    self.events.put(('memory', ('Erased', '(whole-device FF fill)', 0, count-1, 8)))
                    self.events.put(('progress', count * 50 / size))
                verified = 0
                for block in device.read_memory(0, size-1):
                    if block != b'\xff' * len(block):
                        raise IOError(f'Erase verification failed near 0x{verified:05X}. Memory may be partially erased.')
                    verified += len(block)
                    self.events.put(('progress', 50 + verified * 50 / size))
                if verified != size:
                    raise IOError('Erase verification returned incomplete memory.')
            except Exception as error:
                primary_error = error
                raise
            finally:
                try:
                    device.set_io_bank(original_bank)
                    if device.get_io_bank() != original_bank:
                        raise IOError('Bank readback did not match.')
                except Exception as restore_error:
                    raise IOError(f'{str(primary_error) + "; " if primary_error else ""}Could not restore I/O bank {original_bank}: {restore_error}') from restore_error
            return f'Whole device erased and verified: 524,288 bytes (512 KiB). I/O bank {original_bank} restored.'
        self.run('Erasing and verifying whole device', operation)

    def record_memory(self, action, filename, start, end, bank):
        # Show acknowledged bytes, including partial writes if a later block fails.
        if action == 'Erased':
            erase_base = 0 if bank == 8 else bank * 0x10000
            erase_start, erase_end = erase_base + start, erase_base + end
            retained = []
            for record in self.ranges:
                old_action, old_file, _, old_bank = record['key']
                base = 0 if old_bank == 8 else old_bank * 0x10000
                lo, hi = base + record['start'], base + record['end']
                if hi < erase_start or lo > erase_end:
                    retained.append(record)
                    continue
                self.locations.delete(record['item'])
                # Preserve portions outside the erased physical range.
                for left, right in [(lo, min(hi, erase_start-1)), (max(lo, erase_end+1), hi)]:
                    if left <= right:
                        local_start, local_end = left-base, right-base
                        item = self.locations.insert('', 0, values=(old_action, Path(old_file).name, f'0x{local_start:05X} – 0x{local_end:05X}', f'{right-left+1:,}', old_bank))
                        retained.append(dict(key=(old_action, old_file, local_start, old_bank), start=local_start, end=local_end, action=old_action, item=item))
            self.ranges = retained
        key = (action, filename, start, bank)
        previous = next((r for r in self.ranges if r['key'] == key), None)
        if previous:
            previous['end'] = end
            self.locations.item(previous['item'], values=(action, Path(filename).name, f'0x{start:05X} – 0x{end:05X}', f'{end-start+1:,}', bank))
        else:
            item = self.locations.insert('', 0, values=(action, Path(filename).name, f'0x{start:05X} – 0x{end:05X}', f'{end-start+1:,}', bank))
            self.ranges.append(dict(key=key, start=start, end=end, action=action, item=item))
        self.memory_status.set(f'{action}: {Path(filename).name} • 0x{start:05X}–0x{end:05X} • {end-start+1:,} bytes • I/O bank {bank}\nHistory for this session; existing contents and later external changes are unknown.')
        if action == 'Erased' and bank == 8 and start == 0 and end == 0x7ffff:
            self.memory_status.set('Whole device overwritten with FF • 512 KiB • No loaded tune remains.\nReadback verification must finish before the erase is reported complete.')
        self.draw_map()

    def draw_map(self):
        self.map.delete('all')
        width = max(100, self.map.winfo_width()) - 12
        self.map.create_rectangle(6, 3, width, 26, fill='#d7dce4', outline='')
        for record in self.ranges:
            bank = record['key'][3]
            base = 0 if bank == 8 else bank * 0x10000
            x1 = 6 + (width-6) * (base + record['start']) / 0x80000
            x2 = 6 + (width-6) * (base + record['end']+1) / 0x80000
            color = {'Written': '#258655', 'Read': '#2879b9', 'Erased': '#bd641e'}[record['action']]
            self.map.create_rectangle(x1, 3, max(x1+2, x2), 26, fill=color, outline='')
        self.map.create_text(6, 42, text='0x00000', anchor='w')
        self.map.create_text(width, 42, text='0x7FFFF', anchor='e')

    def close(self):
        if self.busy:
            messagebox.showinfo('Transfer in progress', 'Wait for the current operation to finish before closing.', parent=self.root)
        else:
            self.root.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    App(root)
    root.mainloop()
