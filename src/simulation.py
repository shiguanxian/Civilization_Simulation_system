"""模拟编排模块 —— Simulation 主类与事件数据类。

此模块提供：
- SimEvent: 模拟事件数据类
- StepResult: 单步执行结果数据类
- Simulation: 模拟编排器，协调所有规则模块
"""

from __future__ import annotations

import json
import random
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from src.config import SimulationConfig
from src.entity import Civilization, CivilizationFactory, NameGenerator
from src.output.data_saver import DataSaver
from src.output.stats import StatsCollector, StepStats
from src.rules.dark_forest import apply_cosmic_strike, apply_dark_forest
from src.rules.detection import ContactEvent, detect_contacts
from src.rules.expansion import apply_expansion
from src.rules.tech_bomb import apply_development
from src.spatial import SpatialIndex, auto_select_cell_size


@dataclass
class SimEvent:
    """模拟中发生的一个事件。

    Attributes:
        event_type: 事件类型，如 "birth", "destruction", "tech_explosion",
                    "contact", "attack", "cosmic_strike"。
        civ_id: 相关文明 ID。
        detail: 事件详情描述。
        step: 事件发生时的时间步。
    """

    event_type: str
    civ_id: int
    detail: str = ""
    step: int = 0


@dataclass
class StepResult:
    """单步执行的结果。

    Attributes:
        step: 执行的时间步编号。
        stats: 本步统计数据。
        new_civs_count: 本步新生文明数。
        destroyed_count: 本步被毁灭文明数。
        skipped: 是否因暂停而跳过。
        events: 本步发生的事件列表。
    """

    step: int
    stats: StepStats
    new_civs_count: int = 0
    destroyed_count: int = 0
    skipped: bool = False
    events: list[SimEvent] = field(default_factory=list)

    @property
    def has_data(self) -> bool:
        """是否有实际数据（即非跳过状态）。"""
        return not self.skipped


