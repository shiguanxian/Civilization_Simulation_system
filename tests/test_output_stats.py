"""输出统计模块测试 — StepStats, StatsCollector, format_step_summary。"""

from dataclasses import fields, is_dataclass

import pytest

from src.entity import Civilization
from src.output.stats import StatsCollector, StepStats, format_step_summary

# =============================================================================
# StepStats 数据类测试
# =============================================================================

STEPSTATS_FIELDS: dict[str, type] = {
    "step": int,
    "total_civilizations": int,
    "new_born": int,
    "destroyed": int,
    "level_distribution": dict[int, int],
    "average_level": float,
    "max_level": int,
    "average_tech_points": float,
    "total_tech_points": float,
    "tech_explosions": int,
    "average_aggressiveness": float,
    "average_stealth": float,
    "exposed_civilizations": int,
    "average_detection_range": float,
    "average_expansion_radius": float,
    "total_energy": float,
    "total_population": float,
    "average_energy": float,
    "average_population": float,
    "contacts_count": int,
    "attacks_count": int,
    "cosmic_strikes": int,
}


def test_stepstats_is_dataclass() -> None:
    """验证 StepStats 使用 @dataclass 装饰器。"""
    assert is_dataclass(StepStats)


def test_stepstats_has_exactly_22_fields() -> None:
    """验证 StepStats 有且仅有 22 个字段。"""
    field_names = {f.name for f in fields(StepStats)}
    assert len(field_names) == 22
    assert field_names == set(STEPSTATS_FIELDS.keys())


def test_stepstats_field_types() -> None:
    """验证 StepStats 所有字段的类型注解正确。

    注意：stats.py 使用 ``from __future__ import annotations``，
    因此运行时的 ``field.type`` 为字符串。这里验证字符串表示的基类型一致。
    """
    for field in fields(StepStats):
        expected_type = STEPSTATS_FIELDS[field.name]
        # 处理字符串注解（from __future__ import annotations）
        actual_str = field.type if isinstance(field.type, str) else str(field.type)
        # 获取预期类型的简单名（如 "dict"、"int"）
        if hasattr(expected_type, "__name__"):
            expected_str = expected_type.__name__
        else:
            expected_str = str(expected_type)
        # 验证实际注解字符串以预期类型名开头
        # 如 "dict[int, int]" 以 "dict" 开头
        assert actual_str.startswith(expected_str), (
            f"字段 {field.name} 类型应为 {expected_str}，"
            f"实际为 {actual_str}"
        )


def test_stepstats_default_values() -> None:
    """验证 StepStats 的默认值正确。"""
    s = StepStats()
    assert s.step == 0
    assert s.total_civilizations == 0
    assert s.new_born == 0
    assert s.destroyed == 0
    assert s.level_distribution == {}
    assert s.average_level == 0.0
    assert s.max_level == 0
    assert s.average_tech_points == 0.0
    assert s.total_tech_points == 0.0
    assert s.tech_explosions == 0
    assert s.average_aggressiveness == 0.0
    assert s.average_stealth == 0.0
    assert s.exposed_civilizations == 0
    assert s.average_detection_range == 0.0
    assert s.average_expansion_radius == 0.0
    assert s.total_energy == 0.0
    assert s.total_population == 0.0
    assert s.average_energy == 0.0
    assert s.average_population == 0.0
    assert s.contacts_count == 0
    assert s.attacks_count == 0
    assert s.cosmic_strikes == 0


def test_stepstats_custom_values() -> None:
    """验证 StepStats 可以接收自定义字段值。"""
    s = StepStats(
        step=42,
        total_civilizations=5,
        new_born=2,
        destroyed=1,
        level_distribution={1: 2, 2: 3},
        average_level=1.6,
        max_level=2,
        average_tech_points=1500.0,
        total_tech_points=7500.0,
        tech_explosions=1,
        average_aggressiveness=0.5,
        average_stealth=0.3,
        exposed_civilizations=3,
        average_detection_range=200.0,
        average_expansion_radius=50.0,
        total_energy=1e15,
        total_population=1e10,
        average_energy=2e14,
        average_population=2e9,
        contacts_count=4,
        attacks_count=2,
        cosmic_strikes=0,
    )
    assert s.step == 42
    assert s.total_civilizations == 5
    assert s.new_born == 2
    assert s.destroyed == 1
    assert s.level_distribution == {1: 2, 2: 3}
    assert s.average_level == 1.6
    assert s.max_level == 2
    assert s.average_tech_points == 1500.0
    assert s.total_tech_points == 7500.0
    assert s.tech_explosions == 1
    assert s.average_aggressiveness == 0.5
    assert s.average_stealth == 0.3
    assert s.exposed_civilizations == 3
    assert s.average_detection_range == 200.0
    assert s.average_expansion_radius == 50.0
    assert s.total_energy == 1e15
    assert s.total_population == 1e10
    assert s.average_energy == 2e14
    assert s.average_population == 2e9
    assert s.contacts_count == 4
    assert s.attacks_count == 2
    assert s.cosmic_strikes == 0


