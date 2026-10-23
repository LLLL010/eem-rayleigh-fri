"""Batch Rayleigh interpolation and five-region EEM integration."""
from __future__ import annotations

import bisect
import math
import sys
from pathlib import Path

from openpyxl import Workbook, load_workbook


EX = list(range(200, 501, 10))
EM = list(range(250, 601, 2))
AREAS = [4000, 2500, 11000, 8450, 47800]
MF = [sum(AREAS) / area for area in AREAS]
REGIONS = [
    ([j for j, ex in enumerate(EX) if ex <= 250], [i for i, em in enumerate(EM) if em <= 330]),
    ([j for j, ex in enumerate(EX) if ex <= 250], [i for i, em in enumerate(EM) if 330 <= em <= 380]),
    ([j for j, ex in enumerate(EX) if ex <= 250], [i for i, em in enumerate(EM) if em >= 380]),
    ([j for j, ex in enumerate(EX) if ex >= 250], [i for i, em in enumerate(EM) if em <= 380]),
    ([j for j, ex in enumerate(EX) if ex >= 250], [i for i, em in enumerate(EM) if em >= 380]),
]


def read_matrix(path: Path) -> list[list[float]]:
    book = load_workbook(path, read_only=True, data_only=True)
    try:
        if "Sheet1" not in book.sheetnames:
            raise ValueError("缺少 Sheet1")
        sheet = book["Sheet1"]
        if sheet.max_row != 177 or sheet.max_column != 32:
            raise ValueError(f"Sheet1 应为 177 行 × 32 列，实际为 {sheet.max_row} × {sheet.max_column}")
        rows = list(sheet.iter_rows(min_row=1, max_row=177, min_col=1, max_col=32, values_only=True))
    finally:
        book.close()
    if rows[0][0] not in (None, ""):
        raise ValueError("A1 应为空白")
    def numeric(value, position):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{position} 应为有限数值；公式请先保存计算结果")
        return float(value)
    ex = [numeric(v, f"第一行第 {j+2} 列") for j, v in enumerate(rows[0][1:])]
    em = [numeric(row[0], f"第一列第 {i+2} 行") for i, row in enumerate(rows[1:])]
    if ex != EX or em != EM:
        raise ValueError("波长轴需为 Ex 200–500/10 nm、Em 250–600/2 nm")
    return [[numeric(v, f"第 {i+2} 行第 {j+2} 列") for j, v in enumerate(row[1:])]
            for i, row in enumerate(rows[1:])]


def line_fill(axis: list[int], values: list[float], keep: list[bool]) -> list[float]:
    known_axis = [a for a, ok in zip(axis, keep) if ok]
    known_values = [v for v, ok in zip(values, keep) if ok]
    if len(known_axis) < 2:
        raise ValueError("散射窗口外不足两个点，无法插值")
    result = []
    for a in axis:
        right = bisect.bisect_left(known_axis, a)
        if right == 0:
            result.append(known_values[0])
        elif right == len(known_axis):
            result.append(known_values[-1])
        elif known_axis[right] == a:
            result.append(known_values[right])
        else:
            left = right - 1
            fraction = (a - known_axis[left]) / (known_axis[right] - known_axis[left])
            result.append(known_values[left] + fraction * (known_values[right] - known_values[left]))
    return result


def interpolate(x: list[list[float]]):
    first = [[abs(em - ex) <= 12 for ex in EX] for em in EM]
    second = [[abs(em - (2 * ex + 4)) <= 20 for ex in EX] for em in EM]
    mask = [[first[i][j] or second[i][j] for j in range(len(EX))] for i in range(len(EM))]
    saturated = sum(value == 9999.9 for row in x for value in row)
    if any(x[i][j] == 9999.9 and not mask[i][j]
           for i in range(len(EM)) for j in range(len(EX))):
        raise ValueError("散射窗口外发现 9999.9 饱和值，未自动填补")
    vertical = [line_fill(EM, [x[i][j] for i in range(len(EM))],
                          [not mask[i][j] for i in range(len(EM))]) for j in range(len(EX))]
    horizontal = [line_fill(EX, x[i], [not m for m in mask[i]]) for i in range(len(EM))]
    filled = [[max(0.0, (vertical[j][i] + horizontal[i][j]) / 2) if mask[i][j] else x[i][j]
               for j in range(len(EX))] for i in range(len(EM))]
    counts = [sum(map(sum, first)),
              sum(second[i][j] and not first[i][j] for i in range(len(EM)) for j in range(len(EX))),
              sum(map(sum, mask)), saturated]
    return filled, counts


