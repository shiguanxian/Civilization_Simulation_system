"""技术爆炸模块单元测试。

覆盖范围：
- R2.2 科技点自然积累
- R2.3 人口增长（逻辑斯蒂增长模型）
- R2.4 能量输出增长
- R2.5 技术爆炸判定与触发（含等级上限 5）
- 死亡文明跳过处理
"""

import pytest

from src.config import SimulationConfig
from src.entity import Civilization
from src.rules.tech_bomb import (
    _calc_carrying_capacity,
    _tech_needed,
    _trigger_tech_explosion,
    apply_development,
)

# ========================================================================
# 测试辅助函数
# ========================================================================


def _make_civ(**overrides: object) -> Civilization:
    """创建一个配备默认参数的文明用于测试。

    Args:
        **overrides: 覆盖 Civilization 默认字段的值。

    Returns:
        配置好的 Civilization 实例。
    """
    defaults: dict[str, object] = {
        "id": 1,
        "name": "TestCiv",
        "x": 5000.0,
        "y": 5000.0,
        "level": 1,
        "tech_points": 0.0,
        "tech_explosion_prob": 1.0,
        "expansion_radius": 50.0,
        "population": 1e8,
        "energy_output": 1e15,
        "aggressiveness": 0.5,
        "stealth": 0.5,
        "detection_range": 250.0,
        "is_alive": True,
        "birth_time": 0,
        "communication_active": False,
    }
    defaults.update(overrides)
    return Civilization(**defaults)  # type: ignore[arg-type]


def _default_config() -> SimulationConfig:
    """创建默认配置。"""
    return SimulationConfig()


# ========================================================================
# R2.2 科技点自然积累
# ========================================================================


class TestTechPointsAccumulation:
    """科技点自然积累测试。"""

    def test_tech_points_increase(self) -> None:
        """验证科技点随时间增长。"""
        civ = _make_civ(tech_points=0.0, tech_explosion_prob=0.0)
        config = _default_config()
        initial = civ.tech_points
        apply_development([civ], config)
        assert civ.tech_points > initial

    def test_tech_growth_scales_with_level(self) -> None:
        """验证科技点增长量与等级正相关。"""
        config = _default_config()
        civ_low = _make_civ(level=1, tech_points=0.0, tech_explosion_prob=0.0)
        civ_high = _make_civ(level=3, tech_points=0.0, tech_explosion_prob=0.0)

        apply_development([civ_low, civ_high], config)

        expected_low = config.tech_growth_base * (1 + 1 * 0.5)
        expected_high = config.tech_growth_base * (1 + 3 * 0.5)
        assert civ_low.tech_points == pytest.approx(expected_low)
        assert civ_high.tech_points == pytest.approx(expected_high)
        assert civ_high.tech_points > civ_low.tech_points

    def test_dead_civ_no_tech_growth(self) -> None:
        """验证死亡文明不获得科技点。"""
        civ = _make_civ(tech_points=10.0, is_alive=False)
        config = _default_config()
        apply_development([civ], config)
        assert civ.tech_points == 10.0


# ========================================================================
# R2.5 技术爆炸 — _tech_needed 函数
# ========================================================================


class TestTechNeeded:
    """_tech_needed 函数测试。"""

    def test_tech_needed_formula(self) -> None:
        """验证所需科技点公式：100.0 * level²。"""
        assert _tech_needed(1) == 100.0
        assert _tech_needed(2) == 400.0
        assert _tech_needed(3) == 900.0
        assert _tech_needed(4) == 1600.0
        assert _tech_needed(5) == 2500.0

    def test_tech_needed_increasing(self) -> None:
        """验证等级越高需求越大。"""
        assert _tech_needed(2) > _tech_needed(1)
        assert _tech_needed(3) > _tech_needed(2)
        assert _tech_needed(4) > _tech_needed(3)
        assert _tech_needed(5) > _tech_needed(4)


# ========================================================================
# R2.5 技术爆炸 — 触发条件
# ========================================================================


