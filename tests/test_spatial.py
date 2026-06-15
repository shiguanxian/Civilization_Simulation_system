"""空间索引模块测试 — 环形距离工具与 SpatialIndex 核心功能。"""

import math

from src.entity import Civilization
from src.spatial import (
    SpatialIndex,
    auto_select_cell_size,
    normalize_position,
    ring_distance,
)

# =============================================================================
# 环形距离工具函数测试
# =============================================================================


def test_ring_distance_direct() -> None:
    """验证两点间直接距离（不跨边界）计算正确。"""
    dist = ring_distance(1.0, 1.0, 4.0, 5.0, universe_size=100.0)
    # dx=3, dy=4 => sqrt(9+16)=5
    assert math.isclose(dist, 5.0)


def test_ring_distance_wrap_x() -> None:
    """验证绕左/右边界（x 方向环绕）的距离计算正确。"""
    dist = ring_distance(1.0, 1.0, 98.0, 1.0, universe_size=100.0)
    # dx=min(97,3)=3, dy=0 => sqrt(9)=3
    assert math.isclose(dist, 3.0)


def test_ring_distance_wrap_y() -> None:
    """验证绕上/下边界（y 方向环绕）的距离计算正确。"""
    dist = ring_distance(1.0, 1.0, 1.0, 97.0, universe_size=100.0)
    # dx=0, dy=min(96,4)=4 => sqrt(16)=4
    assert math.isclose(dist, 4.0)


def test_ring_distance_wrap_both() -> None:
    """验证同时绕两个边界的距离计算正确。"""
    dist = ring_distance(1.0, 1.0, 98.0, 97.0, universe_size=100.0)
    # dx=min(97,3)=3, dy=min(96,4)=4 => sqrt(9+16)=5
    assert math.isclose(dist, 5.0)


def test_ring_distance_exact_half() -> None:
    """验证两点在完全对角位置时距离计算正确。"""
    dist = ring_distance(0.0, 0.0, 50.0, 50.0, universe_size=100.0)
    # dx=50, dy=50, both min(50,50)=50 => sqrt(2500+2500)=~70.7107
    assert math.isclose(dist, math.sqrt(5000.0))


def test_ring_distance_zero() -> None:
    """验证相同点距离为 0。"""
    dist = ring_distance(42.0, 73.0, 42.0, 73.0, universe_size=100.0)
    assert math.isclose(dist, 0.0)


# =============================================================================
# 坐标标准化测试
# =============================================================================


def test_normalize_position_within_bounds() -> None:
    """验证已在该范围内的坐标不变。"""
    x, y = normalize_position(25.0, 75.0, universe_size=100.0)
    assert math.isclose(x, 25.0)
    assert math.isclose(y, 75.0)


def test_normalize_position_overflow() -> None:
    """验证超出上界的坐标被正确包裹。"""
    x, y = normalize_position(105.0, 200.0, universe_size=100.0)
    assert math.isclose(x, 5.0)
    assert math.isclose(y, 0.0)


def test_normalize_position_negative() -> None:
    """验证负坐标被正确包裹。"""
    x, y = normalize_position(-5.0, -10.0, universe_size=100.0)
    assert math.isclose(x, 95.0)
    assert math.isclose(y, 90.0)


def test_normalize_position_exact_boundary() -> None:
    """验证精确等于边界值的坐标被包裹到 0。"""
    x, y = normalize_position(100.0, 100.0, universe_size=100.0)
    assert math.isclose(x, 0.0)
    assert math.isclose(y, 0.0)


# =============================================================================
# SpatialIndex 核心数据结构测试
# =============================================================================


def test_spatial_index_init() -> None:
    """验证 SpatialIndex 初始化正确。"""
    index = SpatialIndex(universe_size=100.0, cell_size=10.0)
    assert index.universe_size == 100.0
    assert index.cell_size == 10.0
    assert index.grid_size == 10  # ceil(100/10)
    assert len(index._grid) == 100  # 10 * 10
    assert all(len(cell) == 0 for cell in index._grid)
    assert len(index._id_to_cell) == 0


