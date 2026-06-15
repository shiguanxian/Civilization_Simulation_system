"""配置模块 —— SimulationConfig 与 ComputerCapability 数据类。

SimulationConfig 保存所有模拟参数的默认值，在模拟开始前确定，运行时只读。
ComputerCapability 保存性能检测的量化结果。
"""

import argparse
import math
import platform
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path

import psutil


@dataclass
class ComputerCapability:
    """描述当前电脑计算能力的量化结果。

    Attributes:
        cpu_score: CPU 基准分数（0~10）
        memory_gb: 可用内存（GB）
        recommended_civ_count: 推荐的文明数量上限
        recommended_grid_size: 推荐的空间网格单元大小（光年）
        estimated_step_time_ms: 预估每步耗时（毫秒）
    """

    cpu_score: float
    memory_gb: float
    recommended_civ_count: int
    recommended_grid_size: float
    estimated_step_time_ms: float

    def format_report(self) -> str:
        """Return a formatted terminal report of computer capability."""
        try:
            cpu_name = platform.processor() or "Unknown"
        except Exception:
            cpu_name = "Unknown"
        try:
            cpu_logical = psutil.cpu_count(logical=True) or 0
        except Exception:
            cpu_logical = 0
        try:
            total_gb = psutil.virtual_memory().total / (1024**3)
        except Exception:
            total_gb = 0.0
        if self.cpu_score >= 7.0:
            mode = "standard"
        elif self.cpu_score >= 4.0:
            mode = "standard"
        else:
            mode = "fast"
        lines = [
            "┌─────────────────────────────────────────┐",
            "│   🖥 计算机性能检测报告                    │",
            "├─────────────────────────────────────────┤",
            f"│   CPU: {cpu_name} ({cpu_logical}核)        │",
            f"│   内存: {total_gb:.1f} GB (可用 {self.memory_gb:.1f} GB)       │",
            f"│   CPU基准评分: {self.cpu_score}/10                        │",
            "│                                         │",
            "│   📊 推荐模拟参数:                        │",
            f"│   文明数量上限: {self.recommended_civ_count:,}                    │",
            f"│   网格单元大小: {self.recommended_grid_size:.0f} 光年                 │",
            f"│   预估每步耗时: {self.estimated_step_time_ms:.0f} ms                   │",
            f"│   建议运行模式: {mode}                     │",
            "└─────────────────────────────────────────┘",
        ]
        return "\n".join(lines)