def integrate(x: list[list[float]]) -> list[float]:
    z = [[max(0.0, x[i][j]) if em > ex else 0.0 for j, ex in enumerate(EX)]
         for i, em in enumerate(EM)]
    phi = []
    for cols, rows in REGIONS:
        total = 0.0
        for ri, i in enumerate(rows):
            row_weight = 0.5 if ri in (0, len(rows) - 1) else 1.0
            for cj, j in enumerate(cols):
                col_weight = 0.5 if cj in (0, len(cols) - 1) else 1.0
                total += z[i][j] * row_weight * col_weight
        phi.append(total * 10 * 2)
    normalized = [p * m for p, m in zip(phi, MF)]
    total = sum(normalized)
    if total <= 0 or not math.isfinite(total):
        raise ValueError("面积归一化积分总量不为正")
    return phi + normalized + [v / total for v in normalized] + [total]


def save_matrix(path: Path, x: list[list[float]]):
    book = Workbook()
    sheet = book.active
    sheet.title = "Sheet1"
    sheet.append([None] + EX)
    for em, row in zip(EM, x):
        sheet.append([em] + row)
    book.save(path)


def save_summary(path: Path, results, log):
    book = Workbook()
    sheet = book.active
    sheet.title = "积分结果"
    sheet.append(["文件名"] + [f"Phi_{i}" for i in "I II III IV V".split()] +
                 [f"PhiN_{i}" for i in "I II III IV V".split()] +
                 [f"P_{i}" for i in "I II III IV V".split()] + ["PhiN_total"])
    for row in results:
        sheet.append(row)
    sheet = book.create_sheet("运行记录")
    sheet.append(["文件名", "状态", "说明", "一阶点数", "二阶点数", "插值点数", "饱和点数"])
    for row in log:
        sheet.append(row)
    sheet = book.create_sheet("方法")
    sheet.append(["项目", "规则"])
    for row in [
        ("输入", "Sheet1：列 Ex=200–500 nm/10；行 Em=250–600 nm/2"),
        ("插值", "一阶 |Em−Ex|≤12 nm；二阶 |Em−(2Ex+4)|≤20 nm；沿 Ex 与 Em 双向线性插值取平均，插值负数截 0"),
        ("积分", "插值矩阵中负数及 Em≤Ex 对积分记 0；各区二维梯形积分，边半权，角四分之一权"),
        ("面积归一化", "PhiN_i=Phi_i×(73750/区域面积_i)；P_i=PhiN_i/sum(PhiN_i)"),
        ("分区边界", "I: Ex≤250/Em≤330；II: Ex≤250/330–380；III: Ex≤250/Em≥380；IV: Ex≥250/Em≤380；V: Ex≥250/Em≥380"),
        ("用途", "插值点是估计值，输出矩阵适合绘图；定量结果与早先零值掩膜积分不可混用"),
    ]:
        sheet.append(row)
    sheet = book.create_sheet("分区面积")
    sheet.append(["区域", "面积_nm2", "MF"])
    for name, area, mf in zip("I II III IV V".split(), AREAS, MF):
        sheet.append([name, area, mf])
    book.save(path)


def main(input_dir: Path) -> int:
    if not input_dir.is_dir():
        print(f"输入文件夹不存在：{input_dir}")
        return 2
    files = sorted((p for p in input_dir.iterdir() if p.is_file()
                    and p.suffix.lower() == ".xlsx" and not p.name.startswith("~$")),
                   key=lambda p: p.name)
    if not files:
        print("当前文件夹顶层没有 .xlsx 文件")
        return 2
    output = input_dir / "EEM_处理结果"
    matrix_dir = output / "01_插值矩阵"
    matrix_dir.mkdir(parents=True, exist_ok=True)
    results, log = [], []
    for path in files:
        print(f"处理：{path.name}", flush=True)
        try:
            x = read_matrix(path)
            corrected, counts = interpolate(x)
            values = integrate(corrected)
            save_matrix(matrix_dir / path.name, corrected)
            results.append([path.name] + values)
            log.append([path.name, "成功", ""] + counts)
        except Exception as exc:
            print(f"  失败：{exc}", flush=True)
            log.append([path.name, "失败", str(exc), None, None, None, None])
    save_summary(output / "02_五区积分汇总.xlsx", results, log)
    failures = sum(row[1] == "失败" for row in log)
    print(f"完成：{len(results)} 成功，{failures} 失败。\n输出目录：{output}")
    return 1 if failures else 0


if __name__ == "__main__":
    try:
        folder = Path(sys.argv[1] if len(sys.argv) > 1 else Path.cwd()).resolve()
        sys.exit(main(folder))
    except Exception as exc:
        print(f"程序错误：{exc}")
        sys.exit(2)
