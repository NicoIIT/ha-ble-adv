"""Smart Light Remote codecs.

Implements the BLE advertisement protocol used by Smart Light (Agarce) physical
remotes for ceiling fan/light controllers (e.g. Revneey).

Protocol details (derived from issue #191):

Packet format (26 bytes raw):
    [0x19, 0xFF]   BLE type header (manufacturer specific, length=0x19=25)
    [0xF9, 0x09]   Manufacturer ID / header
    [prefix]       0x03 or 0x04 (remote version identifier)
    [seed0..3]     4-byte random seed
    [enc0..15]     16-byte encrypted payload
    [checksum]     1-byte checksum = sum(all prior bytes) & 0xFF

Encryption:
    XOR_MATRIX = [0xAA, 0xBB, 0xCC, 0xDD, 0x5A, 0xA5, 0xA5, 0x5A]
    pivot = [seed0, seed1, seed2, seed3, seed3, seed2, seed1, seed0]
    encrypted[i] = decrypted[i] ^ pivot[i%8] ^ XOR_MATRIX[i%8]

Decrypted payload (16 bytes):
    [0]     tx_count
    [1]     app_restart_count
    [2-3]   reserved (0x00, 0x00)
    [4-9]   6-byte device ID
    [10]    reserved (0x00)
    [11]    command code
    [12]    rolling code (UNKNOWN - varies with tx, cmd, id)
    [13]    index (0xFF for remote)
    [14]    previous state byte (mostly 0x00)
    [15]    inner checksum = sum(bytes 0-14) & 0xFF

Command codes (remote):
    0x03: Brightness up
    0x04: Brightness down
    0x05: Color temperature up (colder)
    0x06: Color temperature down (warmer)
    0x07: Night light mode (moon/star)
    0x09: Full warm+cold (K button)
    0x0B: Light toggle (on/off)
    0x3C-0x41: Fan speed 1-6
    0x42: Fan off / Pair
    0x45: Fan breeze preset
    0x47: Fan forward direction
    0x48: Fan reverse direction
    0x4A: Timer (2H)
    0x4E: All off (device off)
    0x52: Fan oscillation
"""

from typing import ClassVar

from .const import (
    ATTR_CMD,
    ATTR_CMD_BR_DOWN,
    ATTR_CMD_BR_UP,
    ATTR_CMD_CT_DOWN,
    ATTR_CMD_CT_UP,
    ATTR_CMD_PAIR,
    ATTR_CMD_TIMER,
    ATTR_CMD_TOGGLE,
    ATTR_COLD,
    ATTR_DIR,
    ATTR_ON,
    ATTR_OSC,
    ATTR_PRESET,
    ATTR_PRESET_BREEZE,
    ATTR_SPEED,
    ATTR_STEP,
    ATTR_TIME,
    ATTR_WARM,
)
from .models import (
    BleAdvCodec,
    BleAdvConfig,
    BleAdvEncCmd,
    CTLightCmd,
    DeviceCmd,
    Fan6SpeedCmd,
    FanCmd,
    LightCmd,
    Trans,
)
from .models import EncoderMatcher as EncCmd


