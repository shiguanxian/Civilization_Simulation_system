# 详细设计文档 — 第3部分：空间索引模块

## 1. 模块概述

### 1.1 模块职责

`src/spatial.py` 负责实现空间索引，加速文明之间的邻近查询。

### 1.2 为什么需要空间索引

模拟中每步都需要执行大量邻近查询——每个文明都要在探测范围内查找其他文明。

如果没有空间索引，每次查询需遍历所有文明：**O(N²)** 复杂度。
使用空间网格索引后，平均复杂度降为 **O(N × k)**，其中 k 是每个网格内的平均文明数。

### 1.3 技术选型

**固定网格索引（Fixed Grid Index）**，原因：
- 实现简单、极低开销
- 文明分布相对均匀时性能极好
- 重建索引为 **O(N)**，查询为 **O(1)**（查找网格）+ **O(k)**（遍历网格内元素）
- 适合"每步重建"的更新模式（每步所有文明可能移动/变化）

---

## 2. 环形宇宙坐标处理

由于宇宙边界是环形的（左←→右相连，上←→下相连），距离计算和网格映射都需要考虑环形拓扑。

### 2.1 环形距离公式

```python
def ring_distance(x1: float, y1: float, x2: float, y2: float, 
                  universe_size: float) -> float:
    """
    计算环形宇宙中两点之间的最短距离。
    
    在环形拓扑中，从 (x1, y1) 到 (x2, y2) 有 4 条路径：
    - 直接路径
    - 绕左/右边界
    - 绕上/下边界
    - 同时绕两个边界
    
    取最短距离。
    """
    dx = abs(x1 - x2)
    dy = abs(y1 - y2)
    # 环形：考虑绕边界的情况
    dx = min(dx, universe_size - dx)
    dy = min(dy, universe_size - dy)
    return (dx * dx + dy * dy) ** 0.5
```

### 2.2 环形坐标标准化

```python
def normalize_position(x: float, y: float, universe_size: float) -> tuple[float, float]:
    """
    将坐标标准化到 [0, universe_size) 范围内。
    用于处理文明移动后超出边界的情况。
    """
    return (x % universe_size, y % universe_size)
```

---

## 3. SpatialIndex 类设计

### 3.1 核心数据结构

```python
class SpatialIndex:
    """
    固定网格空间索引。
    
    将宇宙空间划分为 G×G 个网格单元，每个单元存储其中的文明列表。
    查询时，先定位目标网格，再检查目标网格及其相邻网格。
    """

    def __init__(self, universe_size: float, cell_size: float):
        """
        初始化空间索引。
        
        参数：
            universe_size: 宇宙空间边长（光年）
            cell_size: 网格单元边长（光年）
                      推荐值：等于或略大于文明的 detection_range 平均值
        """
        self.universe_size = universe_size
        self.cell_size = cell_size
        self.grid_size = math.ceil(universe_size / cell_size)  
        # 每行/列的网格数
        
        # 网格数据：二维列表，每个元素是 list[Civilization]
        # 使用一维数组模拟二维以提高 cache 友好性
        self._grid: list[list[Civilization]] = [
            [] for _ in range(self.grid_size * self.grid_size)
        ]
        
        # 按文明 id 的快速查找映射（用于删除已毁灭的文明）
        self._id_to_cell: dict[int, tuple[int, int]] = {}

    def _cell_index(self, x: float, y: float) -> int:
        """
        将 (x, y) 坐标映射到网格一维索引。
        处理环形边界。
        """
        gx = int(x / self.cell_size) % self.grid_size
        gy = int(y / self.cell_size) % self.grid_size
        return gy * self.grid_size + gx

    def _neighbor_cell_indices(self, x: float, y: float, 
                                radius: float) -> list[int]:
        """
        返回以 (x, y) 为中心、radius 为半径所覆盖的所有网格单元的一维索引。
        
        由于是环形宇宙，需要考虑环绕边界的网格。
        返回值可能包含重复（如果半径极大覆盖了全部空间）。
        """
        # 计算覆盖范围所处的网格行列范围
        cx = x / self.cell_size
        cy = y / self.cell_size
        cell_radius = math.ceil(radius / self.cell_size)
        
        indices = set()
        for dy in range(-cell_radius, cell_radius + 1):
            for dx in range(-cell_radius, cell_radius + 1):
                gx = (int(cx) + dx) % self.grid_size
                gy = (int(cy) + dy) % self.grid_size
                indices.add(gy * self.grid_size + gx)
        return list(indices)
```

### 3.2 核心方法

