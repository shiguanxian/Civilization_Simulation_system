"""空间索引模块 — 环形宇宙工具函数与固定网格空间索引。

此模块提供：
- ring_distance: 环形宇宙中两点最短距离计算
- normalize_position: 坐标标准化到 [0, universe_size) 范围
- SpatialIndex: 固定网格空间索引，用于加速文明邻近查询
- auto_select_cell_size: 根据宇宙参数自动推荐网格大小
"""

import math

from src.entity import Civilization


def ring_distance(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    universe_size: float,
) -> float:
    """计算环形宇宙中两点之间的最短欧几里得距离。

    在环形拓扑中，从 (x1, y1) 到 (x2, y2) 有 4 条路径：
    - 直接路径（不跨边界）
    - 绕左/右边界（x 方向环绕）
    - 绕上/下边界（y 方向环绕）
    - 同时绕两个边界

    取 4 条路径中的最短距离。

    Args:
        x1: 第一个点的 x 坐标。
        y1: 第一个点的 y 坐标。
        x2: 第二个点的 x 坐标。
        y2: 第二个点的 y 坐标。
        universe_size: 宇宙空间边长（光年）。

    Returns:
        两点之间的最短欧几里得距离。
    """
    dx = abs(x1 - x2)
    dy = abs(y1 - y2)
    dx = min(dx, universe_size - dx)
    dy = min(dy, universe_size - dy)
    return (dx * dx + dy * dy) ** 0.5


def normalize_position(
    x: float,
    y: float,
    universe_size: float,
) -> tuple[float, float]:
    """将坐标标准化到 [0, universe_size) 范围内。

    用于处理文明移动后超出边界的情况。

    Args:
        x: x 坐标。
        y: y 坐标。
        universe_size: 宇宙空间边长（光年）。

    Returns:
        标准化后的 (x, y) 坐标元组。
    """
    return (x % universe_size, y % universe_size)


