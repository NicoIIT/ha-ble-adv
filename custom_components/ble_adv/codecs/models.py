"""Models."""

import copy
import logging
from abc import ABC, abstractmethod
from binascii import hexlify
from dataclasses import dataclass
from typing import Any, Self

from .const import (
    ATTR_SUB_TYPE,
    DEVICE_TYPE,
    FAN_TYPE,
    FAN_TYPE_3SPEED,
    FAN_TYPE_6SPEED,
    FAN_TYPE_100SPEED,
    LIGHT_TYPE,
    LIGHT_TYPE_CWW,
    LIGHT_TYPE_ONOFF,
    LIGHT_TYPE_RGB,
)

_LOGGER = logging.getLogger(__name__)


def as_hex(buffer: bytes) -> str:
    """Represent hex buffer as 00.01.02 format."""
    return str(hexlify(buffer, "."), "ascii").upper()


class BleAdvAdvertisement:
    """Model and Advertisement."""

    @classmethod
    def FromRaw(cls, raw_adv: bytes) -> Self:  # noqa: N802
        """Build an Advertisement from raw."""
        ble_type = 0x00
        rem_data = raw_adv
        while len(rem_data) > 2:
            part_len = rem_data[0]
            if part_len > len(rem_data):
                break
            part_type = rem_data[1]
            if part_type in [0x03, 0x16, 0xFF]:
                ble_type = part_type
                raw_data = rem_data[2 : part_len + 1]
            rem_data = rem_data[part_len + 1 :]
        if ble_type == 0:
            raw_data = raw_adv
        return cls(ble_type, raw_data)

    def __init__(self, ble_type: int, raw: bytes, ad_flag: int = 0) -> None:
        self.ble_type: int = ble_type
        self.raw: bytes = raw
        self.ad_flag = ad_flag

    def __repr__(self) -> str:
        """Repr."""
        return f"Type: 0x{self.ble_type:02X}, raw: {'.'.join(f'{x:02X}' for x in self.raw)}"

    def __hash__(self) -> int:
        return hash((self.ble_type, self.raw))

    def __eq__(self, comp: Self) -> bool:
        return (self.ble_type == comp.ble_type) and (self.raw == comp.raw)

    def to_raw(self) -> bytes:
        """Get the raw buffer."""
        full_raw = bytearray([len(self.raw) + 1, self.ble_type]) + self.raw if self.ble_type != 0 else self.raw
        return full_raw if self.ad_flag == 0 else bytearray([0x02, 0x01, self.ad_flag]) + full_raw


@dataclass
class BleAdvEncCmd:
    """Ble ADV Encoder command."""

    cmd: int = 0
    param: int = 0
    arg0: int = 0
    arg1: int = 0
    arg2: int = 0
    arg3: int = 0
    arg4: int = 0

    def __init__(self, cmd: int) -> None:
        self.cmd = cmd

    def __repr__(self) -> str:
        return f"cmd: 0x{self.cmd:02X}, param: 0x{self.param:02X}, args: [{self.arg0},{self.arg1},{self.arg2}]"


type AttrType = str | bool | int | float | None


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

    def __hash__(self) -> int:
        """Hash."""
        return hash((*set(self.chg_attrs), *self.attrs, self.base_type, self.index))

    def __eq__(self, comp: Self) -> bool:
        return (
            (set(self.chg_attrs) == set(comp.chg_attrs))
            and (self.attrs == comp.attrs)
            and (self.base_type == comp.base_type)
            and (self.index == comp.index)
        )

    def get_attr_as_float(self, attr: str) -> float:
        """Get attr as float."""
        return float(self.attrs[attr])


@dataclass
class BleAdvConfig:
    """Ble Adv Encoder Config."""

    id: int = 0
    index: int = 0
    tx_count: int = 0
    app_restart_count: int = 1
    seed: int = 0

    def __init__(self, config_id: int = 0, index: int = 0) -> None:
        self.id: int = config_id
        self.index: int = index

    def __repr__(self) -> str:
        return f"id: 0x{self.id:08X}, index: {self.index}, tx: {self.tx_count}, seed: 0x{self.seed:04X}"