def test_spatial_index_init_uneven() -> None:
    """验证 universe_size 不是 cell_size 整数倍时 grid_size 取上整。"""
    index = SpatialIndex(universe_size=100.0, cell_size=30.0)
    assert index.grid_size == 4  # ceil(100/30)
    assert len(index._grid) == 16  # 4 * 4


# =============================================================================
# _cell_index 测试
# =============================================================================


def test_cell_index_center() -> None:
    """验证坐标到网格索引的映射正确。"""
    index = SpatialIndex(universe_size=100.0, cell_size=10.0)
    # (15, 25) => gx = int(15/10) = 1, gy = int(25/10) = 2 => idx = 2*10+1 = 21
    assert index._cell_index(15.0, 25.0) == 21


def test_cell_index_origin() -> None:
    """验证原点位置的网格索引为 0。"""
    index = SpatialIndex(universe_size=100.0, cell_size=10.0)
    assert index._cell_index(0.0, 0.0) == 0


def test_cell_index_ring_boundary() -> None:
    """验证靠近边界的坐标通过模运算回到有效网格范围。"""
    index = SpatialIndex(universe_size=100.0, cell_size=10.0)
    # x=99 => int(99/10)=9 % 10 = 9
    # y=99 => int(99/10)=9 % 10 = 9
    # idx = 9*10+9 = 99
    assert index._cell_index(99.0, 99.0) == 99


def test_cell_index_edge() -> None:
    """验证坐标位于网格边界时正确映射。"""
    index = SpatialIndex(universe_size=100.0, cell_size=10.0)
    # x=10 => int(10/10)=1
    # y=0  => int(0/10)=0
    # idx = 0*10+1 = 1
    assert index._cell_index(10.0, 0.0) == 1
    # x=0  => int(0/10)=0
    # y=10 => int(10/10)=1
    # idx = 1*10+0 = 10
    assert index._cell_index(0.0, 10.0) == 10


# =============================================================================
# _neighbor_cell_indices 测试
# =============================================================================


def test_neighbor_cell_indices_radius_zero() -> None:
    """验证半径为 0 时只返回中心网格。"""
    index = SpatialIndex(universe_size=100.0, cell_size=10.0)
    # (25, 35) => cx=2.5 => int(cx)=2, cy=3.5 => int(cy)=3 => center idx=32
    indices = index._neighbor_cell_indices(25.0, 35.0, radius=0.0)
    assert len(indices) == 1
    assert indices[0] == 32


def test_neighbor_cell_indices_small_radius() -> None:
    """验证小半径覆盖 3×3 网格。"""
    index = SpatialIndex(universe_size=100.0, cell_size=10.0)
    # (25, 35) => cx=2.5 => int(cx)=2, cy=3.5 => int(cy)=3
    # cell_radius = ceil(10/10) = 1
    # dx ∈ [-1,0,1], dy ∈ [-1,0,1] => 3×3 = 9 cells
    indices = index._neighbor_cell_indices(25.0, 35.0, radius=10.0)
    assert len(indices) == 9

    # 验证包含中心和邻居网格索引
    expected_indices: set[int] = set()
    for gy in range(2, 5):  # 3 rows
        for gx in range(1, 4):  # 3 cols
            expected_indices.add(gy * 10 + gx)
    assert set(indices) == expected_indices


