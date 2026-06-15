"""探测模块测试 —— detect_contacts() 函数。

测试覆盖：
- R4.1 ContactEvent 数据类属性
- R4.2 空间索引查询（query_neighbors 集成）
- R4.3 探测范围修正（隐蔽性减免、通信加成）
- R4.4 去重逻辑（(min_id, max_id) 集合）
- 非对称探测（一方探测到另一方但反之不成立）
- 死亡文明跳过
- 空列表处理
"""

from src.config import SimulationConfig
from src.entity import Civilization
from src.rules.detection import ContactEvent, detect_contacts
from src.spatial import SpatialIndex


def _make_config(**overrides: float | int | str | bool) -> SimulationConfig:
    """创建测试用 SimulationConfig，可通过关键字参数覆盖默认值。"""
    config = SimulationConfig()
    for key, value in overrides.items():
        setattr(config, key, value)
    return config


def _make_civ(**overrides: float | int | str | bool) -> Civilization:
    """创建测试用 Civilization，可通过关键字参数覆盖默认值。"""
    defaults: dict[str, float | int | str | bool] = {
        "id": 1,
        "name": "测试文明",
        "x": 0.0,
        "y": 0.0,
        "level": 1,
        "tech_points": 0.0,
        "tech_explosion_prob": 0.0,
        "expansion_radius": 10.0,
        "population": 1e8,
        "energy_output": 1e15,
        "aggressiveness": 0.5,
        "stealth": 0.0,
        "detection_range": 100.0,
        "is_alive": True,
        "birth_time": 0,
        "communication_active": False,
    }
    params = {**defaults, **overrides}
    civ = Civilization(**params)  # type: ignore[arg-type]
    return civ


def _make_index(
    universe_size: float,
    civilizations: list[Civilization],
    cell_size: float = 500.0,
) -> SpatialIndex:
    """创建已构建好索引的 SpatialIndex。

    Args:
        universe_size: 宇宙空间边长。
        civilizations: 所有文明的列表。
        cell_size: 网格单元大小（默认 500 光年）。

    Returns:
        已调用 rebuild 的 SpatialIndex 实例。
    """
    index = SpatialIndex(universe_size, cell_size)
    index.rebuild(civilizations)
    return index


# =============================================================================
# R4.1 ContactEvent 数据类
# =============================================================================


class TestContactEvent:
    """ContactEvent 数据类基本属性测试。"""

    def test_contact_event_attributes(self) -> None:
        """验证 ContactEvent 具有所有必需属性。"""
        civ_a = _make_civ(id=1)
        civ_b = _make_civ(id=2)
        event = ContactEvent(
            civ_a=civ_a,
            civ_b=civ_b,
            distance=50.0,
            detected_by_a=True,
            detected_by_b=False,
        )
        assert event.civ_a is civ_a
        assert event.civ_b is civ_b
        assert event.distance == 50.0
        assert event.detected_by_a is True
        assert event.detected_by_b is False

    def test_contact_event_is_dataclass(self) -> None:
        """验证 ContactEvent 是 dataclass。"""
        import dataclasses
        assert dataclasses.is_dataclass(ContactEvent), (
            "ContactEvent 应是 dataclass"
        )


# =============================================================================
# R4.2 范围内探测测试
# =============================================================================


