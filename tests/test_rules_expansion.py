"""扩张模块测试 —— apply_expansion() 函数。

测试覆盖：
- 扩张半径增长（不同等级、能量输出）
- 半径上限（universe_size * 0.1）
- 位置漂移（方向随机性、距离公式）
- 环形宇宙坐标包裹
- 暴露概率逻辑（边界值：必然暴露、绝不暴露、中间值）
- communication_active 在暴露后被设置
- 死亡文明被跳过
"""

import math
import random

from src.config import SimulationConfig
from src.entity import Civilization
from src.rules.expansion import apply_expansion


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
        "x": 5000.0,
        "y": 5000.0,
        "level": 1,
        "energy_output": 1e12,
        "expansion_radius": 10.0,
        "stealth": 0.5,
        "aggressiveness": 0.5,
        "communication_active": False,
        "is_alive": True,
    }
    params = {**defaults, **overrides}
    civ = Civilization(**params)  # type: ignore[arg-type]
    return civ


# =============================================================================
# 扩张半径增长测试
# =============================================================================


def test_expansion_radius_grows() -> None:
    """验证扩张半径增长。"""
    config = _make_config(expansion_rate_base=1.0, universe_size=10000.0)
    civ = _make_civ(level=1, energy_output=1e12, expansion_radius=10.0)
    initial_radius = civ.expansion_radius

    apply_expansion([civ], config)

    # 半径应增长（增长量为正）
    assert civ.expansion_radius > initial_radius, (
        f"预期半径增长，实际从 {initial_radius} 到 {civ.expansion_radius}"
    )


def test_expansion_radius_higher_level_grows_faster() -> None:
    """验证高等级文明扩张更快。

    等级 3 的文明每步增长应是等级 1 的约 3 倍。
    但增长受能量因子影响，只能验证相对大小，不是精确倍数。
    """
    config = _make_config(expansion_rate_base=1.0, universe_size=10000.0)
    civ_low = _make_civ(id=1, level=1, energy_output=1e12, expansion_radius=10.0)
    civ_high = _make_civ(id=2, level=3, energy_output=1e12, expansion_radius=10.0)

    apply_expansion([civ_low, civ_high], config)

    growth_low = civ_low.expansion_radius - 10.0
    growth_high = civ_high.expansion_radius - 10.0

    # 等级 3 的增长应显著大于等级 1
    assert growth_high > growth_low, (
        f"预期高等级增长更快: low={growth_low:.4f}, high={growth_high:.4f}"
    )
    # 近似等级倍数关系（允许 ±20% 偏差，因为两者 energy_factor 相同）
    ratio = growth_high / growth_low if growth_low > 0 else 0
    assert 2.0 <= ratio <= 4.0, (
        f"预期高/低等级增长比 ~3 倍，实际 {ratio:.2f}"
    )


def test_expansion_radius_energy_factor() -> None:
    """验证能量因子公式：energy_factor = log10(energy_output) / 18.0。

    能量输出越大，因子越大（对数增长）。
    能量输出 1e12 → log10(1e12)/18 = 12/18 ≈ 0.667
    能量输出 1e18 → log10(1e18)/18 = 18/18 = 1.0
    """
    config = _make_config(expansion_rate_base=1.0, universe_size=10000.0)

    # 能量输出 1e6 → 因子 ≈ 6/18 = 0.333
    civ_low_energy = _make_civ(
        id=1, level=1, energy_output=1e6, expansion_radius=10.0
    )
    # 能量输出 1e18 → 因子 ≈ 18/18 = 1.0
    civ_high_energy = _make_civ(
        id=2, level=1, energy_output=1e18, expansion_radius=10.0
    )

    apply_expansion([civ_low_energy, civ_high_energy], config)

    growth_low = civ_low_energy.expansion_radius - 10.0
    growth_high = civ_high_energy.expansion_radius - 10.0

    assert growth_high > growth_low, (
        f"预期高能量扩张更快: low={growth_low:.4f}, high={growth_high:.4f}"
    )


# =============================================================================
# 半径上限测试
# =============================================================================


def test_expansion_radius_capped_at_universe_size_10_percent() -> None:
    """验证扩张半径上限为 universe_size * 0.1。"""
    universe_size = 1000.0
    max_allowed = universe_size * 0.1  # 100.0
    config = _make_config(
        expansion_rate_base=1000.0,  # 高增长率，快速达到上限
        universe_size=universe_size,
    )
    # 给一个非常大的初始半径
    civ = _make_civ(level=5, energy_output=1e18, expansion_radius=90.0)

    apply_expansion([civ], config)

    assert civ.expansion_radius <= max_allowed, (
        f"半径 {civ.expansion_radius} 超过上限 {max_allowed}"
    )


