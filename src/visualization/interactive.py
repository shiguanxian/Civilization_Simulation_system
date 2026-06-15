"""交互式可视化与控制模块 — InteractiveRealtimePlotter, InteractiveController。

提供：
- InteractiveRealtimePlotter: 扩展 RealtimePlotter，添加鼠标点击与键盘快捷键支持。
- InteractiveController: 基于 tkinter 的控制面板，包含计时器驱动的步进循环。
- run_interactive: 入口函数，整合控制器与绘图器并启动。
"""

from __future__ import annotations

import datetime
import json
import math
import threading
import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.entity import Civilization
    from src.simulation import Simulation, StepResult

from src.output.stats import format_step_summary
from src.visualization.plotter import RealtimePlotter


class InteractiveRealtimePlotter(RealtimePlotter):
    """交互式实时图表绘制器。

    在 RealtimePlotter 的基础上增加：
    - 鼠标点击：选中最近文明，通过控制器显示详情。
    - 键盘快捷键：空格(暂停/继续)、+/- (调速)、→ (单步)、ESC (停止)。
    """

    def __init__(
        self, universe_size: float, total_steps: int,
        controller: InteractiveController,
    ) -> None:
        """初始化交互式图表并连接事件处理器。

        Args:
            universe_size: 宇宙空间边长（光年）。
            total_steps: 总模拟步数。
            controller: 关联的交互控制器。
        """
        super().__init__(universe_size, total_steps)
        self._controller = controller
        self._connect_event_handlers()

    def _connect_event_handlers(self) -> None:
        """连接 matplotlib 的鼠标点击与键盘按下事件。"""
        self.fig.canvas.mpl_connect("button_press_event", self._on_click)
        self.fig.canvas.mpl_connect("key_press_event", self._on_key_press)

    def _on_click(self, event) -> None:
        """鼠标点击事件处理器。

        仅在散点图区域内触发，将坐标转发给控制器显示文明详情。

        Args:
            event: matplotlib 鼠标事件对象。
        """
        if event.inaxes != self.ax_scatter:
            return
        self._controller.show_civilization_detail(event.xdata, event.ydata)

    def _on_key_press(self, event) -> None:
        """键盘按下事件处理器。

        支持的快捷键：
        - 空格: 暂停/继续
        - +/=: 加速
        - -: 减速
        - →: 单步前进（暂停时有效）
        - ESC: 停止模拟

        Args:
            event: matplotlib 键盘事件对象。
        """
        key = event.key
        if key == " ":
            self._controller.toggle_pause()
        elif key in ("+", "="):
            self._controller.speed_up()
        elif key == "-":
            self._controller.slow_down()
        elif key == "right":
            self._controller.step_forward()
        elif key == "escape":
            self._controller.stop()


