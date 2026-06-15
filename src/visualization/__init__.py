"""可视化模块 — 实时图表绘制与运行模式编排。"""

from src.visualization.plotter import RealtimePlotter
from src.visualization.run_modes import run_fast, run_standard

try:
    from src.visualization.interactive import run_interactive
except ImportError:
    run_interactive = None  # type: ignore[assignment]

__all__ = [
    "RealtimePlotter",
    "run_fast",
    "run_standard",
    "run_interactive",
]
