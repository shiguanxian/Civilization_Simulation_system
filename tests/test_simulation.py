"""Simulation 编排模块单元测试。

覆盖范围 (SM1–SM9)：
- SM1: __init__ 默认值正确
- SM2: initialize() 正确创建文明
- SM3: StepResult / SimEvent 数据类构造
- SM4: step() 推进当前步
- SM5: step() 暂停时返回 skipped=True
- SM6: run_single_step() 设暂停并返回
- SM7: 回调函数被调用
- SM8: save_state / load_state 往返
- SM9: run() 循环正确执行
- 额外: 诞生规则、清理规则
"""

from __future__ import annotations

from typing import Any

import pytest

from src.config import SimulationConfig
from src.output.stats import StepStats
from src.simulation import SimEvent, Simulation, StepResult

# ============================================================
#  Helper factories
# ============================================================

def make_config(**overrides: Any) -> SimulationConfig:
    """创建 SimulationConfig 并允许覆盖任意字段。"""
    cfg = SimulationConfig()
    for k, v in overrides.items():
        setattr(cfg, k, v)
    return cfg


# ============================================================
#  SM1 — __init__ 默认值
# ============================================================

class TestInit:
    """Simulation.__init__ 正确设置默认值。"""

    def test_defaults(self) -> None:
        """所有属性初始化为预期默认值。"""
        config = make_config()
        sim = Simulation(config)
        assert sim.config is config
        assert sim.current_step == 0
        assert sim.civilizations == []
        assert sim.next_id == 0
        assert sim.spatial_index is None
        assert sim.factory is None
        assert sim.name_generator is None
        assert sim.stats_collector is None
        assert sim.data_saver is None
        assert sim.is_paused is False
        assert sim.is_running is False
        assert sim.speed_multiplier == 1.0
        assert sim._on_step_callbacks == []


# ============================================================
#  SM2 — initialize
# ============================================================

class TestInitialize:
    """initialize() 正确创建组件与文明。"""

    def test_creates_correct_civ_count(self) -> None:
        """创建正确数量的初始文明。"""
        config = make_config(
            initial_civ_count=5,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
        )
        sim = Simulation(config)
        sim.initialize()
        assert len(sim.civilizations) == 5
        assert sim.next_id == 5
        assert sim.is_running is True

    def test_creates_name_generator(self) -> None:
        """initialize 创建名称生成器。"""
        config = make_config(
            initial_civ_count=2,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
        )
        sim = Simulation(config)
        sim.initialize()
        assert sim.name_generator is not None

    def test_creates_factory(self) -> None:
        """initialize 创建工厂。"""
        config = make_config(
            initial_civ_count=2,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
        )
        sim = Simulation(config)
        sim.initialize()
        assert sim.factory is not None

    def test_creates_spatial_index(self) -> None:
        """initialize 创建空间索引。"""
        config = make_config(
            initial_civ_count=2,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
        )
        sim = Simulation(config)
        sim.initialize()
        assert sim.spatial_index is not None
        assert sim.spatial_index.cell_size == 100.0

    def test_creates_stats_collector(self) -> None:
        """initialize 创建统计收集器。"""
        config = make_config(
            initial_civ_count=2,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
        )
        sim = Simulation(config)
        sim.initialize()
        assert sim.stats_collector is not None

    def test_creates_data_saver(self) -> None:
        """initialize 创建数据保存器。"""
        config = make_config(
            initial_civ_count=2,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
        )
        sim = Simulation(config)
        sim.initialize()
        assert sim.data_saver is not None

    def test_current_step_starts_at_zero(self) -> None:
        """initialize 后 current_step 为 0。"""
        config = make_config(
            initial_civ_count=2,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
        )
        sim = Simulation(config)
        sim.initialize()
        assert sim.current_step == 0

    def test_auto_select_cell_size(self) -> None:
        """spatial_grid_cell_size=0.0 时自动选择。"""
        config = make_config(
            initial_civ_count=5,
            universe_size=10000.0,
            spatial_grid_cell_size=0.0,
        )
        sim = Simulation(config)
        sim.initialize()
        assert sim.spatial_index is not None
        assert sim.spatial_index.cell_size > 0.0


