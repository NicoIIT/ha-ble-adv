"""Init for HA tests."""

from unittest import mock

import pytest
from ble_adv.codecs.models import BleAdvEntAttr
from ble_adv.device import BleAdvEntity


class _Device(mock.AsyncMock):
    unique_id = "device_id"
    available = True

    add_entity = mock.MagicMock()

    def assert_apply_change(self, ent: BleAdvEntity, chgs: list[str]) -> None:
        self.apply_change.assert_called_once_with(BleAdvEntAttr(chgs, ent.get_attrs(), ent._base_type, ent._index))  # noqa: SLF001
        self.apply_change.reset_mock()

    def assert_no_change(self) -> None:
        self.apply_change.assert_not_called()


@pytest.fixture
def device() -> _Device:
    """Fixture device."""
    return _Device()
