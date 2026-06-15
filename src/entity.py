"""实体模块 — 文明数据容器、名称生成器与文明工厂。

此模块定义了模拟的核心数据实体：
- Civilization: 文明纯数据容器，不含业务逻辑
- NameGenerator: 文明名称生成器，支持词库组合与数字编号两种模式
- CivilizationFactory: 文明工厂，按照配置批量生成文明实例
"""

import random
from dataclasses import dataclass

from src.config import SimulationConfig


@dataclass
class Civilization:
    """一个文明的所有参数。纯数据容器，不包含业务逻辑。"""

    # === 标识 ===
    id: int = 0
    """唯一标识，由 Simulation 分配。"""

    name: str = ""
    """文明名称。"""

    # === 空间位置 ===
    x: float = 0.0
    """二维 X 坐标（光年）。"""

    y: float = 0.0
    """二维 Y 坐标（光年）。"""

    # === 发展水平 ===
    level: int = 1
    """文明等级 1~5。"""

    tech_points: float = 0.0
    """科技点数。"""

    tech_explosion_prob: float = 0.0
    """技术爆炸概率（0~1）。"""

    # === 规模与能量 ===
    expansion_radius: float = 0.0
    """扩张半径（光年）。"""

    population: float = 0.0
    """人口规模。"""

    energy_output: float = 0.0
    """能量输出。"""

    # === 行为倾向 ===
    aggressiveness: float = 0.0
    """攻击性（0~1）。"""

    stealth: float = 0.0
    """隐蔽性（0~1）。"""

    detection_range: float = 0.0
    """探测范围（光年）。"""

    # === 状态 ===
    is_alive: bool = True
    """是否存活。"""

    birth_time: int = 0
    """诞生时间步。"""

    communication_active: bool = False
    """是否正在主动通信。"""


class NameGenerator:
    """文明名称生成器。

    支持两种模式：
    - "auto": 先用预设词库组合名称（前缀+后缀），用完后切换到数字编号。
    - "number": 纯数字编号，格式为 "文明 #000001"。
    """

    # 预设前缀词库
    PREFIXES: tuple[str, ...] = (
        "阿尔法", "贝塔", "伽马", "德尔塔", "伊普西龙",
        "泽塔", "伊塔", "西塔", "约塔", "卡帕",
    )

    # 预设后缀词库
    SUFFIXES: tuple[str, ...] = (
        "仙座", "星系", "星云", "星域", "星团",
        "恒星系", "星区", "星环",
    )

    def __init__(self, mode: str = "auto") -> None:
        """初始化名称生成器。

        Args:
            mode: 生成模式，"auto" 或 "number"。

        Raises:
            ValueError: 当 mode 不是 "auto" 或 "number" 时抛出。
        """
        if mode not in ("auto", "number"):
            raise ValueError(f"mode 必须为 'auto' 或 'number'，收到: {mode!r}")
        self.mode = mode
        self._prefix_index = 0
        self._suffix_index = 0

    def generate(self, civ_id: int) -> str:
        """生成文明名称。

        Args:
            civ_id: 文明唯一 ID，用于数字编号模式及自动模式的回退。

        Returns:
            生成的文明名称字符串。
        """
        if self.mode == "number":
            return f"文明 #{civ_id:06d}"
        return self._generate_named(civ_id)

    def _generate_named(self, civ_id: int) -> str:
        """从词库组合生成名称，用完后 fallback 到数字编号。

        按 (prefix_0, suffix_0), (prefix_0, suffix_1), ...,
        (prefix_1, suffix_0), ... 的顺序遍历所有组合。
        所有组合用完后回退到与数字模式相同的格式。

        Args:
            civ_id: 文明 ID，用于回退时的编号。

        Returns:
            生成的文明名称。
        """
        if self._prefix_index >= len(self.PREFIXES):
            return f"文明 #{civ_id:06d}"

        name = self.PREFIXES[self._prefix_index] + self.SUFFIXES[self._suffix_index]

        # 推进索引
        self._suffix_index += 1
        if self._suffix_index >= len(self.SUFFIXES):
            self._suffix_index = 0
            self._prefix_index += 1

        return name


