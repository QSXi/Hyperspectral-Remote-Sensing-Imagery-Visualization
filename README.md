# 高光谱遥感影像基础操作

本项目用于完成“高光谱遥感影像基础操作”题目，默认使用 EHU 页面中的 **Salinas scene** 数据集。

## 题目目标

需要完成两个输出：

1. 将高光谱遥感影像可视化为 PNG 图片。
2. 绘制影像中典型地物的光谱曲线，并保存为 PNG 图片。

对应输出文件：

```text
T2/1.png
T2/2.png
```

## 数据集下载

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

## 环境安装

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

## 运行步骤

### 1. 生成高光谱影像可视化图

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

### 2. 生成典型地物光谱曲线图

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

## 代码文件说明

```text
T2/1.py          读取高光谱影像，选取 3 个波段生成假彩色图
T2/2.py          根据 ground truth 标注提取典型地物，绘制平均光谱曲线
T2/hsi_utils.py  通用工具函数，用于识别 .mat 变量、读取数据和选择类别
requirements.txt Python 依赖列表
```

## 物体分割算法及实现方式

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

## 可选参数

手动指定 RGB 波段：

```bash
python T2/1.py --bands 57 27 17
```

手动指定要绘制的地物类别：

```bash
python T2/2.py --classes 1,6,8,10,15
```

降低光谱曲线计算时每类抽样像素数：

```bash
python T2/2.py --max-pixels 500
```

## 更换数据集

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

## 运行内存与空间复杂度说明

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

### T2/1.py 的内存处理

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

### T2/2.py 的内存处理

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

### 采样数量选择依据

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

### 实测结果

在 Salinas 数据集上实测峰值内存约为：

```text
T2/1.py 约 147 MB
T2/2.py 约 164 MB
```

两者都明显低于 1G，因此满足题目的运行内存限制。
