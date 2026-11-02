import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
import tkinter as tk
from ostrich_gui import App

class FakeDevice:
    fail = False
    closed = False
    written = None
    def __init__(self, port):
        if self.fail:
            raise OSError('Port unavailable')
    def disconnect(self): FakeDevice.closed = True
    def get_io_bank(self): return 0
    def read_memory(self, start, end): yield b'x' * (end-start+1)
    def write_memory(self, data, start):
        FakeDevice.written = (data, start)
        yield len(data)

class GuiTests(unittest.TestCase):
    def test_full_erase_removes_loaded_ranges_in_every_bank(self):
        self.app.record_memory('Written', 'tune.bin', 0xc000, 0xffff, 3)
        self.app.record_memory('Erased', '(whole-device FF fill)', 0, 0x7ffff, 8)
        self.assertEqual(len(self.app.ranges), 1)
        self.assertEqual(self.app.ranges[0]['action'], 'Erased')
        self.assertNotIn('tune.bin', str([self.app.locations.item(i)['values'] for i in self.app.locations.get_children()]))
    def test_partial_erase_keeps_unaffected_loaded_bytes(self):
        self.app.record_memory('Written', 'tune.bin', 0, 0xfff, 2)
        self.app.record_memory('Erased', '(FF fill)', 0x400, 0x7ff, 2)
        written = [(r['start'], r['end']) for r in self.app.ranges if r['action'] == 'Written']
        self.assertEqual(written, [(0, 0x3ff), (0x800, 0xfff)])
    def test_erase_does_not_clear_other_bank(self):
        self.app.record_memory('Written', 'tune.bin', 0, 0xfff, 2)
        self.app.record_memory('Erased', '(FF fill)', 0, 0xffff, 1)
        self.assertTrue(any(r['action'] == 'Written' for r in self.app.ranges))
    def setUp(self):
        self.root = tk.Tk()
        self.app = App(self.root)
        self.root.update()
        FakeDevice.fail = False
        FakeDevice.closed = False
    def tearDown(self):
        for callback in self.root.tk.call('after', 'info'):
            self.root.after_cancel(callback)
        self.root.destroy()
    def finish(self):
        limit = time.monotonic() + 3
        while self.app.busy and time.monotonic() < limit:
            self.root.update()
            time.sleep(.01)
        self.assertFalse(self.app.busy)
    def test_read_write_and_disconnect(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp)/'backup.bin')
            with patch('ostrich_gui.Ostrich2', FakeDevice), patch.object(FakeDevice, '_validate_range', create=True), patch('ostrich_gui.filedialog.asksaveasfilename', return_value=path):
                self.app.read_file()
                self.finish()
            self.assertEqual(Path(path).read_bytes(), b'x' * 8192)
            self.assertTrue(FakeDevice.closed)
            with patch('ostrich_gui.Ostrich2', FakeDevice), patch.object(FakeDevice, '_validate_range', create=True), patch('ostrich_gui.filedialog.askopenfilename', return_value=path), patch('ostrich_gui.messagebox.askyesno', return_value=True):
                self.app.write_file()
                self.finish()
            self.assertEqual(FakeDevice.written, (b'x' * 8192, 0))
            self.assertEqual(self.app.ranges[-1]['end'], 8191)
            self.assertIn('Written: backup.bin', self.app.memory_status.get())
    def test_connection_error_restores_buttons(self):
        FakeDevice.fail = True
        with patch('ostrich_gui.Ostrich2', FakeDevice), patch('ostrich_gui.messagebox.showerror') as error:
            self.app.info()
            self.finish()
            error.assert_called_once()
        self.assertTrue(all('disabled' not in c.state() for c in self.app.controls))
    def test_memory_history_updates_partial_range_and_clears_on_port_change(self):
        self.app.record_memory('Written', 'test.bin', 0x1000, 0x1fff, 2)
        self.app.record_memory('Written', 'test.bin', 0x1000, 0x2fff, 2)
        self.assertEqual(len(self.app.ranges), 1)
        self.assertEqual(self.app.ranges[0]['end'], 0x2fff)
        self.assertIn('I/O bank 2', self.app.memory_status.get())
        self.app.port.set('COM99')
        with patch('ostrich_gui.Ostrich2', FakeDevice):
            self.app.run('Test', lambda device: 'Done')
            self.finish()
        self.assertEqual(self.app.ranges, [])
    def test_erase_writes_ff_and_verifies(self):
        def read_erased(device, start, end):
            yield b'\xff' * (end-start+1)
        with patch('ostrich_gui.Ostrich2', FakeDevice), patch.object(FakeDevice, '_validate_range', create=True), patch.object(FakeDevice, 'read_memory', read_erased), patch('ostrich_gui.messagebox.askyesno', return_value=True):
            self.app.erase_range()
            self.finish()
        self.assertEqual(FakeDevice.written, (b'\xff' * 8192, 0))
        self.assertEqual(self.app.ranges[-1]['action'], 'Erased')
        self.assertTrue(FakeDevice.closed)
    def test_erase_cancel_does_not_connect(self):
        with patch('ostrich_gui.messagebox.askyesno', return_value=False), patch('ostrich_gui.Ostrich2', wraps=__import__('ostrich2').Ostrich2) as device:
            self.app.erase_range()
            device.assert_not_called()
    def test_erase_unaligned_rejected(self):
        self.app.start.set('1')
        with self.assertRaises(ValueError): self.app.erase_range()
    def test_read_device_opens_snapshot_without_file_dialog(self):
        with patch('ostrich_gui.Ostrich2', FakeDevice), patch.object(self.app, 'show_snapshot') as viewer, patch('ostrich_gui.filedialog.asksaveasfilename') as save:
            self.app.read_device()
            self.finish()
            viewer.assert_called_once_with(b'x' * 65536, 0)
            save.assert_not_called()
        self.assertTrue(FakeDevice.closed)
    def test_whole_device_erase_and_bank_restore(self):
        class WholeDevice(FakeDevice):
            bank = 3
            changes = []
            def get_io_bank(self): return self.bank
            def set_io_bank(self, bank):
                self.bank = bank
                self.changes.append(bank)
            def read_memory(self, start, end):
                self_test.assertEqual((start, end), (0, 0x7ffff))
                yield b'\xff' * 0x80000
        self_test = self
        with patch('ostrich_gui.Ostrich2', WholeDevice), patch('ostrich_gui.messagebox.askyesno', return_value=True):
            self.app.erase_device()
            self.finish()
        self.assertEqual(FakeDevice.written, (b'\xff' * 0x80000, 0))
        self.assertEqual(WholeDevice.changes, [8, 3])
    def test_whole_device_cancel(self):
        with patch('ostrich_gui.Ostrich2') as device, patch('ostrich_gui.messagebox.askyesno', return_value=False):
            self.app.erase_device()
            device.assert_not_called()
    def test_whole_erase_failure_restores_bank(self):
        class BrokenDevice(FakeDevice):
            bank = 2
            changes = []
            def get_io_bank(self): return self.bank
            def set_io_bank(self, bank):
                self.bank = bank
                self.changes.append(bank)
            def write_memory(self, data, start):
                raise IOError('USB disconnected')
                yield 0
        with patch('ostrich_gui.Ostrich2', BrokenDevice), patch('ostrich_gui.messagebox.askyesno', return_value=True), patch('ostrich_gui.messagebox.showerror') as error:
            self.app.erase_device()
            self.finish()
            error.assert_called_once()
        self.assertEqual(BrokenDevice.changes, [8, 2])
        self.assertTrue(FakeDevice.closed)

if __name__ == '__main__': unittest.main()