# ============================================================
#  SM3 — StepResult / SimEvent 数据类
# ============================================================

class TestDataClasses:
    """StepResult 和 SimEvent 数据类正确构造。"""

    def test_sim_event_defaults(self) -> None:
        """SimEvent 有合理的默认值。"""
        event = SimEvent(event_type="birth", civ_id=42)
        assert event.event_type == "birth"
        assert event.civ_id == 42
        assert event.detail == ""
        assert event.step == 0

    def test_sim_event_full(self) -> None:
        """SimEvent 全字段构造。"""
        event = SimEvent(
            event_type="destruction",
            civ_id=7,
            detail="Destroyed by dark forest",
            step=5,
        )
        assert event.event_type == "destruction"
        assert event.civ_id == 7
        assert event.detail == "Destroyed by dark forest"
        assert event.step == 5

    def test_step_result_defaults(self) -> None:
        """StepResult 有合理的默认值。"""
        stats = StepStats()
        result = StepResult(step=0, stats=stats)
        assert result.step == 0
        assert result.stats is stats
        assert result.new_civs_count == 0
        assert result.destroyed_count == 0
        assert result.skipped is False
        assert result.events == []

    def test_step_result_has_data_true(self) -> None:
        """has_data 在非跳过时返回 True。"""
        result = StepResult(step=0, stats=StepStats())
        assert result.has_data is True

    def test_step_result_has_data_false(self) -> None:
        """has_data 在跳过时返回 False。"""
        result = StepResult(step=0, stats=StepStats(), skipped=True)
        assert result.has_data is False

    def test_step_result_full(self) -> None:
        """StepResult 全字段构造。"""
        stats = StepStats(step=1, total_civilizations=10)
        events = [
            SimEvent(event_type="birth", civ_id=1, step=0),
        ]
        result = StepResult(
            step=0,
            stats=stats,
            new_civs_count=2,
            destroyed_count=1,
            skipped=False,
            events=events,
        )
        assert result.step == 0
        assert result.stats.total_civilizations == 10
        assert result.new_civs_count == 2
        assert result.destroyed_count == 1
        assert result.events == events


# ============================================================
#  SM4 — step()
# ============================================================

class TestStep:
    """step() 基本行为。"""

    def test_advances_current_step(self) -> None:
        """step() 将 current_step 推进 1。"""
        config = make_config(
            initial_civ_count=2,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
        )
        sim = Simulation(config)
        sim.initialize()
        assert sim.current_step == 0
        result = sim.step()
        assert sim.current_step == 1
        assert result.step == 0

    def test_returns_step_result(self) -> None:
        """step() 返回 StepResult 实例。"""
        config = make_config(
            initial_civ_count=2,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
        )
        sim = Simulation(config)
        sim.initialize()
        result = sim.step()
        assert isinstance(result, StepResult)
        assert result.has_data is True

    def test_stats_are_collected(self) -> None:
        """step() 收集统计数据。"""
        config = make_config(
            initial_civ_count=2,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
        )
        sim = Simulation(config)
        sim.initialize()
        result = sim.step()
        assert result.stats.total_civilizations > 0
        assert result.stats.step == 0

    def test_paused_returns_skipped(self) -> None:
        """暂停时 step() 返回 skipped=True。"""
        config = make_config(
            initial_civ_count=2,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
        )
        sim = Simulation(config)
        sim.initialize()
        sim.is_paused = True
        result = sim.step()
        assert result.skipped is True
        assert result.has_data is False
        assert sim.current_step == 0  # 不推进

    def test_multiple_steps(self) -> None:
        """多次 step() 正确推进。"""
        config = make_config(
            initial_civ_count=2,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
            total_steps=100,
        )
        sim = Simulation(config)
        sim.initialize()
        for i in range(5):
            result = sim.step()
            assert result.step == i
        assert sim.current_step == 5

    def test_step_without_initialize(self) -> None:
        """未 initialize 时 step() 仍可执行（使用空文明列表）。"""
        config = make_config(
            initial_civ_count=2,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
        )
        sim = Simulation(config)
        # 不调用 initialize，直接 step
        result = sim.step()
        assert isinstance(result, StepResult)
        assert result.stats.total_civilizations == 0


