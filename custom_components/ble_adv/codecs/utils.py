"""Utils for codecs."""


def whiten(buffer: bytes, seed: int) -> bytes:
    """Whiten / Unwiten buffer with seed."""
    obuf = []
    r = seed
    for val in buffer:
        b = 0
        for j in range(8):
            r <<= 1
            if r & 0x80:
                r ^= 0x11
                b |= 1 << j
            r &= 0x7F
        obuf.append(val ^ b)
    return bytes(obuf)


def reverse_byte(x: int) -> int:
    """Reverse a single byte: 1100 1010 => 0101 0011."""
    x = ((x & 0x55) << 1) | ((x & 0xAA) >> 1)
    x = ((x & 0x33) << 2) | ((x & 0xCC) >> 2)
    return ((x & 0x0F) << 4) | ((x & 0xF0) >> 4)


def reverse_all(buffer: bytes) -> bytes:
    """Reverse All bytes in buffer."""
    return bytes([reverse_byte(x) for x in buffer])


def crc16_le(buffer: bytes, seed: int, poly: int = 0x8408, ref_in: bool = True, ref_out: bool = True) -> int:
    """CRC16 ISO14443AB computing."""
    crc = seed if not ref_in else seed ^ 0xFFFF
    for byte in buffer:
        crc = crc ^ byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ poly
            else:
                crc = crc >> 1
    return crc if not ref_out else crc ^ 0xFFFF
