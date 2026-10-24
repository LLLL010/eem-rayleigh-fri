"""Rebuild the published anonymized EEM example outputs."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from eem_tool import calculate_fri, interpolate, read_eem, save_matrix, save_summary
from eem_metrics import calculate_metrics


def main():
    target = ROOT / "examples" / "input" / "示例数据.xlsx"
    ex, em, raw = read_eem(target)
    corrected, counts = interpolate(raw, ex, em)
    result = ROOT / "examples" / "expected"
    result.mkdir(parents=True, exist_ok=True)
    save_matrix(result / "示例数据_插值后.xlsx", corrected, ex, em)
    phi, areas = calculate_fri(corrected, ex, em)
    save_summary(result / "示例数据_五区积分.xlsx",
                 [[target.name] + phi], [[target.name, "成功", ""] + counts],
                 [(target.name, areas)], [(target.name, calculate_metrics(corrected, ex, em))])
    print("input:", target)
    print("processed:", result / "示例数据_插值后.xlsx")
    print("Phi:", phi[:5])
    print("P:", phi[10:15])
    print("mask counts:", counts)


if __name__ == "__main__":
    main()