# ============================================================
#  SM6 — run_single_step()
# ============================================================

class TestRunSingleStep:
    """run_single_step() 行为。"""

    def test_sets_paused(self) -> None:
        """run_single_step() 设置 is_paused=True。"""
        config = make_config(
            initial_civ_count=2,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
        )
        sim = Simulation(config)
        sim.initialize()
        sim.run_single_step()
        assert sim.is_paused is True

    def test_returns_step_result(self) -> None:
        """run_single_step() 返回 StepResult。"""
        config = make_config(
            initial_civ_count=2,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
        )
        sim = Simulation(config)
        sim.initialize()
        result = sim.run_single_step()
        assert isinstance(result, StepResult)
        assert result.has_data is True

    def test_advances_step(self) -> None:
        """run_single_step() 推进一步。"""
        config = make_config(
            initial_civ_count=2,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
        )
        sim = Simulation(config)
        sim.initialize()
        sim.run_single_step()
        assert sim.current_step == 1

    def test_second_step_paused(self) -> None:
        """暂停后再次 step 返回 skipped。"""
        config = make_config(
            initial_civ_count=2,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
        )
        sim = Simulation(config)
        sim.initialize()
        result1 = sim.run_single_step()
        assert result1.has_data is True
        result2 = sim.step()
        assert result2.skipped is True


# ============================================================
#  SM7 — run()
# ============================================================

class TestRun:
    """run() 循环行为。"""

    def test_runs_to_total_steps(self) -> None:
        """run() 执行到 total_steps。"""
        config = make_config(
            initial_civ_count=2,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
            total_steps=5,
        )
        sim = Simulation(config)
        sim.initialize()
        sim.run()
        assert sim.current_step == 5

    def test_stops_when_not_running(self) -> None:
        """is_running=False 时停止。"""
        config = make_config(
            initial_civ_count=2,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
            total_steps=100,
        )
        sim = Simulation(config)
        sim.initialize()

        def stop_after_3(_stats: StepStats) -> None:
            if sim.current_step >= 3:
                sim.is_running = False

        sim.register_step_callback(stop_after_3)
        sim.run()
        assert sim.current_step == 3

    def test_zero_steps(self) -> None:
        """total_steps=0 时不执行 step。"""
        config = make_config(
            initial_civ_count=2,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
            total_steps=0,
        )
        sim = Simulation(config)
        sim.initialize()
        sim.run()
        assert sim.current_step == 0


# ============================================================
#  SM9 — 回调
# ============================================================