class InteractiveController:
    """交互模式控制器，提供 tkinter 控制面板与计时器驱动的步进循环。

    控制面板包含：
    - 暂停/继续、加速、减速、单步前进、导出、停止按钮。
    - 速度与状态标签。
    - 状态栏显示当前步数、文明数量、事件信息。
    """

    def __init__(
        self, simulation: Simulation,
        universe_size: float, total_steps: int,
    ) -> None:
        """初始化控制器。

        Args:
            simulation: 已初始化的 Simulation 实例。
            universe_size: 宇宙空间边长（光年）。
            total_steps: 总模拟步数。
        """
        self.sim = simulation
        self._universe_size = universe_size
        self._total_steps = total_steps
        self._is_running = False
        self._is_paused = False
        self._speed = 1.0
        self._step_interval = simulation.config.step_interval_seconds
        self._timer: threading.Timer | None = None
        self.plotter: InteractiveRealtimePlotter | None = None

        # 创建 tkinter 主窗口
        self.root = tk.Tk()
        self.root.title("宇宙文明模拟控制")
        self.root.protocol("WM_DELETE_WINDOW", self.stop)
        self.root.resizable(False, False)

        self._build_ui()

    # ── UI 构建 ─────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        """构建控制面板 UI：按钮面板、速度控制、状态信息栏。"""
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ── 按钮面板 ──
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 5))

        self._btn_pause = ttk.Button(
            btn_frame, text="暂停", command=self.toggle_pause, width=10,
        )
        self._btn_pause.pack(side=tk.LEFT, padx=2)

        self._btn_slower = ttk.Button(
            btn_frame, text="减速", command=self.slow_down, width=8,
        )
        self._btn_slower.pack(side=tk.LEFT, padx=2)

        self._btn_faster = ttk.Button(
            btn_frame, text="加速", command=self.speed_up, width=8,
        )
        self._btn_faster.pack(side=tk.LEFT, padx=2)

        self._btn_step = ttk.Button(
            btn_frame, text="单步", command=self.step_forward, width=8,
        )
        self._btn_step.pack(side=tk.LEFT, padx=2)

        self._btn_export = ttk.Button(
            btn_frame, text="导出", command=self.export_state, width=8,
        )
        self._btn_export.pack(side=tk.LEFT, padx=2)

        self._btn_stop = ttk.Button(
            btn_frame, text="停止", command=self.stop, width=8,
        )
        self._btn_stop.pack(side=tk.LEFT, padx=2)

        # ── 速度与状态标签 ──
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=(5, 5))

        ttk.Label(info_frame, text="速度:").pack(side=tk.LEFT)
        self._speed_label = ttk.Label(info_frame, text="1.0x", width=8)
        self._speed_label.pack(side=tk.LEFT, padx=(2, 10))

        self._status_label = ttk.Label(
            info_frame, text="就绪", foreground="#555555",
        )
        self._status_label.pack(side=tk.LEFT, padx=(10, 0))

        # ── 状态栏（底部） ──
        self._status_bar = ttk.Label(
            main_frame, text="步数: 0  |  文明: 0",
            relief=tk.SUNKEN, anchor=tk.W, padding=(5, 2),
        )
        self._status_bar.pack(fill=tk.X, pady=(5, 0))

    # ── 生命周期 ──────────────────────────────────────────────────────────

    def start(self) -> None:
        """启动交互式模拟。"""
        self._is_running = True
        self._is_paused = False
        self._update_button_states()
        self._status_label.config(text="运行中", foreground="#006600")
        self._run_step_loop()

    def stop(self) -> None:
        """停止模拟并关闭所有窗口。"""
        self._is_running = False
        self._is_paused = False
        self._cancel_timer()

        if self.plotter is not None:
            try:
                self.plotter.close()
            except Exception:
                pass
            self.plotter = None

        try:
            if self.root.winfo_exists():
                self.root.quit()
                self.root.destroy()
        except Exception:
            pass

    def toggle_pause(self) -> None:
        """切换暂停/继续状态。"""
        if not self._is_running:
            return
        self._is_paused = not self._is_paused
        self._update_button_states()

        if self._is_paused:
            self._status_label.config(text="已暂停", foreground="#999900")
            self._btn_pause.config(text="继续")
            self._cancel_timer()
        else:
            self._status_label.config(text="运行中", foreground="#006600")
            self._btn_pause.config(text="暂停")
            self._run_step_loop()

    def speed_up(self) -> None:
        """加速：将速度乘以 1.5。"""
        self._speed = min(self._speed * 1.5, 100.0)
        self._update_speed_display()

    def slow_down(self) -> None:
        """减速：将速度除以 1.5。"""
        self._speed = max(self._speed / 1.5, 0.1)
        self._update_speed_display()

    def step_forward(self) -> None:
        """执行单步模拟（仅在暂停状态下可用）。"""
        if not self._is_running or not self._is_paused:
            return
        result = self.sim.step()
        self._update_display(result)

    def export_state(self) -> None:
        """导出当前模拟状态到 JSON 文件。"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"simulation_state_{timestamp}.json"
        try:
            self.sim.save_state()
            # save_state 由 DataSaver 处理，我们在额外位置再存一份友好格式
            state_data = {
                "step": self.sim.current_step,
                "timestamp": timestamp,
                "civilizations": [
                    {
                        "id": c.id,
                        "name": c.name,
                        "x": c.x,
                        "y": c.y,
                        "level": c.level,
                        "is_alive": c.is_alive,
                    }
                    for c in self.sim.civilizations
                ],
            }
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
            msg = f"已导出 {filename}"
            self._status_label.config(text=msg, foreground="#000099")
        except Exception as e:
            self._status_label.config(
                text=f"导出失败: {e}", foreground="#cc0000",
            )

    # ── 文明详情 ──────────────────────────────────────────────────────────

    def show_civilization_detail(
        self, click_x: float, click_y: float,
    ) -> None:
        """在点击位置附近查找最近的存活文明并显示详情弹窗。

        Args:
            click_x: 点击位置的 X 坐标。
            click_y: 点击位置的 Y 坐标。
        """
        civ = self._find_nearest_civilization(click_x, click_y)
        if civ is None:
            return

        detail = (
            f"文明: {civ.name} (ID: {civ.id})\n"
            f"位置: ({civ.x:.1f}, {civ.y:.1f})\n"
            f"等级: {civ.level}\n"
            f"科技: {civ.tech_points:.1f}\n"
            f"人口: {civ.population:.2e}\n"
            f"能量: {civ.energy_output:.2e}\n"
            f"攻击性: {civ.aggressiveness:.2f}\n"
            f"隐蔽性: {civ.stealth:.2f}\n"
            f"探测范围: {civ.detection_range:.1f}\n"
            f"扩张半径: {civ.expansion_radius:.1f}\n"
            f"存活: {'是' if civ.is_alive else '否'}"
        )

        popup = tk.Toplevel(self.root)
        popup.title(f"文明详情 - {civ.name}")
        popup.resizable(False, False)
        label = tk.Label(popup, text=detail, justify=tk.LEFT, padx=10, pady=10)
        label.pack()
        ttk.Button(popup, text="关闭", command=popup.destroy).pack(pady=(0, 10))

    def _find_nearest_civilization(
        self, x: float, y: float, max_dist: float = 100.0,
    ) -> Civilization | None:
        """在存活文明中查找离指定坐标最近的文明。

        Args:
            x: 查询点 X 坐标。
            y: 查询点 Y 坐标。
            max_dist: 最大有效距离，超出此范围返回 None。

        Returns:
            最近的 Civilization，如果最近距离超过 max_dist 则返回 None。
        """
        alive = [c for c in self.sim.civilizations if c.is_alive]
        if not alive:
            return None

        nearest: Civilization | None = None
        min_dist = float("inf")
        for c in alive:
            dx = c.x - x
            dy = c.y - y
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < min_dist:
                min_dist = dist
                nearest = c

        if min_dist <= max_dist:
            return nearest
        return None

    # ── 内部方法 ──────────────────────────────────────────────────────────

    def _run_step_loop(self) -> None:
        """计时器驱动的步进执行循环。

        当模拟正在运行且未暂停时，执行一步模拟，更新显示，
        然后根据当前速度调度下一步。
        """
        if not self._is_running or self._is_paused:
            return

        # 执行一步模拟
        result = self.sim.step()

        # 在 tkinter 主线程中更新显示
        self.root.after(0, self._update_display, result)

        # 检查是否完成所有步数
        if self.sim.current_step >= self._total_steps:
            self.root.after(0, self._on_simulation_complete)
            return

        # 根据速度调度下一步
        interval = self._step_interval / self._speed
        self._timer = threading.Timer(interval, self._run_step_loop)
        self._timer.daemon = True
        self._timer.start()

    def _update_display(self, result: StepResult) -> None:
        """更新终端、绘图器和状态栏。

        Args:
            result: 上一步的执行结果。
        """
        # 终端输出
        #print(format_step_summary(result.stats))

        # 更新绘图器
        if self.plotter is not None and result.has_data:
            self.plotter.update(self.sim.civilizations, result.stats)

        # 更新状态栏
        total = len(self.sim.civilizations)
        self._status_bar.config(
            text=f"步数: {self.sim.current_step}  |  "
            f"文明: {total}  |  "
            f"新生: {result.new_civs_count}  |  "
            f"毁灭: {result.destroyed_count}",
        )

    def _on_simulation_complete(self) -> None:
        """模拟完成时的回调：更新 UI 状态。"""
        self._is_running = False
        self._is_paused = False
        self._update_button_states()
        self._status_label.config(text="已完成", foreground="#006600")
        self._status_bar.config(text=f"模拟完成，共 {self._total_steps} 步")
        if self._btn_pause.winfo_exists():
            self._btn_pause.config(text="暂停")
        

    def _update_button_states(self) -> None:
        """更新按钮启用/禁用状态。"""
        state = tk.NORMAL if self._is_running else tk.DISABLED
        try:
            self._btn_pause.config(state=state)
            self._btn_slower.config(state=state)
            self._btn_faster.config(state=state)
            # 单步按钮仅在暂停时启用
            step_state = tk.NORMAL if (self._is_running and self._is_paused) else tk.DISABLED
            self._btn_step.config(state=step_state)
        except Exception:
            pass

    def _update_speed_display(self) -> None:
        """更新速度标签显示。"""
        self._speed_label.config(text=f"{self._speed:.1f}x")

    def _cancel_timer(self) -> None:
        """取消当前计时器（如果存在）。"""
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None


def run_interactive(simulation: Simulation) -> None:
    """启动交互式模式：控制面板 + 增强绘图器。

    创建 InteractiveController 和 InteractiveRealtimePlotter，
    建立双向引用，初始化显示，启动控制循环。

    Args:
        simulation: 已初始化的 Simulation 实例。
    """
    controller = InteractiveController(
        simulation,
        simulation.config.universe_size,
        simulation.config.total_steps,
    )
    plotter = InteractiveRealtimePlotter(
        simulation.config.universe_size,
        simulation.config.total_steps,
        controller,
    )
    controller.plotter = plotter

    # 初始绘制（如有已有统计数据）
    collector = simulation.stats_collector
    if collector is not None:
        latest = collector.get_latest()
        if latest is not None:
            plotter.update(simulation.civilizations, latest)

    controller.start()
    controller.root.mainloop()
