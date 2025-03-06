"""Models."""

import logging
from abc import ABC, abstractmethod
from binascii import hexlify
from typing import Any, Self

_LOGGER = logging.getLogger(__name__)

FAN_TYPE = "fan"
FAN_TYPE_3SPEED = "3speed"
FAN_TYPE_6SPEED = "6speed"

LIGHT_TYPE = "light"
LIGHT_TYPE_ONOFF = "onoff"
LIGHT_TYPE_RGB = "rgb"
LIGHT_TYPE_CWW = "cww"


def as_hex(buffer: bytes) -> bytes:
    """Represent hex buffer as 00.01.02 format."""
    return hexlify(buffer, ".").upper()


class BleAdvAdvertisement:
    """Model and Advertisement."""

    @classmethod
    def FromRaw(cls, raw_adv: bytes) -> Self | None:  # noqa: N802
        """Build an Advertisement from raw."""
        ble_type = 0x00
        rem_data = raw_adv
        while len(rem_data) > 2:
            part_len = rem_data[0]
            part_type = rem_data[1]
            if part_type in [0x03, 0x16, 0xFF]:
                ble_type = part_type
                raw_data = rem_data[2 : part_len + 1]
            rem_data = rem_data[part_len + 1 :]
        if ble_type == 0:
            return None
        return cls(ble_type, raw_data)

    def __init__(self, ble_type: int, raw: bytes, ad_flag: int = 0) -> None:
        self.ble_type: int = ble_type
        self.raw: bytes = raw
        self.ad_flag = ad_flag

    def __repr__(self) -> str:
        """Repr."""
        return f"Type: 0x{self.ble_type:02X}, raw: {'.'.join(f'{x:02X}' for x in self.raw)}"

    def __eq__(self, comp: Self) -> bool:
        return (self.ble_type == comp.ble_type) and (self.raw == comp.raw)

    def to_raw(self) -> bytes:
        """Get the raw buffer."""
        full_raw = bytearray([len(self.raw) + 1, self.ble_type]) + self.raw
        return full_raw if self.ad_flag == 0 else bytearray([0x02, 0x01, self.ad_flag]) + full_raw


class BleAdvEncCmd:
    """Ble ADV Encoder command."""

    def __init__(self, cmd: int) -> None:
        self.cmd = cmd
        self.param = 0
        self.arg0 = 0
        self.arg1 = 0
        self.arg2 = 0

    def __repr__(self) -> str:
        return f"cmd: 0x{self.cmd:02X}, param: 0x{self.param:02X}, args: [{self.arg0},{self.arg1},{self.arg2}]"


type AttrType = str | bool | int | float


class BleAdvEntAttr:
    """Ble Adv Entity Attributes."""

    def __init__(self, changed_attrs: list[str], attrs: dict[str, Any], base_type: str, index: int) -> None:
        self.chg_attrs: list[str] = changed_attrs
        self.attrs: dict[str, Any] = attrs
        self.base_type: str = base_type
        self.index: int = index

    @property
    def id(self) -> tuple[str, int]:
        """Entity ID."""
        return (self.base_type, self.index)

    def __repr__(self) -> str:
        return f"{self.base_type}_{self.index}: {self.chg_attrs} / {self.attrs}"

    def get_attr_as_float(self, attr: str) -> float:
        """Get attr as float."""
        return float(self.attrs[attr])


class BleAdvConfig:
    """Ble Adv Encoder Config."""

    def __init__(self, config_id: int = 0, index: int = 0) -> None:
        self.id: int = config_id
        self.index: int = index
        self.tx_count: int = 0
        self.seed: int = 0

    def __repr__(self) -> str:
        return f"id: 0x{self.id:08X}, index: {self.index}, tx: {self.tx_count}, seed: 0x{self.seed:04X}"