# =============================================================================
# StatsCollector 测试
# =============================================================================


def _make_civ(
    *,
    civ_id: int = 0,
    level: int = 1,
    tech_points: float = 0.0,
    aggressiveness: float = 0.0,
    stealth: float = 0.0,
    communication_active: bool = False,
    detection_range: float = 0.0,
    expansion_radius: float = 0.0,
    energy_output: float = 0.0,
    population: float = 0.0,
    is_alive: bool = True,
) -> Civilization:
    """创建具有指定参数的 Civilization 实例的辅助函数。"""
    return Civilization(
        id=civ_id,
        name=f"Test #{civ_id}",
        level=level,
        tech_points=tech_points,
        aggressiveness=aggressiveness,
        stealth=stealth,
        communication_active=communication_active,
        detection_range=detection_range,
        expansion_radius=expansion_radius,
        energy_output=energy_output,
        population=population,
        is_alive=is_alive,
    )


def test_collector_init() -> None:
    """验证 StatsCollector 初始化后历史记录为空。"""
    collector = StatsCollector()
    assert collector.history == []
    assert collector.get_latest() is None
    assert collector.get_history_since(0) == []


def test_collect_empty_list() -> None:
    """验证空文明列表的统计返回全零 StepStats。"""
    collector = StatsCollector()
    result = collector.collect([], step=0)
    assert result.step == 0
    assert result.total_civilizations == 0
    assert result.level_distribution == {}
    assert result.max_level == 0
    assert result.average_level == 0.0
    assert result.average_tech_points == 0.0
    assert len(collector.history) == 1
    assert collector.get_latest() is result


def test_collect_empty_ignores_dead_only() -> None:
    """验证空列表中也包含所有已死文明时仍返回全零。"""
    collector = StatsCollector()
    dead_civ = _make_civ(civ_id=0, level=3, is_alive=False)
    result = collector.collect([dead_civ], step=1)
    assert result.total_civilizations == 0
    assert result.step == 1


def test_collect_single_civ() -> None:
    """验证单个文明的统计正确。"""
    collector = StatsCollector()
    civ = _make_civ(
        civ_id=1,
        level=3,
        tech_points=5000.0,
        aggressiveness=0.7,
        stealth=0.3,
        communication_active=True,
        detection_range=300.0,
        expansion_radius=80.0,
        energy_output=1e15,
        population=1e9,
    )
    result = collector.collect([civ], step=1)

    assert result.step == 1
    assert result.total_civilizations == 1
    assert result.level_distribution == {3: 1}
    assert result.average_level == 3.0
    assert result.max_level == 3
    assert result.average_tech_points == 5000.0
    assert result.total_tech_points == 5000.0
    assert result.average_aggressiveness == 0.7
    assert result.average_stealth == 0.3
    assert result.exposed_civilizations == 1
    assert result.average_detection_range == 300.0
    assert result.average_expansion_radius == 80.0
    assert result.total_energy == 1e15
    assert result.total_population == 1e9
    assert result.average_energy == 1e15
    assert result.average_population == 1e9


def test_collect_multiple_civs_averages() -> None:
    """验证多个文明的平均值计算正确。"""
    collector = StatsCollector()
    civs = [
        _make_civ(
            civ_id=1, level=1, tech_points=100.0,
            aggressiveness=0.1, stealth=0.9,
            energy_output=1e12, population=1e6,
        ),
        _make_civ(
            civ_id=2, level=3, tech_points=500.0,
            aggressiveness=0.5, stealth=0.5,
            energy_output=1e14, population=1e8,
        ),
        _make_civ(
            civ_id=3, level=5, tech_points=1000.0,
            aggressiveness=0.9, stealth=0.1,
            energy_output=1e16, population=1e10,
        ),
    ]
    result = collector.collect(civs, step=10)

    assert result.total_civilizations == 3
    assert result.average_level == 3.0  # (1+3+5)/3
    assert result.max_level == 5
    assert result.average_tech_points == pytest.approx(533.333, abs=0.01)
    assert result.total_tech_points == 1600.0
    assert result.average_aggressiveness == 0.5
    assert result.average_stealth == 0.5
    assert result.total_energy == pytest.approx(1.0101e16, abs=1e12)  # 1e12 + 1e14 + 1e16
    assert result.average_energy == pytest.approx(3.3667e15, abs=1e12)


