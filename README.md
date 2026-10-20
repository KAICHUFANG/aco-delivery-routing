# 基于改进蚁群算法的配送路径优化

一个考虑**交通信号灯**与**多路径选择**的配送路径优化系统。用 A\* 与 Yen's K 最短路径算法预计算备选路径，再以**基于时间的蚁群算法（ACO）**求解多目标点的最优配送顺序。

> 课程项目（群体智能）。含交互式地图编辑器，可自行绘制道路网、放置红绿灯与配送点。

---

## 1. 它解决什么问题

外卖/快递配送的现实约束有三条，传统的"最短距离"路径规划都处理不好：

| 约束 | 传统做法的缺陷 | 本项目的处理 |
|---|---|---|
| **交通信号灯** | 距离最短 ≠ 时间最短，红灯会吃掉优势 | `TrafficLightSimulator` 模拟相位与倒计时，把等待时间计入路径代价 |
| **多路径选择** | 只算一条最短路，遇到拥堵无备选 | `MultiPathFinder` 用 **Yen's K 最短路径**为每个点对预计算 K 条备选路径 |
| **配送顺序** | 访问顺序固定，总时间被顺序拖垮 | `TimeOptimizedACO` 用蚁群算法优化**访问顺序**，信息素按**总耗时**而非总距离更新 |

---

## 2. 核心算法

### 2.1 多路径预计算（`MultiPathFinder`）

- `a_star_search()` —— 标准 A\* 搜索，启发式为曼哈顿距离
- `a_star_search_with_removed_edges()` —— 支持"禁用若干条边"再搜一次，Yen's 算法靠它生成偏离路径
- `yen_k_shortest_paths()` —— **Yen's K 最短路径算法**：先求最短路，再逐个禁用路径上的边求偏离路径，合并取前 K 条

### 2.2 红绿灯建模（`TrafficLightSimulator`）

每个红绿灯有周期 `cycle_time` 与初始绿灯时刻 `initial_green`，`get_light_state()` 与 `get_time_to_next_change()` 负责回答两个问题：**现在是什么灯**、**还要等多久**。到达时刻不同，等待时间就不同——这正是"基于时间的路径代价"的关键。

### 2.3 时间优化蚁群算法（`TimeOptimizedACO`）

```
for 每轮迭代:
    for 每只蚂蚁:
        从起点出发，反复调用 select_next_node() 选下一个配送点
        —— 转移概率 = 信息素^alpha × 启发信息^beta，并带 q0 贪心阈值
        每到一个点，累加"移动时间 + 红绿灯等待时间"
    按每只蚂蚁的**总耗时**更新信息素（evaporation_rate 蒸发 + 短耗时路径加浓）
记录历史最优路径
```

关键参数（当前默认值）：

| 参数 | 默认 | 含义 |
|---|---|---|
| `alpha` | 0.8 | 信息素重要程度 |
| `beta` | 2.0 | 启发信息重要程度 |
| `evaporation_rate` | 0.5 | 信息素蒸发率 |
| `q0` | 0.5 | 贪心阈值（越大越偏向直接选最优） |
| `k_paths` | 3 | 每个点对的备选路径数 |
| `ant_count` | 4 | 蚂蚁数量 |
| `iterations` | 50 | 迭代次数 |

### 2.4 交互式地图编辑器（`MapEditor`）

基于 `matplotlib.widgets` 的可视化编辑器，无需手写坐标：

- 点击/拖拽绘制矩形道路区域，支持橡皮擦
- 一键生成城市网格路网（`create_city_grid`）
- 放置起点、配送点、红绿灯，并配置红绿灯周期
- 导出为 `delivery_map.pkl` 供优化器读取

---

## 3. 环境与运行

### 3.1 安装依赖

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### 3.2 运行路径优化

```bash
python 路径优化器.py
```

程序会优先读取当前目录的 `delivery_map.pkl`；**找不到时自动生成一张测试地图**，所以第一次跑不需要任何数据文件。

运行结束后弹出两张图：
- 最优配送路径在地图上的走向（含红绿灯标记）
- 迭代过程中的最优耗时收敛曲线

### 3.3 运行地图编辑器

```bash
python 地图编辑器.py
```

界面上画好路网、放好点和红绿灯后，点击保存，会在当前目录生成 `delivery_map.pkl`。

---

## 4. 文件说明

| 文件 | 行数 | 作用 |
|---|---|---|
| `路径优化器.py` | 837 | 红绿灯模拟 + A\*/Yen's 多路径 + 时间优化 ACO + 可视化 |
| `地图编辑器.py` | 1006 | matplotlib 交互式地图编辑器，产出地图数据 |
| `delivery_map.pkl` | — | 地图数据（pickle）：`grid_size` / `start` / `delivery_points` / `roads` / `traffic_lights` |
| `delivery_map.txt` | — | 同一份地图的可读版本 |
| `custom_map.pkl` / `.txt` | — | 自建地图数据 |
| `requirements.txt` | — | 依赖声明 |

---

## 5. 已知限制

- **信息素更新是本项目最关键的设计点**，但收敛速度对 `alpha` / `evaporation_rate` 敏感，目前靠手工调参，未做参数自适应
- `k_paths` 固定为 3，未评估 K 值对求解质量的影响
- 红绿灯模型为**固定配时**（周期 + 初始绿灯），未支持感应式信号或绿波协调
- 配送点规模在 10 个量级，点数增多时 Yen's 预计算开销会显著上升
- 尚未补充量化评测集（如不同地图规模下的耗时对比）

---

## 6. 参考

- Yen, J. Y. (1971). *Finding the K Shortest Loopless Paths in a Network*
- Dorigo, M., & Gambardella, L. M. (1997). *Ant Colony System: A Cooperative Learning Approach to the Traveling Salesman Problem*