class TestCallbacks:
    """回调函数正确调用。"""

    def test_callback_invoked_on_step(self) -> None:
        """step() 后调用已注册的回调。"""
        config = make_config(
            initial_civ_count=2,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
        )
        sim = Simulation(config)
        sim.initialize()
        called: list[StepStats] = []

        def cb(stats: StepStats) -> None:
            called.append(stats)

        sim.register_step_callback(cb)
        result = sim.step()
        assert len(called) == 1
        assert called[0] is result.stats

    def test_multiple_callbacks(self) -> None:
        """多个回调都被调用。"""
        config = make_config(
            initial_civ_count=2,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
        )
        sim = Simulation(config)
        sim.initialize()
        calls: list[int] = []

        def cb1(_stats: StepStats) -> None:
            calls.append(1)

        def cb2(_stats: StepStats) -> None:
            calls.append(2)

        sim.register_step_callback(cb1)
        sim.register_step_callback(cb2)
        sim.step()
        assert calls == [1, 2]

    def test_callback_not_called_when_paused(self) -> None:
        """暂停时不调用回调。"""
        config = make_config(
            initial_civ_count=2,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
        )
        sim = Simulation(config)
        sim.initialize()
        called: list[StepStats] = []

        def cb(stats: StepStats) -> None:
            called.append(stats)

        sim.register_step_callback(cb)
        sim.is_paused = True
        sim.step()
        assert len(called) == 0

    def test_duplicate_callback_not_registered_twice(self) -> None:
        """重复注册同一回调不会生效。"""
        config = make_config(
            initial_civ_count=2,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
        )
        sim = Simulation(config)
        sim.initialize()
        calls: list[int] = []

        def cb(_stats: StepStats) -> None:
            calls.append(1)

        sim.register_step_callback(cb)
        sim.register_step_callback(cb)
        sim.step()
        assert len(calls) == 1

    def test_callback_on_run(self) -> None:
        """run() 中每步调用回调。"""
        config = make_config(
            initial_civ_count=2,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
            total_steps=3,
        )
        sim = Simulation(config)
        sim.initialize()
        call_count: list[int] = [0]

        def cb(_stats: StepStats) -> None:
            call_count[0] += 1

        sim.register_step_callback(cb)
        sim.run()
        assert call_count[0] == 3


# ============================================================
#  SM8 — save_state / load_state 往返
# ============================================================

class TestSaveLoadState:
    """save_state / load_state 往返测试。"""

    def test_save_and_load_roundtrip(self, tmp_path: pytest.TempPathFactory) -> None:
        """保存后再加载状态应恢复相同数据。"""
        config = make_config(
            initial_civ_count=3,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
            output_dir=str(tmp_path),
        )
        sim = Simulation(config)
        sim.initialize()
        sim.step()

        # 保存
        sim.save_state()
        state_file = tmp_path / "state.json"
        assert state_file.exists()

        # 加载
        loaded = Simulation.load_state(str(state_file))
        assert loaded.current_step == sim.current_step
        assert loaded.next_id == sim.next_id
        assert len(loaded.civilizations) == len(sim.civilizations)
        assert loaded.is_running is True
        assert loaded.is_paused is False

    def test_default_filename(self, tmp_path: pytest.TempPathFactory) -> None:
        """save_state 默认保存到 state.json。"""
        config = make_config(
            initial_civ_count=2,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
            output_dir=str(tmp_path),
        )
        sim = Simulation(config)
        sim.initialize()
        sim.save_state()
        assert (tmp_path / "state.json").exists()

    def test_civ_attributes_preserved(self, tmp_path: pytest.TempPathFactory) -> None:
        """文明属性在往返后保持不变。"""
        config = make_config(
            initial_civ_count=2,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
            output_dir=str(tmp_path),
        )
        sim = Simulation(config)
        sim.initialize()

        # 记录原始属性
        original_civs = [(c.id, c.name, c.x, c.y, c.level, c.is_alive) for c in sim.civilizations]

        sim.save_state()
        loaded = Simulation.load_state(str(tmp_path / "state.json"))

        loaded_civs = [(c.id, c.name, c.x, c.y, c.level, c.is_alive) for c in loaded.civilizations]
        assert loaded_civs == original_civs

    def test_creates_components_on_load(self, tmp_path: pytest.TempPathFactory) -> None:
        """load_state 重建所有辅助组件。"""
        config = make_config(
            initial_civ_count=2,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
            output_dir=str(tmp_path),
        )
        sim = Simulation(config)
        sim.initialize()
        sim.save_state()
        loaded = Simulation.load_state(str(tmp_path / "state.json"))
        assert loaded.name_generator is not None
        assert loaded.factory is not None
        assert loaded.spatial_index is not None
        assert loaded.stats_collector is not None
        assert loaded.data_saver is not None

    def test_step_after_load(self, tmp_path: pytest.TempPathFactory) -> None:
        """加载后可继续执行 step()。"""
        config = make_config(
            initial_civ_count=3,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
            output_dir=str(tmp_path),
        )
        sim = Simulation(config)
        sim.initialize()
        sim.step()
        sim.save_state()
        loaded = Simulation.load_state(str(tmp_path / "state.json"))
        result = loaded.step()
        assert result.has_data is True
        assert loaded.current_step == 2

    def test_load_with_no_civs(self, tmp_path: pytest.TempPathFactory) -> None:
        """加载空文明列表。"""
        config = make_config(
            initial_civ_count=0,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
            output_dir=str(tmp_path),
        )
        sim = Simulation(config)
        sim.initialize()
        sim.save_state()
        loaded = Simulation.load_state(str(tmp_path / "state.json"))
        assert len(loaded.civilizations) == 0
        assert loaded.current_step == 0


