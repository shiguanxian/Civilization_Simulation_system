"""可视化模块测试 — RealtimePlotter, run_fast, run_standard。

所有测试使用 matplotlib Agg 后端（无需显示器）。
"""

from dataclasses import dataclass

import matplotlib
import pytest

matplotlib.use("Agg")

from src.entity import Civilization
from src.output.stats import StepStats
from src.simulation import StepResult
from src.visualization.plotter import RealtimePlotter
from src.visualization.run_modes import run_fast, run_standard

# =============================================================================
# Mock Simulation（用于 run_fast / run_standard 测试）
# =============================================================================


@dataclass
class MockConfig:
    """模拟 SimulationConfig，仅包含 run_modes 所需的字段。"""

    universe_size: float = 1000.0
    total_steps: int = 20
    plot_update_interval: int = 10


class MockSimulation:
    """模拟 Simulation，不执行真实逻辑，仅模拟接口行为。"""

    def __init__(self) -> None:
        self.config = MockConfig()
        self._step_count: int = 0
        self.civilizations: list[Civilization] = []
        self._civs: list[Civilization] = []

    def step(self) -> StepResult:
        """模拟一步推进，返回包含 StepStats 的 StepResult。"""
        self._step_count += 1
        alive_count = sum(1 for c in self._civs if c.is_alive)
        stats = StepStats(
            step=self._step_count,
            total_civilizations=alive_count,
            level_distribution=self._build_level_distribution(),
        )
        return StepResult(step=self._step_count, stats=stats)

    def _build_level_distribution(self) -> dict[int, int]:
        """从当前文明列表构建等级分布字典。"""
        dist: dict[int, int] = {}
        for c in self._civs:
            if c.is_alive:
                dist[c.level] = dist.get(c.level, 0) + 1
        return dist


# =============================================================================
# RealtimePlotter 测试
# =============================================================================


def test_plotter_init_creates_figure() -> None:
    """验证 __init__ 能创建双面板图表（无头环境）。"""
    plotter = RealtimePlotter(universe_size=1000.0, total_steps=100)
    try:
        assert plotter.fig is not None
        assert plotter.ax_scatter is not None
        assert plotter.ax_curves is not None
        assert plotter.scatter is not None
        # 验证双面板布局
        axes = plotter.fig.axes
        assert len(axes) == 2
    finally:
        plotter.close()


def test_plotter_update_with_mock_data() -> None:
    """验证 update() 传入模拟数据不抛出异常。"""
    plotter = RealtimePlotter(universe_size=1000.0, total_steps=100)
    try:
        civ = Civilization(
            id=1,
            name="测试文明",
            x=500.0,
            y=500.0,
            level=3,
            energy_output=1e15,
            is_alive=True,
        )
        stats = StepStats(
            step=1,
            total_civilizations=1,
            level_distribution={3: 1},
        )
        plotter.update([civ], stats)
    finally:
        plotter.close()


def test_plotter_close_does_not_raise() -> None:
    """验证 close() 不抛出异常。"""
    plotter = RealtimePlotter(universe_size=1000.0, total_steps=100)
    plotter.close()  # 首次关闭
    plotter.close()  # 重复关闭不应抛出


def test_level_colors_all_five_levels() -> None:
    """验证 LEVEL_COLORS 包含 1~5 全部五个等级的颜色映射。"""
    assert len(RealtimePlotter.LEVEL_COLORS) == 5
    for level in range(1, 6):
        assert level in RealtimePlotter.LEVEL_COLORS
        assert isinstance(RealtimePlotter.LEVEL_COLORS[level], str)
        assert RealtimePlotter.LEVEL_COLORS[level].startswith("#")


def test_scatter_empty_civ_list() -> None:
    """验证传入空文明列表时 update() 不抛出异常。"""
    plotter = RealtimePlotter(universe_size=1000.0, total_steps=100)
    try:
        stats = StepStats(step=1, total_civilizations=0)
        plotter.update([], stats)
    finally:
        plotter.close()


def test_scatter_only_dead_civs() -> None:
    """验证所有文明已死时 update() 不抛出异常。"""
    plotter = RealtimePlotter(universe_size=1000.0, total_steps=100)
    try:
        dead_civ = Civilization(
            id=1, name="Dead", x=0.0, y=0.0, level=1,
            energy_output=1.0, is_alive=False,
        )
        stats = StepStats(step=1, total_civilizations=0)
        plotter.update([dead_civ], stats)
    finally:
        plotter.close()


# =============================================================================
# Stats 曲线 deque 内存安全测试
# =============================================================================


def test_stats_curve_maxlen() -> None:
    """验证内部 deque 不会增长超过 MAX_HISTORY_POINTS（500 点）。"""
    plotter = RealtimePlotter(universe_size=1000.0, total_steps=1000)
    try:
        for i in range(600):
            stats = StepStats(
                step=i,
                total_civilizations=100,
                level_distribution={1: 25, 2: 25, 3: 25, 4: 15, 5: 10},
            )
            plotter._update_stats_curves(stats)

        assert len(plotter.steps) == 500
        assert len(plotter.total_civs) == 500
        for level in range(1, 6):
            assert len(plotter.level_counts[level]) == 500

        # 验证最早数据已被丢弃（环形缓冲区行为）
        assert plotter.steps[0] == 100  # 索引 0 对应第 100 步
        assert plotter.steps[-1] == 599  # 最后一步
    finally:
        plotter.close()


# =============================================================================
# run_fast 测试
# =============================================================================


def test_run_fast_completes(capsys: pytest.CaptureFixture[str]) -> None:
    """验证 run_fast 能运行完成所有步数。"""
    sim = MockSimulation()
    sim.config.total_steps = 50
    run_fast(sim)
    assert sim._step_count == 50

    # 验证终端输出包含第一步的概要（step_num=0 时输出 stats.step=1）
    captured = capsys.readouterr()
    assert "时间步: 0001" in captured.out


def test_run_fast_capsys_every_100_steps(capsys: pytest.CaptureFixture[str]) -> None:
    """验证 run_fast 每 100 步打印一次概要。"""
    sim = MockSimulation()
    sim.config.total_steps = 250
    run_fast(sim)
    assert sim._step_count == 250

    captured = capsys.readouterr()
    # MockSimulation.step() 返回的 step 从 1 开始
    # step_num=0 → stats.step=1, step_num=100 → stats.step=101, step_num=200 → stats.step=201
    assert "时间步: 0001" in captured.out
    assert "时间步: 0101" in captured.out
    assert "时间步: 0201" in captured.out


# =============================================================================
# run_standard 测试
# =============================================================================


def test_run_standard_with_agg_backend() -> None:
    """验证 run_standard 在使用 Agg 后端时不抛出异常。"""
    sim = MockSimulation()
    sim.config.total_steps = 10
    # run_standard 在 Agg 后端下不会实际弹出窗口
    run_standard(sim)
    assert sim._step_count == 10
