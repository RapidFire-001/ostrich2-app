import unittest
from ostrich2 import Ostrich2, make_checksum

class Channel:
    def __init__(self, response=b''):
        self.response = response
        self.sent = bytearray()
    def write(self, data):
        self.sent.extend(data)
        return len(data)
    def flush(self): pass
    def read(self, size):
        data, self.response = self.response[:size], self.response[size:]
        return data

def device(response):
    d = Ostrich2.__new__(Ostrich2)
    d.channel = Channel(response)
    return d

class ProtocolTests(unittest.TestCase):
    def test_serial_checksum_includes_command(self):
        payload = bytes([0, 1, 2, 3, 4, 5, 6, 7, 8])
        d = device(payload + bytes([make_checksum(b'NS' + payload)]))
        self.assertEqual(d.serial_number(), (0, '0102030405060708'))
    def test_serial_corruption_rejected(self):
        with self.assertRaises(IOError): device(bytes(9) + b'\x00').serial_number()
    def test_unaligned_read_and_final_page(self):
        payload = bytes(range(256)) * 2
        d = device(payload + bytes([make_checksum(payload)]))
        self.assertEqual(b''.join(d.read_memory(0x10, 0x101)), payload[0x10:0x102])
        self.assertEqual(d.channel.sent, b'ZR\x02\x00\x00' + bytes([make_checksum(b'ZR\x02\x00\x00')]))
    def test_multi_chunk_read(self):
        a, b = b'a' * 4096, b'b' * 256
        d = device(a + bytes([make_checksum(a)]) + b + bytes([make_checksum(b)]))
        self.assertEqual(b''.join(d.read_memory(0, 4096)), a + b'b')
        self.assertEqual(d.channel.sent[8], 1)
    def test_checksum_rejected(self):
        with self.assertRaises(IOError): device(b'abc\x00').read_with_checksum(3)
    def test_write_packet(self):
        d = device(b'O')
        payload = bytes(range(256))
        self.assertEqual(list(d.write_memory(payload, 0x100)), [256])
        packet = b'ZW\x01\x00\x01' + payload
        self.assertEqual(d.channel.sent, packet + bytes([make_checksum(packet)]))
    def test_invalid_ranges(self):
        for start, end in [(-1, 255), (256, 0), (0, 0x80000)]:
            with self.assertRaises(ValueError): list(device(b'').read_memory(start, end))
    def test_timeout(self):
        with self.assertRaises(Exception): device(b'').read(1)

if __name__ == '__main__': unittest.main()