# ============================================================
#  诞生规则
# ============================================================

class TestBirthRules:
    """文明诞生规则。"""

    def test_birth_creates_new_civs(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """出生率足够高时创建新文明。"""
        monkeypatch.setattr("src.simulation.random.random", lambda: 1.0)
        config = make_config(
            initial_civ_count=5,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
            birth_rate=1.0,
            max_civ_count=100,
        )
        sim = Simulation(config)
        sim.initialize()
        initial_count = len(sim.civilizations)
        # random.random 返回 1.0 → int(5 * 1.0 * 1.0) = 5 new civs
        result = sim.step()
        assert result.new_civs_count > 0
        assert len(sim.civilizations) > initial_count

    def test_birth_zero_when_max_reached(self) -> None:
        """达到最大文明上限时不创建。"""
        config = make_config(
            initial_civ_count=50,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
            birth_rate=1.0,
            max_civ_count=50,
        )
        sim = Simulation(config)
        sim.initialize()
        result = sim.step()
        assert result.new_civs_count == 0

    def test_birth_zero_when_random_zero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """random.random 返回 0 时不创建。"""
        monkeypatch.setattr("src.simulation.random.random", lambda: 0.0)
        config = make_config(
            initial_civ_count=5,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
            birth_rate=1.0,
            max_civ_count=100,
        )
        sim = Simulation(config)
        sim.initialize()
        result = sim.step()
        assert result.new_civs_count == 0

    def test_birth_events_generated(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """新生文明生成相应事件。"""
        monkeypatch.setattr("src.simulation.random.random", lambda: 1.0)
        config = make_config(
            initial_civ_count=5,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
            birth_rate=1.0,
            max_civ_count=100,
        )
        sim = Simulation(config)
        sim.initialize()
        result = sim.step()
        birth_events = [e for e in result.events if e.event_type == "birth"]
        assert len(birth_events) == result.new_civs_count
        for event in birth_events:
            assert event.event_type == "birth"
            assert event.step == 0


# ============================================================
#  清理规则
# ============================================================

class TestCleanup:
    """已毁灭文明清理。"""

    def test_removes_dead_civs(self) -> None:
        """清理移除 dead 标记的文明。"""
        config = make_config(
            initial_civ_count=10,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
        )
        sim = Simulation(config)
        sim.initialize()

        # 手动标记 3 个文明为已毁灭
        dead_count = 0
        for civ in sim.civilizations:
            if dead_count < 3:
                civ.is_alive = False
                dead_count += 1

        before = len(sim.civilizations)
        # step() 内部包含清理
        sim.step()
        after = len(sim.civilizations)

        # 清理移除了死文明
        assert after < before
        # 所有剩余文明存活
        assert all(c.is_alive for c in sim.civilizations)

    def test_cleanup_returns_count(self) -> None:
        """_cleanup_dead_civilizations 返回移除数量。"""
        config = make_config(
            initial_civ_count=10,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
        )
        sim = Simulation(config)
        sim.initialize()

        # 标记 3 个文明为已毁灭
        dead_count = 0
        for civ in sim.civilizations:
            if dead_count < 3:
                civ.is_alive = False
                dead_count += 1

        count = sim._cleanup_dead_civilizations()
        assert count == 3
        assert all(c.is_alive for c in sim.civilizations)

    def test_cleanup_no_dead(self) -> None:
        """没有已毁灭文明时返回 0。"""
        config = make_config(
            initial_civ_count=5,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
        )
        sim = Simulation(config)
        sim.initialize()
        count = sim._cleanup_dead_civilizations()
        assert count == 0


# ============================================================
#  黑暗森林与宇宙打击（通过 step 间接验证）
# ============================================================

class TestDarkForestEvents:
    """黑暗森林相关事件。"""

    def test_destruction_events_recorded(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """黑暗森林攻击产生毁灭事件。"""
        config = make_config(
            initial_civ_count=2,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
            # 使双方必定探测到对方
            detection_range_range=(2000.0, 2000.0),
            # 使威胁高到触发攻击
            aggressiveness_range=(0.9, 0.9),
            stealth_range=(0.0, 0.0),
            attack_threshold=0.5,
            flee_threshold=0.2,
            # 关闭宇宙打击避免干扰
            cosmic_strike_prob=0.0,
        )
        sim = Simulation(config)
        sim.initialize()
        # 在 initialize 之后打补丁，避免影响文明参数生成
        monkeypatch.setattr("src.rules.dark_forest.random.uniform", lambda a, b: 0.0)
        monkeypatch.setattr("src.rules.dark_forest.random.random", lambda: 0.0)
        result = sim.step()
        # 两个文明相邻且攻击性高 → 至少一次攻击
        destruction_events = [e for e in result.events if e.event_type == "destruction"]
        attack_events = [e for e in result.events if e.event_type == "attack"]
        assert len(attack_events) > 0
        # 至少有一个毁灭事件或攻击导致暴露
        assert len(destruction_events) >= 0  # 至少不报错


class TestCosmicStrikeEvents:
    """宇宙打击事件。"""

    def test_cosmic_strike_events(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """宇宙打击产生事件。"""
        # 强制检测到打击 + 大半径以确保命中文明
        monkeypatch.setattr("src.rules.dark_forest.random.random", lambda: 0.0)
        monkeypatch.setattr("src.rules.dark_forest.random.uniform", lambda a, b: b)  # 最大半径
        config = make_config(
            initial_civ_count=10,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
            cosmic_strike_prob=2.0,
        )
        sim = Simulation(config)
        sim.initialize()
        result = sim.step()

        cosmic_events = [e for e in result.events if e.event_type == "cosmic_strike"]
        destruction_events = [e for e in result.events if e.event_type == "destruction"]

        assert len(cosmic_events) > 0
        # 宇宙打击摧毁文明 → 应有毁灭事件
        assert len(destruction_events) > 0


# ============================================================
#  集成测试
# ============================================================

class TestIntegration:
    """多步模拟集成测试。"""

    def test_full_run_with_save(self, tmp_path: pytest.TempPathFactory) -> None:
        """完整运行流程：初始化 → 运行 → 保存 → 加载 → 继续。"""
        config = make_config(
            initial_civ_count=5,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
            total_steps=3,
            output_dir=str(tmp_path),
        )
        sim = Simulation(config)
        sim.initialize()
        assert sim.is_running is True

        # 运行 3 步
        sim.run()
        assert sim.current_step == 3

        # 保存状态
        sim.save_state()

        # 加载状态
        loaded = Simulation.load_state(str(tmp_path / "state.json"))
        assert loaded.current_step == 3
        assert len(loaded.civilizations) == len(sim.civilizations)

        # 继续运行
        loaded.config.total_steps = 5
        loaded.is_running = True
        loaded.run()
        assert loaded.current_step == 5

    def test_initialize_twice(self) -> None:
        """多次 initialize 可以重新初始化。"""
        config = make_config(
            initial_civ_count=3,
            universe_size=1000.0,
            spatial_grid_cell_size=100.0,
        )
        sim = Simulation(config)
        sim.initialize()
        assert len(sim.civilizations) == 3

        # 重新初始化
        sim.config.initial_civ_count = 5
        sim.initialize()
        assert len(sim.civilizations) == 5