class CommonMatcher:
    """Matcher Base."""

    def __init__(self) -> None:
        self._eqs: dict[str, Any] = {}
        self._mins: dict[str, float] = {}
        self._maxs: dict[str, float] = {}

    def eq(self, attr: str, attr_val: AttrType) -> Self:
        """Force Entity to have attribute equal to this value."""
        self._eqs[attr] = attr_val
        return self

    def min(self, attr: str, attr_val: float) -> Self:
        """Force Entity to have attribute of maximum this value."""
        self._mins[attr] = attr_val
        return self

    def max(self, attr: str, attr_val: float) -> Self:
        """Force Entity to have attribute of minimum this value."""
        self._maxs[attr] = attr_val
        return self


class EntityMatcher(CommonMatcher):
    """Matcher for Entity."""

    def __init__(self, base_type: str, index: int, sub_type: str | None = None, enforced_sub_type: bool = True) -> None:
        super().__init__()
        self._base_type: str = base_type
        self._sub_type: str | None = sub_type
        self._index: int = index
        self._actions: list[str] = []
        if (sub_type is not None) and enforced_sub_type:
            self._eqs["type"] = sub_type

    def __repr__(self) -> str:
        return f"{self._base_type}_{self._index} / {self._actions}"

    def act(self, action: str, action_value: AttrType | None = None) -> Self:
        """Match Activity on given attribute, with value."""
        self._actions.append(action)
        return self.eq(action, action_value) if action_value is not None else self

    def matches(self, ent_attr: BleAdvEntAttr) -> bool:
        """Effective match for the incoming Enitity Attributes."""
        return (
            (self._base_type == ent_attr.base_type)
            and (self._index == ent_attr.index)
            and any(attr in ent_attr.chg_attrs for attr in self._actions)
            and all(ent_attr.attrs.get(attr) == val for attr, val in self._eqs.items())
            and all(ent_attr.attrs.get(attr) >= val for attr, val in self._mins.items())  # type: ignore[none]
            and all(ent_attr.attrs.get(attr) <= val for attr, val in self._maxs.items())  # type: ignore[none]
        )

    def create(self) -> BleAdvEntAttr:
        """Create Ble Adv Entity Features from self."""
        ent_attr: BleAdvEntAttr = BleAdvEntAttr(self._actions.copy(), self._eqs.copy(), self._base_type, self._index)
        return ent_attr

    def get_features(self) -> tuple[str, int, str | None]:
        """Get Features."""
        return (self._base_type, self._index, self._sub_type)


class FanCmd(EntityMatcher):
    """Specific Fan Base Matcher."""

    def __init__(self, index: int = 0) -> None:
        super().__init__(FAN_TYPE, index)


class Fan3SpeedCmd(EntityMatcher):
    """Specific 3 level speed Fan Matcher."""

    def __init__(self, index: int = 0) -> None:
        super().__init__(FAN_TYPE, index, FAN_TYPE_3SPEED)


class Fan6SpeedCmd(EntityMatcher):
    """Specific 6 level speed Fan Matcher."""

    def __init__(self, index: int = 0) -> None:
        super().__init__(FAN_TYPE, index, FAN_TYPE_6SPEED)


class LightCmd(EntityMatcher):
    """Specific Light Base Matcher."""

    def __init__(self, index: int = 0) -> None:
        super().__init__(LIGHT_TYPE, index, LIGHT_TYPE_ONOFF, False)


class RGBLightCmd(EntityMatcher):
    """Specific RGB Light Matcher."""

    def __init__(self, index: int = 0) -> None:
        super().__init__(LIGHT_TYPE, index, LIGHT_TYPE_RGB)


class CTLightCmd(EntityMatcher):
    """Specific RGB Light Matcher."""

    def __init__(self, index: int = 0) -> None:
        super().__init__(LIGHT_TYPE, index, LIGHT_TYPE_CWW)


class DeviceCmd(EntityMatcher):
    """Specific Device Matcher."""

    def __init__(self) -> None:
        super().__init__("device", 0)


