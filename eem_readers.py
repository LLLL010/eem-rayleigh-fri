"""Read text EEM exports into (Ex, Em, intensity[Em][Ex]).

The instrument-specific rules are adapted from the user-supplied 01_readers.R.
Ambiguous files use the documented standard orientation: first row Ex, first column Em.
"""
from __future__ import annotations

import csv
import math
import re
from pathlib import Path


def _decode(path: Path) -> str:
    raw = path.read_bytes()
    if not raw or (b"\x00" in raw[:100] and not raw.startswith((b"\xff\xfe", b"\xfe\xff"))):
        raise ValueError("文件为空或不是可读取的文本")
    encodings = ("utf-16",) if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else ("utf-8-sig", "gb18030")
    for encoding in encodings:
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            pass
    raise ValueError("文本编码无法识别；请导出为 UTF-8、GB18030 或 UTF-16")


def _number(value: str) -> float | None:
    try:
        number = float(value.strip())
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _rows(lines: list[str], delimiter: str) -> list[list[str]]:
    return [[cell.strip() for cell in row] for row in csv.reader(lines, delimiter=delimiter)
            if any(cell.strip() for cell in row)]


def _header_at(rows: list[list[str]]) -> int:
    for i in range(len(rows) - 1):
        row = rows[i]
        if len(row) < 3 or _number(row[0]) is not None:
            continue
        axis = [_number(cell) for cell in row[1:] if cell != ""]
        following = rows[i + 1]
        if len(axis) >= 2 and all(v is not None for v in axis) and following and _number(following[0]) is not None:
            return i
    raise ValueError("找不到波长表头；预期首格为空、其后为波长，下一行为强度数据")


def _matrix(rows: list[list[str]], header: int) -> tuple[list[float], list[float], list[list[float]]]:
    axis_cells = rows[header][1:]
    while axis_cells and axis_cells[-1] == "":
        axis_cells.pop()
    first_axis = [_number(cell) for cell in axis_cells]
    if len(first_axis) < 2 or any(v is None for v in first_axis):
        raise ValueError("第一行波长轴包含空值或非数字")
    first_axis = [float(v) for v in first_axis]
    second_axis, matrix = [], []
    for row in rows[header + 1:]:
        if not row or _number(row[0]) is None:
            break  # instrument footer begins
        if len(row) < len(first_axis) + 1:
            raise ValueError("数据行少于波长表头所需的列数；请检查导出文件是否截断")
        values = [_number(cell) for cell in row[1:len(first_axis) + 1]]
        if any(v is None for v in values):
            raise ValueError("强度矩阵含空值或非数字；请先修正原始导出")
        if any(cell != "" for cell in row[len(first_axis) + 1:]):
            raise ValueError("数据行比波长表头多出非空强度列")
        second_axis.append(float(_number(row[0])))
        matrix.append([float(v) for v in values])
    if len(second_axis) < 2:
        raise ValueError("有效波长数据行少于两行")
    return first_axis, second_axis, matrix


def _meter_header_at(rows: list[list[str]]) -> int:
    """Locate a PicoQuant header with Em wavelengths starting in the first cell."""
    for i in range(len(rows) - 1):
        header, following = rows[i], rows[i + 1]
        wavelengths = [_number(cell) for cell in header]
        if (len(wavelengths) >= 2 and all(v is not None and 0 < v < 1e-4 for v in wavelengths)
                and len(following) >= len(header) + 1
                and _number(following[0]) is not None
                and 0 < _number(following[0]) < 1e-4):
            return i
    raise ValueError("找不到 PicoQuant 米单位波长表头")


def _meter_matrix(rows: list[list[str]], header: int) -> tuple[list[float], list[float], list[list[float]]]:
    first_axis = [float(_number(cell)) for cell in rows[header]]
    second_axis, matrix = [], []
    for row in rows[header + 1:]:
        wavelength = _number(row[0])
        if wavelength is None:
            break
        if len(row) < len(first_axis) + 1:
            raise ValueError("PicoQuant 数据行少于波长表头所需的列数")
        values = [_number(cell) for cell in row[1:len(first_axis) + 1]]
        if any(v is None for v in values):
            raise ValueError("PicoQuant 强度矩阵含空值或非数字")
        if any(cell != "" for cell in row[len(first_axis) + 1:]):
            raise ValueError("PicoQuant 数据行比波长表头多出非空强度列")
        second_axis.append(float(wavelength))
        matrix.append([float(v) for v in values])
    if len(second_axis) < 2:
        raise ValueError("PicoQuant 有效波长数据行少于两行")
    return first_axis, second_axis, matrix