class TestBasicDetection:
    """基础探测功能测试。"""

    def test_both_detect_within_range(self) -> None:
        """验证两个文明在探测范围内时互相探测到。"""
        config = _make_config(universe_size=10000.0)
        civ1 = _make_civ(id=1, x=0.0, y=0.0, detection_range=100.0, stealth=0.0)
        civ2 = _make_civ(id=2, x=50.0, y=0.0, detection_range=100.0, stealth=0.0)
        index = _make_index(10000.0, [civ1, civ2])

        contacts = detect_contacts([civ1, civ2], index, config)

        assert len(contacts) == 1, f"预期 1 个接触事件，实际 {len(contacts)}"
        event = contacts[0]
        assert event.detected_by_a is True, "civ1 应探测到 civ2"
        assert event.detected_by_b is True, "civ2 应探测到 civ1"
        assert event.distance == 50.0

    def test_no_contact_when_out_of_range(self) -> None:
        """验证超出探测范围时不生成接触事件。"""
        config = _make_config(universe_size=10000.0)
        # detection_range=100，两文明距离 500 >> 100
        civ1 = _make_civ(id=1, x=0.0, y=0.0, detection_range=100.0)
        civ2 = _make_civ(id=2, x=500.0, y=0.0, detection_range=100.0)
        index = _make_index(10000.0, [civ1, civ2])

        contacts = detect_contacts([civ1, civ2], index, config)

        assert len(contacts) == 0, (
            f"超出范围不应产生接触事件，实际 {len(contacts)}"
        )

    def test_contact_at_exact_range_boundary(self) -> None:
        """验证文明恰好在探测范围边界上时仍能探测到。"""
        config = _make_config(universe_size=10000.0)
        # detection_range=100，距离=100 → 边界上应能探测到（<=）
        civ1 = _make_civ(id=1, x=0.0, y=0.0, detection_range=100.0, stealth=0.0)
        civ2 = _make_civ(id=2, x=100.0, y=0.0, detection_range=100.0, stealth=0.0)
        index = _make_index(10000.0, [civ1, civ2])

        contacts = detect_contacts([civ1, civ2], index, config)

        assert len(contacts) == 1, (
            f"边界距离应产生接触事件，实际 {len(contacts)}"
        )
        assert contacts[0].distance == 100.0
        assert contacts[0].detected_by_a is True
        assert contacts[0].detected_by_b is True

    def test_no_contact_just_beyond_range(self) -> None:
        """验证稍超出探测范围时无法探测。"""
        config = _make_config(universe_size=10000.0)
        # detection_range=100，距离=101 → 超出范围
        civ1 = _make_civ(id=1, x=0.0, y=0.0, detection_range=100.0, stealth=0.0)
        civ2 = _make_civ(id=2, x=101.0, y=0.0, detection_range=100.0, stealth=0.0)
        index = _make_index(10000.0, [civ1, civ2])

        contacts = detect_contacts([civ1, civ2], index, config)

        assert len(contacts) == 0, (
            f"超出范围不应产生接触事件，实际 {len(contacts)}"
        )


# =============================================================================
# R4.3 隐蔽性影响测试
# =============================================================================


class TestStealthEffect:
    """隐蔽性减免探测测试。

    公式: effective_range = detection_range * (1 - target.stealth * 0.5)

    stealth=0.0 → 全额探测 range
    stealth=1.0 → 有效范围减半
    """

    def test_no_stealth_full_detection(self) -> None:
        """验证目标无隐蔽性时全额探测。"""
        config = _make_config(universe_size=10000.0)
        # detection_range=100, stealth=0.0, 距离 80 → 全额探测
        civ_a = _make_civ(id=1, x=0.0, y=0.0, detection_range=100.0, stealth=0.0)
        civ_b = _make_civ(id=2, x=80.0, y=0.0, detection_range=100.0, stealth=0.0)
        index = _make_index(10000.0, [civ_a, civ_b])

        contacts = detect_contacts([civ_a, civ_b], index, config)

        assert len(contacts) == 1
        # effective_range_a = 100 * (1 - 0 * 0.5) = 100
        # 80 <= 100 → detected_by_a = True
        assert contacts[0].detected_by_a is True

    def test_high_stealth_reduces_detection_range(self) -> None:
        """验证高隐蔽性目标的有效探测范围缩小。

        civ_a: detection_range=30, stealth=0.0
        civ_b: detection_range=30, stealth=1.0
        距离: 20

        A 探测 B: 30 * (1 - 1.0*0.5) = 15 < 20 → 不探测
        B 探测 A: 30 * (1 - 0.0*0.5) = 30 >= 20 → 探测
        """
        config = _make_config(universe_size=10000.0)
        civ_a = _make_civ(id=1, x=0.0, y=0.0, detection_range=30.0, stealth=0.0)
        civ_b = _make_civ(id=2, x=20.0, y=0.0, detection_range=30.0, stealth=1.0)
        index = _make_index(10000.0, [civ_a, civ_b])

        contacts = detect_contacts([civ_a, civ_b], index, config)

        assert len(contacts) == 1
        # A 不应探测到 B（隐蔽性减免）
        assert contacts[0].detected_by_a is False, (
            "A 不应探测到高隐蔽性的 B，但 detected_by_a=True"
        )
        # B 应探测到 A（A 无隐蔽性）
        assert contacts[0].detected_by_b is True, (
            "B 应探测到无隐蔽性的 A，但 detected_by_b=False"
        )

    def test_stealth_completely_hides(self) -> None:
        """验证双方都有高隐蔽性时完全无法互相探测。

        双方 detection_range=20, stealth=1.0, 距离=15
        A 探测 B: 20 * (1 - 0.5) = 10 < 15 → 不探测
        B 探测 A: 20 * (1 - 0.5) = 10 < 15 → 不探测
        """
        config = _make_config(universe_size=10000.0)
        civ_a = _make_civ(id=1, x=0.0, y=0.0, detection_range=20.0, stealth=1.0)
        civ_b = _make_civ(id=2, x=15.0, y=0.0, detection_range=20.0, stealth=1.0)
        index = _make_index(10000.0, [civ_a, civ_b])

        contacts = detect_contacts([civ_a, civ_b], index, config)

        assert len(contacts) == 0, (
            f"双方高隐蔽性不应产生接触事件，实际 {len(contacts)}"
        )

    def test_partial_stealth(self) -> None:
        """验证中等隐蔽性的部分减免效果。

        civ_a: detection_range=100, stealth=0.0
        civ_b: detection_range=100, stealth=0.6
        距离: 75

        A 探测 B: 100 * (1 - 0.6*0.5) = 100 * 0.7 = 70 < 75 → 不探测
        B 探测 A: 100 * (1 - 0.0*0.5) = 100 >= 75 → 探测
        """
        config = _make_config(universe_size=10000.0)
        civ_a = _make_civ(id=1, x=0.0, y=0.0, detection_range=100.0, stealth=0.0)
        civ_b = _make_civ(id=2, x=75.0, y=0.0, detection_range=100.0, stealth=0.6)
        index = _make_index(10000.0, [civ_a, civ_b])

        contacts = detect_contacts([civ_a, civ_b], index, config)

        assert len(contacts) == 1
        assert contacts[0].detected_by_a is False, (
            "A 不应探测到有隐蔽性的 B"
        )
        assert contacts[0].detected_by_b is True, (
            "B 应探测到无隐蔽性的 A"
        )