class EncoderMatcher(CommonMatcher):
    """Specific Encoder Matcher."""

    def __init__(self, cmd: int) -> None:
        super().__init__()
        self._cmd: int = cmd

    def matches(self, enc_cmd: BleAdvEncCmd) -> bool:
        """Match with Encoder Attributes."""
        return (
            (enc_cmd.cmd == self._cmd)
            and all(getattr(enc_cmd, attr) == val for attr, val in self._eqs.items())
            and all(getattr(enc_cmd, attr) >= val for attr, val in self._mins.items())
            and all(getattr(enc_cmd, attr) <= val for attr, val in self._maxs.items())
        )

    def create(self) -> BleAdvEncCmd:
        """Create a Ble Adv Encoder Cmd from self."""
        enc_cmd: BleAdvEncCmd = BleAdvEncCmd(self._cmd)
        for eq_attr, eq_val in self._eqs.items():
            setattr(enc_cmd, eq_attr, eq_val)
        return enc_cmd


class Trans:
    """Base translator."""

    def __init__(self, ent: EntityMatcher, enc: EncoderMatcher) -> None:
        self.ent = ent
        self.enc = enc
        self._copies = []
        self._direct = True
        self._reverse = True
        self._sv = None

    def __repr__(self) -> str:
        return f"{self.ent} / {self.enc} / {self._copies}"

    def copy(self, attr_ent: str, attr_enc: str, factor: float = 1.0) -> Self:
        """Apply copy from attr_ent to attr_enc, with factor."""
        self._copies.append((attr_ent, attr_enc, factor))
        return self

    def split_value(self, src: str, dests: list[str], modulo: int = 256) -> Self:
        """Split the value in src iteratively to dests with each time applying a modulo."""
        self._sv = (src, dests, modulo)
        return self

    def no_direct(self) -> Self:
        """Do not consider this translator for direct translation."""
        self._direct = False
        return self

    def no_reverse(self) -> Self:
        """Do not consider this translator for reverse translation."""
        self._reverse = False
        return self

    def matches_ent(self, ent_attr: BleAdvEntAttr) -> bool:
        """Check if the translator matches the entity attributes."""
        return self._direct and self.ent.matches(ent_attr)

    def matches_enc(self, enc_cmd: BleAdvEncCmd) -> bool:
        """Check if the translator matches the encoder command."""
        return self._reverse and self.enc.matches(enc_cmd)

    def ent_to_enc(self, ent_attr: BleAdvEntAttr) -> BleAdvEncCmd:
        """Apply transformations to Encoder Attributes: direct."""
        enc_cmd = self.enc.create()
        for attr_ent, attr_enc, factor in self._copies:
            setattr(enc_cmd, attr_enc, int(factor * ent_attr.attrs.get(attr_ent)))
        if self._sv:
            val = getattr(enc_cmd, self._sv[0])
            for dest in self._sv[1]:
                setattr(enc_cmd, dest, val % self._sv[2])
                val = int(val / self._sv[2])
        return enc_cmd

    def enc_to_ent(self, enc_cmd: BleAdvEncCmd) -> BleAdvEntAttr:
        """Apply transformations to Entity Attributes: reverse."""
        ent_attr = self.ent.create()
        if self._sv:
            val = 0
            for dest in reversed(self._sv[1]):
                val = self._sv[2] * val + getattr(enc_cmd, dest)
            setattr(enc_cmd, self._sv[0], val)
        for attr_ent, attr_enc, factor in self._copies:
            ent_attr.attrs[attr_ent] = (1.0 / factor) * getattr(enc_cmd, attr_enc)
        return ent_attr


