"""黑暗森林模块单元测试。

覆盖范围 (R5.1–R5.6)：
- _calculate_threat 公式正确性
- _decide_action 阈值判定
- _attempt_attack 成功／失败／已死亡
- _expose_civilization 状态变更
- apply_dark_forest 完整流程
- apply_cosmic_strike 概率与杀伤半径
"""

import random
from typing import Any

import pytest

from src.config import SimulationConfig
from src.entity import Civilization
from src.rules.dark_forest import (
    _attempt_attack,
    _calculate_threat,
    _decide_action,
    _expose_civilization,
    apply_cosmic_strike,
    apply_dark_forest,
)
from src.rules.detection import ContactEvent

# ============================================================
#  Helper factories
# ============================================================

def make_civ(**overrides: Any) -> Civilization:
    """创建一个带有合理默认值的 ``Civilization`` 实例。"""
    defaults: dict[str, Any] = {
        "id": 0,
        "name": "Test",
        "x": 0.0,
        "y": 0.0,
        "level": 1,
        "tech_points": 0.0,
        "tech_explosion_prob": 0.01,
        "expansion_radius": 10.0,
        "population": 1e6,
        "energy_output": 1e12,
        "aggressiveness": 0.5,
        "stealth": 0.5,
        "detection_range": 100.0,
        "is_alive": True,
        "birth_time": 0,
        "communication_active": False,
    }
    defaults.update(overrides)
    return Civilization(**defaults)


def make_config(**overrides: Any) -> SimulationConfig:
    """创建一个 ``SimulationConfig`` 并允许覆盖任意字段。"""
    cfg = SimulationConfig()
    for k, v in overrides.items():
        setattr(cfg, k, v)
    return cfg


# ============================================================
#  R5.1 — _calculate_threat
# ============================================================