```python
    def rebuild(self, civilizations: list[Civilization]) -> None:
        """
        重建索引。每步开始时调用一次。
        
        将所有存活的文明重新插入网格。
        复杂度 O(N)。
        """
        # 清空网格
        for cell in self._grid:
            cell.clear()
        self._id_to_cell.clear()
        
        # 重新插入
        for civ in civilizations:
            if civ.is_alive:
                idx = self._cell_index(civ.x, civ.y)
                self._grid[idx].append(civ)
                self._id_to_cell[civ.id] = idx

    def query_neighbors(self, x: float, y: float, 
                        radius: float) -> list[Civilization]:
        """
        查询以 (x, y) 为中心、radius 为半径范围内的所有文明。
        
        复杂度 O(k)，k = 覆盖网格内的总文明数。
        返回的列表中不包含位于 (x, y) 的原文明（如果有的话通过 id 排除）。
        """
        # 1. 获取覆盖的网格索引
        cell_indices = self._neighbor_cell_indices(x, y, radius)
        
        # 2. 收集候选文明
        candidates = []
        for idx in cell_indices:
            candidates.extend(self._grid[idx])
        
        # 3. 精确距离过滤
        result = []
        radius_sq = radius * radius
        for civ in candidates:
            dx = abs(civ.x - x)
            dy = abs(civ.y - y)
            dx = min(dx, self.universe_size - dx)
            dy = min(dy, self.universe_size - dy)
            if dx * dx + dy * dy <= radius_sq:
                result.append(civ)
        
        return result

    def query_region(self, x_min: float, x_max: float,
                     y_min: float, y_max: float) -> list[Civilization]:
        """
        查询矩形区域内的所有文明。
        用于黑暗森林打击（大范围毁灭）。
        需要考虑环形边界情况。
        """
        ...

    def remove_civilization(self, civ_id: int) -> None:
        """
        从索引中移除某个文明（当文明被毁灭时调用）。
        
        如果每次 step 结束后都 rebuild，这个方法的调用是可选优化。
        但为了支持"在 step 中间动态移除文明"的场景，保留此接口。
        """
        if civ_id in self._id_to_cell:
            idx = self._id_to_cell[civ_id]
            cell = self._grid[idx]
            self._grid[idx] = [c for c in cell if c.id != civ_id]
            del self._id_to_cell[civ_id]

    @property
    def cell_count(self) -> int:
        """返回非空网格数。"""
        return sum(1 for cell in self._grid if cell)

    @property
    def load_balance_stats(self) -> dict:
        """
        返回网格负载统计，用于性能分析：
        - min/max/avg 每个网格的文明数
        - 空网格比例
        """
        ...
```

---

## 4. 网格尺寸选择策略

### 4.1 自动选择逻辑

```python
def auto_select_cell_size(universe_size: float, 
                          civ_count: int,
                          avg_detection_range: float,
                          cpu_score: float) -> float:
    """
    自动选择最优网格单元大小。
    
    策略：
    1. 基础值 = avg_detection_range（让查询覆盖约 3×3 网格）
    2. 调整：使每个网格平均文明数 ≈ 10~50
       grid_cell_size = sqrt(universe_size² / (civ_count / target_per_cell))
    3. 取两者的中间值
    4. 根据 CPU 评分微调（高分用更细网格，低分用更粗网格）
    
    最终结果限制在 [min_cell, max_cell] 范围内。
    """
    ...
```

### 4.2 常见场景的推荐值

| 宇宙大小 | 文明数 | 探测范围均值 | 推荐网格大小 | 每网格文明数 |
|----------|--------|-------------|-------------|-------------|
| 10,000 | 5,000 | 200 | 200~300 | 10~25 |
| 10,000 | 20,000 | 200 | 100~150 | 20~45 |
| 100,000 | 10,000 | 500 | 500~800 | 6~16 |

---

## 5. 模块的独立可测试性

### 5.1 测试要点

```python
# tests/test_spatial.py

def test_ring_distance():
    """验证环形距离计算正确。"""
    ...

def test_normalize_position():
    """验证坐标标准化正确。"""
    ...

def test_rebuild_empty():
    """验证空索引重建后查询返回空列表。"""
    ...

def test_rebuild_single():
    """验证索引中包含单个文明时，精确位置查询返回该文明。"""
    ...

def test_query_neighbors_found():
    """验证在一定范围内的文明能被查询到。"""
    ...

def test_query_neighbors_not_found():
    """验证超出范围的文明不会被查询到。"""
    ...

def test_query_neighbors_ring_boundary():
    """验证跨环形边界的查询正确。"""
    ...

def test_query_neighbors_self_exclusion():
    """验证查询不返回自身。"""
    ...

def test_remove_civilization():
    """验证移除文明后查询不到。"""
    ...

def test_multiple_cells():
    """验证多个网格的插入和查询正确。"""
    ...

def test_large_scale_performance():
    """
    性能测试：创建 10000 个文明并查询，验证耗时在可接受范围内。
    使用 pytest.mark.benchmark 或手动计时。
    """
    ...
```

---

## 6. 依赖关系

```
spatial.py → entity.py（使用 Civilization 类型）
spatial.py → config.py（使用 SimulationConfig.universe_size）
```

---

*下一篇：`detailed-design-04-simulation.md` — 模拟引擎模块详细设计*