def test_neighbor_cell_indices_larger_radius() -> None:
    """验证较大半径覆盖 5×5 网格。"""
    index = SpatialIndex(universe_size=100.0, cell_size=10.0)
    # (25, 35) => int(cx)=2, int(cy)=3
    # cell_radius = ceil(25/10) = 3
    # dx ∈ [-3,-2,-1,0,1,2,3], dy ∈ [-3,-2,-1,0,1,2,3] => 7×7 = 49 cells
    indices = index._neighbor_cell_indices(25.0, 35.0, radius=25.0)
    assert len(indices) == 49

    expected_indices: set[int] = set()
    for gy in range(0, 10):  # all rows
        for gx in range(0, 10):  # all cols
            expected_indices.add(gy * 10 + gx)
    # With grid_size=10 and cell_radius=3, int(cx)=2, int(cy)=3
    # gy = (3 + dy) % 10, dy ∈ [-3,3] => gy ∈ [0,6]
    # gx = (2 + dx) % 10, dx ∈ [-3,3] => gx ∈ [9,0,1,2,3,4,5]
    actual = set(indices)
    assert len(actual) == 49
    # 验证特定边界单元格
    assert 0 * 10 + 9 in actual  # (0, 9)
    assert 0 * 10 + 0 in actual  # (0, 0)
    assert 6 * 10 + 5 in actual  # (6, 5)
    # (7, 2) 不应在范围内：gy=7 > 6
    assert 7 * 10 + 2 not in actual


def test_neighbor_cell_indices_ring_wrap() -> None:
    """验证靠近左边界时查询正确环绕到右侧。"""
    index = SpatialIndex(universe_size=100.0, cell_size=10.0)
    # (2, 50) => cx=0.2 => int(cx)=0, cy=5.0 => int(cy)=5
    # cell_radius = ceil(20/10) = 2
    # dx ∈ [-2,-1,0,1,2] => gx = (0+dx) % 10
    #   gx = 8, 9, 0, 1, 2 (左边界环绕到右侧)
    # dy ∈ [-2,-1,0,1,2] => gy = (5+dy) % 10
    #   gy = 3, 4, 5, 6, 7
    indices = index._neighbor_cell_indices(2.0, 50.0, radius=20.0)
    unique_gx = {idx % 10 for idx in indices}
    assert 8 in unique_gx
    assert 9 in unique_gx
    assert 0 in unique_gx
    assert 1 in unique_gx
    assert 2 in unique_gx
    # 验证总共 25 个不同网格
    assert len(set(indices)) == 25


# =============================================================================
# rebuild 方法测试
# =============================================================================


def _make_civ(
    civ_id: int, x: float, y: float, alive: bool = True
) -> Civilization:
    """辅助函数：创建测试用文明。"""
    return Civilization(id=civ_id, x=x, y=y, is_alive=alive)


def test_rebuild_empty() -> None:
    """验证空列表重建后所有网格为空。"""
    index = SpatialIndex(universe_size=100.0, cell_size=10.0)
    index.rebuild([])
    assert all(len(cell) == 0 for cell in index._grid)
    assert len(index._id_to_cell) == 0


def test_rebuild_single() -> None:
    """验证单个文明重建后位于正确网格。"""
    index = SpatialIndex(universe_size=100.0, cell_size=10.0)
    civ = _make_civ(1, 15.0, 25.0)
    index.rebuild([civ])
    # (15, 25) => gx=1, gy=2 => idx = 2*10+1 = 21
    expected_idx = 21
    assert len(index._grid[expected_idx]) == 1
    assert index._grid[expected_idx][0] is civ
    assert index._id_to_cell[1] == expected_idx


def test_rebuild_ignores_dead() -> None:
    """验证已毁灭的文明不被插入网格。"""
    index = SpatialIndex(universe_size=100.0, cell_size=10.0)
    live_civ = _make_civ(1, 15.0, 25.0, alive=True)
    dead_civ = _make_civ(2, 75.0, 75.0, alive=False)
    index.rebuild([live_civ, dead_civ])
    # 存活文明应被插入到 (15,25) => idx 21
    assert len(index._grid[21]) == 1
    assert index._grid[21][0] is live_civ
    # 已毁灭的文明不应出现在任何网格
    for cell in index._grid:
        assert dead_civ not in cell
    assert 2 not in index._id_to_cell


