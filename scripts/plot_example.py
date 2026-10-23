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
from eem_tool import integrate, read_eem


def display_grid(ex, em, values, scale=4):
    """Resample and lightly smooth the figure only; numerical outputs stay unchanged."""
    smooth_ex = np.linspace(ex[0], ex[-1], (len(ex) - 1) * scale + 1)
    smooth_em = np.linspace(em[0], em[-1], (len(em) - 1) * scale + 1)
    along_em = np.vstack([np.interp(smooth_em, em, row) for row in values])
    fine = np.column_stack([np.interp(smooth_ex, ex, along_em[:, j])
                            for j in range(len(smooth_em))])
    # A small Gaussian blur softens contour stair steps caused by sparse Ex sampling.
    # Edge padding keeps the plotting range and endpoint values stable.
    sigma = 2.0
    radius = int(np.ceil(3 * sigma))
    positions = np.arange(-radius, radius + 1)
    kernel = np.exp(-0.5 * (positions / sigma) ** 2)
    kernel /= kernel.sum()
    for axis in (0, 1):
        padded = np.pad(fine, [(radius, radius) if i == axis else (0, 0)
                               for i in range(2)], mode="edge")
        fine = np.apply_along_axis(lambda line: np.convolve(line, kernel, mode="valid"),
                                   axis, padded)
    return smooth_ex, smooth_em, fine


def main():
    ex, em, raw_values = read_eem(ROOT / "examples/input/示例数据.xlsx")
    processed_ex, processed_em, corrected_values = read_eem(
        ROOT / "examples/expected/示例数据_插值后.xlsx")
    original = np.asarray(raw_values)
    processed = np.asarray(corrected_values)
    if ex != processed_ex or em != processed_em:
        raise ValueError("处理前后的波长轴不一致")
    if original.shape != processed.shape:
        raise ValueError("矩阵形状不一致")
    proportions = np.asarray(integrate(processed, ex, em)[10:15]) * 100
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False})
    fig = plt.figure(figsize=(13.2, 4.65), layout="constrained")
    axes = [fig.add_subplot(1, 3, i + 1) for i in range(3)]
    vmax = 400.0
    for ax, data, title in zip(axes[:2], [original, processed],
                               ["A   Before interpolation", "B   After interpolation"]):
        display = np.maximum(data, 0).T
        smooth_ex, smooth_em, fine = display_grid(ex, em, display)
        image = ax.contourf(smooth_em, smooth_ex, fine, levels=np.linspace(0, vmax, 41),
                            cmap="jet", norm=Normalize(vmin=0, vmax=vmax), extend="max")
        ax.contour(smooth_em, smooth_ex, fine, levels=[50, 100, 150, 200, 300, 400],
                   colors="black", alpha=.32, linewidths=.5)
        ax.axhline(250, color="white", lw=1.5)
        ax.axvline(380, color="white", lw=1.5)
        ax.plot([330, 330], [min(ex), 250], color="white", lw=1.5)
        for name, x, y in [
            ("I", (min(em) + 330) / 2, (min(ex) + 250) / 2),
            ("II", 355, (min(ex) + 250) / 2),
            ("III", (380 + max(em)) / 2, (min(ex) + 250) / 2),
            ("IV", (min(em) + 380) / 2, (250 + max(ex)) / 2),
            ("V", (380 + max(em)) / 2, (250 + max(ex)) / 2),
        ]:
            ax.text(x, y, name, color="white", ha="center", va="center",
                    fontsize=11, fontweight="bold",
                    path_effects=[withStroke(linewidth=1.4, foreground="black")])
        ax.set(xlabel="Emission Em (nm)", ylabel="Excitation Ex (nm)", title=title,
               xlim=(min(em), max(em)), ylim=(min(ex), max(ex)))
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
    path = ROOT / "examples/example_before_after.png"
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(path)


if __name__ == "__main__":
    main()