class CommonMatcher:
    """Matcher Base."""

    def __init__(self) -> None:
        self.eqs: dict[str, Any] = {}
        self.mins: dict[str, float] = {}
        self.maxs: dict[str, float] = {}

    def eq(self, attr: str, attr_val: AttrType) -> Self:
        """Force Entity to have attribute equal to this value."""
        self.eqs[attr] = attr_val
        return self

    def min(self, attr: str, attr_val: float) -> Self:
        """Force Entity to have attribute of maximum this value."""
        self.mins[attr] = attr_val
        return self

    def max(self, attr: str, attr_val: float) -> Self:
        """Force Entity to have attribute of minimum this value."""
        self.maxs[attr] = attr_val
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
            self.eqs[ATTR_SUB_TYPE] = sub_type

    def __repr__(self) -> str:
        return f"{self._base_type}_{self._index} / {self._actions}"

    def act(self, action: str, action_value: AttrType = None) -> Self:
        """Match Activity on given attribute, with value."""
        self._actions.append(action)
        return self.eq(action, action_value) if action_value is not None else self

    def matches(self, ent_attr: BleAdvEntAttr) -> bool:
        """Effective match for the incoming Enitity Attributes."""
        return (
            (self._base_type == ent_attr.base_type)
            and (self._index == ent_attr.index)
            and any(attr in ent_attr.chg_attrs for attr in self._actions)
            and all(ent_attr.attrs.get(attr) == val for attr, val in self.eqs.items())
            and all(ent_attr.attrs.get(attr) >= val for attr, val in self.mins.items())  # type: ignore[none]
            and all(ent_attr.attrs.get(attr) <= val for attr, val in self.maxs.items())  # type: ignore[none]
        )

    def create(self) -> BleAdvEntAttr:
        """Create Ble Adv Entity Features from self."""
        ent_attr: BleAdvEntAttr = BleAdvEntAttr(self._actions.copy(), self.eqs.copy(), self._base_type, self._index)
        return ent_attr

    def get_supported_features(self) -> tuple[str, int, dict[str, Any]]:
        """Get Features."""
        feats: dict[str, Any] = {**self.eqs}
        feats[ATTR_SUB_TYPE] = self._sub_type
        return (self._base_type, self._index, feats)


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


class Fan100SpeedCmd(EntityMatcher):
    """Specific 100 level speed Fan Matcher."""

    def __init__(self, index: int = 0) -> None:
        super().__init__(FAN_TYPE, index, FAN_TYPE_100SPEED)


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
        super().__init__(DEVICE_TYPE, 0)


class EncoderMatcher(CommonMatcher):
    """Specific Encoder Matcher."""

    def __init__(self, cmd: int) -> None:
        super().__init__()
        self._cmd: int = cmd

    def __repr__(self) -> str:
        return f"cmd: 0x{self._cmd:02X}"

    def matches(self, enc_cmd: BleAdvEncCmd) -> bool:
        """Match with Encoder Attributes."""
        return (
            (enc_cmd.cmd == self._cmd)
            and all(getattr(enc_cmd, attr) == val for attr, val in self.eqs.items())
            and all(getattr(enc_cmd, attr) >= val for attr, val in self.mins.items())
            and all(getattr(enc_cmd, attr) <= val for attr, val in self.maxs.items())
        )

    def create(self) -> BleAdvEncCmd:
        """Create a Ble Adv Encoder Cmd from self."""
        enc_cmd: BleAdvEncCmd = BleAdvEncCmd(self._cmd)
        for eq_attr, eq_val in self.eqs.items():
            setattr(enc_cmd, eq_attr, eq_val)
        return enc_cmd


