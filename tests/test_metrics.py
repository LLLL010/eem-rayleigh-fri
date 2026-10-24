"""Independent index formulas on a nonuniform EEM grid."""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from eem_metrics import calculate_metrics


def test():
    ex = [200, 250, 260, 270, 280, 310, 320, 350, 370, 400]
    em = [250, 300, 310, 340, 345, 380, 420, 430, 435, 460, 470, 480, 520, 600]

    def f(e, m):
        return 100 + e / 10 + m / 5

    x = [[f(e, m) for e in ex] for m in em]
    result = calculate_metrics(x, ex, em)
    assert math.isclose(result["BIX"], f(310, 380) / f(310, 430), abs_tol=1e-12)
    assert math.isclose(result["FI_470_520"], f(370, 470) / f(370, 520), abs_tol=1e-12)

    def integral(e, lower, upper):
        return (upper - lower) * (f(e, lower) + f(e, upper)) / 2

    short = integral(254, 300, 345)  # Ex=254 and Em=345 require interpolation.
    long = integral(254, 435, 480)
    assert math.isclose(result["HIX_Ohno"], long / (short + long), abs_tol=1e-12)
    for name, e, m in (("A", 260, 460), ("B", 275, 310),
                       ("C", 350, 480), ("M", 312, 420), ("T", 275, 340)):
        assert math.isclose(result[f"Peak_{name}_强度"], f(e, m), abs_tol=1e-12)
        if name in ("A", "C", "M"):
            assert result[f"Peak_{name}_Em_nm"] == m
    assert result["备注"] == ""

    # Missing FI wavelengths should leave that metric blank without losing the others.
    limited = calculate_metrics([row[:8] for row in x[:12]], ex[:8], em[:12])
    assert limited["FI_470_520"] is None
    assert limited["BIX"] is not None and limited["HIX_Ohno"] is not None
    assert "FI" in limited["备注"]
    print("indices, peak intensities, interpolation and missing-wavelength behavior passed")


if __name__ == "__main__":
    test()