class SpatialIndex:
    """固定网格空间索引。

    将宇宙空间划分为 G×G 个网格单元，每个单元存储其中的文明列表。
    查询时，先定位目标网格，再检查目标网格及其相邻网格。
    """

    def __init__(self, universe_size: float, cell_size: float) -> None:
        """初始化空间索引。

        Args:
            universe_size: 宇宙空间边长（光年）。
            cell_size: 网格单元边长（光年）。
                       推荐值：等于或略大于文明的 detection_range 平均值。
        """
        self.universe_size = universe_size
        self.cell_size = cell_size
        self.grid_size = math.ceil(universe_size / cell_size)

        # 使用一维数组模拟二维网格
        self._grid: list[list[Civilization]] = [
            [] for _ in range(self.grid_size * self.grid_size)
        ]

        # 文明 ID 到网格索引的快速查找映射
        self._id_to_cell: dict[int, int] = {}

    def _cell_index(self, x: float, y: float) -> int:
        """将 (x, y) 坐标映射到网格一维索引。

        处理环形边界：当坐标超出范围时，通过模运算自动环绕。

        Args:
            x: x 坐标（应为标准化后的值，取值范围 [0, universe_size)）。
            y: y 坐标（应为标准化后的值，取值范围 [0, universe_size)）。

        Returns:
            网格一维索引，计算公式：gy * grid_size + gx。
        """
        gx = int(x / self.cell_size) % self.grid_size
        gy = int(y / self.cell_size) % self.grid_size
        return gy * self.grid_size + gx

    def _neighbor_cell_indices(
        self,
        x: float,
        y: float,
        radius: float,
    ) -> list[int]:
        """返回以 (x, y) 为中心、radius 为半径所覆盖的所有网格单元的一维索引。

        由于是环形宇宙，需要考虑环绕边界的网格。
        返回值不包含重复（使用 set 去重）。

        Args:
            x: 中心点 x 坐标。
            y: 中心点 y 坐标。
            radius: 查询半径（光年）。

        Returns:
            覆盖范围内所有网格单元的一维索引列表。
        """
        cx = x / self.cell_size
        cy = y / self.cell_size
        cell_radius = math.ceil(radius / self.cell_size)

        indices: set[int] = set()
        for dy in range(-cell_radius, cell_radius + 1):
            for dx in range(-cell_radius, cell_radius + 1):
                gx = (int(cx) + dx) % self.grid_size
                gy = (int(cy) + dy) % self.grid_size
                indices.add(gy * self.grid_size + gx)
        return list(indices)

    def rebuild(self, civilizations: list[Civilization]) -> None:
        """重建索引，每步开始时调用一次。

        将所有存活的文明重新插入网格。
        复杂度 O(N)。

        Args:
            civilizations: 所有文明的列表（包含已毁灭的文明）。
        """
        # 清空网格
        for cell in self._grid:
            cell.clear()
        self._id_to_cell.clear()

        # 重新插入存活的文明
        for civ in civilizations:
            if civ.is_alive:
                idx = self._cell_index(civ.x, civ.y)
                self._grid[idx].append(civ)
                self._id_to_cell[civ.id] = idx

    def query_neighbors(
        self,
        x: float,
        y: float,
        radius: float,
    ) -> list[Civilization]:
        """查询以 (x, y) 为中心、radius 为半径范围内的所有文明。

        1. 通过 _neighbor_cell_indices 获取覆盖的网格单元。
        2. 收集候选文明。
        3. 使用平方环形距离进行精确过滤（避免 sqrt 计算）。
        4. 排除位于精确查询位置 (x, y) 的文明。

        Args:
            x: 查询中心点 x 坐标。
            y: 查询中心点 y 坐标。
            radius: 查询半径（光年）。

        Returns:
            范围内所有文明（不含查询位置上的文明）的列表。
        """
        # 1. 获取覆盖的网格索引
        cell_indices = self._neighbor_cell_indices(x, y, radius)

        # 2. 收集候选文明
        candidates: list[Civilization] = []
        for idx in cell_indices:
            candidates.extend(self._grid[idx])

        # 3. 精确环形距离过滤（使用平方距离避免 sqrt）
        result: list[Civilization] = []
        radius_sq = radius * radius
        for civ in candidates:
            dx = abs(civ.x - x)
            dy = abs(civ.y - y)
            dx = min(dx, self.universe_size - dx)
            dy = min(dy, self.universe_size - dy)
            if dx * dx + dy * dy <= radius_sq:
                # 4. 排除查询位置上的文明
                if not (civ.x == x and civ.y == y):
                    result.append(civ)

        return result

    def _in_region(
        self,
        x: float,
        y: float,
        x_min: float,
        x_max: float,
        y_min: float,
        y_max: float,
    ) -> bool:
        """判断坐标 (x, y) 是否在矩形区域内（考虑环形包裹）。

        当 x_min > x_max 时，矩形在 x 方向包裹环形边界（分为两段）。
        当 y_min > y_max 时，矩形在 y 方向包裹环形边界。

        Args:
            x: 待检测 x 坐标。
            y: 待检测 y 坐标。
            x_min: 矩形 x 方向下界。
            x_max: 矩形 x 方向上界。
            y_min: 矩形 y 方向下界。
            y_max: 矩形 y 方向上界。

        Returns:
            (x, y) 是否在矩形区域内。
        """
        if x_min <= x_max:
            x_ok = x_min <= x <= x_max
        else:
            x_ok = x >= x_min or x <= x_max

        if y_min <= y_max:
            y_ok = y_min <= y <= y_max
        else:
            y_ok = y >= y_min or y <= y_max

        return x_ok and y_ok

    def query_region(
        self,
        x_min: float,
        x_max: float,
        y_min: float,
        y_max: float,
    ) -> list[Civilization]:
        """查询矩形区域 [x_min, x_max] × [y_min, y_max] 内的所有文明。

        用于黑暗森林打击（大范围毁灭）等场景。
        需要考虑环形边界情况：当 x_min > x_max 时矩形在 x 方向包裹，
        当 y_min > y_max 时在 y 方向包裹。

        实现策略：
        - 计算矩形覆盖的网格行列范围。
        - 对于包裹的情况，拆分为两个连续范围。
        - 遍历覆盖网格，收集候选文明。
        - 使用 _in_region 进行精确边界过滤。

        Args:
            x_min: 矩形 x 方向下界。
            x_max: 矩形 x 方向上界。
            y_min: 矩形 y 方向下界。
            y_max: 矩形 y 方向上界。

        Returns:
            矩形区域内的文明列表。
        """
        # 计算 x 方向网格范围
        if x_min <= x_max:
            gx_ranges: list[tuple[int, int]] = [
                (int(x_min / self.cell_size), int(x_max / self.cell_size)),
            ]
        else:
            gx_ranges = [
                (int(x_min / self.cell_size), self.grid_size - 1),
                (0, int(x_max / self.cell_size)),
            ]

        # 计算 y 方向网格范围
        if y_min <= y_max:
            gy_ranges: list[tuple[int, int]] = [
                (int(y_min / self.cell_size), int(y_max / self.cell_size)),
            ]
        else:
            gy_ranges = [
                (int(y_min / self.cell_size), self.grid_size - 1),
                (0, int(y_max / self.cell_size)),
            ]

        # 遍历覆盖网格并收集文明
        result: list[Civilization] = []
        for gy_start, gy_end in gy_ranges:
            for gx_start, gx_end in gx_ranges:
                for gy in range(gy_start, gy_end + 1):
                    for gx in range(gx_start, gx_end + 1):
                        idx = gy * self.grid_size + gx
                        for civ in self._grid[idx]:
                            if self._in_region(
                                civ.x, civ.y, x_min, x_max, y_min, y_max
                            ):
                                result.append(civ)
        return result

    def remove_civilization(self, civ_id: int) -> None:
        """从索引中移除指定文明。

        当文明被毁灭时调用此方法，将其从网格和 _id_to_cell 中移除。
        如果文明 ID 不在索引中，静默忽略。

        注意：如果每步结束后都调用 rebuild，此方法是可选优化。
        但为了支持"在 step 中间动态移除文明"的场景，保留此接口。

        Args:
            civ_id: 要移除的文明 ID。
        """
        flat_idx = self._id_to_cell.get(civ_id)
        if flat_idx is not None:
            cell = self._grid[flat_idx]
            self._grid[flat_idx] = [c for c in cell if c.id != civ_id]
            del self._id_to_cell[civ_id]

    @property
    def cell_count(self) -> int:
        """返回非空网格的数量。

        Returns:
            至少包含一个文明的网格单元数。
        """
        return sum(1 for cell in self._grid if cell)

    @property
    def load_balance_stats(self) -> dict[str, float]:
        """返回网格负载统计信息，用于性能分析。

        Returns:
            包含以下键的字典：
            - min: 非空网格的最小文明数（0 如果全空）
            - max: 所有网格的最大文明数
            - avg: 所有网格的平均文明数（含空网格）
            - empty_ratio: 空网格比例（0.0 ~ 1.0）
        """
        counts = [len(cell) for cell in self._grid]
        total_cells = len(self._grid)
        non_empty = [c for c in counts if c > 0]

        return {
            "min": min(non_empty) if non_empty else 0,
            "max": max(counts) if counts else 0,
            "avg": sum(counts) / total_cells if total_cells > 0 else 0.0,
            "empty_ratio": (
                (total_cells - len(non_empty)) / total_cells if total_cells > 0 else 0.0
            ),
        }


