"""Plot the published example after build_example.py has generated XLSX files."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.patheffects import withStroke

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from eem_tool import EX, EM, integrate, read_matrix


def main():
    original = np.asarray(read_matrix(ROOT / "examples/input/黑.xlsx"))
    processed = np.asarray(read_matrix(ROOT / "examples/expected/黑_插值后.xlsx"))
    if original.shape != processed.shape:
        raise ValueError("矩阵形状不一致")
    proportions = np.asarray(integrate(processed)[10:15]) * 100
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False})
    fig = plt.figure(figsize=(13.2, 4.65), layout="constrained")
    axes = [fig.add_subplot(1, 3, i + 1) for i in range(3)]
    vmax = 400.0
    for ax, data, title in zip(axes[:2], [original, processed],
                               ["A   Before interpolation", "B   After interpolation"]):
        display = np.maximum(data, 0).T
        image = ax.pcolormesh(EM, EX, display, shading="nearest",
                              cmap="jet", norm=Normalize(vmin=0, vmax=vmax), rasterized=True)
        ax.contour(EM, EX, display, levels=[50, 100, 150, 200, 300, 400],
                   colors="black", alpha=.32, linewidths=.5)
        ax.axhline(250, color="white", lw=1.5)
        ax.axvline(380, color="white", lw=1.5)
        ax.plot([330, 330], [min(EX), 250], color="white", lw=1.5)
        for name, x, y in [("I", 290, 225), ("II", 355, 225), ("III", 460, 225),
                           ("IV", 315, 320), ("V", 470, 320)]:
            ax.text(x, y, name, color="white", ha="center", va="center",
                    fontsize=11, fontweight="bold",
                    path_effects=[withStroke(linewidth=1.4, foreground="black")])
        ax.set(xlabel="Emission Em (nm)", ylabel="Excitation Ex (nm)", title=title,
               xlim=(min(EM), max(EM)), ylim=(min(EX), max(EX)))
    colorbar = fig.colorbar(image, ax=axes[:2], location="bottom", shrink=.75, pad=.12)
    colorbar.set_label(f"Fluorescence intensity (display clipped at {vmax:.0f})")
    ax = axes[2]
    bars = ax.bar(["I", "II", "III", "IV", "V"], proportions,
                  color=["#4e79a7", "#59a14f", "#f28e2b", "#e15759", "#b07aa1"])
    for bar, value in zip(bars, proportions):
        ax.text(bar.get_x() + bar.get_width() / 2, value + .7, f"{value:.2f}%",
                ha="center", va="bottom", fontsize=9)
    ax.set(xlabel="FRI region", ylabel="Normalized contribution (%)",
           title="C   Five-region integration", ylim=(0, max(proportions) * 1.18))
    path = ROOT / "examples/black_before_after.png"
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(path)


if __name__ == "__main__":
    main()