class TestTechExplosionTrigger:
    """技术爆炸触发条件测试。"""

    def test_explosion_triggers_when_tech_sufficient(self) -> None:
        """验证科技点达标时触发爆炸（等级提升）。"""
        civ = _make_civ(level=1, tech_points=100.0, tech_explosion_prob=1.0)
        config = _default_config()
        apply_development([civ], config)
        assert civ.level == 2

    def test_explosion_not_triggers_when_prob_zero(self) -> None:
        """验证概率为 0 时不触发爆炸。"""
        civ = _make_civ(level=1, tech_points=100.0, tech_explosion_prob=0.0)
        config = _default_config()
        apply_development([civ], config)
        assert civ.level == 1

    def test_explosion_not_triggers_when_tech_insufficient(self) -> None:
        """验证科技点不足时不触发爆炸。"""
        civ = _make_civ(level=2, tech_points=0.0, tech_explosion_prob=1.0)
        config = _default_config()
        apply_development([civ], config)
        assert civ.level == 2


# ========================================================================
# R2.5 技术爆炸 — 触发效果
# ========================================================================


class TestTechExplosionEffects:
    """技术爆炸效果测试（含随机倍数范围验证）。"""

    def test_level_increases(self) -> None:
        """验证技术爆炸时等级 +1。"""
        civ = _make_civ(level=2, tech_points=500.0, tech_explosion_prob=1.0)
        config = _default_config()
        apply_development([civ], config)
        assert civ.level == 3

    def test_tech_points_halved(self) -> None:
        """验证科技点减半（爆炸消耗）。"""
        civ = _make_civ(level=1, tech_points=200.0, tech_explosion_prob=1.0)
        config = _default_config()
        initial_tech = civ.tech_points
        apply_development([civ], config)
        # 爆炸前有科技点积累，爆炸后半值必然小于初始值
        assert civ.tech_points < initial_tech

    def test_tech_points_halved_exact_ratio(self) -> None:
        """验证 `_trigger_tech_explosion` 将科技点精确减半。"""
        civ = _make_civ(level=1, tech_points=500.0)
        _trigger_tech_explosion(civ, _default_config())
        assert civ.tech_points == 250.0

    def test_energy_output_multiplied(self) -> None:
        """验证能量输出乘以 2~5 倍。"""
        civ = _make_civ(level=1, tech_points=200.0, tech_explosion_prob=1.0)
        config = _default_config()
        initial_energy = civ.energy_output
        apply_development([civ], config)
        assert initial_energy * 2.0 <= civ.energy_output <= initial_energy * 5.0

    def test_detection_range_multiplied(self) -> None:
        """验证探测范围乘以 1.5~3 倍。"""
        civ = _make_civ(level=1, tech_points=200.0, tech_explosion_prob=1.0)
        config = _default_config()
        initial_range = civ.detection_range
        apply_development([civ], config)
        assert initial_range * 1.5 <= civ.detection_range <= initial_range * 3.0

    def test_expansion_radius_multiplied(self) -> None:
        """验证扩张半径乘以 2~4 倍。"""
        civ = _make_civ(level=1, tech_points=200.0, tech_explosion_prob=1.0)
        config = _default_config()
        initial_radius = civ.expansion_radius
        apply_development([civ], config)
        assert initial_radius * 2.0 <= civ.expansion_radius <= initial_radius * 4.0

    def test_population_multiplied(self) -> None:
        """验证人口乘以 1.5~3 倍。"""
        civ = _make_civ(level=1, tech_points=200.0, tech_explosion_prob=1.0)
        config = _default_config()
        initial_pop = civ.population
        apply_development([civ], config)
        assert initial_pop * 1.5 <= civ.population <= initial_pop * 3.0

    def test_explosion_prob_halved(self) -> None:
        """验证技术爆炸概率减半。"""
        civ = _make_civ(level=1, tech_points=200.0, tech_explosion_prob=0.8)
        _trigger_tech_explosion(civ, _default_config())
        assert civ.tech_explosion_prob == pytest.approx(0.4)

    def test_explosion_skips_regular_growth(self) -> None:
        """验证爆炸后跳过常规人口/能量增长步骤（属性由爆炸倍数决定）。"""
        civ = _make_civ(
            level=1,
            tech_points=200.0,
            tech_explosion_prob=1.0,
            population=1e8,
            energy_output=1e15,
        )
        config = _default_config()
        apply_development([civ], config)
        # 爆炸后 population 在 1.5~3 倍范围（而非常规增长的小幅变化）
        initial_pop = 1e8
        assert civ.population >= initial_pop * 1.5
        assert civ.population <= initial_pop * 3.0