def test_expansion_radius_capped_exactly() -> None:
    """验证半径被精确限制在 max_radius。"""
    universe_size = 500.0
    max_allowed = universe_size * 0.1  # 50.0
    config = _make_config(
        expansion_rate_base=1e6,  # 极快增长
        universe_size=universe_size,
    )
    civ = _make_civ(level=5, energy_output=1e18, expansion_radius=0.0)

    apply_expansion([civ], config)

    assert abs(civ.expansion_radius - max_allowed) < 1e-9, (
        f"半径应为 {max_allowed}，实际 {civ.expansion_radius}"
    )


def test_expansion_radius_does_not_shrink() -> None:
    """验证扩张半径不会因上限而缩小。

    如果半径已经超过上限，它不应被缩小，仅保持上限。
    """
    universe_size = 1000.0
    max_allowed = universe_size * 0.1  # 100.0
    config = _make_config(universe_size=universe_size)
    civ = _make_civ(expansion_radius=200.0)  # 已经超过上限

    apply_expansion([civ], config)

    # 半径不应缩小低于上限
    assert civ.expansion_radius >= max_allowed, (
        f"半径不应缩小: {civ.expansion_radius} < {max_allowed}"
    )


# =============================================================================
# 位置漂移测试
# =============================================================================


def test_position_changes_after_expansion() -> None:
    """验证文明位置在扩张后发生变化。"""
    config = _make_config(universe_size=10000.0)
    civ = _make_civ(level=1, expansion_radius=10.0, energy_output=1e12)
    original_x, original_y = civ.x, civ.y

    apply_expansion([civ], config)

    # 位置应至少有一个坐标发生变化
    assert (civ.x != original_x) or (civ.y != original_y), (
        "扩张后位置应发生变化"
    )


def test_position_drift_distance_formula() -> None:
    """验证漂移距离公式：drift = expansion_radius * 0.1 * random(0.5, 1.0)。

    使用固定 seed 验证漂移距离在预期范围内。
    """
    random.seed(42)
    config = _make_config(universe_size=10000.0)
    civ = _make_civ(level=1, expansion_radius=100.0, energy_output=1e12)
    original_x, original_y = civ.x, civ.y

    apply_expansion([civ], config)

    dx = civ.x - original_x
    dy = civ.y - original_y
    distance = math.sqrt(dx * dx + dy * dy)

    # 半径 100.0 → drift_base = 10.0 → 最终距离在 [5.0, 10.0] 范围内
    # （允许因 seed 角度不同导致的偏差，但总距离应在 5~10 内）
    assert 4.0 <= distance <= 11.0, (
        f"漂移距离 {distance:.4f} 不在预期范围 [5.0, 10.0] 附近"
    )


def test_position_drift_multiple_directions() -> None:
    """验证多次漂移产生不同方向。"""
    config = _make_config(universe_size=10000.0)

    # 不固定 seed，运行多次，验证至少产生过不同的坐标变化
    positions: set[tuple[float, float]] = set()
    for i in range(20):
        c = _make_civ(
            id=i,
            expansion_radius=50.0,
            energy_output=1e12,
            x=5000.0,
            y=5000.0,
        )
        apply_expansion([c], config)
        positions.add((round(c.x, 4), round(c.y, 4)))

    # 至少应有 2 种不同的漂移结果
    assert len(positions) >= 2, (
        f"预期多种漂移方向，实际只有 {len(positions)} 种"
    )


# =============================================================================
# 环形宇宙坐标包裹测试
# =============================================================================


def test_coordinates_wrap_around_x_positive() -> None:
    """验证 X 坐标正向溢出时被模运算包裹。"""
    config = _make_config(universe_size=100.0)
    # 靠近右边界，漂移应包裹到左侧
    civ = _make_civ(x=98.0, y=50.0, expansion_radius=50.0, level=1, energy_output=1e12)

    apply_expansion([civ], config)

    assert 0.0 <= civ.x < 100.0, (
        f"X 坐标 {civ.x} 不在 [0, 100) 范围内"
    )


def test_coordinates_wrap_around_x_negative() -> None:
    """验证 X 坐标负向溢出时被模运算包裹。"""
    config = _make_config(universe_size=100.0)
    # 给一个会向左漂移的情况（cos(pi) = -1）
    # 用固定 seed 控制角度
    random.seed(42)
    civ = _make_civ(x=2.0, y=50.0, expansion_radius=50.0, level=1, energy_output=1e12)

    apply_expansion([civ], config)

    assert 0.0 <= civ.x < 100.0, (
        f"X 坐标 {civ.x} 不在 [0, 100) 范围内"
    )


