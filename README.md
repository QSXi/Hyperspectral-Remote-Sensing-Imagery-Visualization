# RSIDEA 基础编程能力测试解答

两道遥感影像基础操作题的解答。数据文件体积较大，仓库只上传代码、说明文档和必要输出图，不上传原始遥感数据。

## 目录

- [第一题：大幅宽高分辨率遥感影像基础操作](#t1)
  - [数据集下载](#t1-data)
  - [运行步骤](#t1-run)
  - [解题思路](#t1-method)
  - [运行内存与空间复杂度说明](#t1-memory)
- [第二题：高光谱遥感影像基础操作](#t2)
  - [数据集下载](#t2-data)
  - [运行步骤](#t2-run)
  - [物体分割算法及实现方式](#t2-segmentation)
  - [运行内存与空间复杂度说明](#t2-memory)
  - [采样数量选择依据](#t2-sampling)

<a id="t1"></a>
## 第一题：大幅宽高分辨率遥感影像基础操作

### 题目目标

本题要求对给定的高分辨率遥感影像（GeoTIFF 格式，`Boston.tif`）完成两项统计任务：

1. 求出各波段均值与标准差（精确到小数点后 3 位）
2. 求出各波段最大值与最小值（精确到小数点后 3 位）

测试环境为 Python 3，运行内存限制 1 GB（即 1024 MB）。题目特别提示：需考虑计算复杂度与空间复杂度。

对应文件：

```text
solution/
  Boston.py     # 统计各波段均值、标准差、最大值、最小值
```

<a id="t1-data"></a>
### 数据集下载

数据来源：

```text
https://pan.baidu.com/s/1FiDIgaxN2GbQk1I4Dr73Aw
```

进入百度网盘后下载 `Boston.tif` 文件。文件大小约为 2 GB（压缩后），推荐下载后放入项目根目录：

```text
Boston.tif
T1/
  Boston.py
```

说明：原始 GeoTIFF 数据文件约 2 GB，仓库中没有上传。

### 数据集基本信息

- 文件格式：GeoTIFF（`.tif`）
- 数据类型：`uint8`（每像素 1 字节）
- 文件大小：约 2 GB（压缩后 GeoTIFF）
- 影像尺寸：宽 29184 × 高 26880
- 波段数：3（R、G、B）
- 总像素数：2,353,397,760（约 23.5 亿像素）
- 原始数据体积：29184 × 26880 × 3 × 1 byte = 2,353,397,760 bytes ≈ 2.19 GB
- NoData 值：由 GeoTIFF 文件元数据中 nodata 标签定义，程序通过 rasterio 的 `src.nodata` 属性自动读取。若该属性为 `None`，则认为所有像素均为有效值，不做过滤。

由于影像原始数据体积约为 2.19 GB，远超题目的 1 GB 运行内存限制，因此无法将整幅影像一次性读入内存，必须采用分块读取策略。这也是本题的核心难点。

### 环境安装

使用虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install rasterio numpy
```

依赖说明：

```text
rasterio    # GeoTIFF 读写，基于 GDAL，支持 Window 分块读取
numpy       # 数值计算，提供 float64 累加器与向量化运算
```

关于 GDAL：`rasterio` 底层依赖 GDAL 库。通常 `pip install rasterio` 会自动安装预编译的 GDAL 二进制包（通过 rasterio 的 wheel）。若安装失败，可能需要系统预先安装 GDAL 开发包（如 `sudo apt install libgdal-dev`）再 `pip install rasterio`。

<a id="t1-run"></a>
### 运行步骤

#### 1. 生成各波段统计结果

运行：

```bash
python T1/Boston.py
```

默认读取：

```text
data/Boston.tif
```

程序输出各波段的均值、标准差、最大值、最小值，均精确到小数点后 3 位。

### 实测结果

在 `Boston.tif`（29184 × 26880，3 波段，uint8）上运行结果如下：

```text
影像尺寸：宽29184, 高26880, 波段数：3

===== 第1波段 =====
均值:   80.022
标准差: 44.685
最大值: 255.000
最小值: 0.000

===== 第2波段 =====
均值:   82.947
标准差: 41.991
最大值: 255.000
最小值: 0.000

===== 第3波段 =====
均值:   75.070
标准差: 42.571
最大值: 255.000
最小值: 0.000
```

### 代码文件说明

`T1/Boston.py`：分块读取遥感影像，统计各波段均值、标准差、最大值、最小值。

程序核心逻辑全部在 `Boston.py` 中实现，无额外依赖文件。

<a id="t1-method"></a>
### 解题思路

#### 1. 问题分析：为什么不能直接读入整幅影像

`Boston.tif` 影像尺寸为 29184 × 26880，共 3 个波段，数据类型为 `uint8`（每像素 1 字节）。全量读入内存所需空间为：

```text
29184 × 26880 × 3 × 1 byte = 2,353,397,760 bytes ≈ 2.19 GB
```

这已经超过 1 GB 内存限制的 2 倍以上，直接读入必然 OOM。因此必须采用分块流式处理，将内存占用控制在条带级别。

#### 2. 行条带分块读取

核心策略：将影像按行方向切分为多个条带（stripe），每次仅读取一个条带到内存，处理完后释放，再读取下一个条带。

具体实现：

- 定义 `chunk_rows = 128`，表示每个条带读取的行数。
- 使用 `rasterio.windows.Window(0, row_off, width, actual_rows)` 指定读取区域。
- 外层循环 `for row_off in range(0, height, chunk_rows)`，逐步遍历全图。
- 每次迭代的条带数据内存占用为 B × chunk_rows × W × 1 byte，对于本题数据（3 波段 × 128 行 × 29184 列 × 1 byte）约为 10.7 MB，远小于 1 GB。

```python
for row_off in range(0, height, chunk_rows):
    actual_rows = min(chunk_rows, height - row_off)
    window = Window(0, row_off, width, actual_rows)
    chunk = src.read(window=window)  # shape: (B, actual_rows, W)
```

总条带数：⌈26880 / 128⌉ = 210，即 I/O 次数为 210 次。

#### 3. 多波段同时读取，减少 I/O 次数

题目给出的提示中隐含要求：降低计算复杂度与 I/O 开销。如果对每个波段分别调用 `src.read(band_idx)`，I/O 次数将变为 B × H/chunk_rows = 3 × 210 = 630 次，效率较低。

本方案的改进：每次 `src.read(window=...)` 同时读取该条带的全部波段，返回形状为 `(B, chunk_rows, W)` 的三维数组。这样：

- I/O 次数仅为 210 次（H/chunk_rows），而非 630 次
- 在同一次读取结果上逐波段计算统计量，复用同一次磁盘 I/O
- 相比逐波段读取，I/O 次数减少了 B 倍（3 倍）

```python
chunk = src.read(window=window)     # 一次读取全部波段
for b_idx in range(band_count):
    arr = chunk[b_idx]             # view，零拷贝
    # 对 arr 进行统计计算
```

#### 4. Welford/Chan 并行合并公式——在线流式计算均值与方差

这是本方案最核心的算法。问题在于：我们需要在分块流式处理中（每次只看到一小块数据）计算全局均值和标准差。

##### 朴素方案的缺陷

朴素的两趟扫描法需要先存全部数据再算方差，内存不可接受；若在每块上分别计算后取简单平均，则当各块像素数不等（因 NoData 过滤）时会产生偏差。

###### 传统期望平方差法及其数值稳定性缺陷

在流式计算方差的朴素方案中，最容易想到的是维护 $\sum x$ 和 $\sum x^2$，最后利用传统期望方差公式计算：
$$Var(X) = E(X^2) - (E(X))^2 = \frac{\sum x^2}{n} - \left(\frac{\sum x}{n}\right)^2$$
虽然该方法只需单遍扫描，但在计算机浮点数体系下存在致命的**数值稳定性问题**（大数相消 / Catastrophic Cancellation）。

当影像像素值存在较大常数偏移（如辐射定标后的高 DN 值），而真实方差极小时，$E(X^2)$ 会累积成极大的数值。在 `float32` 或大规模 `float64` 累加中，由于浮点数有效位数有限（`float32` 仅约 7 位十进制有效数字），极小的方差信息会在计算 $E(X^2)$ 时被当作尾数截断丢失。当执行 $E(X^2) - (E(X))^2$ 时，两个相近的大数相减会将误差急剧放大，甚至导致算出的方差为负数或完全归零。

为验证此缺陷，编写了对照测试程序 `T1/test.py` 与测试数据生成脚本 `T1/generate_data.py`。脚本生成了基准值为 $2^{20}$（约 104 万）、微小波动在 $0 \sim 1$ 之间的极端数据（真实方差约 0.083），对比传统公式与 Chan 公式（分块合并）的输出。实验结果如下：

| 组号 | 数据特征 (float32)  | 真值 (float64)    | 传统公式 (float32)  | Chan公式 (float32) | 传统绝对误差    | Chan绝对误差      |
|---:|----------------------|-------------------|---------------------|--------------------|-----------------|-------------------|
| 1  | 基准~1e6, 极小方差   | 0.0856570875      | 0.0000000000        | 0.1008763164       | 0.0856570875    | 0.0152192290      |
| 2  | 基准~6.5e4, 极小方差 | 0.0833859759      | 0.0000000000        | 0.0833911449       | 0.0833859759    | 0.0000051690      |
| 3  | 常规数据 (0~100)     | 831.2877860022    | 831.2875976562      | 831.2877807617     | 0.0001883459    | 0.0000052405      |

**结果分析**：
在组 1 和组 2 的极端数据中，传统公式算出的方差完全归零（`0.0000000000`），方差信息被彻底截断丢失；而 Chan 公式基于偏差（$\Delta$）累加，成功避开了大数平方相减，在 `float32` 下依然逼近 `0.083` 的真值。组 3 在常规数据下两者表现相当，证明 Chan 公式在正常场景下不会引入额外开销。

需要特别指出的是，在测试传统公式时，无论是直接调用 `np.mean(data**2)` 按顺序单遍计算，还是分块累加 $\sum x^2$ 后合并，最终结果均一致为 `0.0`。这是因为在浮点数体系中，加法并不严格满足结合律，不同计算顺序本应产生微小差异；但由于 $E(X^2)$ 达到了 $10^{12}$ 量级，`float32` 在此量级的最小刻度（ULP）高达 $131072$，不同累加顺序产生的差异远小于该刻度，因而被直接截断。无论怎么改变计算顺序，极小的方差信息在 $E(X^2)$ 累加阶段就已丢失殆尽。这进一步印证了传统公式在处理大数小方差时的彻底失效，必须采用 Chan 并行合并公式以保障数值稳定性。


##### Chan 并行合并公式

采用 Chan 等人（1982）提出的并行合并公式，它是 Welford 在线算法的并行推广。该公式允许将任意多个数据块的局部统计量（均值、方差、样本数）数值稳定地合并为全局统计量。

设已有全局统计量（`n_old` 个像素，均值 `mean_old`，方差累计量 `M2_old`），新来一个数据块（`n_b` 个有效像素，块均值 `mean_b`，块方差 `var_b`），则合并后：

```text
n_new    = n_old + n_b
delta    = mean_b - mean_old
mean_new = (n_old × mean_old + n_b × mean_b) / n_new
M2_new   = M2_old + var_b × n_b + delta² × n_old × n_b / n_new
```

最终标准差：

```text
σ = √(M2 / n)
```

为什么选择 Chan 公式而非其他方案：

1. 数值稳定：避免了“大数相减”问题。朴素方差公式 E[X²] - (E[X])² 在数据值较大时，两个相近的大数相减会损失大量有效数字。Chan 公式通过 delta² 项保持精度。
2. 单遍处理：每个数据块只需计算一次 mean 和 var，不需要存储原始数据，适合流式场景。
3. 自然处理 NoData：每个块的 `n_b` 是该块的有效像素数（去除了 NoData），不同块的 `n_b` 可以不同，合并公式自动加权处理。

代码实现：

```python
# 当前块的局部统计量（NumPy 向量化，高效）
n_b    = valid.size
mean_b = valid.mean()       # float64 标量
var_b  = valid.var()        # 总体方差，ddof=0

# Chan 并行合并到全局统计量
n_old  = pixel_nums[b_idx]
n_new  = n_old + n_b
delta  = mean_b - mean_vals[b_idx]
mean_vals[b_idx] = (n_old * mean_vals[b_idx] + n_b * mean_b) / n_new
M2s[b_idx]      += var_b * n_b + delta**2 * n_old * n_b / n_new
pixel_nums[b_idx] = n_new
```

#### 5. 最大值与最小值的在线合并

最大值和最小值的合并比均值/方差简单得多——只需在分块间取极值即可：

```python
pix_mins[b_idx] = min(pix_mins[b_idx], float(valid.min()))
pix_maxs[b_idx] = max(pix_maxs[b_idx], float(valid.max()))
```

初始化为 `float('inf')` / `float('-inf')`，确保第一个有效值即可更新。

#### 6. NoData 处理

`rasterio` 通过 `src.nodata` 属性读取文件元数据中标记的 NoData 值。程序的处理逻辑：

```python
if src.nodata is not None:
    valid = arr[arr != src.nodata].astype(np.float64)
else:
    valid = arr.astype(np.float64)
```

- 若文件定义了 NoData 值，则使用布尔索引过滤，仅保留有效像素参与统计。
- 若文件未定义 NoData 值（`src.nodata is None`），则所有像素均视为有效。
- 过滤后的数据转换为 `float64` 进行累加，保证均值和方差计算的数值精度。

<a id="t1-memory"></a>
### 运行内存与空间复杂度说明

题目要求注意 1 GB 运行内存限制（即 1024 MB）。设影像尺寸为 W × H × B，数据类型为 `uint8`（1 字节/像素）。

#### 为什么全量读入不可行

本题影像参数：

```text
全量内存 = 29184 × 26880 × 3 × 1 byte = 2,353,397,760 bytes ≈ 2.19 GB
```

2.19 GB 远超 1 GB 限制，全量读入必然失败。

#### 本方案的内存处理

本方案采用行条带分块读取 + 在线流式统计，不将整幅影像同时放入内存。

任意时刻内存中的主要数据为：

- 1 个条带数据块：B × chunk_rows × W × 1 byte = 3 × 128 × 29184 ≈ 10.7 MB（uint8 原始数据）
- 1 个有效值数组：（经 NoData 过滤后转为 float64）≤ 3 × 128 × 29184 × 8 bytes ≈ 85.9 MB（float64，最大情况）
- 各波段的 float64 累加器（pixel_nums、mean_vals、M2s、pix_mins、pix_maxs），每个波段仅占用固定几个 float64 变量，总计可忽略不计。

数据层面的额外空间复杂度：

```text
O(chunk_rows × W × B)
```

无论影像多大，峰值数据内存都只取决于条带大小，与影像总体积无关。默认 `chunk_rows = 128` 下，条带原始数据仅约 10.7 MB。

### chunk_rows 对性能的影响——数值实验

为验证 `chunk_rows` 参数对执行时间与峰值内存的影响，在 `Boston.tif` 上进行了 10 组对照实验，覆盖从 1 行到 512 行的不同条带大小。

| chunk_rows | I/O 次数 | 执行时间 (秒) | 峰值内存 (MB) | 状态 |
|---:|---:|---:|---:|:---:|
| 1 | 26880 | 11.874 | 877.6 | ✅ 达标 |
| 2 | 13440 | 9.416 | 877.5 | ✅ 达标 |
| 4 | 6720 | 8.633 | 879.4 | ✅ 达标 |
| 8 | 3360 | 5.980 | 888.3 | ✅ 达标 |
| 16 | 1680 | 4.943 | 885.8 | ✅ 达标 |
| 32 | 840 | 9.107 | 895.6 | ✅ 达标 |
| 64 | 420 | 5.411 | 915.0 | ✅ 达标 |
| 128 | 210 | 3.781 | 954.3 | ✅ 达标 |
| 256 | 105 | 5.521 | 1032.7 | ⚠️ 超限 |
| 512 | 53 | 5.670 | 1211.2 | ⚠️ 超限 |

所有 `chunk_rows` 取值下的统计结果（均值、标准差、最大值、最小值）完全一致，验证了 Chan 并行合并公式的正确性与数值稳定性。

#### 实验结果分析

##### 1. 峰值内存随 chunk_rows 递增

峰值内存由两部分构成：

```text
峰值内存 = 基础开销（GDAL 缓存 + Python 运行时）+ 数据条带开销
```

从实验数据可以看出，即使 `chunk_rows = 1`，峰值内存仍有 877.6 MB，说明 GDAL 内部缓存与 Python 运行时的基础开销占据了绝大部分内存。数据条带本身的开销（chunk_rows × W × B × 8 bytes，float64 最大情况）仅在 chunk_rows 较大时才显著：

- `chunk_rows = 1` 时：3 × 1 × 29184 × 8 ≈ 0.7 MB，几乎可忽略
- `chunk_rows = 128` 时：3 × 128 × 29184 × 8 ≈ 85.9 MB，比 `chunk_rows = 1` 高出约 77 MB
- `chunk_rows = 256` 时：约 172 MB，叠加基础开销后超过 1 GB

基础开销约 877 MB，留给数据条带的预算仅约 147 MB。因此 `chunk_rows = 128` 已接近安全上限（954.3 MB），`chunk_rows = 256` 则必然超限（1032.7 MB）。

##### 2. 执行时间非线性下降，存在最优值

执行时间并非随 `chunk_rows` 单调递减，而是呈现先快降、后波动的趋势：

- `chunk_rows` 从 1 增至 16 时，I/O 次数从 26880 降至 1680，执行时间从 11.874 秒降至 4.943 秒，提升显著——此时瓶颈在 I/O 次数过多，每次读取的开销无法被 GDAL 内部缓存充分摊薄。
- `chunk_rows = 128` 时达到最优 3.781 秒，此时 I/O 次数为 210 次，每次读取的数据量恰好与 GDAL 内部块缓存形成较好的匹配。
- `chunk_rows = 32` 出现异常回升（9.107 秒），推测是该条带大小与 GeoTIFF 内部的 tile/block 划分不对齐，导致 GDAL 需要跨 tile 拼接数据，产生了额外的 I/O 和计算开销。`chunk_rows = 64`（5.411 秒）和 `chunk_rows = 256`（5.521 秒）也略慢于 `chunk_rows = 128`，同样可能受到 tile 对齐的影响。
- `chunk_rows = 512` 时执行时间反而略增至 5.670 秒，因为 I/O 次数已很少（53 次），瓶颈从 I/O 转向了每次迭代内的 NumPy 向量化计算量。

##### 3. chunk_rows = 128 是本题的最优选择

综合时间与内存两个维度：

- 内存安全：954.3 MB，低于 1024 MB 限制，留有约 70 MB 余量。
- 执行最快：3.781 秒，是所有达标方案中的最优值。
- I/O 效率：210 次，在不超限的前提下达到了较好的 I/O 摊薄效果。

若运行环境内存更紧张，可降低 `chunk_rows` 至 16 或 64（峰值内存约 886–915 MB），代价是执行时间略增至 4.9–5.4 秒，仍在可接受范围内。

#### 实测峰值内存分析

实测峰值内存为 954.3 MB（`chunk_rows = 128`），远高于纯数据条带的约 10.7 MB（uint8 原始数据）。原因在于内存占用不仅来自程序自身的数据数组，还包括：

- GDAL 内部缓存：GDAL 在读取 GeoTIFF 时会维护内部块缓存（block cache），用于加速随机访问。对于大影像，此缓存可能达到数百 MB。
- Python 运行时开销：Python 解释器自身、NumPy 运行时库、rasterio/GDAL 的 C 扩展库加载等占用数十 MB。
- 临时数组：每个条带内 NoData 过滤产生的 valid 数组（float64 副本）、布尔掩码数组等。

尽管如此，954.3 MB 仍低于 1 GB（1024 MB）限制，达标通过。

### 时间复杂度

- 外层循环遍历所有 210 个条带，每个像素恰好被读取一次。
- 在每个条带内，对每个波段的每个有效像素进行有限次算术运算（均值、方差、最大值、最小值）。
- 时间复杂度：O(W × H × B)，与全量读入方案相同，没有额外开销。

### 与朴素方案对比

| 方案 | 时间复杂度 | 空间复杂度（峰值） | I/O 次数 | 能否通过 1 GB |
|---|---|---|---:|:---:|
| 全量读入 | O(W × H × B) | O(W × H × B) ≈ 2.19 GB | 1 | ❌ OOM |
| 逐波段分块读入 | O(W × H × B) | O(chunk_rows × W) | 210 × 3 = 630 | ✅ 但 I/O 多 |
| 本方案（多波段同时分块） | O(W × H × B) | O(chunk_rows × W × B) | 210 | ✅ 954.3 MB |

本方案在时间复杂度上与全量读入持平，空间复杂度远优于全量读入（满足 1 GB 限制），I/O 次数仅为逐波段分块方案的 1/3。

### 代码实现要点

- 使用 `rasterio` 读取 GeoTIFF，支持任意波段数与 NoData 值。
- `chunk[b_idx]` 返回的是 NumPy view（不复制数据），逐波段遍历时不会产生额外的内存副本。
- 所有统计累加器使用 `float64`（Python float 默认即为 float64），保证大规模数据累加时的计算精度。
- 最大值/最小值在分块间直接取极值合并（min / max），无需特殊公式。
- NoData 过滤使用 NumPy 布尔索引，过滤后直接转 `float64`，避免中间转换步骤。

### 运行方式

```bash
# 安装依赖
pip install rasterio numpy

# 运行统计程序
python solution/Boston.py

# 如果影像文件放在其他位置
python solution/Boston.py --input /path/to/Boston.tif
```

若影像文件名或存放位置不同，可通过 `--input` 指定 GeoTIFF 文件路径。

程序输出各波段的均值、标准差、最大值、最小值，均精确到小数点后 3 位。

<a id="t2"></a>
## 第二题：高光谱遥感影像基础操作
## 第二题：高光谱遥感影像基础操作

### 题目目标

需要完成两个输出：

1. 将高光谱遥感影像可视化为 PNG 图片。
2. 绘制影像中典型地物的光谱曲线，并保存为 PNG 图片。

对应输出文件：

```text
T2/1.png
T2/2.png
```

<a id="t2-data"></a>
### 数据集下载

数据来源：

```text
https://www.ehu.eus/ccwintco/index.php/Hyperspectral_Remote_Sensing_Scenes
```

进入页面后找到 **Salinas scene**，下载以下两个文件：

```text
Salinas_corrected.mat
Salinas_gt.mat
```

在项目根目录下新建 `data` 文件夹，并将下载好的文件放入其中：

```text
data/Salinas_corrected.mat
data/Salinas_gt.mat
```

说明：原始 `.mat` 数据文件较大，仓库中没有上传，需要按上述方式自行下载。

### 数据集与光谱含义

本项目默认使用的 Salinas scene 是 AVIRIS 传感器获取的高光谱数据。`Salinas_corrected.mat` 的空间尺寸为 `512 x 217`，包含 `204` 个有效波段。原始 AVIRIS 数据通常有 `224` 个波段，EHU 提供的 corrected 版本去除了部分水汽吸收等噪声波段，因此剩余 `204` 个波段。

需要注意的是，EHU 页面提供的 Salinas 数据通常表述为 **at-sensor radiance data**。因此，本项目中光谱曲线纵轴默认写作：

```text
Mean at-sensor radiance value (a.u.)
```

也就是平均传感器接收辐亮度/数据值，单位以任意单位 `a.u.` 表示。除非额外进行大气校正或反射率标定，否则不应把它严格表述为地表反射率。

由于 `.mat` 文件中没有直接保存每个波段的中心波长，本项目在绘制 Salinas 光谱曲线时使用 AVIRIS 常见范围 `400 nm - 2500 nm` 做线性近似，并删除 EHU corrected 数据中被去除的波段，从而得到 `204` 个近似波长位置。该处理主要用于增强图像解读和汇报表达；如果有传感器官方精确波长表，应优先替换为官方波长。

### 环境安装

建议使用虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

依赖包括：

```text
numpy
scipy
matplotlib
```

### 代码文件说明

```text
T2/1.py          第一小题，读取高光谱影像，选取 3 个波段生成假彩色图
T2/2.py          第二小题，根据 ground truth 标注提取典型地物，利用矩阵乘法计算每一个地物的平均光谱并绘制曲线
T2/hsi_utils.py  通用工具函数，用于识别 .mat 变量、读取数据和选择类别
```

<a id="t2-run"></a>
### 运行步骤

#### 1. 生成高光谱影像可视化图

运行：

```bash
python T2/1.py
```

默认读取：

```text
data/Salinas_corrected.mat
```

默认输出：

```text
T2/1.png
```

`T2/1.py` 默认采用假彩色合成。对于 Salinas corrected 数据，默认波段组合为：

```text
R = 第 57 波段，约 927 nm，近红外
G = 第 27 波段，约 645 nm，红光
B = 第 17 波段，约 551 nm，绿光
```

该组合相当于“近红外-红-绿”假彩色合成，常用于突出植被差异。显示前会对每个通道做 `2% - 98%` 百分位拉伸，减少极端值对显示效果的影响。若希望使用普通 min-max 拉伸，也可以运行：

```bash
python T2/1.py --stretch minmax
```

输出为一张假彩色图像，可以直观查看不同地物的空间分布。

#### 2. 生成典型地物光谱曲线图

运行：

```bash
python T2/2.py
```

默认读取：

```text
data/Salinas_corrected.mat
data/Salinas_gt.mat
```

默认输出：

```text
T2/2.png
```

`T2/2.py` 默认使用近似波长作为横轴，而不是仅使用波段编号。若只想显示波段编号，可以运行：

```bash
python T2/2.py --x-axis band
```

光谱曲线默认绘制原始平均辐亮度/数据值，不做归一化。若只比较曲线形状、弱化不同地物整体亮度差异，可以使用 min-max 归一化：

```bash
python T2/2.py --normalize minmax
```

如果不传入 `--classes` 参数，程序默认提取 `Salinas_gt.mat` 中所有非零类别（即全地物，共16类）进行绘制。

输出为一幅包含多个子图的光谱曲线图，每条曲线代表一个地物类别，图例中显示类别编号，便于对比不同地物的波谱特征。

### 可选参数

第一小题生成伪彩色照片可以手动指定 RGB 波段：

```bash
python T2/1.py --bands 57 27 17
```

第一小题生成伪彩色照片可以手动指定显示拉伸方式：

```bash
python T2/1.py --stretch minmax
```

第二小题的地物光谱曲线可以手动指定要绘制的地物类别（如只绘制 1, 6, 8 类），但是不推荐：

```bash
python T2/2.py --classes 1,6,8
```

第二小题的地物光谱曲线可以按曲线形状进行归一化显示：

```bash
python T2/2.py --normalize minmax
```

### 更换数据集

代码可以适配 EHU 页面中多数 `.mat + gt.mat` 格式的数据集。例如 Indian Pines：

```bash
python T2/1.py --input data/Indian_pines_corrected.mat --output T2/indian_pines_image.png
python T2/2.py --cube data/Indian_pines_corrected.mat --gt data/Indian_pines_gt.mat --output T2/indian_pines_spectra.png
```

如果自动识别变量失败，可以手动指定 `.mat` 文件中的变量名：

```bash
python T2/1.py --input data/example.mat --variable image_variable
python T2/2.py --cube data/example.mat --gt data/example_gt.mat --cube-variable image_variable --gt-variable gt_variable
```

注意：如果数据集没有 ground truth 标注文件，只能运行 `T2/1.py` 生成影像可视化图，不能按地物类别绘制光谱曲线。

<a id="t2-segmentation"></a>
### 物体分割算法及实现方式

本项目在 `T2/2.py` 中使用的是 **基于 ground truth 标注图的监督式标签掩膜分割**。该方法直接利用数据集官方提供的像素级类别标注，不重新训练分类模型或使用无监督聚类。

为了高效、精确地提取全量地物的平均光谱，本方案在算法和工程实现上进行了两步关键优化：

#### 1. 向量化矩阵乘法替代逐类循环
提取各类别平均光谱的朴素方法是使用 `for` 循环遍历每个类别，通过花式索引（Fancy Indexing）提取像素再求均值。这种方法在 Python 层面效率低下，且内存访问不连续。

本方案将其转化为**线性代数中的矩阵乘法问题**：
- 设有效像素数为 $N$，类别数为 $K$，波段数为 $B$。
- 构造 One-Hot 矩阵 $A$ ($N \times K$)，每一行代表一个像素，其对应的类别列置1，其余为0。
- 图像矩阵 $X$ ($N \times B$)，每一行代表一个像素的光谱。
- 则所有类别的光谱和矩阵 $S = A^T \times X$，形状为 $(K \times B)$。

利用 NumPy 的 `np.dot`（底层调用 BLAS 库），将 $N$ 次 Python 循环转化为一次底层的 C 级别矩阵乘法，利用 SIMD 向量化指令大幅提升计算速度。

#### 2. CUDA 异构加速自动检测
考虑到未来该代码可能应用于大幅宽高光谱影像（$N$ 极大），CPU 矩阵乘法可能成为瓶颈。本方案在代码中引入了 CuPy 库的自动检测逻辑：
- 如果运行环境支持 CUDA 且安装了 CuPy，程序会自动将 `One-Hot` 矩阵和光谱矩阵搬运到 GPU 显存，利用 GPU 数以千计的核心完成并行矩阵乘法。
- 如果没有 GPU，则无缝回退至 NumPy 的 CPU 计算。
这种设计兼顾了实验室无 GPU 环境的兼容性和高性能计算集群上的扩展性。

<a id="t2-memory"></a>
### 运行内存与空间复杂度说明

题目要求注意 1G 运行内存限制。设高光谱影像尺寸为 $H \times W \times B$，有效像素数为 $N$。

#### T2/1.py 的内存处理
程序只从完整高光谱影像中取 3 个波段映射为 RGB，而不是把所有波段都转换成新的大数组。其额外空间复杂度约为 $O(H \times W)$。

#### T2/2.py 的内存处理（全量向量化方案）
本方案采用 One-Hot 矩阵乘法，核心数据结构的空间复杂度如下：
- `cube_valid` 矩阵 ($N \times B$)：存储所有有效像素的光谱。
- `one_hot` 矩阵 ($N \times K$)：存储像素类别映射。
- `sums` 矩阵 ($K \times B$) 与 `mean_spectra` ($K \times B$)：极小。
- 总空间复杂度：$O(N \times (B + K))$

虽然在处理极大影像时，一次性读取 $N \times B$ 可能导致 MLE，但在本题 Salinas 数据中，$N \approx 54000$，上述数组总占用极小。此外，代码内建了安全检查：如果预估内存需求超过 1GB，会主动抛出异常提示缩小类别范围（在未使用流式分块读取的前提下）。

#### 实测结果与性能分析

**1. T2/1.py (假彩色合成) 运行结果**

在 Salinas 数据集上运行，控制台输出如下：

```text
Saved false-color image to T2\1.png
Cube variable: salinas_corrected; shape: (512, 217, 204); RGB bands: (57, 27, 17)
Band wavelength labels: ['57 (~927 nm)', '27 (~645 nm)', '17 (~551 nm)']
Display stretch: percentile; clip percentiles: (2.0, 98.0) 
```

- **内存与时间**：程序仅提取 3 个目标波段进行处理，避免了全波段数据的内存复制。实测峰值内存约为 `147 MB`，运行时间在 1 秒以内，远低于 1GB 限制。
- **可视化效果**：采用近红外-红-绿波段组合，辅以 2%-98% 百分位拉伸，有效抑制了极端高亮像素，突出了植被与土壤的边界细节。

**2. T2/2.py (光谱曲线计算) 运行结果**

控制台输出如下：

```text
Saved spectral-curve plot to T2\2.png
Total elapsed time (main function): 1.1669 seconds
Cube variable: salinas_corrected; GT variable: salinas_gt; shape: (512, 217, 204)
Total Classes count: 16
Classes: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
X-axis: wavelength; normalization: none
Computation device: CPU (NumPy); Matrix multiplication time: 0.0078 seconds
--- Memory usage ---
  cube_valid  (      N x   B float32):    42.12 MB
  one_hot     (      N x   K float32):     3.30 MB
  sums        (      K x   B float32):     0.01 MB
  counts      (      K x   1 float32):     0.00 MB
  mean_spectra(      K x   B float32):     0.01 MB
  Total compute arrays:                   45.45 MB
  Peak memory (tracemalloc):             108.41 MB
```

**性能分析：**
1. **计算效率极高**：得益于底层的 BLAS 加速，对 16 个类别、5万多个像素的矩阵乘法仅耗时 `0.0078` 秒。整个 `main` 函数（含数据读取、预处理、绘图保存）总耗时约 1.17 秒。
2. **内存占用极低**：核心计算数组仅占 `45.45 MB`，加上 Python 运行时和 Matplotlib 绘图开销，峰值内存仅 `108.41 MB`，远低于 1GB 限制。
3. **结果最精确**：直接利用全部像素计算真实平均光谱，去除了随机性，任何时间运行结果均100%一致。

### 采样数量选择依据

在获取各类别平均光谱时，常见做法是对大类别进行随机采样以减少计算量，避免内存溢出。但本方案默认选择**放弃采样，直接使用全量像素计算**，主要依据如下：

1. **数据规模安全**  
   Salinas 数据集的有效像素总数约 5.4 万个，全量提取的 `cube_valid` 矩阵仅占约 42 MB，即使加上 One-Hot 矩阵等辅助结构，总计算内存也不过 45 MB 左右，远未达到 1 GB 限制。不存在 OOM 风险，因此无需通过采样来缩减内存。

2. **消除采样误差与随机性**  
   随机采样会引入不确定性，每次运行可能得到略有差异的光谱曲线，不利于结果复现和精确对比。全量计算得到的平均光谱是真实的总体均值，具有唯一性和可复现性。

3. **不影响计算速度**  
   得益于矩阵乘法的高效实现，5.4 万像素 × 204 波段的计算仅需 0.0078 秒，采样所能节省的时间微乎其微，反而增加了采样本身的代码复杂度和结果解释的成本。

对于未来可能处理的大幅宽高光谱数据（有效像素数远超百万），若内存确实逼近上限，代码亦保留了按类别随机采样或分块处理的扩展接口。此时采样数量的确定需要根据目标内存预算、类别像素总数和所需统计精度综合权衡。原则上在内存允许范围内应取尽可能多的样本，以减少估计方差。


### 实测结果

在 Salinas 数据集上实测峰值内存约为：

```text
T2/1.py 约 147 MB
T2/2.py 约 108 MB
```

两者都明显低于 1G，因此满足题目的运行内存限制。
