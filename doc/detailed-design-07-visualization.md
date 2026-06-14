# 详细设计文档 — 第7部分：可视化模块

## 1. 模块概述

### 1.1 模块职责

`src/visualization/` 目录下包含可视化层的所有代码，负责：

| 文件 | 类/主要函数 | 职责 |
|------|-------------|------|
| `plotter.py` | `RealtimePlotter` | 标准模式和交互模式下的实时图表绘制 |
| `interactive.py` | `InteractiveController` | 交互模式的 GUI 控制面板 |

### 1.2 设计原则

- **可视化层不依赖模拟引擎**：通过回调/轮询方式获取数据
- **图表更新独立于模拟计算**：不阻塞模拟线程
- **交互控制通过 Simulation 的接口实现**（pause/resume/speed）

---

## 2. 实时图表模块 (`src/visualization/plotter.py`)

### 2.1 RealtimePlotter 类设计

```python
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.colors import Normalize
import numpy as np


class RealtimePlotter:
    """
    实时图表绘制器。
    
    布局：
    ┌─────────────────────┬──────────────────┐
    │                     │                  │
    │   空间分布散点图     │   统计曲线图     │
    │   (左图)            │   (右图)         │
    │                     │                  │
    │   x: 文明位置       │   x: 时间步      │
    │   y: 文明位置       │   y: 文明数量    │
    │   颜色: 等级        │   多线: 等级分布 │
    │   大小: 能量        │                  │
    │                     │                  │
    └─────────────────────┴──────────────────┘
    """

    def __init__(self, config: SimulationConfig, 
                 figsize: tuple = (14, 7)):
        self.config = config
        self.fig: Figure
        self.ax_scatter: Axes      # 左图：空间分布
        self.ax_stats: Axes        # 右图：统计曲线

        # 历史数据缓存（用于绘制曲线）
        self._step_history: list[int] = []
        self._total_history: list[int] = []
        self._level_history: dict[int, list[int]] = {1: [], 2: [], 3: [], 4: [], 5: []}

        # 散点图对象引用（用于高效更新）
        self._scatter_plot = None

        # 初始化图表
        self._setup_figure(figsize)

    def _setup_figure(self, figsize: tuple) -> None:
        """初始化 matplotlib 图形和坐标轴。"""
        self.fig, (self.ax_scatter, self.ax_stats) = plt.subplots(
            1, 2, figsize=figsize
        )
        self.fig.suptitle("宇宙文明模拟器", fontsize=14, fontweight="bold")

        # 左图设置
        self.ax_scatter.set_xlim(0, self.config.universe_size)
        self.ax_scatter.set_ylim(0, self.config.universe_size)
        self.ax_scatter.set_xlabel("X (光年)")
        self.ax_scatter.set_ylabel("Y (光年)")
        self.ax_scatter.set_title("文明空间分布")
        self.ax_scatter.set_aspect("equal")
        self.ax_scatter.grid(True, alpha=0.3)

        # 右图设置
        self.ax_stats.set_xlabel("时间步")
        self.ax_stats.set_ylabel("文明数量")
        self.ax_stats.set_title("文明数量趋势")
        self.ax_stats.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.ion()  # 交互模式

    def update(self, stats: StepStats, 
               civilizations: list[Civilization]) -> None:
        """
        更新图表。
        
        参数：
            stats: 当前步的统计数据
            civilizations: 当前所有存活文明
        """
        self._update_scatter(civilizations)
        self._update_stats_curves(stats)
        self._update_title(stats)

        # 刷新图表
        self.fig.canvas.draw_idle()
        self.fig.canvas.flush_events()

    def _update_scatter(self, 
                        civilizations: list[Civilization]) -> None:
        """更新空间分布散点图。"""
        alive = [c for c in civilizations if c.is_alive]
        if not alive:
            return

        xs = np.array([c.x for c in alive])
        ys = np.array([c.y for c in alive])
        levels = np.array([c.level for c in alive])
        energies = np.array([c.energy_output for c in alive])

        # 点大小映射到能量（对数缩放）
        sizes = np.log10(energies) * 5
        sizes = np.clip(sizes, 5, 100)

        # 颜色映射到等级
        color_map = {1: "blue", 2: "green", 3: "yellow", 
                     4: "orange", 5: "red"}
        colors = [color_map.get(l, "gray") for l in levels]

        if self._scatter_plot is None:
            self._scatter_plot = self.ax_scatter.scatter(
                xs, ys, s=sizes, c=colors, alpha=0.6, edgecolors="none"
            )
        else:
            self._scatter_plot.set_offsets(np.column_stack([xs, ys]))
            self._scatter_plot.set_sizes(sizes)
            self._scatter_plot.set_color(colors)

    def _update_stats_curves(self, stats: StepStats) -> None:
        """更新统计曲线图。"""
        self._step_history.append(stats.step)
        self._total_history.append(stats.total_civilizations)

        for level in range(1, 6):
            count = stats.level_distribution.get(level, 0)
            if len(self._level_history[level]) < len(self._step_history):
                self._level_history[level].append(count)

        # 限制显示点数（防止性能下降）
        max_points = 500
        if len(self._step_history) > max_points:
            self._step_history = self._step_history[-max_points:]
            self._total_history = self._total_history[-max_points:]
            for level in self._level_history:
                self._level_history[level] = \
                    self._level_history[level][-max_points:]

        # 重绘曲线
        self.ax_stats.cla()
        self.ax_stats.plot(self._step_history, self._total_history,
                          label="总文明数", color="black", linewidth=2)

        colors = {1: "blue", 2: "green", 3: "yellow", 
                  4: "orange", 5: "red"}
        for level in range(1, 6):
            if self._level_history[level]:
                self.ax_stats.plot(
                    self._step_history, 
                    self._level_history[level],
                    label=f"Lv.{level}",
                    color=colors[level],
                    linewidth=1,
                    alpha=0.7
                )

        self.ax_stats.legend(loc="upper right", fontsize=8)
        self.ax_stats.set_xlabel("时间步")
        self.ax_stats.set_ylabel("文明数量")
        self.ax_stats.grid(True, alpha=0.3)

    def _update_title(self, stats: StepStats) -> None:
        """更新图表标题显示当前步信息。"""
        self.ax_scatter.set_title(
            f"文明空间分布 (步 {stats.step}, "
            f"存活 {stats.total_civilizations:,})"
        )

    def close(self) -> None:
        """关闭图表。"""
        plt.ioff()
        plt.close(self.fig)
```