class SmartLightRemoteEncoder(BleAdvCodec):
    """Smart Light Remote encoder/decoder.

    Handles the 19FF F909 03/04 protocol used by physical remotes
    for Smart Light (Agarce) ceiling fan/light controllers.
    """

    duration: int = 400
    interval: int = 10
    repeat: int = 60
    _len = 22  # payload bytes after header (prefix[1] + seed[4] + encrypted[16] + checksum[1])
    _seed_max = 0xFFFFFFFF

    MATRIX: ClassVar[list[int]] = [0xAA, 0xBB, 0xCC, 0xDD, 0x5A, 0xA5, 0xA5, 0x5A]

    def _make_pivot(self, seed_bytes: bytes) -> list[int]:
        """Build the 8-byte pivot matrix from 4 seed bytes."""
        return [*seed_bytes, *reversed(seed_bytes)]

    def _crypt(self, buffer: bytes, seed_bytes: bytes) -> bytearray:
        """XOR encrypt/decrypt buffer using seed-derived pivot and MATRIX."""
        pivot = self._make_pivot(seed_bytes)
        return bytearray(x ^ pivot[i % 8] ^ self.MATRIX[i % 8] for i, x in enumerate(buffer))

    def decrypt(self, buffer: bytes) -> bytes | None:
        """Decrypt / unwhiten an incoming raw buffer into a readable buffer.

        buffer layout (after header strip):
            [prefix_byte] [seed0..3] [encrypted0..15] [outer_checksum]
        """
        # Outer checksum validation: includes the sum of prefix/seed/encrypted bytes
        # plus the prepended length (0x19), type (0xFF), and header (0xF9, 0x09) bytes.
        # sum([0x19, 0xFF, 0xF9, 0x09]) & 0xFF = 0x1A.
        if not self.is_eq((0x1A + sum(buffer[:-1])) & 0xFF, buffer[-1], "Outer Checksum"):
            return None

        seed_bytes = buffer[1:5]  # after prefix byte
        encrypted = buffer[5:-1]  # 16 encrypted bytes

        decoded = self._crypt(encrypted, seed_bytes)

        # Inner checksum: sum of decoded[0:15] & 0xFF == decoded[15]
        if not self.is_eq(sum(decoded[:-1]) & 0xFF, decoded[-1], "Inner Checksum"):
            return None

        # Return prefix + seed + decoded (without inner checksum) as readable buffer
        return bytes([buffer[0], *seed_bytes, *decoded[:-1]])

    def encrypt(self, buffer: bytes) -> bytes:
        """Encrypt / whiten a readable buffer.

        buffer layout (from convert_from_enc, with prefix prepended by framework):
            [prefix_byte] [seed0..3] [decoded0..14]
        Output:
            [prefix_byte] [seed0..3] [encrypted0..15] [outer_checksum]
        """
        prefix = buffer[0]
        seed_bytes = buffer[1:5]
        decoded_payload = bytearray(buffer[5:])

        # Append inner checksum
        decoded_payload.append(sum(decoded_payload) & 0xFF)

        # Encrypt
        encrypted = self._crypt(bytes(decoded_payload), seed_bytes)

        # Build output: prefix + seed + encrypted
        result = bytearray([prefix, *seed_bytes, *encrypted])

        # Append outer checksum including the 0x1A offset for the header bytes
        result.append((0x1A + sum(result)) & 0xFF)
        return bytes(result)

    def convert_to_enc(self, decoded: bytes) -> tuple[BleAdvEncCmd | None, BleAdvConfig | None]:
        """Convert a readable buffer into an encoder command and a config.

        decoded layout (after decrypt):
            [seed0..3] [tx_count] [app_restart_count] [0x00] [0x00]
            [id0..5] [0x00] [cmd_code] [rolling_code] [index] [prev_state]
        """
        seed_bytes = decoded[0:4]

        conf = BleAdvConfig()
        conf.tx_count = decoded[4]
        conf.app_restart_count = decoded[5]
        conf.id = int.from_bytes(decoded[8:14], "little")
        conf.index = decoded[18]  # typically 0xFF
        conf.seed = int.from_bytes(seed_bytes, "little")

        enc_cmd = BleAdvEncCmd(decoded[15])  # command code
        enc_cmd.param = decoded[16]  # rolling code (UNKNOWN)
        enc_cmd.arg0 = decoded[17]  # index byte (0xFF)
        enc_cmd.arg1 = decoded[18]  # prev_state byte

        return enc_cmd, conf

    def convert_from_enc(self, enc_cmd: BleAdvEncCmd, conf: BleAdvConfig) -> bytes:
        """Convert an encoder command and a config into a readable buffer."""
        uid = conf.id.to_bytes(6, "little")
        seed_bytes = conf.seed.to_bytes(4, "little")

        # The rolling code uses an XOR combination of tx_count and command code.
        rolling_code = (conf.tx_count ^ enc_cmd.cmd) & 0xFF

        return bytes(
            [
                *seed_bytes,
                conf.tx_count,
                conf.app_restart_count,
                0x00,
                0x00,
                *uid,
                0x00,
                enc_cmd.cmd,
                rolling_code,
                0xFF,  # index
                enc_cmd.arg1,  # prev_state (usually 0)
            ]
        )