def test_collect_level_distribution() -> None:
    """验证等级分布统计正确。"""
    collector = StatsCollector()
    civs = [
        _make_civ(civ_id=1, level=1),
        _make_civ(civ_id=2, level=1),
        _make_civ(civ_id=3, level=2),
        _make_civ(civ_id=4, level=3),
        _make_civ(civ_id=5, level=3),
        _make_civ(civ_id=6, level=3),
        _make_civ(civ_id=7, level=5),
    ]
    result = collector.collect(civs, step=0)

    assert result.total_civilizations == 7
    assert result.level_distribution == {1: 2, 2: 1, 3: 3, 5: 1}
    assert result.max_level == 5
    # (1+1+2+3+3+3+5)/7 = 18/7 = 2.571...
    assert result.average_level == pytest.approx(2.5714, abs=0.001)


def test_collect_filters_dead_civilizations() -> None:
    """验证 collect 只统计存活文明，忽略已毁灭文明。"""
    collector = StatsCollector()
    alive = _make_civ(civ_id=1, level=4, is_alive=True)
    dead = _make_civ(civ_id=2, level=2, is_alive=False)
    result = collector.collect([alive, dead], step=1)

    assert result.total_civilizations == 1
    assert result.level_distribution == {4: 1}
    assert result.max_level == 4


def test_collect_with_events() -> None:
    """验证 step_events 能正确统计增量事件。"""
    collector = StatsCollector()
    civs = [_make_civ(civ_id=1, level=1)]

    events = [
        {"event_type": "birth"},
        {"event_type": "birth"},
        {"event_type": "destruction"},
        {"event_type": "tech_explosion"},
        {"event_type": "contact"},
        {"event_type": "contact"},
        {"event_type": "attack"},
        {"event_type": "cosmic_strike"},
    ]

    result = collector.collect(civs, step=1, step_events=events)

    assert result.new_born == 2
    assert result.destroyed == 1
    assert result.tech_explosions == 1
    assert result.contacts_count == 2
    assert result.attacks_count == 1
    assert result.cosmic_strikes == 1


def test_collect_events_empty_list() -> None:
    """验证 step_events 为空列表时增量数据均为 0。"""
    collector = StatsCollector()
    civs = [_make_civ(civ_id=1, level=1)]
    result = collector.collect(civs, step=0, step_events=[])

    assert result.new_born == 0
    assert result.destroyed == 0
    assert result.tech_explosions == 0
    assert result.contacts_count == 0
    assert result.attacks_count == 0
    assert result.cosmic_strikes == 0


def test_collect_events_unknown_type_ignored() -> None:
    """验证未知 event_type 被忽略。"""
    collector = StatsCollector()
    civs = [_make_civ(civ_id=1, level=1)]
    events = [
        {"event_type": "unknown_event"},
        {"event_type": "another_unknown"},
    ]
    result = collector.collect(civs, step=0, step_events=events)

    assert result.new_born == 0
    assert result.destroyed == 0
    assert result.tech_explosions == 0
    assert result.contacts_count == 0
    assert result.attacks_count == 0
    assert result.cosmic_strikes == 0


def test_collect_with_previous_stats() -> None:
    """验证 previous_stats 用于推算增量。"""
    collector = StatsCollector()
    prev = StepStats(
        step=0,
        total_civilizations=5,
        new_born=0,
        destroyed=0,
    )

    civs = [_make_civ(civ_id=i, level=1) for i in range(3)]
    result = collector.collect(civs, step=1, previous_stats=prev)

    # 从 5 个下降到 3 个，没有 step_events
    # destroyed = prev.total (5) - current.total (3) + new_born (0) = 2
    # new_born = total (3) - prev.total (5) + destroyed (2) = 0
    assert result.destroyed == 2
    assert result.new_born == 0


def test_collect_with_previous_stats_growth() -> None:
    """验证 previous_stats 在文明增长时推算正确。"""
    collector = StatsCollector()
    prev = StepStats(step=0, total_civilizations=3)

    civs = [_make_civ(civ_id=i, level=1) for i in range(5)]
    result = collector.collect(civs, step=1, previous_stats=prev)

    # 从 3 个增长到 5 个 => delta = +2
    assert result.new_born == 2
    assert result.destroyed == 0


def test_history_append() -> None:
    """验证多次 collect 会追加到历史记录。"""
    collector = StatsCollector()
    c1 = _make_civ(civ_id=1, level=1)
    c2 = _make_civ(civ_id=2, level=2)
    c3 = _make_civ(civ_id=3, level=3)

    s1 = collector.collect([c1], step=1)
    s2 = collector.collect([c1, c2], step=2)
    s3 = collector.collect([c1, c2, c3], step=3)

    assert len(collector.history) == 3
    assert collector.history[0] is s1
    assert collector.history[1] is s2
    assert collector.history[2] is s3