class Trans:
    """Base translator."""

    def __init__(self, ent: EntityMatcher, enc: EncoderMatcher) -> None:
        self.ent = ent
        self.enc = enc
        self._copies = []
        self.direct = True
        self.reverse = True
        self._scopy = None

    def __repr__(self) -> str:
        return f"{self.ent} / {self.enc} / {self._copies}"

    def copy(self, attr_ent: str, attr_enc: str, factor: float = 1.0) -> Self:
        """Apply copy from attr_ent to attr_enc, with factor."""
        self._copies.append((attr_ent, attr_enc, factor))
        return self

    def split_copy(self, attr_ent: str, dests: list[str], factor: float = 1.0, modulo: int = 256) -> Self:
        """Split the value in src iteratively to dests with each time applying a modulo."""
        self._scopy = (attr_ent, dests, factor, modulo)
        return self

    def no_direct(self) -> Self:
        """Do not consider this translator for direct translation."""
        self.direct = False
        return self

    def no_reverse(self) -> Self:
        """Do not consider this translator for reverse translation."""
        self.reverse = False
        return self

    def matches_ent(self, ent_attr: BleAdvEntAttr) -> bool:
        """Check if the translator matches the entity attributes."""
        return self.direct and self.ent.matches(ent_attr)

    def matches_enc(self, enc_cmd: BleAdvEncCmd) -> bool:
        """Check if the translator matches the encoder command."""
        return self.reverse and self.enc.matches(enc_cmd)

    def ent_to_enc(self, ent_attr: BleAdvEntAttr) -> BleAdvEncCmd:
        """Apply transformations to Encoder Attributes: direct."""
        enc_cmd = self.enc.create()
        for attr_ent, attr_enc, factor in self._copies:
            setattr(enc_cmd, attr_enc, int(factor * ent_attr.attrs.get(attr_ent, 0)))
        if self._scopy is not None:
            attr_ent, dests, factor, modulo = self._scopy
            val = int(factor * ent_attr.attrs[attr_ent])
            for dest in dests:
                setattr(enc_cmd, dest, val % modulo)
                val = int(val / modulo)
        return enc_cmd

    def enc_to_ent(self, enc_cmd: BleAdvEncCmd) -> BleAdvEntAttr:
        """Apply transformations to Entity Attributes: reverse."""
        ent_attr = self.ent.create()
        if self._scopy is not None:
            attr_ent, dests, factor, modulo = self._scopy
            val = 0
            for dest in reversed(dests):
                val = modulo * val + getattr(enc_cmd, dest)
            ent_attr.attrs[attr_ent] = (1.0 / factor) * val
        for attr_ent, attr_enc, factor in self._copies:
            ent_attr.attrs[attr_ent] = (1.0 / factor) * getattr(enc_cmd, attr_enc)
        return ent_attr