# =============================================================================
# R4.3 通信加成测试
# =============================================================================


class TestCommunicationBonus:
    """通信中的文明更容易被探测测试。

    公式: 如果 target.communication_active, effective_range *= 1.5
    """

    def test_communication_increases_detection_range(self) -> None:
        """验证通信中的文明更容易被探测到。

        query_neighbors 原始查询使用 civ.detection_range 过滤，
        通信加成在 detect_contacts 内部生效。

        设计: civ_a 的原始 detection_range 足够大，使 civ_b 出现在邻居列表，
        但 stealth 减免后有效范围 < 距离。通信加成使有效范围 > 距离。

        civ_a: detection_range=100, stealth=0.0
        civ_b: detection_range=30, stealth=0.6, communication_active=True
        距离: 80

        A 探测 B（无通信加成）:
          effective = 100 * (1 - 0.6*0.5) = 70 < 80 → 不探测
        A 探测 B（有通信加成，target.communication_active=True）:
          effective = 70 * 1.5 = 105 >= 80 → 探测！
        B 探测 A:
          effective = 30 * (1 - 0) = 30 < 80 → 不探测
        """
        config = _make_config(universe_size=10000.0)
        civ_a = _make_civ(id=1, x=0.0, y=0.0, detection_range=100.0, stealth=0.0)
        civ_b = _make_civ(
            id=2, x=80.0, y=0.0, detection_range=30.0, stealth=0.6,
            communication_active=True,
        )
        index = _make_index(10000.0, [civ_a, civ_b])

        contacts = detect_contacts([civ_a, civ_b], index, config)

        assert len(contacts) == 1, (
            "通信加成应使接触被探测到"
        )
        # 按 ID 查找 civ_a(id=1) 是否探测到 civ_b(id=2)
        event = contacts[0]
        if event.civ_a.id == 1:
            assert event.detected_by_a is True, (
                "civ_a(id=1) 应因通信加成探测到 civ_b(id=2)"
            )
        else:
            assert event.detected_by_b is True, (
                "civ_a(id=1) 应因通信加成探测到 civ_b(id=2)"
            )

    def test_communication_bonus_stacks_with_stealth(self) -> None:
        """验证通信加成与隐蔽性减免叠加计算。

        civ_a: detection_range=100, stealth=0.0
        civ_b: detection_range=100, stealth=0.8, communication_active=True
        距离: 80

        A 探测 B:
          base = 100 * (1 - 0.8*0.5) = 100 * 0.6 = 60
          通信加成: 60 * 1.5 = 90 >= 80 → 探测！
        无通信时: 60 < 80 → 不探测
        """
        config = _make_config(universe_size=10000.0)
        civ_a = _make_civ(id=1, x=0.0, y=0.0, detection_range=100.0, stealth=0.0)
        civ_b = _make_civ(
            id=2, x=80.0, y=0.0, detection_range=100.0, stealth=0.8,
            communication_active=True,
        )
        index = _make_index(10000.0, [civ_a, civ_b])

        contacts = detect_contacts([civ_a, civ_b], index, config)

        assert len(contacts) == 1
        # 通信加成使有效范围从 60 提升到 90，足以及到 80 距离
        assert contacts[0].detected_by_a is True, (
            "通信加成应与隐蔽性减免叠加后仍能探测到"
        )

    def test_communication_only_affects_detector_side(self) -> None:
        """验证通信只影响探测者对被探测方的探测（target.communication_active），
        不影响探测方自身的探测能力。

        civ_a 有通信但小探测范围，civ_b 无通信但大探测范围。
        距离 30，query_neighbors 用 civ_b 的 detection_range=100 可查到 civ_a，
        但用 civ_a 的 detection_range=20 查不到 civ_b。

        civ_a (id=1): x=0, detection_range=20, communication_active=True
        civ_b (id=2): x=30, detection_range=100, communication_active=False

        预期:
        - civ_a(id=1) 自身通信不影响其探测能力 → 20 < 30 → 不探测 civ_b
        - civ_b(id=2) 大范围 100 >= 30 → 探测 civ_a
        - civ_a 通信使自身更容易被 civ_b 探测（但本例中即使无通信也 100 >= 30）
        """
        config = _make_config(universe_size=10000.0)
        civ_a = _make_civ(
            id=1, x=0.0, y=0.0, detection_range=20.0, stealth=0.0,
            communication_active=True,
        )
        civ_b = _make_civ(
            id=2, x=30.0, y=0.0, detection_range=100.0, stealth=0.0,
            communication_active=False,
        )
        index = _make_index(10000.0, [civ_a, civ_b])

        contacts = detect_contacts([civ_a, civ_b], index, config)

        assert len(contacts) == 1

        # 按 ID 查找 civ_a(id=1) 是否探测到 civ_b(id=2)
        event = contacts[0]
        if event.civ_a.id == 1:
            # civ_a is civ_a in the event
            assert event.detected_by_a is False, (
                "civ_a 自身通信不影响其探测能力，不应探测到 civ_b"
            )
            assert event.detected_by_b is True, (
                "civ_b 应能探测到 civ_a"
            )
        else:
            # civ_a is civ_b in the event
            assert event.detected_by_b is False, (
                "civ_a 自身通信不影响其探测能力，不应探测到 civ_b"
            )
            assert event.detected_by_a is True, (
                "civ_b 应能探测到 civ_a"
            )