# ========================================================================
# R2.5 技术爆炸 — 等级上限（max 5）
# ========================================================================


class TestTechExplosionLevelCap:
    """技术爆炸等级上限测试。"""

    def test_level_capped_at_5(self) -> None:
        """验证等级 5 时触发爆炸不会超过上限。"""
        civ = _make_civ(
            level=5,
            tech_points=1e10,
            tech_explosion_prob=1.0,
        )
        config = _default_config()
        apply_development([civ], config)
        assert civ.level == 5

    def test_explosion_effects_still_apply_at_cap(self) -> None:
        """验证等级已达上限时爆炸效果（科技点减半等）仍然生效。"""
        civ = _make_civ(
            level=5,
            tech_points=10000.0,
            tech_explosion_prob=1.0,
        )
        config = _default_config()
        initial_tech = civ.tech_points
        apply_development([civ], config)
        assert civ.level == 5
        assert civ.tech_points < initial_tech  # 科技点仍减半
        assert civ.tech_explosion_prob == pytest.approx(0.5)  # 概率仍减半


# ========================================================================
# R2.3 人口增长（逻辑斯蒂增长模型）
# ========================================================================


class TestPopulationGrowth:
    """人口逻辑斯蒂增长测试。"""

    def test_population_increases(self) -> None:
        """验证人口正常增长。"""
        civ = _make_civ(
            tech_points=0.0,
            tech_explosion_prob=0.0,
            population=1e8,
            energy_output=1e15,
            level=1,
        )
        config = _default_config()
        initial_pop = civ.population
        apply_development([civ], config)
        assert civ.population > initial_pop

    def test_population_approaches_carrying_capacity(self) -> None:
        """验证人口接近承载上限时增长率趋缓、不超限。"""
        civ = _make_civ(
            tech_points=0.0,
            tech_explosion_prob=0.0,
            population=1e8,
            energy_output=1e15,
            level=1,
        )
        config = _default_config()

        for _ in range(100):
            apply_development([civ], config)

        carrying = _calc_carrying_capacity(civ)
        # 逻辑斯蒂增长保证人口不超过承载上限
        assert civ.population < carrying * 1.001

    def test_population_decreases_when_over_capacity(self) -> None:
        """验证人口超过承载上限时呈负增长（逻辑斯蒂模型核心特性）。"""
        civ = _make_civ(
            tech_points=0.0,
            tech_explosion_prob=0.0,
            population=2e12,  # 超过 carrying = 1e6 * 1 * 1e6 = 1e12
            energy_output=1e6,
            level=1,
        )
        config = _default_config()
        initial_pop = civ.population
        apply_development([civ], config)
        # 超过承载上限 → 负增长（(1 - p/K) < 0）
        assert civ.population < initial_pop


class TestCarryingCapacity:
    """承载上限计算测试。"""

    def test_carrying_capacity_formula(self) -> None:
        """验证承载上限 = energy_output * level * 1e6。"""
        civ = _make_civ(energy_output=2e15, level=3)
        carrying = _calc_carrying_capacity(civ)
        assert carrying == 2e15 * 3 * 1e6

    def test_carrying_capacity_scales_with_level(self) -> None:
        """验证等级越高承载上限越大。"""
        civ_low = _make_civ(energy_output=1e15, level=1)
        civ_high = _make_civ(energy_output=1e15, level=5)
        assert _calc_carrying_capacity(civ_high) > _calc_carrying_capacity(civ_low)

    def test_carrying_capacity_scales_with_energy(self) -> None:
        """验证能量输出越高承载上限越大。"""
        civ_low = _make_civ(energy_output=1e12, level=2)
        civ_high = _make_civ(energy_output=1e18, level=2)
        assert _calc_carrying_capacity(civ_high) > _calc_carrying_capacity(civ_low)


# ========================================================================
# R2.4 能量输出增长
# ========================================================================