class BleAdvCodec(ABC):
    """Class representing a base encoder / decoder."""

    _len: int = 0
    _tx_step: int = 1
    _tx_max: int = 125
    debug_mode: bool = False
    duration: int = 750
    interval: int = 30
    repeat: int = 9
    ign_duration: int = 12000
    multi_advs: bool = False

    def __init__(self) -> None:
        self.codec_id: str = ""
        self.match_id: str = ""
        self._header: bytearray = bytearray()  # header is excluded from the data sent to the child encoder
        self._header_start_pos: int = 0
        self._prefix: bytearray = bytearray()  # prefix is included in the data sent to the child encoder
        self._ble_type: int = 0
        self._ad_flag: int = 0
        self._translators: list[Trans] = []

    @abstractmethod
    def decrypt(self, buffer: bytes) -> bytes | None:
        """Decrypt / unwhiten an incoming raw buffer into a readable buffer."""

    @abstractmethod
    def encrypt(self, decoded: bytes) -> bytes:
        """Encrypt / whiten a readable buffer."""

    @abstractmethod
    def convert_to_enc(self, decoded: bytes) -> tuple[BleAdvEncCmd | None, BleAdvConfig | None]:
        """Convert a readable buffer into an encoder command and a config."""

    @abstractmethod
    def convert_from_enc(self, enc_cmd: BleAdvEncCmd, conf: BleAdvConfig) -> bytes:
        """Convert an encoder command and a config into a readable buffer."""

    def convert_multi_from_enc(self, enc_cmd: BleAdvEncCmd, conf: BleAdvConfig) -> list[bytes]:
        """Convert an encoder command and a config into a list of readable buffers."""
        # Call the single buffer encoder by default for standard encoders
        return [self.convert_from_enc(enc_cmd, conf)]

    def fid(self, codec_id: str, match_id: str) -> Self:
        """Set codec id / match id."""
        self.match_id = match_id
        self.codec_id = codec_id
        return self

    def id(self, match_id: str, sub_id: str | None = None) -> Self:
        """Set match_id and codec_id from id and sub_id if any."""
        return self.fid(f"{match_id}/{sub_id}" if sub_id is not None else match_id, match_id)

    def header(self, header: list[int], start_pos: int = 0) -> Self:
        """Set header."""
        self._header = bytearray(header)
        self._header_start_pos = start_pos
        return self

    def prefix(self, prefix: list[int]) -> Self:
        """Set prefix."""
        self._prefix = bytearray(prefix)
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

    def add_rev_only_trans(self, translators: list[Trans]) -> Self:
        """Add Reverse Only Translators."""
        self._translators.extend([copy.copy(trans).no_direct() for trans in translators if trans.reverse])
        return self

    def get_supported_features(self, base_type: str) -> list[dict[str, set[Any]]]:
        """Get the features supported by the translators in DIRECT mode only.

        Builds a list of all potential attribute values if fixed (not floats / int / None):
           [
                {attr_name1: set(value011 value012, ...), attr_name2: set(value021 value022, ...),}, # For entity 0 of type base_type
                {attr_name1: set(value111 value112, ...), attr_name2: set(value121 value122, ...),}, # For entity 1 of type base_type
           ]
        """
        capa: list[dict[str, set[Any]]] = []
        for trans in self._translators:
            if not trans.direct:
                continue
            (bt, ind, feats) = trans.ent.get_supported_features()
            if bt == base_type:
                missing = ind - len(capa) + 1
                if missing > 0:
                    capa = capa + [{} for i in range(missing)]
                for feat, val in feats.items():
                    if val is not None:
                        capa[ind].setdefault(feat, set()).add(val)
        return capa

    def ent_to_enc(self, ent_attr: BleAdvEntAttr) -> list[BleAdvEncCmd]:
        """Convert Entity Attributes to list of Encoder Attributes."""
        return [trans.ent_to_enc(ent_attr) for trans in self._translators if trans.matches_ent(ent_attr)]

    def enc_to_ent(self, enc_cmd: BleAdvEncCmd) -> list[BleAdvEntAttr]:
        """Convert Encoder Attributes to list of Entity Attributes."""
        return [trans.enc_to_ent(enc_cmd) for trans in self._translators if trans.matches_enc(enc_cmd)]

    def decode_adv(self, adv: BleAdvAdvertisement) -> tuple[BleAdvEncCmd | None, BleAdvConfig | None]:
        """Decode Adv into Encoder Attributes / Config."""
        if (
            not self.is_eq(self._ble_type, adv.ble_type, "BLE Type")
            or not self.is_eq(self._len, len(adv.raw) - len(self._header) - self._header_start_pos, "Length")
            or not self.is_eq_buf(self._header, adv.raw[self._header_start_pos :], "Header")
        ):
            return None, None
        self.log_buffer(adv.raw, "Decode/Full")
        read_buffer = self.decrypt(adv.raw[: self._header_start_pos] + adv.raw[self._header_start_pos + len(self._header) :])
        if read_buffer is None or not self.is_eq_buf(self._prefix, read_buffer, "Prefix"):
            return None, None
        read_buffer = read_buffer[len(self._prefix) :]
        self.log_buffer(read_buffer, "Decode/Decrypted")
        return self.convert_to_enc(read_buffer)

    def encode_advs(self, enc_cmd: BleAdvEncCmd, conf: BleAdvConfig) -> list[BleAdvAdvertisement]:
        """Encode an Encoder Command with Config into a list of Adv."""
        conf.tx_count = (conf.tx_count + self._tx_step) % self._tx_max
        if conf.tx_count == 0:
            conf.app_restart_count = (conf.app_restart_count + 1) % 255
        advs: list[BleAdvAdvertisement] = []
        for read_buffer in self.convert_multi_from_enc(enc_cmd, conf):
            self.log_buffer(read_buffer, "Encode/Decrypted")
            encrypted = self.encrypt(self._prefix + read_buffer)
            encrypted = encrypted[: self._header_start_pos] + self._header + encrypted[self._header_start_pos :]
            self.log_buffer(encrypted, "Encode/Full")
            advs.append(BleAdvAdvertisement(self._ble_type, encrypted, self._ad_flag))
        return advs

    def is_eq(self, ref: int, comp: int, msg: str) -> bool:
        """Check equal and log if not."""
        if ref != comp:
            if self.debug_mode:
                _LOGGER.debug(f"[{self.codec_id}] '{msg}' differs - expected: '0x{ref:X}', received: '0x{comp:X}'")
            return False
        return True

    def is_eq_buf(self, ref_buf: bytes, comp_buf: bytes, msg: str) -> bool:
        """Check buffer equal and log if not."""
        trunc_comp_buf = comp_buf[: len(ref_buf)]
        if trunc_comp_buf != ref_buf:
            if self.debug_mode:
                _LOGGER.debug(f"[{self.codec_id}] '{msg}' differs - expected: {as_hex(ref_buf)}, received: {as_hex(trunc_comp_buf)}")
            return False
        return True

    def log_buffer(self, buf: bytes, msg: str) -> None:
        """Log buffer."""
        if self.debug_mode:
            _LOGGER.debug(f"[{self.codec_id}] {msg} - {as_hex(buf)}")
