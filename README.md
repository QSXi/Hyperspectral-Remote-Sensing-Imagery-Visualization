# RSIDEA 基础编程能力测试解答

本项目合并整理图片中两道遥感影像基础操作题的解答。数据文件体积较大，仓库只上传代码、说明文档和必要输出图，不上传原始遥感数据。

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

### 数据集下载

数据来源：

```text
https://pan.baidu.com/s/1FiDIgaxN2GbQk1I4Dr73Aw
```

进入百度网盘后下载 `Boston.tif` 文件。文件大小约为 2 GB（压缩后），推荐下载后放入项目根目录：

```text
Boston.tif
solution/
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

### 运行步骤

#### 1. 生成各波段统计结果

运行：

```bash
python solution/Boston.py
```

默认读取：

```text
Boston.tif
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

`solution/Boston.py`：分块读取遥感影像，统计各波段均值、标准差、最大值、最小值。

程序核心逻辑全部在 `Boston.py` 中实现，无额外依赖文件。

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

### 代码文件说明

```text
T2/1.py          读取高光谱影像，选取 3 个波段生成假彩色图
T2/2.py          根据 ground truth 标注提取典型地物，绘制平均光谱曲线
T2/hsi_utils.py  通用工具函数，用于识别 .mat 变量、读取数据和选择类别
requirements.txt Python 依赖列表
```

### 物体分割算法及实现方式

本项目在 `T2/2.py` 中使用的是 **基于 ground truth 标注图的监督式标签掩膜分割**。该方法不重新训练分类模型，也不使用 K-means、阈值分割或深度学习语义分割，而是直接利用数据集官方提供的像素级类别标注。

EHU 提供的 `Salinas_gt.mat` 是一张二维标注图，其尺寸与高光谱影像的空间尺寸一致。标注图中每个像素值表示该位置所属的地物类别：

```text
0 表示未标注背景
1, 2, 3, ... 表示不同地物类别
```

算法步骤如下：

1. 读取高光谱影像 `Salinas_corrected.mat`，得到三维数组 `cube`，形状为 `H x W x B`。
2. 读取地物标注文件 `Salinas_gt.mat`，得到二维数组 `gt`，形状为 `H x W`。
3. 对某个类别 `class_id`，构造标签掩膜：

```python
gt == class_id
```

4. 使用 `np.flatnonzero(gt.ravel() == class_id)` 找到该类别所有像素位置。
5. 将一维位置还原为行列坐标：

```python
rows, cols = np.unravel_index(flat_indices, gt.shape)
```

6. 从高光谱影像中取出这些像素的完整光谱：

```python
spectra = cube[rows, cols, :]
```

7. 对该类别像素的光谱求平均，得到该地物类别的代表性光谱曲线：

```python
spectrum = spectra.mean(axis=0)
```

因此，本项目的“物体分割”本质上是利用官方标注图将不同地物类别的像素分离出来，再对每个类别计算平均光谱。这样做的优点是类别边界和类别编号来自数据集官方标注，结果稳定、可解释，适合本题要求的“可视化影像中包含地物的光谱曲线”。

需要注意：如果更换的数据集没有 ground truth 标注文件，则只能生成高光谱影像可视化图，不能使用本方法按地物类别绘制光谱曲线。

### 可选参数

手动指定 RGB 波段：

```bash
python T2/1.py --bands 57 27 17
```

手动指定显示拉伸方式：

```bash
python T2/1.py --stretch minmax
```

手动指定要绘制的地物类别：

```bash
python T2/2.py --classes 1,6,8,10,15
```

降低光谱曲线计算时每类抽样像素数：

```bash
python T2/2.py --max-pixels 500
```

按曲线形状进行归一化显示：

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

### 运行内存与空间复杂度说明

题目要求注意 1G 运行内存限制。设高光谱影像尺寸为：

```text
H x W x B
```

其中 `H` 为图像高度，`W` 为图像宽度，`B` 为波段数。Salinas corrected 数据约为：

```text
512 x 217 x 204
```

因此主要内存来自读取后的高光谱三维数组，空间复杂度为：

```text
O(H * W * B)
```

本项目的低内存处理重点是控制“额外空间”，避免在读取原始数据后继续产生多个同样大小的三维副本。

#### T2/1.py 的内存处理

`T2/1.py` 用于生成假彩色图。程序只从完整高光谱影像中取 3 个波段映射为 RGB，而不是把所有波段都转换成新的大数组。

额外空间主要包括：

```text
3 个单波段数组 + 1 个 RGB 图像数组
```

其额外空间复杂度约为：

```text
O(H * W)
```

这样做的原因是：题目只要求输出一张可视化 PNG，不需要对全部 `B` 个波段同时进行可视化处理，所以没有必要复制完整的 `H x W x B` 数据。

