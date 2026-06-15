"""运行模式模块 — 高性能快跑模式与标准可视化模式。

提供两个顶层入口函数，供 CLI/main 直接调用：
- run_fast: 无图表，仅终端输出
- run_standard: 实时图表 + 终端输出
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib.pyplot as plt

from src.output.stats import format_step_summary
from src.visualization.plotter import RealtimePlotter

if TYPE_CHECKING:
    from src.simulation import Simulation


def run_fast(simulation: Simulation) -> None:
    """高性能模式：不生成图表，仅在终端每 100 步输出概要。

    适用于大规模模拟或低性能机器。循环调用 ``simulation.step()``
    直到所有步数完成，每 100 步打印一次 ``format_step_summary``。

    Args:
        simulation: 已初始化的 Simulation 实例。
    """
    for step_num in range(simulation.config.total_steps):
        result = simulation.step()
        if step_num % 100 == 0:
            print(format_step_summary(result.stats))


def run_standard(simulation: Simulation) -> None:
    """标准模式：实时图表 + 终端输出。

    创建 ``RealtimePlotter`` 实例，循环调用 ``simulation.step()``，
    每 ``config.plot_update_interval`` 步更新一次图表。
    模拟结束后保持窗口打开（``plt.show(block=True)``）。

    Args:
        simulation: 已初始化的 Simulation 实例。
    """
    plotter = RealtimePlotter(
        simulation.config.universe_size,
        simulation.config.total_steps,
    )
    try:
        for step_num in range(simulation.config.total_steps):
            result = simulation.step()
            if step_num % simulation.config.plot_update_interval == 0:
                plotter.update(simulation.civilizations, result.stats)
    finally:
        plt.show(block=True)
        plotter.close()