@dataclass
class SimulationConfig:
    """模拟全局配置。在模拟开始前确定，运行时只读。

    所有字段均有合理默认值，可通过以下方式覆盖（优先级递增）：
    1. 代码默认值
    2. pyproject.toml [tool.simulation] 节
    3. 命令行参数
    """

    # ============ 宇宙参数 ============
    universe_size: float = 10000.0
    """宇宙空间边长（光年）"""

    # ============ 文明参数 ============
    initial_civ_count: int = 5000
    """初始文明数量"""
    max_civ_count: int = 20000
    """最大文明数量（防止性能爆炸）"""
    initial_distribution_mode: str = "uniform"
    """初始分布模式："uniform" = 均匀随机, "cluster" = 聚簇分布"""

    # ============ 聚簇分布参数（仅 distribution_mode = "cluster" 时使用） ============
    cluster_count: int = 50
    """聚簇数量"""
    cluster_radius: float = 500.0
    """每个聚簇的半径（光年）"""

    # ============ 演化参数 ============
    total_steps: int = 1000
    """总模拟步数"""
    birth_rate: float = 0.05
    """每步新文明诞生概率因子"""
    tech_explosion_base_prob: float = 0.01
    """技术爆炸基础概率"""
    cosmic_strike_prob: float = 0.001
    """黑暗森林打击每步概率"""

    # ============ 文明参数范围（用于随机生成） ============
    level_range: tuple[int, int] = (1, 3)
    """初始等级范围"""
    aggressiveness_range: tuple[float, float] = (0.1, 0.9)
    """攻击性范围"""
    stealth_range: tuple[float, float] = (0.1, 0.9)
    """隐蔽性范围"""
    detection_range_range: tuple[float, float] = (50.0, 500.0)
    """探测范围（光年）"""
    expansion_radius_range: tuple[float, float] = (10.0, 100.0)
    """扩张半径（光年）"""
    population_range: tuple[float, float] = (1e6, 1e10)
    """人口规模范围"""
    energy_output_range: tuple[float, float] = (1e12, 1e18)
    """能量输出范围"""

    # ============ 运行参数 ============
    run_mode: str = "standard"
    """运行模式："fast" = 高性能, "standard" = 标准, "interactive" = 交互"""
    step_interval_seconds: float = 0.1
    """交互模式下每步间隔（秒），用户可调速"""

    # ============ 输出参数 ============
    output_dir: str = "output"
    """输出目录"""
    save_step_data: bool = True
    """是否保存每步全量数据"""
    save_summary: bool = True
    """是否保存汇总数据"""
    save_interval: int = 1
    """每 N 步保存一次"""
    plot_update_interval: int = 5
    """标准模式下每 N 步更新图表"""

    # ============ 性能参数 ============
    spatial_grid_cell_size: float = 0.0
    """空间网格单元大小（光年），0.0 表示自动计算"""
    use_spatial_index: bool = True
    """是否启用空间索引"""

    # ============ 名称生成 ============
    name_generator_mode: str = "auto"
    """名称生成模式："auto" 或 "number" """

    # ============ 规则模块参数 ============

    # --- 技术爆炸相关 ---
    tech_growth_base: float = 5.0
    """科技点基础增长"""
    pop_growth_rate: float = 0.01
    """人口增长率"""
    energy_growth_rate: float = 0.005
    """能量输出增长率"""

    # --- 扩张相关 ---
    expansion_rate_base: float = 1.0
    """扩张基础速率"""
    base_exposure_prob: float = 0.01
    """坐标暴露基础概率"""
    exposure_threshold: float = 5.0
    """扩张暴露阈值"""

    # --- 黑暗森林相关 ---
    attack_threshold: float = 0.65
    """攻击阈值。威胁感知 >= 此值时文明选择攻击"""
    flee_threshold: float = 0.35
    """规避阈值。威胁感知 <= 此值时文明选择规避"""


# ========================================================================
# CLI → SimulationConfig 字段映射表
# ========================================================================
_CLI_MAPPING: dict[str, str] = {
    "size": "universe_size",
    "civs": "initial_civ_count",
    "steps": "total_steps",
    "birth_rate": "birth_rate",
    "mode": "name_generator_mode",
    "max_civs": "max_civ_count",
}


def _read_toml_config() -> dict:
    """读取 pyproject.toml 中 ``[tool.simulation]`` 节的配置覆盖。

    如果文件不存在、TOML 格式错误、或缺少 ``[tool.simulation]`` 节，
    均静默返回空字典 —— 不会因配置缺失而中断加载流程。

    Returns:
        ``[tool.simulation]`` 下的键值字典，或空字典。
    """
    toml_path = Path("pyproject.toml")
    if not toml_path.exists():
        return {}
    try:
        with toml_path.open("rb") as f:
            data = tomllib.load(f)
        return data.get("tool", {}).get("simulation", {})
    except (tomllib.TOMLDecodeError, OSError):
        return {}


def _apply_cli_overrides(config: SimulationConfig, args: argparse.Namespace) -> None:
    """将 ``argparse.Namespace`` 中的 CLI 参数应用到 *config*。

    仅映射 ``_CLI_MAPPING`` 中定义的字段；Namespace 中不存在的属性或
    ``None`` 值会被跳过。
    """
    for cli_attr, config_field in _CLI_MAPPING.items():
        cli_value = getattr(args, cli_attr, None)
        if cli_value is not None:
            setattr(config, config_field, cli_value)