### 2.2 交互模式下的增强

在交互模式中，`RealtimePlotter` 需要额外支持：

```python
class InteractiveRealtimePlotter(RealtimePlotter):
    """
    交互模式增强版图表。
    
    在标准 Plotter 基础上增加：
    - 点击文明点弹出详情
    - 快捷键绑定
    """

    def __init__(self, config: SimulationConfig,
                 interactive_controller: 'InteractiveController'):
        super().__init__(config)
        self.controller = interactive_controller

        # 绑定点击事件
        self._connect_event_handlers()

    def _connect_event_handlers(self) -> None:
        """连接 matplotlib 事件处理器。"""
        self.fig.canvas.mpl_connect(
            "button_press_event", self._on_click
        )
        self.fig.canvas.mpl_connect(
            "key_press_event", self._on_key_press
        )

    def _on_click(self, event) -> None:
        """
        点击散点图中的文明点时，弹出文明详情。
        
        使用 matplotlib 的 picking 或者最近邻搜索。
        """
        if event.inaxes != self.ax_scatter:
            return

        # 找最近的文明
        click_x, click_y = event.xdata, event.ydata
        # 通过 controller 查找最近文明
        self.controller.show_civilization_detail(click_x, click_y)

    def _on_key_press(self, event) -> None:
        """处理键盘快捷键。"""
        key = event.key
        if key == " ":
            self.controller.toggle_pause()
        elif key == "+" or key == "=":
            self.controller.speed_up()
        elif key == "-":
            self.controller.slow_down()
        elif key == "right":
            self.controller.step_forward()
        elif key == "escape":
            self.controller.stop()
```

---

## 3. 交互控制模块 (`src/visualization/interactive.py`)

### 3.1 交互模式架构