class TestEnergyGrowth:
    """能量输出增长测试。"""

    def test_energy_increases(self) -> None:
        """验证能量输出正常增长。"""
        civ = _make_civ(
            tech_points=100.0,
            tech_explosion_prob=0.0,
            energy_output=1e15,
        )
        config = _default_config()
        initial_energy = civ.energy_output
        apply_development([civ], config)
        assert civ.energy_output > initial_energy

    def test_energy_growth_scales_with_tech(self) -> None:
        """验证能量增长率与科技点正相关。"""
        config = _default_config()
        civ_low = _make_civ(
            tech_points=0.0,
            tech_explosion_prob=0.0,
            energy_output=1e15,
        )
        civ_high = _make_civ(
            tech_points=1e8,
            tech_explosion_prob=0.0,
            energy_output=1e15,
        )

        apply_development([civ_low, civ_high], config)
        # 科技点高的文明能量增长更快
        assert civ_high.energy_output > civ_low.energy_output

    def test_energy_growth_formula(self) -> None:
        """验证能量增长率的计算公式。"""
        civ = _make_civ(
            tech_points=500000.0,  # tech_points * 1e-6 = 0.5
            tech_explosion_prob=0.0,
            energy_output=1e15,
        )
        config = _default_config()
        # energy_growth = 0.005 * (1 + 500000 * 1e-6) = 0.005 * 1.5 = 0.0075
        # energy_output = 1e15 * (1 + 0.0075) = 1.0075e15
        apply_development([civ], config)
        expected = 1e15 * (1 + config.energy_growth_rate * (1 + 500000.0 * 1e-6))
        assert civ.energy_output == pytest.approx(expected)


# ========================================================================
# 主流程集成
# ========================================================================


class TestApplyDevelopment:
    """apply_development 主流程集成测试。"""

    def test_alive_civ_processed(self) -> None:
        """验证存活文明被正常处理。"""
        civ = _make_civ(
            tech_points=0.0,
            tech_explosion_prob=0.0,
            population=1e8,
            energy_output=1e15,
        )
        config = _default_config()
        apply_development([civ], config)
        assert civ.tech_points > 0.0
        assert civ.population > 1e8
        assert civ.energy_output > 1e15

    def test_dead_civ_skipped(self) -> None:
        """验证死亡文明所有发展步骤都被跳过。"""
        civ = _make_civ(
            is_alive=False,
            tech_points=10.0,
            population=1e8,
            energy_output=1e15,
        )
        config = _default_config()
        apply_development([civ], config)
        assert civ.tech_points == 10.0
        assert civ.population == 1e8
        assert civ.energy_output == 1e15

    def test_mixed_alive_and_dead(self) -> None:
        """验证存活与死亡文明混合列表的正确处理。"""
        alive = _make_civ(
            id=1,
            tech_points=0.0,
            tech_explosion_prob=0.0,
            population=1e8,
            energy_output=1e15,
        )
        dead = _make_civ(
            id=2,
            is_alive=False,
            tech_points=50.0,
            population=1e8,
            energy_output=1e15,
        )
        config = _default_config()
        apply_development([alive, dead], config)
        assert alive.tech_points > 0.0
        assert dead.tech_points == 50.0  # 未变化

    def test_empty_list(self) -> None:
        """验证空列表不会报错。"""
        config = _default_config()
        apply_development([], config)  # 不应抛出异常


# ========================================================================
# _trigger_tech_explosion 直接测试
# ========================================================================


class TestTriggerTechExplosionDirect:
    """直接调用 _trigger_tech_explosion 的精确效果测试。"""

    def test_level_does_not_exceed_5(self) -> None:
        """验证 _trigger_tech_explosion 不会将等级提升至 5 以上。"""
        civ = _make_civ(level=5, tech_explosion_prob=0.5)
        _trigger_tech_explosion(civ, _default_config())
        assert civ.level == 5

    def test_all_fields_modified(self) -> None:
        """验证所有相关字段都得到修改。"""
        civ = _make_civ(
            level=1,
            tech_points=100.0,
            tech_explosion_prob=0.5,
            energy_output=1e15,
            detection_range=250.0,
            expansion_radius=50.0,
            population=1e8,
        )
        _trigger_tech_explosion(civ, _default_config())
        assert civ.level == 2
        assert civ.tech_points == 50.0  # 精确减半
        assert civ.tech_explosion_prob == 0.25  # 精确减半
        # 随机倍数在预期范围内
        assert 2e15 <= civ.energy_output <= 5e15
        assert 375.0 <= civ.detection_range <= 750.0
        assert 100.0 <= civ.expansion_radius <= 200.0
        assert 1.5e8 <= civ.population <= 3.0e8