# =============================================================================
# R4.4 去重逻辑测试
# =============================================================================


class TestDeduplication:
    """接触事件去重测试。"""

    def test_no_duplicate_contacts_for_pair(self) -> None:
        """验证同一对文明只生成一个接触事件。"""
        config = _make_config(universe_size=10000.0)
        civ_a = _make_civ(id=1, x=0.0, y=0.0, detection_range=200.0, stealth=0.0)
        civ_b = _make_civ(id=2, x=50.0, y=0.0, detection_range=200.0, stealth=0.0)
        index = _make_index(10000.0, [civ_a, civ_b])

        contacts = detect_contacts([civ_a, civ_b], index, config)

        assert len(contacts) == 1, (
            f"一对文明应只有一个接触事件，实际 {len(contacts)}"
        )

    def test_no_duplicate_with_multiple_civs(self) -> None:
        """验证三文明互相探测时不产生重复事件。"""
        config = _make_config(universe_size=10000.0)
        civ1 = _make_civ(id=1, x=0.0, y=0.0, detection_range=200.0, stealth=0.0)
        civ2 = _make_civ(id=2, x=50.0, y=0.0, detection_range=200.0, stealth=0.0)
        civ3 = _make_civ(id=3, x=100.0, y=0.0, detection_range=200.0, stealth=0.0)
        index = _make_index(10000.0, [civ1, civ2, civ3])

        contacts = detect_contacts([civ1, civ2, civ3], index, config)

        # 三文明两两配对，应有 C(3,2) = 3 个事件
        assert len(contacts) == 3, (
            f"三文明应有 3 个接触事件，实际 {len(contacts)}"
        )

        # 验证每对唯一
        pairs = {(min(e.civ_a.id, e.civ_b.id), max(e.civ_a.id, e.civ_b.id))
                 for e in contacts}
        assert len(pairs) == 3, (
            f"应有 3 个唯一对，实际 {len(pairs)}"
        )
        assert (1, 2) in pairs
        assert (1, 3) in pairs
        assert (2, 3) in pairs

    def test_deduplication_reverse_direction(self) -> None:
        """验证即使文明列表顺序不同也能正确去重。

        如果 detect_contacts 内部遍历顺序导致 (B,A) 先于 (A,B) 被处理，
        应仍然只生成一个事件。
        """
        config = _make_config(universe_size=10000.0)
        civ_a = _make_civ(id=1, x=0.0, y=0.0, detection_range=200.0, stealth=0.0)
        civ_b = _make_civ(id=2, x=50.0, y=0.0, detection_range=200.0, stealth=0.0)
        index = _make_index(10000.0, [civ_a, civ_b])

        # 以不同顺序传入列表，验证去重仍有效
        contacts_reversed = detect_contacts([civ_b, civ_a], index, config)

        assert len(contacts_reversed) == 1, (
            f"反向顺序仍应产生 1 个接触事件，实际 {len(contacts_reversed)}"
        )