def test_get_latest() -> None:
    """验证 get_latest 返回最后一次 collect 的结果。"""
    collector = StatsCollector()

    assert collector.get_latest() is None

    c1 = _make_civ(civ_id=1, level=1)
    s1 = collector.collect([c1], step=1)
    assert collector.get_latest() is s1

    c2 = _make_civ(civ_id=2, level=2)
    s2 = collector.collect([c1, c2], step=2)
    assert collector.get_latest() is s2


def test_get_history_since() -> None:
    """验证 get_history_since 返回从指定步数开始的历史。"""
    collector = StatsCollector()

    c1 = _make_civ(civ_id=1, level=1)
    c2 = _make_civ(civ_id=2, level=2)
    c3 = _make_civ(civ_id=3, level=3)

    collector.collect([c1], step=1)
    collector.collect([c1, c2], step=2)
    collector.collect([c1, c2, c3], step=3)
    collector.collect([c1, c2, c3], step=5)

    since_2 = collector.get_history_since(2)
    assert len(since_2) == 3
    assert since_2[0].step == 2
    assert since_2[1].step == 3
    assert since_2[2].step == 5

    since_4 = collector.get_history_since(4)
    assert len(since_4) == 1
    assert since_4[0].step == 5


def test_get_history_since_large_step() -> None:
    """验证 get_history_since 在步数超过所有记录时返回空列表。"""
    collector = StatsCollector()
    civ = _make_civ(civ_id=1, level=1)
    collector.collect([civ], step=10)
    assert collector.get_history_since(100) == []


def test_clear() -> None:
    """验证 clear 清空历史记录。"""
    collector = StatsCollector()
    civ = _make_civ(civ_id=1, level=1)
    collector.collect([civ], step=0)
    assert len(collector.history) == 1

    collector.clear()
    assert collector.history == []
    assert collector.get_latest() is None


def test_collect_after_clear() -> None:
    """验证 clear 后重新收集工作正常。"""
    collector = StatsCollector()
    civ = _make_civ(civ_id=1, level=1)

    collector.collect([civ], step=0)
    collector.clear()

    result = collector.collect([civ], step=1, step_events=[{"event_type": "birth"}])
    assert result.step == 1
    assert result.total_civilizations == 1
    assert result.new_born == 1
    assert len(collector.history) == 1


# =============================================================================
# format_step_summary 测试
# =============================================================================


def test_format_step_summary_contains_step() -> None:
    """验证输出包含步数信息。"""
    stats = StepStats(
        step=42,
        total_civilizations=4238,
        new_born=12,
        destroyed=8,
        max_level=4,
        average_level=2.1,
        tech_explosions=2,
        exposed_civilizations=156,
        contacts_count=45,
        attacks_count=12,
        total_energy=3.45e18,
        total_population=2.1e14,
    )
    output = format_step_summary(stats)

    assert "时间步: 0042" in output
    assert "存活文明: 4,238" in output
    assert "新生: 12" in output
    assert "毁灭: 8" in output
    assert "最高等级: 4" in output
    assert "平均等级: 2.1" in output
    assert "科技爆炸: 2" in output
    assert "暴露文明: 156" in output
    assert "接触: 45" in output
    assert "攻击: 12" in output
    assert "总能量: 3.45e+18" in output or "总能量: 3.45e18" in output
    assert "总人口: 2.10e+14" in output or "总人口: 2.10e14" in output


def test_format_step_summary_returns_multiline() -> None:
    """验证输出为多行字符串。"""
    stats = StepStats(step=1, total_civilizations=10)
    output = format_step_summary(stats)

    lines = output.split("\n")
    assert len(lines) == 7  # header + 5 content + footer
    # 首行以 ── 开头
    assert lines[0].startswith("──")
    # 末行为分隔线
    assert lines[-1].startswith("─")


def test_format_step_summary_empty_stats() -> None:
    """验证全零统计信息的格式化输出。"""
    stats = StepStats(step=0)
    output = format_step_summary(stats)

    assert "时间步: 0000" in output
    assert "存活文明: 0" in output
    assert "最高等级: 0" in output
    assert "平均等级: 0.0" in output


def test_format_step_summary_large_numbers() -> None:
    """验证大数字格式化包含千位分隔符。"""
    stats = StepStats(
        step=1,
        total_civilizations=1234567,
    )
    output = format_step_summary(stats)
    assert "存活文明: 1,234,567" in output



