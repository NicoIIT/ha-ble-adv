"""FanLamp pro Unit Tests."""

import pytest

from . import _TestEncoderBase

TESTS = [
    ("zhijia_v0", 0xFF, "F9.08.49.89.E4.E1.A2.3E.6C.95.0B.58.C9.38.28.07"),
    ("zhijia_v1", 0xFF, "F9.08.49.13.E1.2B.48.C3.33.4A.85.E5.C5.56.60.96.C4.A0.2C.89.BB.11.76.92.99.AA"),
    ("zhijia_v2", 0xFF, "22.9D.AB.CB.5F.CF.2F.FC.F3.5F.52.EC.4D.85.00.6E.87.99.F2.4A.5F.85.F6.9C.A9.19"),
    ("zhijia_vr1", 0xFF, "F0.FF.CF.5E.EC.CF.CC.CF.30.EF.CE.6A.CC.CD.67.C9.EC.28.C9"),
    ("zhiguang_v0", 0xFF, "F9.08.49.B2.CE.2C.91.3F.6D.94.0A.F2.FB.39.25.67"),
    ("zhiguang_v1", 0xFF, "F9.08.49.E6.29.AF.D4.17.38.AC.51.33.11.82.8D.42.10.76.F8.C4.78.FC.C8.46.23.8E"),
    ("zhiguang_v2", 0xFF, "22.9D.8D.36.4B.E9.0F.DA.D5.40.79.CA.69.A3.BF.5B.95.D5.D4.4A.5F.85.F6.9C.A9.19"),
]


@pytest.mark.parametrize(_TestEncoderBase.PARAM_NAMES, TESTS)
class TestEncoderFanlamp(_TestEncoderBase):
    """Fanlamp Encoder tests."""
