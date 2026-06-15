"""交互式可视化与控制模块测试。

所有 matplotlib 测试使用 Agg 后端（无需显示器）。
tkinter 相关测试使用 object.__new__ 绕过窗口创建或 patch 模拟。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock, patch

import matplotlib
import pytest

matplotlib.use("Agg")

# =============================================================================
# tkinter 可用性检查（用于条件跳过）
# =============================================================================

try:
    import tkinter as tk

    _test_root = tk.Tk()
    _test_root.withdraw()
    HAS_TK = True
except (tk.TclError, Exception):
    HAS_TK = False


# =============================================================================
# 在被测模块引入前设置后端
# =============================================================================

from src.entity import Civilization
from src.output.stats import StepStats
from src.simulation import StepResult
from src.visualization.interactive import (
    InteractiveController,
    InteractiveRealtimePlotter,
    run_interactive,
)
from src.visualization.plotter import RealtimePlotter

# =============================================================================
# Mock 辅助
# =============================================================================


@dataclass
class MockConfig:
    """模拟 SimulationConfig，仅包含交互模式所需的字段。"""

    universe_size: float = 1000.0
    total_steps: int = 100
    step_interval_seconds: float = 0.05


class MockSimulation:
    """模拟 Simulation，不执行真实逻辑，仅模拟接口行为。"""

    def __init__(self) -> None:
        self.config = MockConfig()
        self.current_step = 0
        self.civilizations: list[Civilization] = []
        self.is_paused = False
        self.is_running = True
        self._step_count = 0
        self.stats_collector = MagicMock()
        self.stats_collector.get_latest.return_value = None

    def step(self) -> StepResult:
        """模拟一步推进。"""
        self._step_count += 1
        self.current_step = self._step_count
        stats = StepStats(
            step=self._step_count,
            total_civilizations=sum(1 for c in self.civilizations if c.is_alive),
        )
        return StepResult(step=self._step_count, stats=stats)

    def save_state(self) -> None:
        """模拟状态保存。"""
        pass


class MockController:
    """模拟 InteractiveController，用于测试绘图器事件。"""

    def __init__(self) -> None:
        self.toggle_pause_called = False
        self.speed_up_called = False
        self.slow_down_called = False
        self.step_forward_called = False
        self.stop_called = False
        self.detail_x: float | None = None
        self.detail_y: float | None = None

    def toggle_pause(self) -> None:
        self.toggle_pause_called = True

    def speed_up(self) -> None:
        self.speed_up_called = True

    def slow_down(self) -> None:
        self.slow_down_called = True

    def step_forward(self) -> None:
        self.step_forward_called = True

    def stop(self) -> None:
        self.stop_called = True

    def show_civilization_detail(self, x: float, y: float) -> None:
        self.detail_x = x
        self.detail_y = y


class MockEvent:
    """模拟 matplotlib 事件对象。"""

    def __init__(
        self,
        inaxes: object = None,
        xdata: float = 0.0,
        ydata: float = 0.0,
        key: str = "",
    ) -> None:
        self.inaxes = inaxes
        self.xdata = xdata
        self.ydata = ydata
        self.key = key


# =============================================================================
# 辅助函数：创建不启动 tkinter 的控制器
# =============================================================================


def _make_controller(
    sim: MockSimulation,
    universe_size: float = 1000.0,
    total_steps: int = 100,
) -> InteractiveController:
    """创建 InteractiveController 实例，完全绕过 tkinter。

    使用 object.__new__ 避免 __init__（该构造方法创建 tkinter 窗口），
    手动设置所有必要属性，将 UI 组件替换为 MagicMock。

    Args:
        sim: 模拟的 Simulation 实例。
        universe_size: 宇宙空间边长。
        total_steps: 总模拟步数。

    Returns:
        配置好内部状态的 InteractiveController 实例。
    """
    ctrl = object.__new__(InteractiveController)
    ctrl.sim = sim  # type: ignore[assignment]
    ctrl._universe_size = universe_size
    ctrl._total_steps = total_steps
    ctrl._is_running = False
    ctrl._is_paused = False
    ctrl._speed = 1.0
    ctrl._step_interval = sim.config.step_interval_seconds
    ctrl._timer = None
    ctrl.plotter = None

    # 模拟 tkinter UI 组件
    ctrl.root = MagicMock()
    ctrl.root.winfo_exists.return_value = True
    ctrl._status_label = MagicMock()
    ctrl._status_bar = MagicMock()
    ctrl._speed_label = MagicMock()
    ctrl._btn_pause = MagicMock()
    ctrl._btn_slower = MagicMock()
    ctrl._btn_faster = MagicMock()
    ctrl._btn_step = MagicMock()
    ctrl._btn_export = MagicMock()
    ctrl._btn_stop = MagicMock()
    return ctrl


# =============================================================================
# InteractiveRealtimePlotter 测试
# =============================================================================


class TestInteractiveRealtimePlotter:
    """InteractiveRealtimePlotter 的构造与事件处理测试。"""

    def test_plotter_init_creates_instance(self) -> None:
        """验证构造函数创建实例并连接控制器。"""
        controller = MockController()
        plotter = InteractiveRealtimePlotter(
            universe_size=1000.0,
            total_steps=100,
            controller=controller,  # type: ignore[arg-type]
        )
        try:
            assert plotter.fig is not None
            assert plotter._controller is controller
            assert plotter.ax_scatter is not None
        finally:
            plotter.close()

    def test_inherits_from_realtime_plotter(self) -> None:
        """验证 InteractiveRealtimePlotter 是 RealtimePlotter 的子类。"""
        assert issubclass(InteractiveRealtimePlotter, RealtimePlotter)

    def test_on_click_valid_axes_calls_detail(self) -> None:
        """验证在散点图区域内点击时调用 show_civilization_detail。"""
        controller = MockController()
        plotter = InteractiveRealtimePlotter(
            universe_size=1000.0,
            total_steps=100,
            controller=controller,  # type: ignore[arg-type]
        )
        try:
            event = MockEvent(
                inaxes=plotter.ax_scatter, xdata=500.0, ydata=300.0,
            )
            plotter._on_click(event)
            assert controller.detail_x == 500.0
            assert controller.detail_y == 300.0
        finally:
            plotter.close()

    def test_on_click_invalid_axes_ignored(self) -> None:
        """验证在散点图区域外点击时不会调用详情方法。"""
        controller = MockController()
        plotter = InteractiveRealtimePlotter(
            universe_size=1000.0,
            total_steps=100,
            controller=controller,  # type: ignore[arg-type]
        )
        try:
            event = MockEvent(
                inaxes=plotter.ax_curves, xdata=500.0, ydata=300.0,
            )
            plotter._on_click(event)
            assert controller.detail_x is None
            assert controller.detail_y is None
        finally:
            plotter.close()

    def test_on_click_none_axes_ignored(self) -> None:
        """验证在图外区域点击时不会调用详情方法。"""
        controller = MockController()
        plotter = InteractiveRealtimePlotter(
            universe_size=1000.0,
            total_steps=100,
            controller=controller,  # type: ignore[arg-type]
        )
        try:
            event = MockEvent(inaxes=None, xdata=500.0, ydata=300.0)
            plotter._on_click(event)
            assert controller.detail_x is None
        finally:
            plotter.close()

    @pytest.mark.parametrize(
        ("key", "attr"),
        [
            (" ", "toggle_pause_called"),
            ("+", "speed_up_called"),
            ("=", "speed_up_called"),
            ("-", "slow_down_called"),
            ("right", "step_forward_called"),
            ("escape", "stop_called"),
        ],
    )
    def test_key_press_handlers(self, key: str, attr: str) -> None:
        """验证各键盘快捷键触发对应控制器方法。"""
        controller = MockController()
        plotter = InteractiveRealtimePlotter(
            universe_size=1000.0,
            total_steps=100,
            controller=controller,  # type: ignore[arg-type]
        )
        try:
            event = MockEvent(key=key)
            plotter._on_key_press(event)
            assert getattr(controller, attr) is True
        finally:
            plotter.close()

    def test_unknown_key_ignored(self) -> None:
        """验证未注册的按键不会触发任何操作。"""
        controller = MockController()
        plotter = InteractiveRealtimePlotter(
            universe_size=1000.0,
            total_steps=100,
            controller=controller,  # type: ignore[arg-type]
        )
        try:
            event = MockEvent(key="a")
            plotter._on_key_press(event)
            assert controller.toggle_pause_called is False
            assert controller.speed_up_called is False
            assert controller.slow_down_called is False
            assert controller.step_forward_called is False
            assert controller.stop_called is False
        finally:
            plotter.close()


# =============================================================================
# _find_nearest_civilization 测试
# =============================================================================


class TestFindNearestCivilization:
    """InteractiveController._find_nearest_civilization 的单元测试。"""

    def make_civ(
        self,
        id: int,
        x: float,
        y: float,
        alive: bool = True,
    ) -> Civilization:
        """快速创建文明实例的辅助方法。"""
        return Civilization(
            id=id, name=f"文明{id}", x=x, y=y, is_alive=alive,
            level=1, energy_output=100.0,
        )

    def test_returns_nearest_alive_civ(self) -> None:
        """验证返回最近的存活文明。"""
        sim = MockSimulation()
        sim.civilizations = [
            self.make_civ(1, 100.0, 100.0),
            self.make_civ(2, 500.0, 500.0),
            self.make_civ(3, 200.0, 200.0),
        ]
        controller = _make_controller(sim)
        nearest = controller._find_nearest_civilization(50.0, 50.0)
        assert nearest is not None
        assert nearest.id == 1  # (100,100) 距 (50,50) 约 70.7

    def test_returns_none_for_distant_click(self) -> None:
        """验证点击位置远离所有文明时返回 None。"""
        sim = MockSimulation()
        sim.civilizations = [self.make_civ(1, 100.0, 100.0)]
        controller = _make_controller(sim)
        nearest = controller._find_nearest_civilization(1500.0, 1500.0)
        assert nearest is None

    def test_skips_dead_civilizations(self) -> None:
        """验证已毁灭文明不被考虑。"""
        sim = MockSimulation()
        sim.civilizations = [
            self.make_civ(1, 10.0, 10.0, alive=False),
            self.make_civ(2, 80.0, 80.0, alive=True),
        ]
        controller = _make_controller(sim)
        # 存活文明在 (80,80)，距 (50,50) 约 42.4 < 100
        nearest = controller._find_nearest_civilization(50.0, 50.0)
        assert nearest is not None
        assert nearest.id == 2  # alive civ at (80,80)

    def test_empty_civ_list_returns_none(self) -> None:
        """验证文明列表为空时返回 None。"""
        sim = MockSimulation()
        sim.civilizations = []
        controller = _make_controller(sim)
        nearest = controller._find_nearest_civilization(500.0, 500.0)
        assert nearest is None

    def test_max_dist_boundary(self) -> None:
        """验证边界距离：刚好 100 单位范围内返回，超出不返回。"""
        sim = MockSimulation()
        sim.civilizations = [self.make_civ(1, 0.0, 0.0)]
        controller = _make_controller(sim)

        nearest = controller._find_nearest_civilization(100.0, 0.0)
        assert nearest is not None
        assert nearest.id == 1

        nearest = controller._find_nearest_civilization(100.1, 0.0)
        assert nearest is None

    def test_multiple_civs_finds_closest(self) -> None:
        """验证多个文明中正确选择最近的一个。"""
        sim = MockSimulation()
        sim.civilizations = [
            self.make_civ(1, 800.0, 800.0),
            self.make_civ(2, 300.0, 300.0),
            self.make_civ(3, 100.0, 100.0),
            self.make_civ(4, 600.0, 600.0),
        ]
        controller = _make_controller(sim)
        nearest = controller._find_nearest_civilization(90.0, 90.0)
        assert nearest is not None
        assert nearest.id == 3  # (100,100)


# =============================================================================
# InteractiveController 逻辑测试（绕过 tkinter）
# =============================================================================


class TestControllerLogic:
    """InteractiveController 的业务逻辑测试。

    使用 _make_controller 创建控制器，避免 tkinter 依赖。
    测试不启动计时器循环，直接操作状态和方法。
    """

    def test_initial_state(self) -> None:
        """验证控制器初始状态。"""
        sim = MockSimulation()
        controller = _make_controller(sim)
        assert controller._is_running is False
        assert controller._is_paused is False
        assert controller._speed == 1.0
        assert controller._step_interval == 0.05

    def test_toggle_pause(self) -> None:
        """验证 toggle_pause 切换暂停状态。"""
        sim = MockSimulation()
        controller = _make_controller(sim)
        controller._is_running = True
        assert controller._is_paused is False

        controller.toggle_pause()
        assert controller._is_paused is True

        controller.toggle_pause()
        assert controller._is_paused is False

    def test_toggle_pause_not_running(self) -> None:
        """验证未运行时 toggle_pause 无效。"""
        sim = MockSimulation()
        controller = _make_controller(sim)
        controller.toggle_pause()
        assert controller._is_paused is False

    def test_speed_up_slow_down(self) -> None:
        """验证 speed_up 和 slow_down 调整速度。"""
        sim = MockSimulation()
        controller = _make_controller(sim)
        assert controller._speed == 1.0

        controller.speed_up()
        assert controller._speed == 1.5

        controller.speed_up()
        assert controller._speed == 2.25

        controller.slow_down()
        assert controller._speed == 1.5

        controller.slow_down()
        assert controller._speed == 1.0

    def test_speed_bounds(self) -> None:
        """验证速度在有效范围内。"""
        sim = MockSimulation()
        controller = _make_controller(sim)

        for _ in range(20):
            controller.slow_down()
        assert controller._speed >= 0.1

        controller._speed = 1.0
        for _ in range(20):
            controller.speed_up()
        assert controller._speed <= 100.0

    def test_stop_cleans_up(self) -> None:
        """验证 stop() 清理状态和计时器。"""
        sim = MockSimulation()
        controller = _make_controller(sim)
        controller._is_running = True
        controller.stop()
        assert controller._is_running is False
        assert controller._is_paused is False
        assert controller._timer is None

    def test_step_forward_requires_paused(self) -> None:
        """验证 step_forward 仅在暂停时执行步进。"""
        sim = MockSimulation()
        controller = _make_controller(sim)
        controller._is_running = True
        initial_step = sim.current_step

        controller.step_forward()
        assert sim.current_step == initial_step

        controller._is_paused = True
        controller.step_forward()
        assert sim.current_step == initial_step + 1

    def test_export_state_creates_file(self, tmp_path: Path) -> None:
        """验证 export_state 创建 JSON 文件。"""
        sim = MockSimulation()
        sim.civilizations = [
            Civilization(
                id=1, name="Test", x=100.0, y=200.0, level=2, is_alive=True,
            ),
        ]
        controller = _make_controller(sim)

        original_dir = Path.cwd()
        try:
            import os
            os.chdir(str(tmp_path))
            controller.export_state()
            files = list(tmp_path.glob("simulation_state_*.json"))
            assert len(files) >= 1
            if files:
                data = json.loads(files[0].read_text(encoding="utf-8"))
                assert "civilizations" in data
                assert data["civilizations"][0]["name"] == "Test"
        finally:
            os.chdir(str(original_dir))

    def test_show_civilization_detail_no_civ_nearby(self) -> None:
        """验证附近无文明时详情弹窗不弹出（不抛出异常）。"""
        sim = MockSimulation()
        sim.civilizations = [
            Civilization(
                id=1, name="Far", x=9999.0, y=9999.0, is_alive=True, level=1,
            ),
        ]
        controller = _make_controller(sim)
        controller._is_running = True
        controller.show_civilization_detail(0.0, 0.0)


# =============================================================================
# run_interactive 测试
# =============================================================================


class TestRunInteractive:
    """run_interactive 入口函数测试。"""

    @patch("src.visualization.interactive.InteractiveController")
    @patch("src.visualization.interactive.InteractiveRealtimePlotter")
    def test_run_interactive_calls_start_and_mainloop(
        self,
        mock_plotter_cls: MagicMock,
        mock_controller_cls: MagicMock,
    ) -> None:
        """验证 run_interactive 创建控制器和绘图器并启动。"""
        sim = MockSimulation()
        sim.stats_collector.get_latest.return_value = StepStats(
            step=1, total_civilizations=0,
        )
        sim.civilizations = []

        mock_controller = MagicMock()
        mock_controller_cls.return_value = mock_controller

        run_interactive(sim)  # type: ignore[arg-type]

        mock_controller_cls.assert_called_once_with(
            sim, sim.config.universe_size, sim.config.total_steps,
        )
        mock_plotter_cls.assert_called_once()
        assert mock_controller.plotter is mock_plotter_cls.return_value
        mock_controller.start.assert_called_once()
        mock_controller.root.mainloop.assert_called_once()

    @patch("src.visualization.interactive.InteractiveController")
    @patch("src.visualization.interactive.InteractiveRealtimePlotter")
    def test_run_interactive_updates_plotter_with_latest(
        self,
        mock_plotter_cls: MagicMock,
        mock_controller_cls: MagicMock,
    ) -> None:
        """验证 run_interactive 获取最新统计数据并更新绘图器。"""
        sim = MockSimulation()
        stats = StepStats(step=5, total_civilizations=42)
        sim.stats_collector.get_latest.return_value = stats
        sim.civilizations = []

        mock_plotter = MagicMock()
        mock_plotter_cls.return_value = mock_plotter
        mock_controller = MagicMock()
        mock_controller_cls.return_value = mock_controller

        run_interactive(sim)  # type: ignore[arg-type]

        mock_plotter.update.assert_called_once_with(sim.civilizations, stats)


# =============================================================================
# 真实的 tkinter 构造测试（可选）
# =============================================================================


@pytest.mark.skipif(not HAS_TK, reason="需要 tkinter 显示环境")
class TestRealTkinter:
    """使用真实 tkinter 窗口（或模拟）的测试。"""

    def test_controller_init_creates_window(self) -> None:
        """验证控制器初始化创建了 tkinter 窗口。

        使用 patch 避免环境中 tkinter 窗口创建可能失败的问题。
        验证关键属性被正确初始化。
        """
        sim = MockSimulation()

        with (
            patch("tkinter.Tk") as mock_tk,
            patch("tkinter.ttk.Button"),
            patch("tkinter.ttk.Label"),
            patch("tkinter.ttk.Frame"),
        ):
            mock_tk.return_value = MagicMock()
            controller = InteractiveController(
                sim,  # type: ignore[arg-type]
                1000.0, 100,
            )

        assert controller.root is not None
        assert controller._status_bar is not None
        assert controller._btn_pause is not None
        assert controller._speed == 1.0