def _auto_detect_cell_size(config: SimulationConfig) -> None:
    """若 ``detect_computer_capability`` 可用则调用它来设置网格单元大小。

    当 ``spatial_grid_cell_size == 0.0`` 时由 ``load_config`` 调用。
    若 C3／C4 函数尚未实现（并行开发阶段），使用 250.0 作为后备默认值。
    """
    detect_fn = globals().get("detect_computer_capability")
    recommend_fn = globals().get("get_recommended_params")
    if detect_fn is not None and recommend_fn is not None:
        cap = detect_fn()
        rec = recommend_fn(cap)
        # get_recommended_params returns SimulationConfig with spatial_grid_cell_size set
        config.spatial_grid_cell_size = getattr(rec, "spatial_grid_cell_size", 250.0)
    else:
        config.spatial_grid_cell_size = 250.0


def load_config(args: argparse.Namespace | None = None) -> SimulationConfig:
    """加载配置，遵循优先级链：**CLI 参数 > pyproject.toml > 代码默认值**。

    优先级链（从低到高）:
    1. ``SimulationConfig`` 代码默认值（基础）
    2. ``pyproject.toml`` 中 ``[tool.simulation]`` 节（可选）
    3. ``argparse.Namespace`` CLI 参数（可选）

    如果最终 ``spatial_grid_cell_size == 0.0``，自动调用
    ``detect_computer_capability()`` 和 ``get_recommended_params()``
    计算推荐值（若这些函数尚不可用，使用 250.0 作为后备）。

    Args:
        args: 命令行参数命名空间。为 ``None`` 时仅使用默认值与 toml 覆盖。

    Returns:
        合并了所有配置层后的 ``SimulationConfig`` 实例。

    ``pyproject.toml`` 中 ``[tool.simulation]`` 可覆盖字段:
        * ``universe_size`` (float) — 宇宙空间边长
        * ``initial_civ_count`` (int) — 初始文明数量
        * ``max_civ_count`` (int) — 最大文明数量
        * ``birth_rate`` (float) — 诞生概率因子
        * ``total_steps`` (int) — 总模拟步数
        * ``name_generator_mode`` (str) — 名称生成模式

    CLI 参数映射（``args.*`` → ``SimulationConfig.*``）:
        * ``args.size`` → ``universe_size``
        * ``args.civs`` → ``initial_civ_count``
        * ``args.steps`` → ``total_steps``
        * ``args.birth_rate`` → ``birth_rate``
        * ``args.mode`` → ``name_generator_mode``
        * ``args.max_civs`` → ``max_civ_count``

    Example:
        >>> config = load_config()
        >>> config.universe_size
        10000.0
        >>> ns = argparse.Namespace(size=5000.0)
        >>> config = load_config(ns)
        >>> config.universe_size
        5000.0
    """
    # 第 1 层：代码默认值
    config = SimulationConfig()

    # 第 2 层：pyproject.toml 覆盖（中等优先级）
    for key, value in _read_toml_config().items():
        if hasattr(config, key) and value is not None:
            setattr(config, key, value)

    # 第 3 层：CLI 参数覆盖（最高优先级）
    if args is not None:
        _apply_cli_overrides(config, args)

    # 第 4 步：auto-detect spatial_grid_cell_size
    if config.spatial_grid_cell_size == 0.0:
        _auto_detect_cell_size(config)

    return config


# ── Performance detection ────────────────────────────────────────────────────

_BENCHMARK_CIV_COUNT = 1000
"""Number of Civilization objects to create in the micro-benchmark."""
_CIV_MEMORY_ESTIMATE_BYTES = 200
"""Estimated memory per Civilization object (bytes)."""


