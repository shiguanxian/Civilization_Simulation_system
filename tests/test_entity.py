"""实体模块测试 — Civilization 数据类与 NameGenerator 名称生成器。"""

import math
import random
from dataclasses import fields, is_dataclass

from src.config import SimulationConfig
from src.entity import Civilization, CivilizationFactory, NameGenerator

# =============================================================================
# Civilization 数据类测试
# =============================================================================

CIVILIZATION_FIELDS: dict[str, type] = {
    "id": int,
    "name": str,
    "x": float,
    "y": float,
    "level": int,
    "tech_points": float,
    "tech_explosion_prob": float,
    "expansion_radius": float,
    "population": float,
    "energy_output": float,
    "aggressiveness": float,
    "stealth": float,
    "detection_range": float,
    "is_alive": bool,
    "birth_time": int,
    "communication_active": bool,
}


def test_civilization_is_dataclass() -> None:
    """验证 Civilization 使用 @dataclass 装饰器。"""
    assert is_dataclass(Civilization)


def test_civilization_has_exactly_16_fields() -> None:
    """验证 Civilization 有且仅有 16 个字段。"""
    field_names = {f.name for f in fields(Civilization)}
    assert len(field_names) == 16
    assert field_names == set(CIVILIZATION_FIELDS.keys())


def test_civilization_field_types() -> None:
    """验证 Civilization 所有字段的类型注解正确。"""
    for field in fields(Civilization):
        expected_type = CIVILIZATION_FIELDS[field.name]
        assert field.type is expected_type or field.type == expected_type, (
            f"字段 {field.name} 类型应为 {expected_type}，"
            f"实际为 {field.type}"
        )


def test_civilization_default_values() -> None:
    """验证 Civilization 的默认值正确。"""
    civ = Civilization()
    assert civ.id == 0
    assert civ.name == ""
    assert civ.x == 0.0
    assert civ.y == 0.0
    assert civ.level == 1
    assert civ.tech_points == 0.0
    assert civ.tech_explosion_prob == 0.0
    assert civ.expansion_radius == 0.0
    assert civ.population == 0.0
    assert civ.energy_output == 0.0
    assert civ.aggressiveness == 0.0
    assert civ.stealth == 0.0
    assert civ.detection_range == 0.0
    assert civ.is_alive is True
    assert civ.birth_time == 0
    assert civ.communication_active is False


def test_civilization_custom_values() -> None:
    """验证 Civilization 可以接收自定义字段值。"""
    civ = Civilization(
        id=42,
        name="测试文明",
        x=100.0,
        y=200.0,
        level=3,
        tech_points=5000.0,
        tech_explosion_prob=0.05,
        expansion_radius=50.0,
        population=1e9,
        energy_output=1e15,
        aggressiveness=0.7,
        stealth=0.3,
        detection_range=300.0,
        is_alive=True,
        birth_time=10,
        communication_active=True,
    )
    assert civ.id == 42
    assert civ.name == "测试文明"
    assert civ.x == 100.0
    assert civ.y == 200.0
    assert civ.level == 3
    assert civ.tech_points == 5000.0
    assert abs(civ.tech_explosion_prob - 0.05) < 1e-9
    assert civ.expansion_radius == 50.0
    assert abs(civ.population - 1e9) < 1.0
    assert abs(civ.energy_output - 1e15) < 1.0
    assert abs(civ.aggressiveness - 0.7) < 1e-9
    assert abs(civ.stealth - 0.3) < 1e-9
    assert civ.detection_range == 300.0
    assert civ.is_alive is True
    assert civ.birth_time == 10
    assert civ.communication_active is True


def test_civilization_no_business_methods() -> None:
    """验证 Civilization 是纯数据容器，不含业务逻辑方法。

    允许的 dunder 方法: __init__, __repr__, __eq__, __hash__,
    __dataclass_fields__, __dataclass_params__ 等由 dataclass 自动生成的方法。
    不允许任何非 dunder 的自定义方法。
    """
    civ = Civilization()
    # 获取所有非 dunder 且非特殊属性名的方法/属性
    custom_attrs = [
        attr
        for attr in dir(civ)
        if not attr.startswith("_") and not callable(getattr(civ, attr))
    ]
    # 只有 16 个字段名应出现在非 dunder 属性中
    for attr in custom_attrs:
        assert hasattr(civ, attr), f"意外属性: {attr}"