#### T2/2.py 的内存处理

`T2/2.py` 用于绘制典型地物光谱曲线。若直接取出某一类别的全部像素光谱，数据量可能随类别像素数增大而明显增加。因此程序默认对每个类别最多抽样 `2000` 个像素，再计算平均光谱。

设每类最多抽样像素数为 `S`，波段数为 `B`。程序逐个类别处理，不会同时保存所有类别的采样光谱矩阵，因此峰值额外空间主要来自当前类别的采样光谱：

```text
O(S * B)
```

如果绘制 `K` 个类别，最终保存的平均光谱曲线只需要约：

```text
O(K * B)
```

默认情况下 `S = 2000`，远小于整幅影像的像素总数 `H * W`，因此可以避免为某些大类别一次性复制过多像素光谱。

#### 采样数量选择依据

`--max-pixels` 的默认值 `2000` 不是由公式直接推出的固定常数，而是根据本题数据规模、运行内存限制和光谱曲线稳定性选取的折中值。

在 Salinas 数据集中，程序默认选择样本数最多的 5 个非背景类别：

```text
8  Grapes_untrained        11271 像素
15 Vinyard_untrained       7268 像素
9  Soil_vinyard_develop    6203 像素
6  Stubble                 3959 像素
2  Brocoli_green_weeds_2   3726 像素
```

当 `S = 2000` 时，每类至少使用了约一半或较大比例的像素样本，且每个类别的 `float32` 采样光谱矩阵大小约为：

```text
2000 x 204 x 4 bytes ≈ 1.63 MB
```

即使考虑索引和临时数组，额外内存仍然很小。

为了验证不同采样数量的影响，使用“全量类别像素计算出的平均光谱”作为参考值，对 `1000, 1500, 2000, 2500, 3000` 进行对比。每个采样数量使用 100 个随机种子重复实验，评价指标为：

- 平均相对 L2 误差：采样平均光谱与全量平均光谱之间的整体差异。
- 最大相对 L2 误差：所有重复实验和类别中的最坏整体差异。
- 平均最大单波段相对误差：每条曲线中单个波段最大偏差的平均值。

其中，`L2` 指欧几里得距离。对于一条包含 `B` 个波段的光谱曲线，可以把它看成一个 `B` 维向量。若 `A` 表示全量像素计算出的平均光谱，`B_sample` 表示抽样像素计算出的平均光谱，则 L2 误差为：

```text
||B_sample - A||_2
```

也就是把每个波段上的差值平方后求和，再开方。相对 L2 误差是在此基础上除以全量平均光谱自身的长度：

```text
相对 L2 误差 = ||B_sample - A||_2 / ||A||_2
```

因此，相对 L2 误差可以理解为“抽样光谱曲线相对于全量光谱曲线的整体偏差百分比”。例如 `0.0934%` 表示抽样曲线与全量曲线的整体差异约为全量曲线尺度的 `0.0934%`。

结果如下：

| 每类最多采样数 S | 平均相对 L2 误差 | 最大相对 L2 误差 | 平均最大单波段相对误差 | 每类采样矩阵约占用 |
| ---: | ---: | ---: | ---: | ---: |
| 1000 | 0.1496% | 0.4811% | 1.7951% | 0.82 MB |
| 1500 | 0.1182% | 0.4965% | 1.3342% | 1.22 MB |
| 2000 | 0.0934% | 0.3441% | 1.0848% | 1.63 MB |
| 2500 | 0.0763% | 0.2829% | 0.8436% | 2.04 MB |
| 3000 | 0.0614% | 0.3180% | 0.7019% | 2.45 MB |

从表中可以看出，采样数量增大时，平均误差整体下降，曲线会更接近全量均值；但从 `2000` 增加到 `3000` 后，平均相对 L2 误差只从约 `0.0934%` 降到约 `0.0614%`，提升幅度已经较小。

因此，本项目默认使用 `S = 2000` 作为平衡策略：

- 相比 `1000` 和 `1500`，曲线稳定性更好。
- 相比 `2500` 和 `3000`，内存和运行时间更低。
- 在本题 Salinas 数据上，平均相对 L2 误差已经低于 `0.1%`，足以用于作业中的光谱曲线可视化。

如果只追求更平滑、更接近全量均值的曲线，可以设置：

```bash
python T2/2.py --max-pixels 3000
```

如果运行环境更紧张，可以降低为：

```bash
python T2/2.py --max-pixels 500
```

#### 实测结果

在 Salinas 数据集上实测峰值内存约为：

```text
T2/1.py 约 147 MB
T2/2.py 约 164 MB
```

两者都明显低于 1G，因此满足题目的运行内存限制。