def test_rebuild_multiple_different_cells() -> None:
    """验证多个文明分配到不同网格。"""
    index = SpatialIndex(universe_size=100.0, cell_size=10.0)
    civs = [
        _make_civ(1, 5.0, 5.0),     # gx=0, gy=0 => idx=0
        _make_civ(2, 15.0, 25.0),   # gx=1, gy=2 => idx=21
        _make_civ(3, 95.0, 95.0),   # gx=9, gy=9 => idx=99
    ]
    index.rebuild(civs)
    assert len(index._grid[0]) == 1
    assert len(index._grid[21]) == 1
    assert len(index._grid[99]) == 1
    assert index._grid[0][0].id == 1
    assert index._grid[21][0].id == 2
    assert index._grid[99][0].id == 3
    assert index._id_to_cell[1] == 0
    assert index._id_to_cell[2] == 21
    assert index._id_to_cell[3] == 99


def test_rebuild_same_cell() -> None:
    """验证多个文明分配到同一网格时正确追加。"""
    index = SpatialIndex(universe_size=100.0, cell_size=10.0)
    civs = [
        _make_civ(1, 12.0, 14.0),
        _make_civ(2, 18.0, 16.0),
    ]
    index.rebuild(civs)
    # Both in gx=1, gy=1 => idx = 1*10+1 = 11
    assert len(index._grid[11]) == 2
    assert index._grid[11][0].id == 1
    assert index._grid[11][1].id == 2


def test_rebuild_clears_previous() -> None:
    """验证多次重建会清空之前的索引数据。"""
    index = SpatialIndex(universe_size=100.0, cell_size=10.0)
    civ1 = _make_civ(1, 15.0, 25.0)
    index.rebuild([civ1])
    assert len(index._grid[21]) == 1

    # 第二次重建
    civ2 = _make_civ(2, 75.0, 75.0)
    index.rebuild([civ2])

    # 旧文明应被清除
    assert len(index._grid[21]) == 0
    assert 1 not in index._id_to_cell
    # 新文明应在正确位置: (75, 75) => gx=7, gy=7 => idx=77
    assert len(index._grid[77]) == 1
    assert index._id_to_cell[2] == 77


def test_rebuild_all_dead() -> None:
    """验证所有文明都已毁灭时重建后网格全空。"""
    index = SpatialIndex(universe_size=100.0, cell_size=10.0)
    civs = [_make_civ(1, 15.0, 25.0, alive=False)]
    index.rebuild(civs)
    assert all(len(cell) == 0 for cell in index._grid)
    assert len(index._id_to_cell) == 0


# =============================================================================
# query_neighbors 测试
# =============================================================================


def test_query_neighbors_found() -> None:
    """验证范围内的文明能被查询到。"""
    index = SpatialIndex(universe_size=100.0, cell_size=10.0)
    civs = [
        _make_civ(1, 50.0, 50.0),
        _make_civ(2, 55.0, 53.0),  # ~5.83 距离
    ]
    index.rebuild(civs)
    result = index.query_neighbors(50.0, 50.0, radius=10.0)
    assert len(result) == 1
    assert result[0].id == 2


def test_query_neighbors_not_found() -> None:
    """验证超出范围的文明不会被查询到。"""
    index = SpatialIndex(universe_size=100.0, cell_size=10.0)
    civs = [
        _make_civ(1, 50.0, 50.0),
        _make_civ(2, 90.0, 90.0),
    ]
    index.rebuild(civs)
    result = index.query_neighbors(50.0, 50.0, radius=10.0)
    assert len(result) == 0


def test_query_neighbors_ring_boundary() -> None:
    """验证跨环形边界的邻近查询正确。"""
    index = SpatialIndex(universe_size=100.0, cell_size=10.0)
    civs = [
        _make_civ(1, 98.0, 50.0),
        _make_civ(2, 2.0, 50.0),
    ]
    index.rebuild(civs)
    result = index.query_neighbors(98.0, 50.0, radius=10.0)
    assert len(result) == 1
    assert result[0].id == 2


def test_query_neighbors_self_exclusion() -> None:
    """验证邻近查询不返回处于查询位置的文明。"""
    index = SpatialIndex(universe_size=100.0, cell_size=10.0)
    civs = [
        _make_civ(1, 50.0, 50.0),
        _make_civ(2, 53.0, 50.0),
    ]
    index.rebuild(civs)
    result = index.query_neighbors(50.0, 50.0, radius=10.0)
    ids = {c.id for c in result}
    assert 1 not in ids
    assert 2 in ids