def test_coordinates_wrap_around_y_both_sides() -> None:
    """验证 Y 坐标在正负两个方向溢出时都被包裹。"""
    config = _make_config(universe_size=100.0)

    # 靠近上边界
    civ_top = _make_civ(
        id=1, x=50.0, y=98.0, expansion_radius=50.0, level=1, energy_output=1e12
    )
    # 靠近下边界（y 接近 0）
    civ_bottom = _make_civ(
        id=2, x=50.0, y=2.0, expansion_radius=50.0, level=1, energy_output=1e12
    )

    apply_expansion([civ_top, civ_bottom], config)

    assert 0.0 <= civ_top.y < 100.0, (
        f"Y 坐标 {civ_top.y} 不在 [0, 100) 范围内"
    )
    assert 0.0 <= civ_bottom.y < 100.0, (
        f"Y 坐标 {civ_bottom.y} 不在 [0, 100) 范围内"
    )


# =============================================================================
# 暴露概率测试
# =============================================================================


def test_exposure_always_happens_with_low_stealth_large_radius() -> None:
    """验证低隐蔽性大半径文明必然暴露。

    暴露概率 = 0.01 + (expansion_radius / 5.0) + 0 - (stealth * 0.3)
    当 stealth=0, radius=500: prob = 0.01 + 100 + 0 - 0 = 100.01 → clamped to 1.0
    """
    config = _make_config(
        base_exposure_prob=0.01,
        exposure_threshold=5.0,
        universe_size=100000.0,  # 不限制半径
    )
    civ = _make_civ(
        expansion_radius=500.0,  # 极大 → prob >> 1
        stealth=0.0,
        communication_active=False,
    )

    # 必然暴露，1 次就够
    apply_expansion([civ], config)

    assert civ.communication_active is True, (
        "低隐蔽性大半径文明应必然暴露"
    )


def test_exposure_never_happens_with_high_stealth_small_radius() -> None:
    """验证高隐蔽性小半径文明必然不暴露。

    暴露概率 = 0.01 + (0.01 / 5.0) + 0 - (0.9 * 0.3)
             = 0.01 + 0.002 + 0 - 0.27 = -0.258 → clamped to 0.0
    """
    config = _make_config(
        base_exposure_prob=0.01,
        exposure_threshold=5.0,
        universe_size=10000.0,
    )

    # 运行多次确保确实从不暴露
    for _ in range(100):
        c = _make_civ(
            id=1,
            expansion_radius=0.01,
            stealth=0.9,
            communication_active=False,
        )
        apply_expansion([c], config)
        assert c.communication_active is False, (
            "高隐蔽性小半径文明不应暴露"
        )


def test_exposure_probability_increases_with_radius() -> None:
    """验证扩张半径越大，暴露概率越高。

    在大半径多次运行中，暴露比例应显著高于小半径。
    """
    config = _make_config(
        base_exposure_prob=0.0,
        exposure_threshold=5.0,
        universe_size=10000.0,
    )

    # 小半径：prob = 0 + (1/5) + 0 - (0.5*0.3) = 0.2 - 0.15 = 0.05
    # 大半径：prob = 0 + (50/5) + 0 - (0.5*0.3) = 10 - 0.15 = 9.85 → 1.0
    small_radius_exposed = 0
    large_radius_exposed = 0
    n_trials = 200

    for _ in range(n_trials):
        c_small = _make_civ(
            id=1, expansion_radius=1.0, stealth=0.5, communication_active=False
        )
        c_large = _make_civ(
            id=2, expansion_radius=50.0, stealth=0.5, communication_active=False
        )
        apply_expansion([c_small, c_large], config)
        if c_small.communication_active:
            small_radius_exposed += 1
        if c_large.communication_active:
            large_radius_exposed += 1

    assert large_radius_exposed > small_radius_exposed, (
        f"大半径暴露次数 {large_radius_exposed} 应大于小半径 {small_radius_exposed}"
    )
    # 大半径应几乎必然暴露（prob ≈ 1.0）
    assert large_radius_exposed == n_trials, (
        f"大半径应全部暴露，实际 {large_radius_exposed}/{n_trials}"
    )