```
┌─────────────────────────────────────────────────────────┐
│                    InteractiveController                  │
│                                                         │
│  ┌─────────────────┐   ┌────────────────────────────┐  │
│  │  Simulation      │   │  InteractiveRealtimePlotter │  │
│  │  (核心引擎)      │◄──│  (图表 + 点击/按键事件)     │  │
│  │                  │   │                            │  │
│  │  .step()         │   │  .update()                 │  │
│  │  .pause()        │   │  .on_click()               │  │
│  │  .resume()       │   │  .on_key()                 │  │
│  │  .set_speed()    │   │                            │  │
│  └─────────────────┘   └────────────────────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │              ControlPanel (tkinter)              │   │
│  │  ┌─────┐ ┌──────┐ ┌─────┐ ┌─────┐ ┌──────────┐│   │
│  │  │ ▶/❚❚│ │ ⏪ ⏩ │ │ ⏭  │ │ 🔍  │ │ ❌       ││   │
│  │  │暂停 │ │ 调速 │ │单步 │ │详情 │ │退出     ││   │
│  │  └─────┘ └──────┘ └─────┘ └─────┘ └──────────┘│   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 3.2 InteractiveController 类设计

```python
import tkinter as tk
from tkinter import ttk
import threading
import time


class InteractiveController:
    """
    交互模式控制器。
    
    职责：
    1. 管理模拟的暂停/继续/调速
    2. 提供图形界面控制面板（tkinter 按钮）
    3. 处理用户点击文明详情的请求
    4. 管理定时器驱动模拟步进
    """

    def __init__(self, simulation: 'Simulation', 
                 config: SimulationConfig):
        self.sim = simulation
        self.config = config

        # 运行状态
        self._is_running = False
        self._is_paused = False
        self._speed = 1.0
        self._step_interval = config.step_interval_seconds  # 基础间隔（秒）

        # 定时器
        self._timer: threading.Timer | None = None

        # 可视化组件
        self.plotter: InteractiveRealtimePlotter | None = None

        # 创建控制面板
        self._create_control_panel()

    def _create_control_panel(self) -> None:
        """
        创建 tkinter 控制面板窗口。
        
        布局：
        ┌─────────────────────────────────────────────┐
        │  [▶ 开始/暂停]  [⏪ 减速] [⏩ 加速] [⏭ 单步]│
        │  速度: ████████░░░░ 2.0x                     │
        │  信息: 步 42 | 存活 4,238 | 毁灭 8          │
        └─────────────────────────────────────────────┘
        """
        self.root = tk.Tk()
        self.root.title("宇宙文明模拟控制")
        self.root.protocol("WM_DELETE_WINDOW", self.stop)

        # 按钮框架
        btn_frame = ttk.Frame(self.root, padding=10)
        btn_frame.pack(fill=tk.X)

        # 按钮
        self.btn_pause = ttk.Button(
            btn_frame, text="▶ 开始", command=self.toggle_pause,
            width=15
        )
        self.btn_pause.pack(side=tk.LEFT, padx=2)

        ttk.Button(
            btn_frame, text="⏪ 减速", command=self.slow_down,
            width=10
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            btn_frame, text="⏩ 加速", command=self.speed_up,
            width=10
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            btn_frame, text="⏭ 单步", command=self.step_forward,
            width=10
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            btn_frame, text="💾 导出", command=self.export_state,
            width=8
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            btn_frame, text="❌ 退出", command=self.stop,
            width=8
        ).pack(side=tk.RIGHT, padx=2)

        # 速度滑块与标签
        speed_frame = ttk.Frame(self.root, padding=5)
        speed_frame.pack(fill=tk.X)

        ttk.Label(speed_frame, text="速度:").pack(side=tk.LEFT)
        self.speed_var = tk.DoubleVar(value=1.0)
        self.speed_scale = ttk.Scale(
            speed_frame, from_=0.1, to=10.0, variable=self.speed_var,
            orient=tk.HORIZONTAL, length=200,
            command=self._on_speed_change
        )
        self.speed_scale.pack(side=tk.LEFT, padx=5)
        self.speed_label = ttk.Label(speed_frame, text="1.0x")
        self.speed_label.pack(side=tk.LEFT)

        # 状态信息
        self.status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(
            self.root, textvariable=self.status_var,
            padding=5, font=("Consolas", 10)
        )
        status_label.pack(fill=tk.X)

    def start(self) -> None:
        """启动交互模拟。"""
        self._is_running = True
        self._is_paused = False
        self.btn_pause.configure(text="❚❚ 暂停")
        self._run_step_loop()

    def toggle_pause(self) -> None:
        """切换暂停/继续。"""
        self._is_paused = not self._is_paused
        self.sim.is_paused = self._is_paused

        if self._is_paused:
            self.btn_pause.configure(text="▶ 继续")
            self._stop_timer()
        else:
            self.btn_pause.configure(text="❚❚ 暂停")
            self._schedule_next_step()

    def speed_up(self) -> None:
        """加速。"""
        self._speed = min(10.0, self._speed * 1.5)
        self._update_speed_display()
        self.sim.speed_multiplier = self._speed

    def slow_down(self) -> None:
        """减速。"""
        self._speed = max(0.1, self._speed / 1.5)
        self._update_speed_display()
        self.sim.speed_multiplier = self._speed

    def _on_speed_change(self, value: str) -> None:
        """速度滑块变化回调。"""
        self._speed = float(value)
        self._update_speed_display()
        self.sim.speed_multiplier = self._speed

    def _update_speed_display(self) -> None:
        """更新速度显示。"""
        self.speed_var.set(self._speed)
        self.speed_label.configure(text=f"{self._speed:.1f}x")
        # 重置时间间隔
        self._step_interval = self.config.step_interval_seconds / self._speed

    def step_forward(self) -> None:
        """执行单步（仅在暂停时有效）。"""
        if self._is_paused:
            result = self.sim.run_single_step()
            self._update_display(result)

    def show_civilization_detail(self, click_x: float, 
                                  click_y: float) -> None:
        """
        显示文明详情窗口。
        
        查找距离点击位置最近的文明，弹出详情对话框。
        """
        nearest = self._find_nearest_civilization(click_x, click_y)
        if nearest is None:
            return

        # 创建详情弹窗
        detail_win = tk.Toplevel(self.root)
        detail_win.title(f"文明详情: {nearest.name}")
        detail_win.geometry("400x500")

        details = [
            f"ID: {nearest.id}",
            f"名称: {nearest.name}",
            f"位置: ({nearest.x:.1f}, {nearest.y:.1f})",
            f"等级: {nearest.level}",
            f"科技点: {nearest.tech_points:.1f}",
            f"技术爆炸概率: {nearest.tech_explosion_prob:.3f}",
            f"扩张半径: {nearest.expansion_radius:.1f} 光年",
            f"人口: {nearest.population:.2e}",
            f"能量输出: {nearest.energy_output:.2e}",
            f"攻击性: {nearest.aggressiveness:.2f}",
            f"隐蔽性: {nearest.stealth:.2f}",
            f"探测范围: {nearest.detection_range:.1f} 光年",
            f"存活: {'是' if nearest.is_alive else '否'}",
            f"诞生时间: 步 {nearest.birth_time}",
            f"通信中: {'是' if nearest.communication_active else '否'}",
        ]
        for i, text in enumerate(details):
            ttk.Label(detail_win, text=text, 
                     font=("Consolas", 10)).pack(anchor=tk.W, padx=20, pady=2)

    def _find_nearest_civilization(self, x: float, y: float
                                   ) -> Civilization | None:
        """找到距离 (x, y) 最近的文明。"""
        from src.rules.detection import ring_distance
        
        nearest = None
        min_dist = float("inf")
        for civ in self.sim.civilizations:
            if not civ.is_alive:
                continue
            dist = ring_distance(x, y, civ.x, civ.y, 
                                self.config.universe_size)
            if dist < min_dist:
                min_dist = dist
                nearest = civ
        
        # 只返回在一定范围内的文明（比如 100 光年）
        if min_dist < 100.0:
            return nearest
        return None

    def export_state(self) -> None:
        """导出当前模拟状态。"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"state_{timestamp}.json"
        self.sim.save_state(
            str(self.config.output_dir / filename)
        )
        self.status_var.set(f"状态已导出: {filename}")

    def stop(self) -> None:
        """停止模拟并关闭所有窗口。"""
        self._is_running = False
        self._stop_timer()
        if self.plotter:
            self.plotter.close()
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def _run_step_loop(self) -> None:
        """运行模拟步进循环（由定时器驱动）。"""
        if not self._is_running or self._is_paused:
            return

        # 执行一步
        result = self.sim.step()
        self._update_display(result)

        # 检查是否完成
        if self.sim.current_step >= self.config.total_steps:
            self.status_var.set("模拟完成!")
            self.btn_pause.configure(text="✅ 完成")
            return

        # 调度下一步
        self._schedule_next_step()

    def _schedule_next_step(self) -> None:
        """调度下一步执行。"""
        if self._timer is not None:
            self._stop_timer()
        self._timer = threading.Timer(
            self._step_interval, self._run_step_loop
        )
        self._timer.daemon = True
        self._timer.start()

    def _stop_timer(self) -> None:
        """停止定时器。"""
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def _update_display(self, result: StepResult) -> None:
        """更新所有显示元素。"""
        if result.skipped or not result.has_data:
            return

        # 更新终端
        from src.output.stats import format_step_summary
        print(f"\n{format_step_summary(result.stats)}")

        # 更新图表
        if self.plotter:
            self.plotter.update(result.stats, self.sim.civilizations)

        # 更新状态栏
        self.status_var.set(
            f"步 {result.stats.step} | "
            f"存活 {result.stats.total_civilizations:,} | "
            f"新生 {result.stats.new_born} | "
            f"毁灭 {result.stats.destroyed}"
        )
```

### 3.3 交互模式主循环

```python
def run_interactive(simulation: Simulation, config: SimulationConfig) -> None:
    """
    启动交互模式。
    
    流程：
    1. 初始化模拟
    2. 创建交互控制器
    3. 创建交互式图表
    4. 关联控制器和图表
    5. 启动 tkinter 主循环
    """
    from src.visualization.interactive import InteractiveController
    from src.visualization.plotter import InteractiveRealtimePlotter

    # 创建控制器
    controller = InteractiveController(simulation, config)

    # 创建交互式图表
    plotter = InteractiveRealtimePlotter(config, controller)
    controller.plotter = plotter

    # 初始绘制
    initial_stats = simulation.stats_collector.get_latest()
    if initial_stats:
        plotter.update(initial_stats, simulation.civilizations)

    # 启动模拟
    controller.start()

    # 进入 tkinter 主循环（阻塞）
    controller.root.mainloop()
```

---

## 4. 标准模式主循环

```python
def run_standard(simulation: Simulation, config: SimulationConfig) -> None:
    """
    启动标准模式。
    
    流程：
    1. 初始化模拟
    2. 创建 RealtimePlotter
    3. 循环执行 step()，每隔 N 步更新图表
    4. 结束后等待用户关闭图表窗口
    """
    from src.visualization.plotter import RealtimePlotter

    plotter = RealtimePlotter(config)

    for step in range(config.total_steps):
        result = simulation.step()

        if result.has_data:
            # 终端输出
            from src.output.stats import format_step_summary
            print(f"\n{format_step_summary(result.stats)}")

            # 每隔 N 步更新图表
            if step % config.plot_update_interval == 0:
                plotter.update(result.stats, simulation.civilizations)

    print("\n模拟完成!")
    print(f"最终文明数: {result.stats.total_civilizations}")
    print(f"数据已保存至: {config.output_dir}/")

    # 保持图表窗口打开
    plt.show(block=True)
```

---

## 5. 高性能模式主循环

```python
def run_fast(simulation: Simulation, config: SimulationConfig) -> None:
    """
    高性能模式。
    
    不显示图表，最快速度运行。
    每步输出终端摘要。
    """
    from src.output.stats import format_step_summary

    for step in range(config.total_steps):
        result = simulation.step()

        if result.has_data:
            print(f"\n{format_step_summary(result.stats)}")

    print("\n模拟完成!")
    print(f"数据已保存至: {config.output_dir}/")
```

---

## 6. 模块的独立可测试性

### 6.1 测试要点

```python
# tests/test_visualization_plotter.py
# （GUI 测试较复杂，主要验证数据结构而非渲染）

def test_plotter_initialization():
    """验证 Plotter 初始化不报错。"""
    config = SimulationConfig(universe_size=10000)
    plotter = RealtimePlotter(config)
    assert plotter.fig is not None
    assert plotter.ax_scatter is not None
    assert plotter.ax_stats is not None
    plotter.close()

def test_plotter_update():
    """验证更新不报错。"""
    ...

def test_plotter_multiple_updates():
    """验证多次更新不积累内存泄漏。"""
    ...
```

---

## 7. 依赖关系

```
plotter.py      → entity.py（使用 Civilization 数据类型）
plotter.py      → output/stats.py（使用 StepStats）
interactive.py  → simulation.py（使用 Simulation）
interactive.py  → plotter.py（使用 RealtimePlotter）
interactive.py  → tkinter（标准库）
```

---

*下一篇：`detailed-design-08-cli-batch.md` — 命令行与批处理模块详细设计*
