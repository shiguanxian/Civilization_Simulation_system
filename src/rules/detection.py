"""探测模块 —— 文明间的探测与接触事件生成。

此模块定义：
- ContactEvent: 两个文明之间的接触事件数据类
- detect_contacts(): 使用空间索引高效检测所有文明间的接触

依赖:
- src.entity.Civilization: 文明数据容器
- src.spatial.SpatialIndex: 空间索引，用于快速邻近查询
- src.spatial.ring_distance: 环形宇宙距离计算
- src.config.SimulationConfig: 模拟配置（使用 universe_size）
"""

from dataclasses import dataclass

from src.config import SimulationConfig
from src.entity import Civilization
from src.spatial import SpatialIndex, ring_distance


@dataclass
class ContactEvent:
    """两个文明之间的接触事件。

    Attributes:
        civ_a: 第一个文明。
        civ_b: 第二个文明。
        distance: 两个文明之间的实际欧几里得距离（光年）。
        detected_by_a: civ_a 是否探测到了 civ_b。
        detected_by_b: civ_b 是否探测到了 civ_a。
    """

    civ_a: Civilization
    civ_b: Civilization
    distance: float
    detected_by_a: bool
    detected_by_b: bool


def detect_contacts(
    civilizations: list[Civilization],
    spatial_index: SpatialIndex,
    config: SimulationConfig,
) -> list[ContactEvent]:
    """探测所有存活文明之间的接触事件。

    对所有存活文明，使用空间索引查询其探测范围内的其他文明，
    并根据目标的隐蔽性和通信状态修正实际探测范围。

    探测规则:
    1. 实际探测范围受目标隐蔽性影响::
         effective_range = detection_range * (1 - target.stealth * 0.5)

    2. 正在通信的文明更容易被探测到::
         如果 target.communication_active:
             effective_range *= 1.5

    3. 只有至少一方探测到对方才生成 ContactEvent。

    4. 避免重复：使用 ``(min_id, max_id)`` 集合确保每对文明只生成一个事件。

    Args:
        civilizations: 所有文明的列表（包含已毁灭的文明）。
        spatial_index: 已构建好的空间索引（应包含所有存活文明）。
        config: 模拟配置，使用其中的 ``universe_size`` 计算距离。

    Returns:
        检测到的接触事件列表，按探测到的先后顺序排列。
        列表中每对文明最多出现一次。
    """
    contacts: list[ContactEvent] = []
    processed_pairs: set[tuple[int, int]] = set()

    # 只处理存活的文明
    alive_civs = [c for c in civilizations if c.is_alive]

    for civ in alive_civs:
        # 查询探测范围内的所有文明
        neighbors = spatial_index.query_neighbors(
            civ.x, civ.y, civ.detection_range
        )

        for neighbor in neighbors:
            if neighbor.id == civ.id:
                continue

            # 去重：每对文明只生成一个事件
            pair = (min(civ.id, neighbor.id), max(civ.id, neighbor.id))
            if pair in processed_pairs:
                continue
            processed_pairs.add(pair)

            # 计算环形宇宙中的实际距离
            distance = ring_distance(
                civ.x, civ.y,
                neighbor.x, neighbor.y,
                config.universe_size,
            )

            # --- civ_a (civ) 探测 neighbor ---
            effective_range_a = civ.detection_range * (
                1 - neighbor.stealth * 0.5
            )
            if neighbor.communication_active:
                effective_range_a *= 1.5
            detected_by_a = distance <= effective_range_a

            # --- civ_b (neighbor) 探测 civ ---
            effective_range_b = neighbor.detection_range * (
                1 - civ.stealth * 0.5
            )
            if civ.communication_active:
                effective_range_b *= 1.5
            detected_by_b = distance <= effective_range_b

            # 只有至少一方探测到对方才生成事件
            if detected_by_a or detected_by_b:
                contacts.append(ContactEvent(
                    civ_a=civ,
                    civ_b=neighbor,
                    distance=distance,
                    detected_by_a=detected_by_a,
                    detected_by_b=detected_by_b,
                ))

    return contacts