def test_query_neighbors_multiple_results() -> None:
    """验证邻近查询返回多个符合条件的结果。"""
    index = SpatialIndex(universe_size=100.0, cell_size=10.0)
    civs = [
        _make_civ(1, 50.0, 50.0),
        _make_civ(2, 53.0, 50.0),
        _make_civ(3, 50.0, 56.0),
        _make_civ(4, 70.0, 70.0),
    ]
    index.rebuild(civs)
    result = index.query_neighbors(50.0, 50.0, radius=7.0)
    ids = {c.id for c in result}
    assert 1 not in ids
    assert 2 in ids
    assert 3 in ids
    assert 4 not in ids


def test_query_neighbors_no_civs() -> None:
    """验证空索引的邻近查询返回空列表。"""
    index = SpatialIndex(universe_size=100.0, cell_size=10.0)
    index.rebuild([])
    result = index.query_neighbors(50.0, 50.0, radius=10.0)
    assert result == []


def test_query_neighbors_exact_distance() -> None:
    """验证刚好在半径边界上的文明被返回。"""
    index = SpatialIndex(universe_size=100.0, cell_size=10.0)
    civs = [
        _make_civ(1, 50.0, 50.0),
        _make_civ(2, 53.0, 50.0),
    ]
    index.rebuild(civs)
    result = index.query_neighbors(50.0, 50.0, radius=3.0)
    assert len(result) == 1
    assert result[0].id == 2


# =============================================================================
# query_region 测试
# =============================================================================


def _setup_region_index() -> SpatialIndex:
    """辅助函数：创建用于区域查询测试的索引。"""
    index = SpatialIndex(universe_size=100.0, cell_size=10.0)
    civs = [
        _make_civ(1, 10.0, 10.0),
        _make_civ(2, 50.0, 50.0),
        _make_civ(3, 90.0, 90.0),
        _make_civ(4, 95.0, 5.0),
    ]
    index.rebuild(civs)
    return index


def test_query_region_simple() -> None:
    """验证普通矩形区域查询（无包裹）。"""
    index = _setup_region_index()
    result = index.query_region(0.0, 60.0, 0.0, 60.0)
    ids = {c.id for c in result}
    assert 1 in ids  # (10, 10)
    assert 2 in ids  # (50, 50)
    assert 3 not in ids  # (90, 90) - outside
    assert 4 not in ids  # (95, 5) - x outside


def test_query_region_narrow() -> None:
    """验证狭小矩形区域只返回目标文明。"""
    index = _setup_region_index()
    result = index.query_region(5.0, 15.0, 5.0, 15.0)
    assert len(result) == 1
    assert result[0].id == 1


def test_query_region_wrap_x() -> None:
    """验证 x 方向包裹的矩形区域查询。

    x_min=90 > x_max=10 表示矩形在 x 方向包裹：
    x 在 [90, 100) ∪ [0, 10] 范围内。
    """
    index = _setup_region_index()
    result = index.query_region(90.0, 10.0, 0.0, 60.0)
    ids = {c.id for c in result}
    # civ3: (90,90) -> y=90 outside [0,60]
    assert 3 not in ids
    # civ4: (95,5) -> x in [90,100) ∪ [0,10], y in [0,60] ✓
    assert 4 in ids
    # civ1: (10,10) -> x=10 in [0,10], y in [0,60] ✓
    assert 1 in ids
    # civ2: (50,50) -> x=50 not in [90,100) ∪ [0,10]
    assert 2 not in ids


def test_query_region_wrap_y() -> None:
    """验证 y 方向包裹的矩形区域查询。"""
    index = _setup_region_index()
    result = index.query_region(0.0, 60.0, 90.0, 10.0)
    ids = {c.id for c in result}
    # civ3: (90,90) -> x in [0,60]... no, x=90 outside
    assert 3 not in ids
    # civ1: (10,10) -> x in [0,60] ✓, y=10 in [0,10] ✓
    assert 1 in ids
    # civ2: (50,50) -> x in [0,60] ✓, y=50 not in [90,100) ∪ [0,10]
    assert 2 not in ids
    # civ4: (95,5) -> x=95 outside [0,60]
    assert 4 not in ids


