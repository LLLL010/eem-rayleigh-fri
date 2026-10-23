"""Rebuild the published 黑.xlsx example outputs."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from eem_tool import integrate, interpolate, read_matrix, save_matrix, save_summary


def main():
    target = ROOT / "examples" / "input" / "黑.xlsx"
    raw = read_matrix(target)
    corrected, counts = interpolate(raw)
    result = ROOT / "examples" / "expected"
    result.mkdir(parents=True, exist_ok=True)
    save_matrix(result / "黑_插值后.xlsx", corrected)
    phi = integrate(corrected)
    save_summary(result / "黑_五区积分.xlsx",
                 [[target.name] + phi], [[target.name, "成功", ""] + counts])
    print("input:", target)
    print("processed:", result / "黑_插值后.xlsx")
    print("Phi:", phi[:5])
    print("P:", phi[10:15])
    print("mask counts:", counts)


if __name__ == "__main__":
    main()
