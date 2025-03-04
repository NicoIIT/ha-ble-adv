"""FanLamp pro Unit Tests."""

import pytest

from . import _TestEncoderBase

TESTS = [
    ("fanlamp_pro_v1", 0x03, "77.F8.B6.5F.2B.5E.00.FC.31.51.50.FE.D2.08.24.0A.73.FC.08.66.F4.90.14.AF.B4.E5"),
    ("fanlamp_pro_v1", 0x03, "77.F8.B6.5F.2B.5E.00.FC.31.51.CC.FE.D2.4C.2E.0A.33.FC.7E.10.F4.E6.C0.1C.7B.74"),
    ("fanlamp_pro_v1", 0x03, "77.F8.B6.5F.2B.5E.00.FC.31.51.50.FE.D2.08.24.0A.3B.FC.D6.B8.4A.4E.31.20.A9.3E"),
    ("fanlamp_pro_v2", 0x03, "F0.08.10.80.B8.52.E1.22.C6.F2.D3.A7.67.7C.A4.9F.67.F6.B6.A2.22.8B.53.2B.01.6B"),
    ("fanlamp_pro_v3", 0x03, "F0.08.20.80.B8.52.E1.22.C6.F2.D3.A7.67.7C.A4.9F.67.F6.B6.B7.41.8B.53.2B.E9.59"),
    ("fanlamp_pro_v3", 0x03, "F0.08.20.80.8A.3F.2F.22.B9.F2.DB.03.FC.F8.68.C1.28.0C.1D.C3.6E.DA.19.48.88.61"),
    ("remote_v1", 0xFF, "56.55.18.87.52.B6.5F.2B.5E.00.FC.31.51.50.50.9A.08.24.0A.EC.FC.A9.7B.8E.0D.4A.67.60.57"),
    ("remote_v1", 0xFF, "56.55.18.87.52.B6.5F.2B.5E.00.FC.31.51.54.50.9A.08.24.0A.96.FC.F5.27.DB.51.D3.43.60.57"),
    ("remote_v3", 0x16, "F0.08.10.00.5B.B5.CC.F3.7B.EB.FC.C8.4A.F2.0A.2E.3F.FC.18.05.F7.AD.3B.BD.17.A6"),
    ("other_v1b", 0x16, "F9.08.49.13.F0.69.25.4E.31.51.BA.32.08.0A.24.CB.3B.7C.71.DC.8B.B8.97.08.D0.4C"),
    ("other_v1a", 0x03, "77.F8.B6.5F.2B.5E.00.FC.31.51.50.CB.92.08.24.CB.BB.FC.14.C6.9E.B0.E9.EA.73.A4"),
    ("other_v2", 0x16, "F0.08.10.80.0B.9B.DA.CF.BE.B3.DD.56.3B.E9.1C.FC.27.A9.3A.A5.38.2D.3F.D4.6A.50"),
    ("other_v3", 0x16, "F0.08.10.80.33.BC.2E.B0.49.EA.58.76.C0.1D.99.5E.9C.D6.B8.0E.6E.14.2B.A5.30.A9"),
]


@pytest.mark.parametrize(_TestEncoderBase.PARAM_NAMES, TESTS)
class TestEncoderFanlamp(_TestEncoderBase):
    """Fanlamp Encoder tests."""
