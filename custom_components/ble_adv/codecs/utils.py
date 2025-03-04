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