def _transpose(matrix: list[list[float]]) -> list[list[float]]:
    return [list(column) for column in zip(*matrix)]


def _covers_fri(ex: list[float], em: list[float]) -> bool:
    return min(ex) < 250 < max(ex) and min(em) < 330 < 380 < max(em)


def _orient(first: list[float], second: list[float], matrix: list[list[float]]
            ) -> tuple[list[float], list[float], list[list[float]]]:
    if max(first + second) < 1e-4:
        # PicoQuant: first row Em, first column Ex; convert metres to nm.
        keep = [i for i, value in enumerate(first) if value != 0]
        ex = [round(v * 1e9, 9) for v in second]
        em = [round(first[i] * 1e9, 9) for i in keep]
        x = _transpose([[row[i] for i in keep] for row in matrix])
    elif ((0 in first and 0 not in second)
          or (min(first) > min(second) and max(first) > max(second))
          or (_covers_fri(second, first) and not _covers_fri(first, second))):
        # Shimadzu RF-5301 / RF-6000: first row Em, first column Ex.
        keep = [i for i, value in enumerate(first) if value != 0]
        ex, em = second, [first[i] for i in keep]
        x = _transpose([[row[i] for i in keep] for row in matrix])
    else:
        # Standard CSV: first row Ex, first column Em.
        ex, em, x = first, second, matrix
    return ex, em, x


def _read_delimited(lines: list[str]) -> tuple[list[float], list[float], list[list[float]]]:
    errors = []
    for delimiter in (",", "\t"):
        rows = _rows(lines, delimiter)
        try:
            header = _header_at(rows)
            return _orient(*_matrix(rows, header))
        except ValueError as exc:
            errors.append(str(exc))
        try:
            header = _meter_header_at(rows)
            return _orient(*_meter_matrix(rows, header))
        except ValueError as exc:
            errors.append(str(exc))
    raise ValueError("找不到可识别的 EEM 波长表头，或数据矩阵不完整：" + "；".join(dict.fromkeys(errors)))


def read_text_eem(path: Path) -> tuple[list[float], list[float], list[list[float]]]:
    """Identify Hitachi Data Points or parse standard/Shimadzu/PicoQuant text."""
    lines = _decode(path).splitlines()
    if any(line.strip().casefold() == "data points" for line in lines):
        return read_hitachi_txt(path, lines)
    return _read_delimited(lines)


def read_csv_eem(path: Path) -> tuple[list[float], list[float], list[list[float]]]:
    """Backward-compatible entry point for delimited CSV EEMs."""
    return read_text_eem(path)


def _check_hitachi_metadata(lines: list[str], ex: list[float], em: list[float]) -> None:
    """When present, compare the instrument's scan limits with the Data Points axes."""
    for axis_name, axis in (("EX", ex), ("EM", em)):
        expected = {}
        for line in lines:
            match = re.match(rf"^\s*{axis_name}\s+(Start WL|End WL):\s*([+-]?\d+(?:\.\d+)?)\s*nm",
                             line, re.IGNORECASE)
            if match:
                expected[match.group(1).casefold()] = float(match.group(2))
        if "start wl" in expected and "end wl" in expected:
            actual = sorted((axis[0], axis[-1]))
            stated = sorted((expected["start wl"], expected["end wl"]))
            if any(not math.isclose(a, b, rel_tol=0, abs_tol=1e-6)
                   for a, b in zip(actual, stated)):
                raise ValueError(f"{axis_name} 数据段波长范围与仪器参数不一致")


def read_hitachi_txt(path: Path, lines: list[str] | None = None
                     ) -> tuple[list[float], list[float], list[list[float]]]:
    """Read the tab-delimited Data Points block in an F-4600 text export."""
    if lines is None:
        lines = _decode(path).splitlines()
    marker = next((i for i, line in enumerate(lines)
                   if line.strip().casefold() == "data points"), None)
    if marker is None:
        raise ValueError("找不到 Data Points 数据段；请使用仪器导出的文本 TXT")
    rows = _rows(lines[marker + 1:], "\t")
    header = _header_at(rows)
    # This export already has Em rows and Ex columns, so no transpose is needed.
    ex, em, x = _matrix(rows, header)
    _check_hitachi_metadata(lines[:marker], ex, em)
    return ex, em, x