# Command translations for the Smart Light Remote
# These map between encoder commands and HA entity attributes

TRANS = [
    # Light commands
    Trans(LightCmd().act(ATTR_ON, True), EncCmd(0x11)),  # Toggle acts as Turn On
    Trans(LightCmd().act(ATTR_ON, False), EncCmd(0x11)),  # Toggle acts as Turn Off
    Trans(LightCmd().act(ATTR_CMD, ATTR_CMD_TOGGLE), EncCmd(0x11)).no_direct(),
    Trans(CTLightCmd().act(ATTR_CMD, ATTR_CMD_BR_UP).eq(ATTR_STEP, 0.1), EncCmd(0x03)).no_direct(),
    Trans(CTLightCmd().act(ATTR_CMD, ATTR_CMD_BR_DOWN).eq(ATTR_STEP, 0.1), EncCmd(0x04)).no_direct(),
    Trans(CTLightCmd().act(ATTR_CMD, ATTR_CMD_CT_DOWN).eq(ATTR_STEP, 0.1), EncCmd(0x05)).no_direct(),  # K+ = colder = CT down
    Trans(CTLightCmd().act(ATTR_CMD, ATTR_CMD_CT_UP).eq(ATTR_STEP, 0.1), EncCmd(0x06)).no_direct(),  # K- = warmer = CT up
    Trans(CTLightCmd().act(ATTR_COLD, 1.0).act(ATTR_WARM, 1.0), EncCmd(0x09)),  # K button: full warm+cold
    Trans(CTLightCmd().act(ATTR_ON, True).act(ATTR_COLD, 0.1).act(ATTR_WARM, 0.1), EncCmd(0x07)),  # Night light
    # Device commands
    Trans(DeviceCmd().act(ATTR_ON, False), EncCmd(0x4E)),  # All off
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_TIMER).eq(ATTR_TIME, 7200), EncCmd(0x4A)),  # 2H Timer
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_PAIR), EncCmd(0x42)),  # Pair/Fan off
    # Fan speed commands (fan speed 1-6, codes 0x3C-0x41)
    Trans(Fan6SpeedCmd().act(ATTR_ON, True).act(ATTR_SPEED, 1.0), EncCmd(0x3C)),
    Trans(Fan6SpeedCmd().act(ATTR_ON, True).act(ATTR_SPEED, 2.0), EncCmd(0x3D)),
    Trans(Fan6SpeedCmd().act(ATTR_ON, True).act(ATTR_SPEED, 3.0), EncCmd(0x3E)),
    Trans(Fan6SpeedCmd().act(ATTR_ON, True).act(ATTR_SPEED, 4.0), EncCmd(0x3F)),
    Trans(Fan6SpeedCmd().act(ATTR_ON, True).act(ATTR_SPEED, 5.0), EncCmd(0x40)),
    Trans(Fan6SpeedCmd().act(ATTR_ON, True).act(ATTR_SPEED, 6.0), EncCmd(0x41)),
    # Fan control commands
    Trans(FanCmd().act(ATTR_ON, False), EncCmd(0x42)),  # Fan off
    Trans(FanCmd().act(ATTR_DIR, True), EncCmd(0x47)),  # Forward
    Trans(FanCmd().act(ATTR_DIR, False), EncCmd(0x48)),  # Reverse
    Trans(FanCmd().act(ATTR_PRESET, ATTR_PRESET_BREEZE), EncCmd(0x45)),  # Breeze
    Trans(FanCmd().act(ATTR_OSC, True), EncCmd(0x52)),  # Oscillation
]


CODECS = [
    SmartLightRemoteEncoder().id("smartlight_remote_v3").header([0xF9, 0x09]).prefix([0x03]).ble(0x00, 0xFF).add_translators(TRANS),
    SmartLightRemoteEncoder().id("smartlight_remote_v4").header([0xF9, 0x09]).prefix([0x04]).ble(0x00, 0xFF).add_translators(TRANS),
]