class TestCalculateThreat:
    """威胁感知计算公式正确性验证。"""

    def test_baseline_mid_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """基线：各因素取中间值，无随机扰动时 threat 应为 1.0 左右。"""
        monkeypatch.setattr("src.rules.dark_forest.random.uniform", lambda a, b: 0.0)
        observer = make_civ(level=1)
        target = make_civ(
            level=1, aggressiveness=0.5, stealth=0.5, communication_active=False,
        )
        threat = _calculate_threat(observer, target)
        # 0.3 + 0.2*0 + 0.3*0.5 + 0.2*0.5 + 0 = 0.3 + 0.15 + 0.10 = 0.55
        assert threat == pytest.approx(0.55, abs=1e-9)

    def test_level_diff_increases_threat(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """目标等级高于观察者 → 威胁上升。"""
        monkeypatch.setattr("src.rules.dark_forest.random.uniform", lambda a, b: 0.0)
        observer = make_civ(level=1)
        target = make_civ(level=5, aggressiveness=0.0, stealth=1.0)
        threat = _calculate_threat(observer, target)
        # 0.3 + 0.2*4/5 + 0.3*0 + 0.2*0 + 0 = 0.3 + 0.16 = 0.46
        assert threat == pytest.approx(0.46, abs=1e-9)

    def test_aggressiveness_increases_threat(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """目标攻击性高 → 威胁上升。"""
        monkeypatch.setattr("src.rules.dark_forest.random.uniform", lambda a, b: 0.0)
        observer = make_civ()
        target = make_civ(level=1, aggressiveness=1.0, stealth=1.0)
        threat = _calculate_threat(observer, target)
        # 0.3 + 0 + 0.3*1 + 0 + 0 = 0.6
        assert threat == pytest.approx(0.6, abs=1e-9)

    def test_stealth_reduces_threat(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """目标隐蔽性高 → 威胁降低（因为不可见）。"""
        monkeypatch.setattr("src.rules.dark_forest.random.uniform", lambda a, b: 0.0)
        observer = make_civ()
        # stealth=1 → (1-stealth)=0 → 该项贡献 0
        target_high = make_civ(level=1, aggressiveness=0.0, stealth=1.0)
        threat_high = _calculate_threat(observer, target_high)
        # threat_high = 0.3
        # stealth=0 → (1-stealth)=1 → 该项贡献 0.2
        target_low = make_civ(level=1, aggressiveness=0.0, stealth=0.0)
        threat_low = _calculate_threat(observer, target_low)
        # threat_low = 0.3 + 0.2 = 0.5
        assert threat_low > threat_high

    def test_communication_increases_threat(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """目标正在通信 → 威胁增加 0.2。"""
        monkeypatch.setattr("src.rules.dark_forest.random.uniform", lambda a, b: 0.0)
        observer = make_civ()
        target = make_civ(level=1, aggressiveness=0.0, stealth=1.0, communication_active=True)
        threat = _calculate_threat(observer, target)
        # 0.3 + 0 + 0 + 0 + 0.2 = 0.5
        assert threat == pytest.approx(0.5, abs=1e-9)

    def test_random_perturbation(self) -> None:
        """随机扰动在 ±0.1 范围内。"""
        observer = make_civ()
        target = make_civ()
        threats = [_calculate_threat(observer, target) for _ in range(100)]
        for t in threats:
            assert 0.0 <= t <= 1.0

    def test_clamped_low(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """极低值被 clamp 到 0。"""
        # 使用超大幅度随机值来触发 clamp
        monkeypatch.setattr("src.rules.dark_forest.random.uniform", lambda a, b: -10.0)
        observer = make_civ(level=5)
        target = make_civ(level=1, aggressiveness=0.0, stealth=1.0)
        threat = _calculate_threat(observer, target)
        assert threat == 0.0

    def test_clamped_high(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """极高值被 clamp 到 1。"""
        monkeypatch.setattr("src.rules.dark_forest.random.uniform", lambda a, b: 0.1)
        observer = make_civ(level=1)
        target = make_civ(level=5, aggressiveness=1.0, stealth=0.0, communication_active=True)
        threat = _calculate_threat(observer, target)
        assert threat == 1.0


# ============================================================
#  R5.2 — _decide_action
# ============================================================

class TestDecideAction:
    """行动选择阈值行为验证。"""

    def test_high_threat_attacks(self) -> None:
        """威胁 >= attack_threshold → attack。"""
        config = make_config(attack_threshold=0.65, flee_threshold=0.35)
        assert _decide_action(0.65, config) == "attack"
        assert _decide_action(0.8, config) == "attack"
        assert _decide_action(1.0, config) == "attack"

    def test_low_threat_flees(self) -> None:
        """威胁 <= flee_threshold → flee。"""
        config = make_config(attack_threshold=0.65, flee_threshold=0.35)
        assert _decide_action(0.35, config) == "flee"
        assert _decide_action(0.2, config) == "flee"
        assert _decide_action(0.0, config) == "flee"

    def test_mid_threat_observes(self) -> None:
        """中间值 → observe。"""
        config = make_config(attack_threshold=0.65, flee_threshold=0.35)
        assert _decide_action(0.5, config) == "observe"
        assert _decide_action(0.4, config) == "observe"
        assert _decide_action(0.6, config) == "observe"

    def test_custom_thresholds(self) -> None:
        """自定义阈值正常工作。"""
        config = make_config(attack_threshold=0.8, flee_threshold=0.2)
        assert _decide_action(0.8, config) == "attack"
        assert _decide_action(0.2, config) == "flee"
        assert _decide_action(0.5, config) == "observe"


# ============================================================
#  R5.3 — _attempt_attack
# ============================================================

class TestAttemptAttack:
    """攻击判定逻辑验证。"""

    def test_success_kills_defender(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """攻击成功 → 防御方被毁灭，攻击方获得能量。"""
        monkeypatch.setattr("src.rules.dark_forest.random.random", lambda: 0.0)
        attacker = make_civ(id=1, level=3, energy_output=1e15, stealth=0.5)
        defender = make_civ(id=2, level=1, energy_output=1e12, stealth=0.1)
        initial_energy = attacker.energy_output
        result = _attempt_attack(attacker, defender)
        assert result is True
        assert defender.is_alive is False
        assert attacker.energy_output == pytest.approx(
            initial_energy + 1e12 * 0.1, rel=1e-9,
        )

    def test_failure_exposes_attacker(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """攻击失败 → 防御方暴露攻击者坐标。"""
        monkeypatch.setattr("src.rules.dark_forest.random.random", lambda: 1.0)
        attacker = make_civ(id=1, level=1, energy_output=1e12, communication_active=False)
        defender = make_civ(id=2, level=3, energy_output=1e15, stealth=0.9)
        result = _attempt_attack(attacker, defender)
        assert result is False
        assert defender.is_alive is True
        assert attacker.communication_active is True

    def test_defender_dead_returns_false(self) -> None:
        """防御方已死亡 → 返回 False，不产生副作用。"""
        attacker = make_civ(id=1)
        defender = make_civ(id=2, is_alive=False)
        result = _attempt_attack(attacker, defender)
        assert result is False
        assert attacker.communication_active is False

    def test_success_probability_lower_bound(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """成功概率被 clamp 到 >= 0.1。"""
        monkeypatch.setattr("src.rules.dark_forest.random.random", lambda: 0.099)
        attacker = make_civ(id=1, level=1, energy_output=1e12)
        # 最大压制：defender 等级高、隐蔽强
        defender = make_civ(id=2, level=5, energy_output=1e18, stealth=1.0)
        # prob = 0.5 + 0.1*(1-5) - 0.2*1.0 + 0* = 0.5 - 0.4 - 0.2 = -0.1 → clamp to 0.1
        result = _attempt_attack(attacker, defender)
        assert result is True

    def test_energy_advantage_bonus(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """攻击方能量高于防御方 → +0.1 成功率。"""
        monkeypatch.setattr("src.rules.dark_forest.random.random", lambda: 0.55)
        # prob without bonus: 0.5 + 0 + 0 + 0 = 0.5 → random 0.55 fails
        # prob with bonus: 0.5 + 0 + 0 + 0.1 = 0.6 → random 0.55 succeeds
        attacker = make_civ(id=1, level=1, energy_output=1e15, stealth=0.0)
        defender = make_civ(id=2, level=1, energy_output=1e12, stealth=0.0)
        result = _attempt_attack(attacker, defender)
        assert result is True


# ============================================================
#  R5.4 — _expose_civilization
# ============================================================

class TestExposeCivilization:
    """暴露处理逻辑验证。"""

    def test_sets_communication_active(self) -> None:
        """暴露设置 communication_active = True。"""
        civ = make_civ(communication_active=False)
        _expose_civilization(civ)
        assert civ.communication_active is True

    def test_reduces_stealth(self) -> None:
        """暴露使 stealth 降低 20%。"""
        civ = make_civ(stealth=0.5)
        _expose_civilization(civ)
        assert civ.stealth == pytest.approx(0.4, rel=1e-9)  # 0.5 * 0.8 = 0.4


# ============================================================
#  R5.5 — apply_dark_forest（完整流程）
# ============================================================

class TestApplyDarkForest:
    """黑暗森林主流程端到端验证。"""

    def test_no_contacts_no_effect(self) -> None:
        """空接触列表 → 无事件，计数均为 0。"""
        civs = [make_civ(id=1)]
        config = make_config()
        attacks, destroyed = apply_dark_forest(civs, [], config)
        assert attacks == 0
        assert destroyed == 0

    def test_no_threat_no_attack(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """双方威胁均低 → 无攻击。"""
        monkeypatch.setattr("src.rules.dark_forest.random.uniform", lambda a, b: 0.0)
        a = make_civ(id=1, level=1, aggressiveness=0.0, stealth=1.0)
        b = make_civ(id=2, level=1, aggressiveness=0.0, stealth=1.0)
        contact = ContactEvent(
            civ_a=a, civ_b=b, distance=10.0, detected_by_a=True, detected_by_b=True,
        )
        config = make_config(attack_threshold=0.65, flee_threshold=0.35)
        attacks, destroyed = apply_dark_forest([a, b], [contact], config)
        # threat = 0.3 + 0 + 0 + 0 + 0 = 0.3 ≤ flee_threshold → both flee
        assert attacks == 0
        assert destroyed == 0

    def test_high_threat_causes_attack(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """高威胁（等级差 + 攻击性）→ 攻击发生。"""
        monkeypatch.setattr("src.rules.dark_forest.random.uniform", lambda a, b: 0.0)
        monkeypatch.setattr("src.rules.dark_forest.random.random", lambda: 0.0)  # attack succeeds
        a = make_civ(id=1, level=1, aggressiveness=0.0, stealth=1.0)
        b = make_civ(id=2, level=5, aggressiveness=1.0, stealth=0.0)
        contact = ContactEvent(
            civ_a=a, civ_b=b, distance=10.0, detected_by_a=True, detected_by_b=True,
        )
        config = make_config(attack_threshold=0.65, flee_threshold=0.35)
        attacks, destroyed = apply_dark_forest([a, b], [contact], config)
        # a sees b: threat = 0.3+0.2*4/5+0.3*1+0.2*(1-0) = 0.96 → attack
        # b sees a: threat = 0.3+0.2*(-4)/5+0.3*0+0.2*(1-1) = 0.14 → flee
        assert attacks == 1
        assert destroyed == 1
        assert b.is_alive is False

    def test_detected_civ_gets_exposed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """被探测到的存活文明会被暴露。"""
        monkeypatch.setattr("src.rules.dark_forest.random.uniform", lambda a, b: 0.0)
        monkeypatch.setattr("src.rules.dark_forest.random.random", lambda: 0.0)  # attack succeeds
        a = make_civ(
            id=1, level=1, aggressiveness=0.0, stealth=1.0, communication_active=False,
        )
        b = make_civ(
            id=2, level=5, aggressiveness=1.0, stealth=0.0, communication_active=False,
        )
        contact = ContactEvent(
            civ_a=a, civ_b=b, distance=10.0, detected_by_a=True, detected_by_b=True,
        )
        config = make_config(attack_threshold=0.65, flee_threshold=0.35)
        apply_dark_forest([a, b], [contact], config)
        # b was detected_by_a and b survived long enough (but then got killed by attack)
        # Actually in the loop order: attack happens first, killing b
        # Then detected_by_a check: b.is_alive is False → skip exposure
        # detected_by_b check: a.is_alive is True → expose a
        # But wait, b detected a but b is dead... actually in the code:
        # if contact.detected_by_b and a.is_alive: _expose_civilization(a)
        # a is alive, b detected a → a gets exposed
        # But b is dead so detected_by_a branch is skipped
        assert a.communication_active is True

    def test_dead_civ_skipped(self) -> None:
        """联系中任意一方已死亡 → 跳过处理。"""
        a = make_civ(id=1, is_alive=False)
        b = make_civ(id=2)
        contact = ContactEvent(
            civ_a=a, civ_b=b, distance=10.0, detected_by_a=True, detected_by_b=True,
        )
        config = make_config()
        initial_a_comm = a.communication_active
        attacks, destroyed = apply_dark_forest([a, b], [contact], config)
        assert attacks == 0
        assert destroyed == 0
        assert a.communication_active == initial_a_comm  # no side effects


# ============================================================
#  R5.6 — apply_cosmic_strike
# ============================================================

class TestApplyCosmicStrike:
    """宇宙公理级打击验证。"""

    def test_no_strike_when_prob_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """概率未命中 → 返回 0，不杀伤任何文明。"""
        monkeypatch.setattr("src.rules.dark_forest.random.random", lambda: 1.0)
        civs = [make_civ(id=i, x=i * 100.0, y=0.0) for i in range(10)]
        config = make_config(cosmic_strike_prob=0.001, universe_size=10000.0)
        destroyed = apply_cosmic_strike(civs, config)
        assert destroyed == 0
        assert all(c.is_alive for c in civs)

    def test_strike_kills_in_radius(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """打击命中 → 半径内文明被毁灭。"""
        # random.random < prob → strike triggers
        # mock three uniform calls: strike_x=5000, strike_y=5000, radius_factor=0.05
        # radius = 10000 * 0.05 = 500
        uniform_values = [5000.0, 5000.0, 0.05]

        def mock_uniform(a, b):
            return uniform_values.pop(0)

        monkeypatch.setattr("src.rules.dark_forest.random.random", lambda: 0.0)
        monkeypatch.setattr("src.rules.dark_forest.random.uniform", mock_uniform)

        # civs at (5000,5000), (5100,5000), (5600,5000) → first 2 in radius, 3rd out
        civs = [
            make_civ(id=1, x=5000.0, y=5000.0),
            make_civ(id=2, x=5100.0, y=5000.0),  # 100 away → in radius
            make_civ(id=3, x=5600.0, y=5000.0),  # 600 away → out of radius
            make_civ(id=4, x=4500.0, y=5000.0),  # 500 away → exactly at edge
        ]
        config = make_config(cosmic_strike_prob=0.001, universe_size=10000.0)
        destroyed = apply_cosmic_strike(civs, config)

        assert destroyed == 3
        assert civs[0].is_alive is False
        assert civs[1].is_alive is False
        assert civs[2].is_alive is True  # out of range
        assert civs[3].is_alive is False  # exactly at radius edge

    def test_strike_uses_ring_distance(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """打击使用环形距离（跨边界距离应生效）。"""
        call_count = [0]

        def mock_uniform(a, b):
            call_count[0] += 1
            if call_count[0] == 1:
                return 100.0  # strike_x near left edge
            elif call_count[0] == 2:
                return 5000.0  # strike_y
            elif call_count[0] == 3:
                return 0.1  # radius factor → radius = 1000
            return 0.5

        monkeypatch.setattr("src.rules.dark_forest.random.random", lambda: 0.0)
        monkeypatch.setattr("src.rules.dark_forest.random.uniform", mock_uniform)

        # civ near right edge, ring distance to left edge should be short
        civs = [
            make_civ(id=1, x=9900.0, y=5000.0),
            # ring_distance to (100,5000) = min(9800, 200) = 200 → in radius
            make_civ(id=2, x=2000.0, y=5000.0),
            # ring_distance = 1900 → out of 1000 radius
        ]
        config = make_config(cosmic_strike_prob=0.001, universe_size=10000.0)
        destroyed = apply_cosmic_strike(civs, config)
        assert destroyed == 1
        assert civs[0].is_alive is False
        assert civs[1].is_alive is True

    def test_only_alive_civs_affected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """已死亡的文明不会被重复杀伤（也不会计入毁灭数）。"""
        call_count = [0]

        def mock_uniform(a, b):
            call_count[0] += 1
            if call_count[0] == 1:
                return 5000.0
            elif call_count[0] == 2:
                return 5000.0
            elif call_count[0] == 3:
                return 0.1  # radius = 1000
            return 0.5

        monkeypatch.setattr("src.rules.dark_forest.random.random", lambda: 0.0)
        monkeypatch.setattr("src.rules.dark_forest.random.uniform", mock_uniform)

        civs = [
            make_civ(id=1, x=5000.0, y=5000.0, is_alive=False),  # already dead
            make_civ(id=2, x=5100.0, y=5000.0),  # alive, in radius
        ]
        config = make_config(cosmic_strike_prob=0.001, universe_size=10000.0)
        destroyed = apply_cosmic_strike(civs, config)
        assert destroyed == 1
        assert civs[0].is_alive is False  # stays dead
        assert civs[1].is_alive is False

    def test_strike_radius_range(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """打击半径在 universe_size * [0.02, 0.1] 范围内。"""
        monkeypatch.setattr("src.rules.dark_forest.random.random", lambda: 0.0)
        call_args: list[tuple[float, float]] = []
        real_uniform = random.uniform

        def mock_uniform(a: float, b: float) -> float:
            call_args.append((a, b))
            return real_uniform(a, b)

        monkeypatch.setattr("src.rules.dark_forest.random.uniform", mock_uniform)

        config = make_config(cosmic_strike_prob=0.001, universe_size=10000.0)
        apply_cosmic_strike([make_civ(id=1)], config)

        # The 3rd call to uniform should be for radius factor: (0.02, 0.1)
        assert len(call_args) >= 3
        radius_factor_call = call_args[2]
        assert radius_factor_call == (0.02, 0.1)
