from serial import Serial
import platform
import glob

def make_checksum(data):
    return sum(data) & 0xff

def chunks(data, size):
    return [data[i:i + size] for i in range(0, len(data), size)]

class Ostrich2(object):

    def __init__(self, device):
        self.channel = Serial(device, 921600, timeout = 5, write_timeout = 5)
        self.channel.reset_input_buffer()


    def disconnect(self):
        '''
        '''
        self.channel.close()

    @staticmethod
    def default_device():
        if platform.system() == 'Windows':
            return 'COM3'
        elif platform.system() == 'Darwin':
            serial_devices = glob.glob('/dev/tty.usbserial-*')
            return serial_devices[0] if len(serial_devices) else '?'
        else:
            return '/dev/ttyUSB0'

    ###########################################################################
    ##
    ## IO operations
    ##
    ###########################################################################

    def write(self, data):
        '''
        Write a sequence of bytes
        '''
        if isinstance(data, int):
            data = bytes((data,))
        result = self.channel.write(data)
        if result != len(data):
            raise Exception('write timeout')
        self.channel.flush()

    def write_with_checksum(self, data):
        self.write(bytes(data) + bytes((make_checksum(data),)))

    def read_with_checksum(self, size, prefix=b''):
        data = self.read(size)
        checksum = self.read_byte()
        expected = make_checksum(prefix + data)
        if checksum != expected:
            raise IOError(f'Read checksum does not match ({size} bytes: expected 0x{expected:02X}, received 0x{checksum:02X})')
        return data

    def read(self, size = 1):
        '''
        Read a sequence of bytes
        '''
        if size == 0:
            return b''

        result = self.channel.read(size)
        if len(result) != size:
            raise Exception('I/O error')
        return result

    def read_byte(self):
        '''
        Read a single byte
        '''
        return int(self.read()[0])

    ##
    ## Protocol
    ##

    def version(self):
        self.write(b'VV')
        device_type = self.read_byte()
        version = self.read_byte()
        device_id = chr(self.read_byte())
        return (device_type, version, device_id)

    def serial_number(self):
        '''
        returns (vendor ID, serial number)
        '''
        self.write_with_checksum(b'NS')
        result = self.read_with_checksum(9, prefix=b'NS')
        vendor_id = int(result[0])
        serial_number = result[1:].hex()
        return (vendor_id, serial_number)

    def write_memory(self, data, start_address, chunk_size = 0x1000):
        self._validate_range(start_address, start_address + len(data) - 1)
        self._validate_chunk(chunk_size)
        if (len(data) & 0xff) or (start_address & 0xff):
            raise Exception('Can only write 0x0100 byte blocks')

        for address in range(start_address, start_address + len(data), chunk_size):
                offset = address - start_address
                block = data[offset:offset + chunk_size]
                block_count = len(block) >> 8
                mmsb = (address >> 16) & 0x07
                msb = (address >> 8) & 0xff

                message = bytearray(b'ZW')
                message += bytes((block_count,))
                message += bytes((mmsb,))
                message += bytes((msb,))
                message += block
                self.write_with_checksum(message)
                self.expect_ok()
                yield len(block)

    def read_memory(self, start, end, chunk_size = 0x1000):
        self._validate_range(start, end)
        self._validate_chunk(chunk_size)
        read_start = start & ~0xff
        read_end = (end | 0xff) + 1
        for address in range(read_start, read_end, chunk_size):
            size = min(chunk_size, read_end - address)
            message = b'ZR' + bytes((size >> 8, (address >> 16) & 7, (address >> 8) & 255))
            self.write_with_checksum(message)
            data = self.read_with_checksum(size)
            yield data[max(0, start - address):min(size, end + 1 - address)]

    @staticmethod
    def _validate_range(start, end):
        if not 0 <= start <= end < 0x80000:
            raise ValueError('Memory range must be within 0x00000..0x7ffff, with start <= end')

    @staticmethod
    def _validate_chunk(size):
        if size < 256 or size > 0xff00 or size % 256:
            raise ValueError('Chunk size must be a multiple of 256 between 256 and 65280')

    def expect_ok(self):
        response = self.read()
        if response != b'O':
            raise Exception('Write error')

    def set_io_bank(self, bank):
        message = bytearray(b'BR')
        message += bytes((bank,))
        self.write_with_checksum(message)
        self.expect_ok()

    def get_io_bank(self):
        self.write_with_checksum(b'BRR')
        return self.read_byte()

    def set_emulation_bank(self, bank, persistent = False):
        if persistent:
            message = bytearray(b'BS')
        else:
            message = bytearray(b'BE')
        message += bytes((bank,))
        self.write_with_checksum(message)
        self.expect_ok()

    def get_emulation_bank(self, persistent = False):
        if persistent:
            message = b'BES'
        else:
            message = b'BER'
        self.write_with_checksum(message)
        return self.read_byte()