def test_query_region_wrap_both() -> None:
    """验证 x 和 y 同时包裹的矩形区域查询。"""
    index = _setup_region_index()
    result = index.query_region(90.0, 10.0, 90.0, 10.0)
    ids = {c.id for c in result}
    # civ4: (95,5) -> x=95 in [90,100) ∪ [0,10], y=5 in [0,10] ✓
    assert 4 in ids
    # civ3: (90,90) -> x=90 in [90,100) ∪ [0,10], y=90 in [90,100) ∪ [0,10] ✓
    assert 3 in ids
    # civ1: (10,10) -> x=10 in [0,10], y=10 in [0,10] ✓
    assert 1 in ids
    # civ2: (50,50) -> x=50 not in [90,100) ∪ [0,10]
    assert 2 not in ids


# =============================================================================
# remove_civilization 测试
# =============================================================================


def test_remove_civilization() -> None:
    """验证移除文明后索引中不再包含该文明。"""
    index = SpatialIndex(universe_size=100.0, cell_size=10.0)
    civs = [
        _make_civ(1, 10.0, 10.0),
        _make_civ(2, 50.0, 50.0),
    ]
    index.rebuild(civs)
    assert len(index._grid[index._id_to_cell[2]]) == 1

    index.remove_civilization(2)
    assert 2 not in index._id_to_cell
    assert 1 in index._id_to_cell
    for cell in index._grid:
        for c in cell:
            assert c.id != 2


def test_remove_civilization_nonexistent() -> None:
    """验证移除不存在的文明不会报错（静默忽略）。"""
    index = SpatialIndex(universe_size=100.0, cell_size=10.0)
    index.rebuild([_make_civ(1, 50.0, 50.0)])
    index.remove_civilization(999)
    assert 1 in index._id_to_cell


def test_remove_civilization_from_cell_with_multiple() -> None:
    """验证从多文明网格中移除一个不影响其他文明。"""
    index = SpatialIndex(universe_size=100.0, cell_size=10.0)
    civs = [
        _make_civ(1, 12.0, 12.0),
        _make_civ(2, 15.0, 15.0),
        _make_civ(3, 50.0, 50.0),
    ]
    index.rebuild(civs)
    assert len(index._grid[11]) == 2  # idx=11: gx=1, gy=1

    index.remove_civilization(1)
    assert 1 not in index._id_to_cell
    assert 2 in index._id_to_cell
    assert 3 in index._id_to_cell
    remaining_ids = {c.id for c in index._grid[11]}
    assert remaining_ids == {2}


# =============================================================================
# cell_count 属性测试
# =============================================================================


def test_cell_count_empty() -> None:
    """验证空索引的 cell_count 为 0。"""
    index = SpatialIndex(universe_size=100.0, cell_size=10.0)
    index.rebuild([])
    assert index.cell_count == 0


def test_cell_count_non_empty() -> None:
    """验证有文明时返回正确的非空网格数。"""
    index = SpatialIndex(universe_size=100.0, cell_size=10.0)
    civs = [
        _make_civ(1, 5.0, 5.0),
        _make_civ(2, 15.0, 25.0),
        _make_civ(3, 95.0, 95.0),
    ]
    index.rebuild(civs)
    assert index.cell_count == 3


def test_cell_count_same_cell() -> None:
    """验证同网格多个文明只计为 1。"""
    index = SpatialIndex(universe_size=100.0, cell_size=10.0)
    civs = [
        _make_civ(1, 12.0, 14.0),
        _make_civ(2, 18.0, 16.0),
    ]
    index.rebuild(civs)
    assert index.cell_count == 1


# =============================================================================
# load_balance_stats 属性测试
# =============================================================================