class BleAdvCodec(ABC):
    """Class representing a base encoder / decoder."""

    def __init__(self) -> None:
        self.codec_id: str | None = None
        self._header: bytearray = bytearray()
        self._ble_type: int = 0
        self._ad_flag: int = 0
        self._debug_mode: bool = False
        self._len: int = 0
        self._translators: list[Trans] = []

    @abstractmethod
    def decode(self, buffer: bytes) -> tuple[BleAdvEncCmd, BleAdvConfig]:
        """Decode an incoming raw buffer into an encoder command and a config."""

    @abstractmethod
    def encode(self, enc_cmd: BleAdvEncCmd, conf: BleAdvConfig) -> bytes:
        """Encode an encoder command and a config into an Advertisement."""

    def id(self, codec_id: str) -> Self:
        """Set id."""
        self.codec_id = codec_id
        return self

    def header(self, header: list[int]) -> Self:
        """Set header."""
        self._header = bytearray(header)
        return self

    def ble(self, ad_flag: int, ble_type: int) -> Self:
        """Set BLE param."""
        self._ad_flag = ad_flag
        self._ble_type = ble_type
        return self

    def add_translators(self, translators: list[Trans]) -> Self:
        """Add Translators."""
        self._translators.extend(translators)
        return self

    def get_features(self, base_type: str) -> list[Any]:
        """Get the featues supported by the translators."""
        capa: list[Any] = [None] * 3
        for trans in self._translators:
            (bt, ind, st) = trans.ent.get_features()
            if bt == base_type and st is not None:
                if capa[ind] is None:
                    capa[ind] = [st]
                elif st not in capa[ind]:
                    capa[ind].append(st)
        return capa

    def ent_to_enc(self, ent_attr: BleAdvEntAttr) -> list[BleAdvEncCmd]:
        """Convert Entity Attributes to list of Encoder Attributes."""
        return [trans.ent_to_enc(ent_attr) for trans in self._translators if trans.matches_ent(ent_attr)]

    def enc_to_ent(self, enc_cmd: BleAdvEncCmd) -> list[BleAdvEntAttr]:
        """Convert Encoder Attributes to list of Entity Attributes."""
        return [trans.enc_to_ent(enc_cmd) for trans in self._translators if trans.matches_enc(enc_cmd)]

    def decode_adv(self, adv: BleAdvAdvertisement) -> tuple[BleAdvEncCmd | None, BleAdvConfig | None]:
        """Decode Adv into Encoder Attributes / Config."""
        if not self.check_eq(self._ble_type, adv.ble_type, "BLE Type"):
            return None, None
        if not self.check_eq(self._len, len(adv.raw) - len(self._header), "Length"):
            return None, None
        if not self.check_eq_buf(self._header, adv.raw, "Header"):
            return None, None
        return self.decode(adv.raw[len(self._header) :])

    def encode_adv(self, enc_cmd: BleAdvEncCmd, conf: BleAdvConfig) -> BleAdvAdvertisement:
        """Encode an Encoder Attributes with Config into an Adv."""
        return BleAdvAdvertisement(self._ble_type, self._header + self.encode(enc_cmd, conf), self._ad_flag)

    def check_eq(self, ref: int, comp: int, msg: str) -> bool:
        """Check equal and log if not."""
        if ref != comp:
            if self._debug_mode:
                _LOGGER.debug(f"[{self.codec_id}] '{msg}' differs - expected: '0x{ref:X}', received: '0x{comp:X}'")
            return False
        return True

    def check_eq_buf(self, ref_buf: bytes, comp_buf: bytes, msg: str) -> bool:
        """Check buffer equal and log if not."""
        trunc_comp_buf = comp_buf[: len(ref_buf)]
        if trunc_comp_buf != ref_buf:
            if self._debug_mode:
                _LOGGER.debug(f"[{self.codec_id}] '{msg}' differs - expected: {as_hex(ref_buf)}, received: {as_hex(trunc_comp_buf)}")
            return False
        return True

    def log_buffer(self, buf: bytes, msg: str) -> None:
        """Log buffer."""
        if self._debug_mode:
            _LOGGER.debug(f"[{self.codec_id}] {msg} - {as_hex(buf)}")
