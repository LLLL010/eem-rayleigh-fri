# EEM Rayleigh interpolation & five-region FRI

批量处理固定格式的三维荧光激发-发射矩阵（EEM）：对一阶、二阶瑞利散射窗口插值，输出可绘图的 XLSX，并计算五区荧光区域积分（FRI）。

## 先看示例

下面使用仓库内的实测 [`黑.xlsx`](examples/input/黑.xlsx)。左右两张 EEM 图使用相同的 0–600 色标。色标上限只影响显示，XLSX 中数值**没有截断**。

![原始与插值后 EEM 对比及五区积分](examples/black_before_after.png)

| 区域 | 原始积分 Phi | 面积归一化后占比 P |
|---|---:|---:|
| I | 403,643.473 | 18.154% |
| II | 456,768.500 | 32.868% |
| III | 835,419.504 | 13.663% |
| IV | 1,349,209.898 | 28.724% |
| V | 1,751,366.874 | 6.591% |

[查看示例的输入 XLSX、输出 XLSX 和计算记录](examples/README.md)。示例中共插值 550 个矩阵点，包括 38 个 `9999.9` 饱和值；上表用**插值后**矩阵计算，不能与“散射点直接置零”的结果混用。

## Windows 64 位：免安装使用

1. 打开 [`dist/eem-rayleigh-fri-win64-v1.zip`](dist/eem-rayleigh-fri-win64-v1.zip)，点击该文件页面的 **Download raw file** 图标，下载并解压。把包内的 `eem_tool.exe` 和 `启动处理.bat` 放进**原始 XLSX 所在文件夹**。
2. 双击 `启动处理.bat`。程序只扫描该文件夹顶层的 `.xlsx`，不修改原文件，也不读取子文件夹。
3. 在新生成的 `EEM_处理结果` 中查看：`01_插值矩阵` 是逐文件的绘图数据；`02_五区积分汇总.xlsx` 含五区积分、面积归一化结果、运行记录和方法。

无需安装 Python、R 或 Excel 才能运行程序；查看 XLSX 仍需 Excel 或兼容的表格软件。这个 32 MB 工具包使用 Git LFS 存储。GitHub 的 **Code → Download ZIP** 默认可能只含它的指针文件，不能保证得到真正的工具包；请在文件页面单独下载，或安装 Git LFS 后克隆仓库。详见 [GitHub 的 LFS 归档说明](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/managing-git-lfs-objects-in-archives-of-your-repository)。

## 输入条件

每个 XLSX 的 `Sheet1` 必须是 **177 行 × 32 列**：A1 空白；第一行是 Ex=200–500 nm，步长 10 nm；第一列是 Em=250–600 nm，步长 2 nm；其余 176×31 个单元格为有限数值。格式不符会记入运行记录，不会猜测轴的方向或自动重采样。可先用 [示例 XLSX](examples/input/黑.xlsx) 检查表格排列。

## 方法边界

- 一阶窗口 `|Em−Ex|≤12 nm`；二阶窗口 `|Em−(2Ex+4)|≤20 nm`。在每个窗口内沿 Em 和 Ex 分别线性插值，取平均；插值负值截为 0。窗口外测量值保持原样。
- FRI 前将负值和 `Em≤Ex` 的值记为 0；各区按二维梯形法积分，再按区域面积归一化。完整区域边界、面积和公式见 [方法说明](使用说明.md)及输出 XLSX 的“方法”“分区面积”工作表。
- 当前只处理上述**瑞利散射窗口**；没有做空白扣除、水拉曼散射识别、内滤效应校正或其他仪器校正。图中的其他亮峰不能仅凭本程序认定为样品荧光。插值位置为估计值。

## 源码与复现

程序源码为 [`eem_tool.py`](eem_tool.py)，运行需要 Python 3 和 `openpyxl`。`scripts/build_example.py` 从示例 XLSX 重建预期结果；`scripts/plot_example.py` 重建对比图，另外需要 `numpy` 和 `matplotlib`。依赖列在 [`requirements.txt`](requirements.txt) 和 [`requirements-plot.txt`](requirements-plot.txt)。

本项目目前已在 Windows 10 64 位环境下用 18 个样本核对：与此前 R 实现相比，插值矩阵逐格一致，积分最大绝对差约 2.2×10⁻⁸；其他电脑、系统和仪器导出格式尚未实测。遇到问题请提供脱敏后的示例文件、`运行记录` 工作表及程序窗口的报错。