def test_load_balance_stats_empty() -> None:
    """验证空索引的负载统计。"""
    index = SpatialIndex(universe_size=100.0, cell_size=10.0)
    index.rebuild([])
    stats = index.load_balance_stats
    assert stats["min"] == 0
    assert stats["max"] == 0
    assert stats["avg"] == 0.0
    assert stats["empty_ratio"] == 1.0


def test_load_balance_stats_non_empty() -> None:
    """验证有文明时的负载统计正确。"""
    import math

    index = SpatialIndex(universe_size=100.0, cell_size=10.0)
    civs = [
        _make_civ(1, 5.0, 5.0),
        _make_civ(2, 12.0, 14.0),
        _make_civ(3, 18.0, 16.0),
    ]
    index.rebuild(civs)
    stats = index.load_balance_stats
    assert stats["min"] == 1
    assert stats["max"] == 2
    assert math.isclose(stats["avg"], 3.0 / 100.0)
    assert math.isclose(stats["empty_ratio"], 98.0 / 100.0)


def test_load_balance_stats_all_full() -> None:
    """验证所有网格都有文明时的统计。"""
    index = SpatialIndex(universe_size=100.0, cell_size=10.0)
    civs = [
        _make_civ(i, (i % 10) * 10 + 5, (i // 10) * 10 + 5) for i in range(100)
    ]
    index.rebuild(civs)
    stats = index.load_balance_stats
    assert stats["min"] >= 1
    assert stats["max"] >= 1
    assert stats["empty_ratio"] == 0.0


# =============================================================================
# auto_select_cell_size 测试
# =============================================================================


def test_auto_select_cell_size_default() -> None:
    """验证默认参数返回合理的网格大小。"""
    size = auto_select_cell_size(
        universe_size=10000.0,
        civ_count=5000,
        avg_detection_range=200.0,
        cpu_score=5.0,
    )
    assert 50.0 <= size <= 600.0


def test_auto_select_cell_size_high_density() -> None:
    """验证高密度文明时网格更细（更小 cell_size）。"""
    size_low = auto_select_cell_size(10000.0, 1000, 200.0, 5.0)
    size_high = auto_select_cell_size(10000.0, 20000, 200.0, 5.0)
    assert size_high <= size_low


def test_auto_select_cell_size_cpu_impact() -> None:
    """验证更高 CPU 评分产生更细网格。"""
    size_low_cpu = auto_select_cell_size(10000.0, 5000, 200.0, 2.0)
    size_high_cpu = auto_select_cell_size(10000.0, 5000, 200.0, 9.0)
    assert size_high_cpu <= size_low_cpu


def test_auto_select_cell_size_clamping() -> None:
    """验证极端参数被限制在合理范围内。"""
    size = auto_select_cell_size(10000.0, 10, 500.0, 1.0)
    assert 10.0 <= size <= 1500.0
    size = auto_select_cell_size(10000.0, 100000, 50.0, 10.0)
    assert 10.0 <= size <= 150.0


def test_auto_select_cell_size_returns_float() -> None:
    """验证返回值为 float 且保留一位小数。"""
    size = auto_select_cell_size(10000.0, 5000, 200.0, 5.0)
    assert isinstance(size, float)
    assert round(size * 10) == size * 10  # one decimal


# =============================================================================
# 性能基准测试
# =============================================================================


def test_performance_benchmark() -> None:
    """性能基准测试：10000 文明，100 次邻近查询，期望 < 50ms。"""
    import time

    universe_size = 10000.0
    cell_size = 200.0
    index = SpatialIndex(universe_size=universe_size, cell_size=cell_size)
    civs = [
        _make_civ(
            i,
            x=float((i * 157) % int(universe_size)),
            y=float((i * 311) % int(universe_size)),
        )
        for i in range(10000)
    ]
    index.rebuild(civs)

    t0 = time.perf_counter()
    for i in range(100):
        qx = float((i * 101) % int(universe_size))
        qy = float((i * 203) % int(universe_size))
        _ = index.query_neighbors(qx, qy, radius=300.0)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert elapsed_ms < 50.0, (
        f"性能基准测试失败: 100 次查询耗时 {elapsed_ms:.1f}ms (期望 < 50ms)"
    )