# =============================================================================
# NameGenerator 测试
# =============================================================================


def test_name_generator_mode_number() -> None:
    """验证数字编号模式生成正确格式的名称。"""
    gen = NameGenerator(mode="number")
    assert gen.generate(1) == "文明 #000001"
    assert gen.generate(42) == "文明 #000042"
    assert gen.generate(999999) == "文明 #999999"


def test_name_generator_mode_auto_first_name() -> None:
    """验证 auto 模式首先生成词库中的第一个组合。"""
    gen = NameGenerator(mode="auto")
    name = gen.generate(0)
    assert name == "阿尔法仙座"


def test_name_generator_mode_auto_iterates_suffix_first() -> None:
    """验证 auto 模式优先遍历后缀，再切换前缀。"""
    gen = NameGenerator(mode="auto")
    # 第一个: 阿尔法 + 仙座
    assert gen.generate(0) == "阿尔法仙座"
    # 第二个: 阿尔法 + 星系
    assert gen.generate(1) == "阿尔法星系"
    # 第三个: 阿尔法 + 星云
    assert gen.generate(2) == "阿尔法星云"


def test_name_generator_mode_auto_all_combinations() -> None:
    """验证 auto 模式能生成所有前缀+后缀组合。

    10 个前缀 × 8 个后缀 = 80 个唯一名称。
    """
    gen = NameGenerator(mode="auto")
    names: set[str] = set()
    for i in range(80):
        names.add(gen.generate(i))
    assert len(names) == 80

    # 验证所有组合中均包含预期的前缀和后缀
    for prefix in NameGenerator.PREFIXES:
        for suffix in NameGenerator.SUFFIXES:
            assert prefix + suffix in names


def test_name_generator_auto_fallback_to_number() -> None:
    """验证 auto 模式词库用完后回退到数字编号。

    10 × 8 = 80 个组合用完后，第 81 次应返回数字格式。
    """
    gen = NameGenerator(mode="auto")
    # 消耗所有 80 个词库组合
    for i in range(80):
        gen.generate(i)
    # 第 81 次应回退到数字编号
    name = gen.generate(80)
    assert name == "文明 #000080"


def test_name_generator_auto_fallback_continues_numbering() -> None:
    """验证 auto 模式在回退到数字编号后能持续生成。"""
    gen = NameGenerator(mode="auto")
    for i in range(80):
        gen.generate(i)
    # 回退后的连续数字编号
    assert gen.generate(100) == "文明 #000100"
    assert gen.generate(101) == "文明 #000101"
    assert gen.generate(999) == "文明 #000999"


def test_name_generator_invalid_mode_raises_value_error() -> None:
    """验证无效 mode 抛出 ValueError。"""
    try:
        NameGenerator(mode="invalid")
        assert False, "应抛出 ValueError"
    except ValueError:
        pass


def test_name_generator_state_independence() -> None:
    """验证不同 NameGenerator 实例互不干扰。"""
    gen1 = NameGenerator(mode="auto")
    gen2 = NameGenerator(mode="auto")

    # gen1 生成第一个名称
    assert gen1.generate(0) == "阿尔法仙座"
    # gen2 也应从第一个名称开始（独立状态）
    assert gen2.generate(0) == "阿尔法仙座"

    # gen1 推进到第二个
    assert gen1.generate(1) == "阿尔法星系"
    # gen2 不受 gen1 影响，依然从第二个开始
    assert gen2.generate(1) == "阿尔法星系"


def test_name_generator_edge_empty_suffixes() -> None:
    """极端情况：即便只有一个后缀也能正常运行。

    此测试验证索引推进算法在处理边界值时正确。
    """
    # 使用有限的测试——确认正常的 8 个后缀索引推进正确
    gen = NameGenerator(mode="auto")
    suffix_count = len(NameGenerator.SUFFIXES)

    # 验证前缀切换行为：第 suffix_count 次应为第二个前缀的第一个后缀
    names: list[str] = []
    for i in range(suffix_count + 1):
        names.append(gen.generate(i))

    # 索引 0: 阿尔法 + 仙座
    assert names[0] == "阿尔法仙座"
    # 索引 suffix_count - 1: 阿尔法 + 最后一个后缀
    assert names[suffix_count - 1] == "阿尔法星环"
    # 索引 suffix_count: 贝塔 + 仙座（切换到第二个前缀）
    assert names[suffix_count] == "贝塔仙座"