class CivilizationFactory:
    """文明工厂，负责按照配置生成文明实例。

    根据 SimulationConfig 中的参数范围、分布模式等配置，
    批量创建带有随机初始参数的 Civilization 实例。
    """

    def __init__(self, config: SimulationConfig, name_generator: NameGenerator) -> None:
        """初始化文明工厂。

        Args:
            config: 模拟全局配置，包含文明参数范围与分布模式等。
            name_generator: 名称生成器实例。
        """
        self.config = config
        self.name_generator = name_generator

    def create_random(
        self,
        civ_id: int,
        birth_time: int,
        universe_size: float,
        cluster_center: tuple[float, float] | None = None,
        cluster_radius: float | None = None,
    ) -> Civilization:
        """在宇宙中随机位置生成一个文明。

        根据是否提供 cluster_center 决定位置生成方式：
        - 无 cluster_center：均匀随机分布
        - 有 cluster_center：以聚簇中心为基准的高斯偏移分布

        Args:
            civ_id: 文明唯一 ID。
            birth_time: 当前时间步（文明诞生时间）。
            universe_size: 宇宙空间边长（光年）。
            cluster_center: 聚簇中心坐标 (x, y)，为 None 时使用均匀随机分布。
            cluster_radius: 聚簇半径（光年），在聚簇模式下用于限制高斯偏移范围。

        Returns:
            新生成的 Civilization 实例。
        """
        x, y = self._random_position(universe_size, cluster_center, cluster_radius)
        params = self._random_initial_params()
        name = self.name_generator.generate(civ_id)

        return Civilization(
            id=civ_id,
            name=name,
            x=x,
            y=y,
            birth_time=birth_time,
            **params,
        )

    def create_initial_batch(self, universe_size: float) -> list[Civilization]:
        """创建初始文明批次。

        根据 config.initial_distribution_mode 决定分布模式：
        - "uniform": 在宇宙范围内均匀随机分布
        - "cluster": 以若干个聚簇中心为中心的聚簇分布

        Args:
            universe_size: 宇宙空间边长（光年）。

        Returns:
            包含 config.initial_civ_count 个 Civilization 的列表。
        """
        mode = self.config.initial_distribution_mode
        count = self.config.initial_civ_count

        if mode == "cluster":
            return self._create_cluster_batch(count, universe_size)
        return self._create_uniform_batch(count, universe_size)

    def _create_uniform_batch(
        self, count: int, universe_size: float
    ) -> list[Civilization]:
        """在宇宙中均匀随机分布地创建文明批次。

        Args:
            count: 文明数量。
            universe_size: 宇宙空间边长（光年）。

        Returns:
            文明列表。
        """
        return [
            self.create_random(civ_id=i, birth_time=0, universe_size=universe_size)
            for i in range(count)
        ]

    def _create_cluster_batch(
        self, count: int, universe_size: float
    ) -> list[Civilization]:
        """以聚簇分布模式创建文明批次。

        首先生成 config.cluster_count 个随机聚簇中心，
        然后将每个文明分配到随机一个聚簇中心附近。

        Args:
            count: 文明数量。
            universe_size: 宇宙空间边长（光年）。

        Returns:
            文明列表。
        """
        cluster_count = self.config.cluster_count
        cluster_radius = self.config.cluster_radius

        centers = [
            (random.uniform(0, universe_size), random.uniform(0, universe_size))
            for _ in range(cluster_count)
        ]

        return [
            self.create_random(
                civ_id=i,
                birth_time=0,
                universe_size=universe_size,
                cluster_center=random.choice(centers),
                cluster_radius=cluster_radius,
            )
            for i in range(count)
        ]

    def _random_position(
        self,
        universe_size: float,
        cluster_center: tuple[float, float] | None = None,
        cluster_radius: float | None = None,
    ) -> tuple[float, float]:
        """生成随机位置，支持环形宇宙坐标（模运算包裹）。

        Args:
            universe_size: 宇宙空间边长（光年）。
            cluster_center: 聚簇中心坐标，None 表示均匀随机。
            cluster_radius: 聚簇半径。

        Returns:
            坐标元组 (x, y)，取值在 [0, universe_size) 范围内。
        """
        if cluster_center is not None and cluster_radius is not None:
            cx, cy = cluster_center
            x = cx + random.gauss(0, cluster_radius / 3)
            y = cy + random.gauss(0, cluster_radius / 3)
        else:
            x = random.uniform(0, universe_size)
            y = random.uniform(0, universe_size)

        # 环形宇宙坐标包裹
        x = x % universe_size
        y = y % universe_size
        return x, y

    def _random_initial_params(self) -> dict[str, float | int | bool]:
        """根据配置范围随机生成文明初始参数。

        从 config 中各参数范围字段读取上下界，
        使用 random.uniform / random.randint 生成随机值。

        Returns:
            包含随机化参数的字典，可与 Civilization 构造函数配合使用。
        """
        cfg = self.config
        return {
            "level": random.randint(cfg.level_range[0], cfg.level_range[1]),
            "tech_points": 0.0,
            "tech_explosion_prob": cfg.tech_explosion_base_prob,
            "expansion_radius": random.uniform(*cfg.expansion_radius_range),
            "population": random.uniform(*cfg.population_range),
            "energy_output": random.uniform(*cfg.energy_output_range),
            "aggressiveness": random.uniform(*cfg.aggressiveness_range),
            "stealth": random.uniform(*cfg.stealth_range),
            "detection_range": random.uniform(*cfg.detection_range_range),
        }