# =============================================================================
# 非对称探测测试
# =============================================================================


class TestAsymmetricDetection:
    """非对称探测测试（一方探测到另一方但反之不成立）。"""

    def test_one_way_detection(self) -> None:
        """验证单向探测生成接触事件。

        civ_a: detection_range=100, stealth=0.0
        civ_b: detection_range=10, stealth=0.0
        距离: 30

        A 探测 B: 100 >= 30 → 是
        B 探测 A: 10 < 30 → 否
        """
        config = _make_config(universe_size=10000.0)
        civ_a = _make_civ(id=1, x=0.0, y=0.0, detection_range=100.0, stealth=0.0)
        civ_b = _make_civ(id=2, x=30.0, y=0.0, detection_range=10.0, stealth=0.0)
        index = _make_index(10000.0, [civ_a, civ_b])

        contacts = detect_contacts([civ_a, civ_b], index, config)

        assert len(contacts) == 1, (
            f"单向探测应产生接触事件，实际 {len(contacts)}"
        )
        assert contacts[0].detected_by_a is True, (
            "A 探测范围大，应能探测到 B"
        )
        assert contacts[0].detected_by_b is False, (
            "B 探测范围小，不应探测到 A"
        )

    def test_opposite_one_way_detection(self) -> None:
        """验证相反方向的单向探测（civ_a 小范围，civ_b 大范围）。

        civ_a(id=1): detection_range=10
        civ_b(id=2): detection_range=100
        距离: 30

        query_neighbors 用 detection_range=10 查不到 civ_b（30 > 10）。
        query_neighbors 用 detection_range=100 查到 civ_a（30 <= 100）。
        """
        config = _make_config(universe_size=10000.0)
        civ_a = _make_civ(id=1, x=0.0, y=0.0, detection_range=10.0, stealth=0.0)
        civ_b = _make_civ(id=2, x=30.0, y=0.0, detection_range=100.0, stealth=0.0)
        index = _make_index(10000.0, [civ_a, civ_b])

        contacts = detect_contacts([civ_a, civ_b], index, config)

        assert len(contacts) == 1

        # 按 ID 查找 civ_a(id=1) 是否探测到 civ_b(id=2)
        event = contacts[0]
        if event.civ_a.id == 1:
            assert event.detected_by_a is False, (
                "civ_a 探测范围小，不应探测到 civ_b"
            )
            assert event.detected_by_b is True, (
                "civ_b 探测范围大，应能探测到 civ_a"
            )
        else:
            assert event.detected_by_b is False, (
                "civ_a 探测范围小，不应探测到 civ_b"
            )
            assert event.detected_by_a is True, (
                "civ_b 探测范围大，应能探测到 civ_a"
            )


# =============================================================================
# 死亡文明跳过测试
# =============================================================================