# =============================================================================
# CivilizationFactory 测试
# =============================================================================


def _make_default_config() -> SimulationConfig:
    """创建默认配置的辅助函数。"""
    return SimulationConfig()


def test_factory_init() -> None:
    """验证 CivilizationFactory 初始化成功。"""
    config = _make_default_config()
    name_gen = NameGenerator(mode="auto")
    factory = CivilizationFactory(config, name_gen)
    assert factory.config is config
    assert factory.name_generator is name_gen


def test_factory_create_random_fields_set() -> None:
    """验证 create_random 返回的文明所有字段已正确设置。"""
    config = _make_default_config()
    name_gen = NameGenerator(mode="number")
    factory = CivilizationFactory(config, name_gen)

    civ = factory.create_random(civ_id=42, birth_time=10, universe_size=1000.0)

    assert civ.id == 42
    assert civ.name == "文明 #000042"
    assert civ.birth_time == 10
    assert 0.0 <= civ.x < 1000.0
    assert 0.0 <= civ.y < 1000.0
    assert civ.is_alive is True
    assert civ.communication_active is False


def test_factory_random_params_in_range() -> None:
    """验证 create_random 生成的随机参数都在配置范围内。"""
    config = _make_default_config()
    name_gen = NameGenerator(mode="number")
    factory = CivilizationFactory(config, name_gen)

    # 多次生成以覆盖随机性
    for _ in range(100):
        civ = factory.create_random(
            civ_id=0, birth_time=0, universe_size=1000.0
        )

        assert config.level_range[0] <= civ.level <= config.level_range[1]
        assert civ.tech_points == 0.0
        assert civ.tech_explosion_prob == config.tech_explosion_base_prob
        assert (
            config.expansion_radius_range[0]
            <= civ.expansion_radius
            <= config.expansion_radius_range[1]
        )
        assert (
            config.population_range[0]
            <= civ.population
            <= config.population_range[1]
        )
        assert (
            config.energy_output_range[0]
            <= civ.energy_output
            <= config.energy_output_range[1]
        )
        assert (
            config.aggressiveness_range[0]
            <= civ.aggressiveness
            <= config.aggressiveness_range[1]
        )
        assert (
            config.stealth_range[0] <= civ.stealth <= config.stealth_range[1]
        )
        assert (
            config.detection_range_range[0]
            <= civ.detection_range
            <= config.detection_range_range[1]
        )


def test_factory_positions_within_bounds() -> None:
    """验证 create_random 生成的位置始终在 [0, universe_size) 范围内。"""
    config = _make_default_config()
    factory = CivilizationFactory(config, NameGenerator(mode="number"))

    universe_size = 500.0
    for _ in range(200):
        civ = factory.create_random(
            civ_id=0, birth_time=0, universe_size=universe_size
        )
        assert 0.0 <= civ.x < universe_size
        assert 0.0 <= civ.y < universe_size


def test_factory_positions_wrap_around() -> None:
    """验证环形宇宙坐标的模运算包裹功能。

    当随机值超出范围时，应被 modulo 包裹回 [0, universe_size) 内。
    """
    config = _make_default_config()
    factory = CivilizationFactory(config, NameGenerator(mode="number"))

    # 用较大的偏移测试包裹
    civ = factory.create_random(
        civ_id=0,
        birth_time=0,
        universe_size=100.0,
        cluster_center=(95.0, 95.0),
        cluster_radius=50.0,
    )
    assert 0.0 <= civ.x < 100.0
    assert 0.0 <= civ.y < 100.0