class Simulation:
    """模拟编排器。

    协调所有规则模块（技术爆炸、扩张、探测、黑暗森林、宇宙打击），
    管理文明生命周期，收集统计数据，并提供回调和状态保存功能。
    """

    def __init__(self, config: SimulationConfig) -> None:
        """初始化模拟编排器。

        Args:
            config: 模拟全局配置。
        """
        self.config = config
        self.current_step: int = 0
        self.civilizations: list[Civilization] = []
        self.next_id: int = 0
        self.spatial_index: SpatialIndex | None = None
        self.factory: CivilizationFactory | None = None
        self.name_generator: NameGenerator | None = None
        self.stats_collector: StatsCollector | None = None
        self.data_saver: DataSaver | None = None
        self.is_paused: bool = False
        self.is_running: bool = False
        self.speed_multiplier: float = 1.0
        self._on_step_callbacks: list[Callable[[StepStats], None]] = []

    # ── SM2: initialize ──────────────────────────────────────────────────────

    def initialize(self) -> None:
        """初始化模拟状态。

        创建名称生成器、文明工厂、初始文明批次、空间索引、
        统计收集器和数据保存器。
        """
        # 创建名称生成器
        self.name_generator = NameGenerator(self.config.name_generator_mode)

        # 创建文明工厂
        self.factory = CivilizationFactory(self.config, self.name_generator)

        # 创建初始文明批次
        self.civilizations = self.factory.create_initial_batch(
            self.config.universe_size,
        )
        self.next_id = len(self.civilizations)

        # 创建空间索引
        cell_size = self.config.spatial_grid_cell_size
        if cell_size == 0.0:
            alive = [c for c in self.civilizations if c.is_alive]
            avg_range = (
                sum(c.detection_range for c in alive) / len(alive) if alive else 250.0
            )
            cell_size = auto_select_cell_size(
                self.config.universe_size,
                len(self.civilizations),
                avg_range,
                5.0,
            )
        self.spatial_index = SpatialIndex(self.config.universe_size, cell_size)
        self.spatial_index.rebuild(self.civilizations)

        # 创建统计收集器与数据保存器
        self.stats_collector = StatsCollector()
        self.data_saver = DataSaver(self.config)

        self.current_step = 0
        self.is_running = True

    # ── SM4: step ────────────────────────────────────────────────────────────

    def step(self) -> StepResult:
        """执行一步模拟。

        按顺序执行各规则阶段并收集事件与统计数据。

        Returns:
            本步的执行结果。
        """
        if self.is_paused:
            return StepResult(
                step=self.current_step,
                stats=StepStats(),
                skipped=True,
            )

        events: list[SimEvent] = []

        # ── Phase 1: 重建空间索引 ──
        if self.spatial_index is not None:
            self.spatial_index.rebuild(self.civilizations)

        # ── Phase 2: 文明诞生 ──
        prev_civ_count = len(self.civilizations)
        new_civs_count = self._apply_birth_rules()
        for civ in self.civilizations[prev_civ_count:]:
            events.append(SimEvent(
                event_type="birth",
                civ_id=civ.id,
                step=self.current_step,
            ))

        # ── Phase 3: 技术发展 ──
        self._apply_development_rules()

        # ── Phase 4: 扩张 ──
        self._apply_expansion_rules()

        # ── Phase 5: 探测 ──
        contacts = self._apply_detection_rules()
        for contact in contacts:
            events.append(SimEvent(
                event_type="contact",
                civ_id=contact.civ_a.id,
                detail=f"Contact between {contact.civ_a.name} and {contact.civ_b.name}",
                step=self.current_step,
            ))

        # ── Phase 6: 黑暗森林 ──
        attacks_count, destroyed_by_df = self._apply_dark_forest_rules(contacts)
        for _ in range(attacks_count):
            events.append(SimEvent(
                event_type="attack",
                civ_id=0,
                step=self.current_step,
            ))
        for _ in range(destroyed_by_df):
            events.append(SimEvent(
                event_type="destruction",
                civ_id=0,
                step=self.current_step,
            ))

        # ── Phase 7: 宇宙打击 ──
        destroyed_by_strike = self._apply_cosmic_strike()
        for _ in range(destroyed_by_strike):
            events.append(SimEvent(
                event_type="cosmic_strike",
                civ_id=0,
                detail="Cosmic strike destroyed civilizations",
                step=self.current_step,
            ))
            events.append(SimEvent(
                event_type="destruction",
                civ_id=0,
                step=self.current_step,
            ))

        # ── Phase 8: 清理已毁灭文明 ──
        self._cleanup_dead_civilizations()
        total_destroyed = destroyed_by_df + destroyed_by_strike

        # ── Phase 9: 统计 & 数据保存 ──
        step_event_dicts = [{"event_type": e.event_type} for e in events]
        if self.stats_collector is not None:
            stats = self.stats_collector.collect(
                self.civilizations,
                self.current_step,
                step_event_dicts if step_event_dicts else None,
            )
        else:
            stats = StepStats(step=self.current_step)

        if self.data_saver is not None:
            self.data_saver.save_step(stats, self.current_step)

        # ── Phase 10: 推进步数 + 回调 ──
        self.current_step += 1
        self._notify_step_callbacks(stats)

        return StepResult(
            step=self.current_step - 1,
            stats=stats,
            new_civs_count=new_civs_count,
            destroyed_count=total_destroyed,
            events=events,
        )

    # ── SM5: 内部规则方法 ─────────────────────────────────────────────────────

    def _apply_birth_rules(self) -> int:
        """计算并创建新生文明。

        根据存活文明数量和出生率计算新生数量，
        在不超过最大文明数量的前提下创建新文明。

        Returns:
            新诞生的文明数量。
        """
        alive_civs = [c for c in self.civilizations if c.is_alive]
        current_count = len(alive_civs)

        if current_count >= self.config.max_civ_count:
            return 0

        new_births = int(current_count * self.config.birth_rate * random.random())
        if new_births <= 0:
            return 0

        new_births = min(new_births, self.config.max_civ_count - current_count)

        for _ in range(new_births):
            if self.factory is not None:
                civ = self.factory.create_random(
                    civ_id=self.next_id,
                    birth_time=self.current_step,
                    universe_size=self.config.universe_size,
                )
                self.civilizations.append(civ)
                self.next_id += 1

        return new_births

    def _apply_development_rules(self) -> None:
        """执行技术发展规则。"""
        apply_development(self.civilizations, self.config)

    def _apply_expansion_rules(self) -> None:
        """执行扩张规则。"""
        apply_expansion(self.civilizations, self.config)

    def _apply_detection_rules(self) -> list[ContactEvent]:
        """执行探测规则。

        Returns:
            探测到的接触事件列表。
        """
        if self.spatial_index is not None:
            return detect_contacts(
                self.civilizations, self.spatial_index, self.config,
            )
        return []

    def _apply_dark_forest_rules(
        self,
        contacts: list[ContactEvent],
    ) -> tuple[int, int]:
        """执行黑暗森林规则。

        Args:
            contacts: 本步的接触事件列表。

        Returns:
            (攻击次数, 毁灭次数) 元组。
        """
        return apply_dark_forest(self.civilizations, contacts, self.config)

    def _apply_cosmic_strike(self) -> int:
        """执行宇宙打击规则。

        Returns:
            被宇宙打击毁灭的文明数量。
        """
        return apply_cosmic_strike(self.civilizations, self.config)

    def _cleanup_dead_civilizations(self) -> int:
        """清理已毁灭的文明。

        从 self.civilizations 中移除所有 is_alive 为 False 的文明。

        Returns:
            被移除的文明数量。
        """
        before = len(self.civilizations)
        self.civilizations = [c for c in self.civilizations if c.is_alive]
        return before - len(self.civilizations)

    # ── SM6: run ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        """运行完整模拟循环。

        在 is_running 为 True 且未达到总步数时持续执行 step()。
        """
        while self.is_running and self.current_step < self.config.total_steps:
            self.step()

    # ── SM7: run_single_step ────────────────────────────────────────────────

    def run_single_step(self) -> StepResult:
        """运行单步模拟后暂停。

        Returns:
            单步执行结果。
        """
        result = self.step()
        self.is_paused = True
        return result

    # ── SM8: save_state / load_state ─────────────────────────────────────────

    def save_state(self) -> None:
        """保存当前模拟状态到文件。"""
        if self.data_saver is not None:
            self.data_saver.save_simulation_state(
                civilizations=self.civilizations,
                current_step=self.current_step,
                next_id=self.next_id,
            )

    @classmethod
    def load_state(cls, file_path: str) -> Simulation:
        """从 JSON 文件加载模拟状态。

        Args:
            file_path: 状态文件路径。

        Returns:
            恢复状态后的 Simulation 实例。
        """
        with open(file_path, encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)

        # 重建配置
        config_data = data.get("config", {})
        config = SimulationConfig()
        for key, value in config_data.items():
            if hasattr(config, key):
                setattr(config, key, value)

        # 创建 Simulation 实例
        sim = cls(config)
        sim.current_step = data.get("current_step", 0)
        sim.next_id = data.get("next_id", 0)

        # 重建文明列表
        civs_data: list[dict[str, Any]] = data.get("civilizations", [])
        sim.civilizations = []
        for cd in civs_data:
            civ = Civilization(
                id=cd.get("id", 0),
                name=cd.get("name", ""),
                x=cd.get("x", 0.0),
                y=cd.get("y", 0.0),
                level=cd.get("level", 1),
                tech_points=cd.get("tech_points", 0.0),
                tech_explosion_prob=cd.get("tech_explosion_prob", 0.0),
                expansion_radius=cd.get("expansion_radius", 0.0),
                population=cd.get("population", 0.0),
                energy_output=cd.get("energy_output", 0.0),
                aggressiveness=cd.get("aggressiveness", 0.0),
                stealth=cd.get("stealth", 0.0),
                detection_range=cd.get("detection_range", 0.0),
                is_alive=cd.get("is_alive", True),
                birth_time=cd.get("birth_time", 0),
                communication_active=cd.get("communication_active", False),
            )
            sim.civilizations.append(civ)

        # 重新初始化辅助组件
        sim.name_generator = NameGenerator(config.name_generator_mode)
        sim.factory = CivilizationFactory(config, sim.name_generator)
        cell_size = config.spatial_grid_cell_size
        if cell_size == 0.0:
            alive = [c for c in sim.civilizations if c.is_alive]
            avg_range = (
                sum(c.detection_range for c in alive) / len(alive) if alive else 250.0
            )
            cell_size = auto_select_cell_size(
                config.universe_size,
                len(sim.civilizations),
                avg_range,
                5.0,
            )
        sim.spatial_index = SpatialIndex(config.universe_size, cell_size)
        sim.spatial_index.rebuild(sim.civilizations)
        sim.stats_collector = StatsCollector()
        sim.data_saver = DataSaver(config)
        sim.is_running = True
        sim.is_paused = False

        return sim

    # ── SM9: 回调 ────────────────────────────────────────────────────────────

    def register_step_callback(self, fn: Callable[[StepStats], None]) -> None:
        """注册步回调函数。

        Args:
            fn: 每步完成后调用的回调函数，接收 StepStats 参数。
        """
        if fn not in self._on_step_callbacks:
            self._on_step_callbacks.append(fn)

    def _notify_step_callbacks(self, stats: StepStats) -> None:
        """通知所有已注册的步回调。

        Args:
            stats: 当前步的统计数据。
        """
        for callback in self._on_step_callbacks:
            callback(stats)
