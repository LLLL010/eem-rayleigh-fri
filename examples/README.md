# 示例数据与处理结果

这个示例展示从输入 EEM、散射插值到五区积分的完整流程。

| 文件 | 内容 |
|---|---|
| [`input/示例数据.xlsx`](input/示例数据.xlsx) | 输入 EEM：第一行 Ex，第一列 Em |
| [`expected/示例数据_插值后.xlsx`](expected/示例数据_插值后.xlsx) | 散射窗口插值后的绘图矩阵 |
| [`expected/示例数据_五区积分.xlsx`](expected/示例数据_五区积分.xlsx) | 五区积分、BIX/FI/HIX、A/B/C/M/T 峰强度、运行记录和方法 |
| [`example_before_after.png`](example_before_after.png) | 处理前后 EEM 和五区占比的对比图 |

## 自己运行并核对

1. 新建一个文件夹，将 `input/示例数据.xlsx` 与 [Windows 工具包 v1.4.0](../dist/eem-rayleigh-fri-win64-v1.4.0.zip)中的 `启动处理.bat`、`eem_tool.exe` 复制进去。
2. 双击批处理文件。输出会出现在这个空文件夹的 `EEM_处理结果` 下。
3. 输出矩阵应与 `expected/示例数据_插值后.xlsx` 相同；汇总表的一行应与 `expected/示例数据_五区积分.xlsx` 一致。

## 图和数值如何读

对比图横轴为发射波长 Em，纵轴为激发波长 Ex。A、B 面板共用 0–400 色标，白线标出五区边界。图像绘制时进行了轻微平滑；输出 XLSX 和积分都使用实际处理矩阵，不使用绘图平滑值。C 面板展示面积归一化后的五区占比 `P`。

本例共对 550 个散射窗口点进行插值。一阶窗口、二阶窗口及五区的具体边界见[首页的处理方法](../README.md#处理和计算方法)。

计算与作图分别由 `scripts/build_example.py` 和 `scripts/plot_example.py` 生成，可在安装依赖后重新执行。
