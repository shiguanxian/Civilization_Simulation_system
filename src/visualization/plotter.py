"""实时图表绘制模块 — RealtimePlotter 类。

提供双面板实时图表：
- 左面板：文明空间分布散点图（按等级着色）
- 右面板：文明数量随时间变化的曲线图
"""

from __future__ import annotations

import math
from collections import deque

import matplotlib.pyplot as plt

from src.entity import Civilization
from src.output.stats import StepStats

import matplotlib.pyplot as plt
# 解决 Matplotlib 中文显示问题
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False


class RealtimePlotter:
    """实时图表绘制器，双面板布局（左：空间分布散点图，右：统计曲线图）。"""

    LEVEL_COLORS: dict[int, str] = {
        1: "#3498db",
        2: "#2ecc71",
        3: "#f1c40f",
        4: "#e67e22",
        5: "#e74c3c",
    }

    MAX_HISTORY_POINTS: int = 500

    def __init__(self, universe_size: float, total_steps: int) -> None:
        """初始化 matplotlib 双面板图表。

        Args:
            universe_size: 宇宙空间边长（光年），用于设置散点图坐标范围。
            total_steps: 总模拟步数（暂用于图表标题参考，未强制绑定）。
        """
        plt.ion()
        self.fig, (self.ax_scatter, self.ax_curves) = plt.subplots(
            1, 2, figsize=(14, 6)
        )
        self.total_steps = total_steps

        # ── 左面板：空间分布散点图 ──
        self.ax_scatter.set_xlim(0, universe_size)
        self.ax_scatter.set_ylim(0, universe_size)
        self.ax_scatter.set_aspect("equal")
        self.ax_scatter.grid(True, alpha=0.3)
        self.ax_scatter.set_xlabel("X (光年)")
        self.ax_scatter.set_ylabel("Y (光年)")
        self.ax_scatter.set_title("文明空间分布")

        self.scatter = self.ax_scatter.scatter([], [], s=[], c=[], alpha=0.7)

        # ── 右面板：统计曲线图 ──
        self.ax_curves.set_xlabel("时间步")
        self.ax_curves.set_ylabel("文明数量")
        self.ax_curves.set_title("文明数量趋势")
        self.ax_curves.grid(True, alpha=0.3)

        # 历史数据（双端队列，上限 MAX_HISTORY_POINTS 点）
        maxlen = self.MAX_HISTORY_POINTS
        self.steps: deque[int] = deque(maxlen=maxlen)
        self.total_civs: deque[int] = deque(maxlen=maxlen)
        self.level_counts: dict[int, deque[int]] = {
            level: deque(maxlen=maxlen) for level in range(1, 6)
        }

        # 曲线对象
        self.level_lines: dict[int, plt.Line2D] = {}
        for level in range(1, 6):
            (line,) = self.ax_curves.plot(
                [], [],
                label=f"L{level}",
                color=self.LEVEL_COLORS[level],
            )
            self.level_lines[level] = line
        (self.total_line,) = self.ax_curves.plot(
            [], [],
            label="总计",
            color="black",
            linewidth=2,
        )
        self.ax_curves.legend(loc="upper left")

    def update(
        self, civilizations: list[Civilization], stats: StepStats
    ) -> None:
        """更新所有图表元素并重绘。

        Args:
            civilizations: 当前所有文明列表（将过滤出存活文明）。
            stats: 当前时间步的统计数据。
        """
        self._update_scatter(civilizations)
        self._update_stats_curves(stats)
        self._update_title(stats)
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    def _update_scatter(self, civilizations: list[Civilization]) -> None:
        """更新散点图：仅显示存活文明。

        - 按等级使用 LEVEL_COLORS 着色
        - 点大小 = log10(energy) * 5，范围限制在 [5, 100]
        """
        alive = [c for c in civilizations if c.is_alive]
        if not alive:
            # 无存活文明时跳过更新（matplotlib 不接受 1D 空数组作为 offsets）
            return

        offsets = [(c.x, c.y) for c in alive]
        sizes = [
            max(5.0, min(100.0, math.log10(max(c.energy_output, 1.0)) * 5.0))
            for c in alive
        ]
        colors = [self.LEVEL_COLORS.get(c.level, "#3498db") for c in alive]

        self.scatter.set_offsets(offsets)
        self.scatter.set_sizes(sizes)
        self.scatter.set_color(colors)

    def _update_stats_curves(self, stats: StepStats) -> None:
        """更新统计曲线：总文明数 + 各等级文明数。"""
        self.steps.append(stats.step)
        self.total_civs.append(stats.total_civilizations)

        for level in range(1, 6):
            count = stats.level_distribution.get(level, 0)
            self.level_counts[level].append(count)

        # 更新曲线数据
        steps_list = list(self.steps)
        self.total_line.set_data(steps_list, list(self.total_civs))
        for level in range(1, 6):
            self.level_lines[level].set_data(
                steps_list, list(self.level_counts[level])
            )

        # 自动缩放 Y 轴
        if steps_list:
            self.ax_curves.relim()
            self.ax_curves.autoscale_view()

    def _update_title(self, stats: StepStats) -> None:
        """设置图表标题：当前时间步和存活文明数。"""
        self.fig.suptitle(
            f"时间步: {stats.step}  |  存活文明: {stats.total_civilizations}",
            fontsize=12,
        )

    def close(self) -> None:
        """关闭图表：退出交互模式并关闭图形窗口。"""
        plt.ioff()
        plt.close(self.fig)