def detect_computer_capability() -> ComputerCapability:
    """检测当前电脑计算水平并返回量化结果。

    检测内容：
    1. CPU 核心数 + 频率（通过 psutil）
    2. 可用物理内存（通过 psutil.virtual_memory()）
    3. 微型基准测试：创建 N 个 Civilization 对象并计算距离，测量耗时

    Returns:
        ComputerCapability 结构体，包含 CPU 评分、内存、推荐参数。

    Note:
        该函数不会抛出异常 —— 任何失败都会降级为合理默认值。
    """
    from src.entity import Civilization

    # ── CPU 信息 ──
    try:
        cpu_logical = psutil.cpu_count(logical=True) or 4
    except Exception:
        cpu_logical = 4
    # ── 内存信息 ──
    try:
        mem = psutil.virtual_memory()
        available_bytes = mem.available
        memory_gb = available_bytes / (1024**3)
    except Exception:
        available_bytes = 4 * (1024**3)  # 4 GB default
        memory_gb = 4.0

    # ── 微型基准测试：创建 Civilization 对象 + 距离计算 ──
    try:
        t0 = time.perf_counter()
        civs = [
            Civilization(
                id=i,
                name=f"B{i}",
                x=float(i * 1.7),
                y=float(i * 3.1),
                level=(i % 5) + 1,
                detection_range=250.0,
            )
            for i in range(_BENCHMARK_CIV_COUNT)
        ]
        total_dist = 0.0
        pairs = min(_BENCHMARK_CIV_COUNT - 1, 1000)
        for i in range(pairs):
            dx = civs[i].x - civs[(i + 1) % _BENCHMARK_CIV_COUNT].x
            dy = civs[i].y - civs[(i + 1) % _BENCHMARK_CIV_COUNT].y
            total_dist += math.sqrt(dx * dx + dy * dy)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
    except Exception:
        elapsed_ms = 200.0  # conservative fallback

    # ── CPU 评分（0~10） ──
    # 基准: < 50ms → 10 分, >= 500ms → 1 分
    if elapsed_ms <= 50.0:
        cpu_score = 10.0
    elif elapsed_ms >= 500.0:
        cpu_score = 1.0
    else:
        cpu_score = 10.0 - (elapsed_ms - 50.0) / (500.0 - 50.0) * 9.0
    # 多核调整（最高 1.5 倍奖励）
    core_ratio = cpu_logical / 8.0
    cpu_score = min(cpu_score * min(core_ratio, 1.5), 10.0)
    cpu_score = round(max(cpu_score, 0.5), 1)

    # ── 推荐文明数量（使用 50% 可用内存） ──
    usable_for_civs = available_bytes * 0.5
    recommended_civ_count = int(usable_for_civs / _CIV_MEMORY_ESTIMATE_BYTES)
    recommended_civ_count = max(100, min(recommended_civ_count, 200_000))

    # ── 推荐网格单元大小（CPU 评分 10 → 100 光年, 1 → 500 光年） ──
    recommended_grid_size = 500.0 - (cpu_score / 10.0) * 400.0
    recommended_grid_size = round(max(recommended_grid_size, 50.0), 1)

    # ── 预估每步耗时 ──
    scale = max(recommended_civ_count / _BENCHMARK_CIV_COUNT, 1.0)
    estimated_step_time_ms = round(elapsed_ms * scale * 0.3, 1)

    return ComputerCapability(
        cpu_score=cpu_score,
        memory_gb=round(memory_gb, 1),
        recommended_civ_count=recommended_civ_count,
        recommended_grid_size=recommended_grid_size,
        estimated_step_time_ms=estimated_step_time_ms,
    )


def get_recommended_params(cap: ComputerCapability) -> SimulationConfig:
    """根据性能检测结果推荐模拟参数。

    推荐逻辑：
    - max_civ_count 来自 cap.recommended_civ_count
    - spatial_grid_cell_size 来自 cap.recommended_grid_size
    - initial_civ_count 不超过推荐最大值
    - run_mode 根据 CPU 评分选择

    Args:
        cap: 性能检测结果。

    Returns:
        使用推荐值填充的 SimulationConfig。
    """
    config = SimulationConfig()
    config.max_civ_count = cap.recommended_civ_count
    config.spatial_grid_cell_size = cap.recommended_grid_size
    config.initial_civ_count = min(
        config.initial_civ_count, cap.recommended_civ_count
    )

    if cap.cpu_score < 4.0:
        config.run_mode = "fast"
    elif cap.cpu_score < 7.0:
        config.run_mode = "standard"
    else:
        config.run_mode = "standard"

    return config