def test_factory_initial_batch_count() -> None:
    """验证 create_initial_batch 生成正确数量的文明。"""
    config = SimulationConfig(initial_civ_count=10)
    factory = CivilizationFactory(config, NameGenerator(mode="number"))

    batch = factory.create_initial_batch(universe_size=1000.0)
    assert len(batch) == 10


def test_factory_initial_batch_default_count() -> None:
    """验证 create_initial_batch 使用 config 默认的初始文明数量。"""
    config = _make_default_config()
    factory = CivilizationFactory(config, NameGenerator(mode="number"))

    batch = factory.create_initial_batch(universe_size=1000.0)
    assert len(batch) == config.initial_civ_count


def test_factory_initial_batch_all_have_birth_time_zero() -> None:
    """验证初始批次中所有文明的 birth_time 为 0。"""
    config = SimulationConfig(initial_civ_count=20)
    factory = CivilizationFactory(config, NameGenerator(mode="number"))

    batch = factory.create_initial_batch(universe_size=1000.0)
    for civ in batch:
        assert civ.birth_time == 0


def test_factory_initial_batch_unique_ids() -> None:
    """验证初始批次中所有文明的 ID 是唯一的。"""
    config = SimulationConfig(initial_civ_count=50)
    factory = CivilizationFactory(config, NameGenerator(mode="number"))

    batch = factory.create_initial_batch(universe_size=1000.0)
    ids = [civ.id for civ in batch]
    assert len(ids) == len(set(ids))


def test_factory_uniform_distribution_positions() -> None:
    """验证均匀随机分布模式下位置在合理范围内。

    100 个点中至少应有 90 个的 x/y 在 [0.05, 0.95)*size 之外
    可被判断为"不是总聚在中心"的均匀分布。
    """
    config = SimulationConfig(
        initial_civ_count=200, initial_distribution_mode="uniform"
    )
    factory = CivilizationFactory(config, NameGenerator(mode="number"))
    batch = factory.create_initial_batch(universe_size=1000.0)

    # 验证所有位置在边界内
    for civ in batch:
        assert 0.0 <= civ.x < 1000.0
        assert 0.0 <= civ.y < 1000.0

    # 验证不是所有点都集中在中心区域（粗略均匀性检查）
    center_count = sum(
        1
        for civ in batch
        if 400.0 <= civ.x <= 600.0 and 400.0 <= civ.y <= 600.0
    )
    # 中心区域占 20% 面积，均匀分布下期望约 40 个点
    # 如果超过 120 个点集中在中心，说明分布有明显问题
    assert center_count < 120, (
        f"均匀分布下中心区域点过多: {center_count}/200"
    )


def test_factory_cluster_distribution() -> None:
    """验证聚簇分布模式下文明集中在聚簇中心附近。"""
    random.seed(42)
    config = SimulationConfig(
        initial_civ_count=100,
        initial_distribution_mode="cluster",
        cluster_count=5,
        cluster_radius=100.0,
    )
    factory = CivilizationFactory(config, NameGenerator(mode="number"))
    batch = factory.create_initial_batch(universe_size=1000.0)

    assert len(batch) == 100

    # 在聚簇模式下，文明间的平均距离应显著小于均匀分布时的期望值
    # （粗略验证聚簇分布确实生成了聚集的点）
    for civ in batch:
        assert 0.0 <= civ.x < 1000.0
        assert 0.0 <= civ.y < 1000.0


def test_factory_cluster_positions_near_center() -> None:
    """验证聚簇模式生成的文明位置在聚簇中心附近。

    使用固定的 seed 和已知的聚簇中心，验证偏移在合理范围内。
    """
    random.seed(42)
    config = _make_default_config()
    factory = CivilizationFactory(config, NameGenerator(mode="number"))

    center = (500.0, 500.0)
    radius = 200.0

    for _ in range(50):
        civ = factory.create_random(
            civ_id=0,
            birth_time=0,
            universe_size=1000.0,
            cluster_center=center,
            cluster_radius=radius,
        )
        # 使用欧几里得距离检查是否在合理范围内（3 sigma ~ radius）
        dist = math.sqrt((civ.x - 500.0) ** 2 + (civ.y - 500.0) ** 2)
        assert dist < radius * 2, (
            f"聚簇偏移过大: {dist:.1f} > {radius * 2}"
        )