def test_communication_increases_exposure_probability() -> None:
    """验证通信中会增加暴露概率（+0.2）。"""
    config = _make_config(
        base_exposure_prob=0.0,
        exposure_threshold=1000.0,  # 大阈值使半径因子可忽略
        universe_size=10000.0,
    )

    # 不通信：prob = 0 + (10/1000) + 0 - (0.5*0.3) = 0.01 + 0 - 0.15 = -0.14 → 0
    # 通信中：prob = 0 + (10/1000) + 0.2 - (0.5*0.3) = 0.01 + 0.2 - 0.15 = 0.06
    silent_exposed = 0
    communicating_exposed = 0
    n_trials = 500

    for _ in range(n_trials):
        c_silent = _make_civ(
            id=1,
            expansion_radius=10.0,
            stealth=0.5,
            communication_active=False,
        )
        c_comm = _make_civ(
            id=2,
            expansion_radius=10.0,
            stealth=0.5,
            communication_active=True,
        )
        apply_expansion([c_silent, c_comm], config)
        if c_silent.communication_active:
            silent_exposed += 1
        if c_comm.communication_active:
            communicating_exposed += 1

    # 通信中的文明暴露次数应更多
    assert communicating_exposed > silent_exposed, (
        f"通信中暴露次数 {communicating_exposed} 应大于不通信 {silent_exposed}"
    )


def test_exposure_probability_clamped() -> None:
    """验证暴露概率被正确钳制到 [0, 1] 范围。

    使用极端值确保 clamp 生效：
    - 极小 stealth + 极大 radius → prob > 1 → 仍应暴露
    - 极大 stealth + 极小 radius → prob < 0 → 仍不应暴露
    """
    config = _make_config(
        base_exposure_prob=0.01,
        exposure_threshold=5.0,
        universe_size=100000.0,
    )

    # 必然暴露配置（prob >> 1）
    civ_always = _make_civ(
        id=1,
        expansion_radius=1000.0,
        stealth=0.0,
        communication_active=False,
    )

    # 绝不暴露配置（prob << 0）
    civ_never = _make_civ(
        id=2,
        expansion_radius=0.001,
        stealth=1.0,
        communication_active=False,
    )

    apply_expansion([civ_always, civ_never], config)

    assert civ_always.communication_active is True, "极端大半径应暴露"
    assert civ_never.communication_active is False, "极端小半径极隐蔽不应暴露"


# =============================================================================
# 死亡文明跳过测试
# =============================================================================


def test_dead_civilizations_are_skipped() -> None:
    """验证死亡文明被跳过（半径不增长、位置不漂移、不暴露）。"""
    config = _make_config(universe_size=10000.0)
    civ = _make_civ(
        id=1,
        is_alive=False,
        expansion_radius=10.0,
        energy_output=1e12,
    )

    apply_expansion([civ], config)

    # 死亡文明的所有属性不应变化
    assert civ.expansion_radius == 10.0
    assert civ.x == 5000.0
    assert civ.y == 5000.0
    assert civ.communication_active is False


def test_mixed_alive_and_dead() -> None:
    """验证存活与死亡文明混合时，存活文明正常处理。"""
    config = _make_config(universe_size=10000.0)
    alive = _make_civ(id=1, is_alive=True, expansion_radius=10.0, energy_output=1e12)
    dead = _make_civ(id=2, is_alive=False, expansion_radius=10.0, energy_output=1e12)

    apply_expansion([alive, dead], config)

    # 存活文明应增长
    assert alive.expansion_radius > 10.0
    # 死亡文明不应变化
    assert dead.expansion_radius == 10.0


# =============================================================================
# 综合测试：暴露后 communication_active 被设置
# =============================================================================


def test_exposure_sets_communication_active() -> None:
    """验证暴露判定为 True 时，communication_active 被设置为 True。"""
    config = _make_config(
        base_exposure_prob=1.0,  # 100% 暴露概率
        exposure_threshold=1.0,
        universe_size=10000.0,
    )
    civ = _make_civ(
        expansion_radius=1.0,
        stealth=0.0,
        communication_active=False,
    )

    apply_expansion([civ], config)

    assert civ.communication_active is True, "暴露后 communication_active 应为 True"


def test_communication_active_persistent() -> None:
    """验证 communication_active 一旦被设置不会自动消失。"""
    config = _make_config(
        base_exposure_prob=0.0,
        exposure_threshold=1000.0,
        universe_size=10000.0,
    )
    # 已经通信中的文明
    civ = _make_civ(
        expansion_radius=10.0,
        stealth=0.9,  # 高隐蔽性，不会触发新暴露
        communication_active=True,
    )

    apply_expansion([civ], config)

    # communication_active 应保持 True
    assert civ.communication_active is True