class TestDeadCivSkip:
    """死亡文明跳过测试。"""

    def test_dead_civ_not_in_contacts(self) -> None:
        """验证死亡文明不会出现在任何接触事件中。"""
        config = _make_config(universe_size=10000.0)
        alive = _make_civ(
            id=1, x=0.0, y=0.0, detection_range=200.0, stealth=0.0,
        )
        dead = _make_civ(
            id=2, x=50.0, y=0.0, detection_range=200.0, stealth=0.0,
            is_alive=False,
        )
        index = _make_index(10000.0, [alive, dead])

        contacts = detect_contacts([alive, dead], index, config)

        assert len(contacts) == 0, (
            f"死亡文明不应参与接触事件，实际 {len(contacts)}"
        )

    def test_mixed_alive_and_dead(self) -> None:
        """验证混合存活和死亡文明时正确处理。"""
        config = _make_config(universe_size=10000.0)
        alive_a = _make_civ(
            id=1, x=0.0, y=0.0, detection_range=200.0, stealth=0.0,
        )
        alive_b = _make_civ(
            id=2, x=50.0, y=0.0, detection_range=200.0, stealth=0.0,
        )
        dead = _make_civ(
            id=3, x=100.0, y=0.0, detection_range=200.0, stealth=0.0,
            is_alive=False,
        )
        index = _make_index(10000.0, [alive_a, alive_b, dead])

        contacts = detect_contacts([alive_a, alive_b, dead], index, config)

        # 只有 alive_a 和 alive_b 之间的事件
        assert len(contacts) == 1, (
            f"只有存活文明间应产生接触事件，实际 {len(contacts)}"
        )
        assert {contacts[0].civ_a.id, contacts[0].civ_b.id} == {1, 2}


# =============================================================================
# 自身探测排除测试
# =============================================================================


class TestSelfDetection:
    """自身探测排除测试。"""

    def test_no_self_contact(self) -> None:
        """验证文明不会探测到自己。"""
        config = _make_config(universe_size=10000.0)
        civ = _make_civ(id=1, x=0.0, y=0.0, detection_range=1000.0, stealth=0.0)
        index = _make_index(10000.0, [civ])

        contacts = detect_contacts([civ], index, config)

        assert len(contacts) == 0, (
            "不应产生自己与自己的接触事件"
        )


# =============================================================================
# 空列表和边界测试
# =============================================================================


class TestEdgeCases:
    """边界情况测试。"""

    def test_empty_civilizations_list(self) -> None:
        """验证空列表不会报错且返回空列表。"""
        config = _make_config(universe_size=10000.0)
        index = SpatialIndex(10000.0, 500.0)

        contacts = detect_contacts([], index, config)

        assert contacts == [], "空列表应返回空列表"

    def test_all_dead(self) -> None:
        """验证全为死亡文明时返回空列表。"""
        config = _make_config(universe_size=10000.0)
        dead1 = _make_civ(id=1, x=0.0, y=0.0, detection_range=200.0, is_alive=False)
        dead2 = _make_civ(id=2, x=50.0, y=0.0, detection_range=200.0, is_alive=False)
        index = _make_index(10000.0, [dead1, dead2])

        contacts = detect_contacts([dead1, dead2], index, config)

        assert contacts == [], "全死亡应返回空列表"

    def test_single_civilization(self) -> None:
        """验证单个文明不会产生接触事件。"""
        config = _make_config(universe_size=10000.0)
        civ = _make_civ(id=1, x=0.0, y=0.0, detection_range=1000.0)
        index = _make_index(10000.0, [civ])

        contacts = detect_contacts([civ], index, config)

        assert contacts == [], "单个文明不会产生接触事件"

    def test_ring_distance_wrap_around(self) -> None:
        """验证环形宇宙坐标包裹下的接触事件。

        将两个文明放置在环形边界的对面，使跨越边界的距离更短。
        """
        config = _make_config(universe_size=1000.0)
        # civ1 在左边界，civ2 在右边界
        # 直接距离 = 950，环形距离 = 50（绕边界）
        civ1 = _make_civ(id=1, x=10.0, y=0.0, detection_range=100.0, stealth=0.0)
        civ2 = _make_civ(id=2, x=960.0, y=0.0, detection_range=100.0, stealth=0.0)
        index = _make_index(1000.0, [civ1, civ2])

        contacts = detect_contacts([civ1, civ2], index, config)

        # 环形距离 = min(|10-960|, 1000-|10-960|) = min(950, 50) = 50
        # 50 <= 100 → 应探测到
        assert len(contacts) == 1, (
            f"环形边界探测应产生接触事件，实际 {len(contacts)}"
        )
        assert contacts[0].distance == 50.0, (
            f"距离应为 50（环形最短距离），实际 {contacts[0].distance}"
        )
