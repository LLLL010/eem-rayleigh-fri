"""Fluorescence indices and Coble peak intensities for a corrected EEM."""
from __future__ import annotations

import bisect
import math


METRIC_HEADERS = [
    "文件名", "BIX", "FI_470_520", "HIX_Ohno",
    "Peak_A_强度", "Peak_A_Em_nm", "Peak_B_强度",
    "Peak_C_强度", "Peak_C_Em_nm", "Peak_M_强度",
    "Peak_M_Em_nm", "Peak_T_强度", "备注",
]


def _interp(axis: list[float], values: list[float], wavelength: float) -> float | None:
    """Linear interpolation on an increasing axis; never extrapolate."""
    if wavelength < axis[0] or wavelength > axis[-1]:
        return None
    right = bisect.bisect_left(axis, wavelength)
    if axis[right] == wavelength:
        return values[right]
    left = right - 1
    weight = (wavelength - axis[left]) / (axis[right] - axis[left])
    return values[left] + weight * (values[right] - values[left])


def _emission_at_ex(x: list[list[float]], ex_axis: list[float], ex: float) -> list[float] | None:
    if ex < ex_axis[0] or ex > ex_axis[-1]:
        return None
    return [_interp(ex_axis, row, ex) for row in x]


def _point(x: list[list[float]], ex_axis: list[float], em_axis: list[float],
           ex: float, em: float) -> float | None:
    emission = _emission_at_ex(x, ex_axis, ex)
    return None if emission is None else _interp(em_axis, emission, em)


def _band(x: list[list[float]], ex_axis: list[float], em_axis: list[float],
          ex: float, lower: float, upper: float) -> float | None:
    emission = _emission_at_ex(x, ex_axis, ex)
    if emission is None or lower < em_axis[0] or upper > em_axis[-1]:
        return None
    wavelengths = [lower] + [v for v in em_axis if lower < v < upper] + [upper]
    values = [_interp(em_axis, emission, v) for v in wavelengths]
    area = math.fsum((b - a) * (u + v) / 2 for a, b, u, v in
                    zip(wavelengths, wavelengths[1:], values, values[1:]))
    return area


def _peak(x: list[list[float]], ex_axis: list[float], em_axis: list[float],
          ex: float, lower: float, upper: float) -> tuple[float, float] | None:
    emission = _emission_at_ex(x, ex_axis, ex)
    if emission is None or lower < em_axis[0] or upper > em_axis[-1]:
        return None
    wavelengths = [lower] + [v for v in em_axis if lower < v < upper] + [upper]
    return max(((_interp(em_axis, emission, v), v) for v in wavelengths),
               key=lambda peak: peak[0])


def calculate_metrics(x: list[list[float]], ex_axis: list[float],
                      em_axis: list[float]) -> dict[str, float | str | None]:
    """Compute indices after scatter interpolation, using zero for negative intensity."""
    z = [[max(0.0, value) for value in row] for row in x]
    result: dict[str, float | str | None] = {key: None for key in METRIC_HEADERS[1:-1]}
    unavailable = []

    bix_num = _point(z, ex_axis, em_axis, 310, 380)
    bix_den = _point(z, ex_axis, em_axis, 310, 430)
    if bix_num is not None and bix_den is not None and bix_den > 0:
        result["BIX"] = bix_num / bix_den
    else:
        unavailable.append("BIX")

    fi_num = _point(z, ex_axis, em_axis, 370, 470)
    fi_den = _point(z, ex_axis, em_axis, 370, 520)
    if fi_num is not None and fi_den is not None and fi_den > 0:
        result["FI_470_520"] = fi_num / fi_den
    else:
        unavailable.append("FI")

    short = _band(z, ex_axis, em_axis, 254, 300, 345)
    long = _band(z, ex_axis, em_axis, 254, 435, 480)
    if short is not None and long is not None and short + long > 0:
        result["HIX_Ohno"] = long / (short + long)
    else:
        unavailable.append("HIX")

    for name, ex, low, high in (("A", 260, 380, 460),
                                ("C", 350, 420, 480),
                                ("M", 312, 380, 420)):
        peak = _peak(z, ex_axis, em_axis, ex, low, high)
        if peak is None:
            unavailable.append("Peak " + name)
        else:
            result[f"Peak_{name}_强度"], result[f"Peak_{name}_Em_nm"] = peak

    for name, ex, em in (("B", 275, 310), ("T", 275, 340)):
        value = _point(z, ex_axis, em_axis, ex, em)
        if value is None:
            unavailable.append("Peak " + name)
        else:
            result[f"Peak_{name}_强度"] = value

    result["备注"] = "波长范围不足或比值分母为 0：" + "、".join(unavailable) if unavailable else ""
    return result