def auto_select_cell_size(
    universe_size: float,
    civ_count: int,
    avg_detection_range: float,
    cpu_score: float,
) -> float:
    """自动选择最优网格单元大小。

    策略：
    1. 基础值 = avg_detection_range（让查询覆盖约 3×3 网格）。
    2. 密度调整值：使每个网格平均文明数 ≈ 10~50。
       cell_size = universe_size * sqrt(target_per_cell / civ_count)。
    3. 取两者的几何平均。
    4. 根据 CPU 评分微调：高分用更细网格（小 cell_size），低分用更粗网格。
    5. 最终结果限制在 [min_cell, max_cell] 范围内。

    Args:
        universe_size: 宇宙空间边长（光年）。
        civ_count: 文明总数。
        avg_detection_range: 文明平均探测范围（光年）。
        cpu_score: CPU 基准评分（0.5 ~ 10.0），越高表示性能越好。

    Returns:
        推荐的网格单元大小（光年），保留一位小数。

    Example:
        >>> auto_select_cell_size(10000.0, 5000, 200.0, 5.0)
        300.0  # 示例值，实际结果取决于具体参数
    """
    # 1. 基于探测范围的基础值
    base_by_range = avg_detection_range

    # 2. 基于密度的调整值（目标每网格 ~30 个文明）
    target_per_cell = 30.0
    cells_needed = civ_count / target_per_cell
    base_by_density = math.sqrt(
        universe_size * universe_size / max(cells_needed, 1.0)
    )

    # 3. 取几何平均
    cell_size = math.sqrt(base_by_range * base_by_density)

    # 4. CPU 评分微调（高分 → 更细网格）
    # cpu_score 通常在 [0.5, 10.0] 范围
    cpu_factor = 0.85 + (cpu_score / 10.0) * 0.3  # [0.865, 1.15]
    cell_size = cell_size / cpu_factor

    # 5. 限制在合理范围内
    min_cell = max(avg_detection_range * 0.3, 10.0)
    max_cell = max(avg_detection_range * 3.0, 100.0)
    cell_size = max(min_cell, min(cell_size, max_cell))

    return round(cell_size, 1)
