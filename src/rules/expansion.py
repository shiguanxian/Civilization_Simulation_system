"""扩张模块 —— 文明扩张、位置漂移与坐标暴露判定。

此模块包含 apply_expansion() 函数，对所有存活文明执行：
1. 扩张半径增长（受等级和能量输出影响）
2. 位置随机漂移（环形宇宙坐标包裹）
3. 坐标暴露概率判定（受扩张半径、通信状态和隐蔽性影响）
"""

import math
import random

from src.config import SimulationConfig
from src.entity import Civilization


def apply_expansion(
    civilizations: list[Civilization], config: SimulationConfig
) -> None:
    """对所有存活文明执行扩张规则。

    每步依次执行以下操作（所有修改均在原对象上就地完成）：

    1. 扩张半径增长
       增长量 = expansion_rate_base * level * energy_factor
       其中 energy_factor = log10(energy_output) / 18.0（归一化因子）
       增长后半径上限为 universe_size * 0.1

    2. 位置漂移
       随机选择漂移方向（均匀角度 0~2π）
       漂移距离 = expansion_radius * 0.1 * random(0.5, 1.0)
       坐标使用模运算包裹，确保在 [0, universe_size) 范围内

    3. 坐标暴露判定
       暴露概率 = base_exposure_prob
                 + (expansion_radius / exposure_threshold)
                 + (0.2 if communication_active else 0)
                 - (stealth * 0.3)
       概率值被钳制到 [0, 1]
       若暴露，设置 communication_active = True

    Args:
        civilizations: 所有文明的列表。
        config: 模拟全局配置，需包含 expansion_rate_base、base_exposure_prob、
                exposure_threshold、universe_size 等字段。
    """
    for civ in civilizations:
        if not civ.is_alive:
            continue

        # 1. 扩张半径增长
        energy_factor = math.log10(max(civ.energy_output, 1.0)) / 18.0
        radius_growth = config.expansion_rate_base * civ.level * energy_factor
        civ.expansion_radius += radius_growth

        # 半径上限为宇宙大小的 10%
        max_radius = config.universe_size * 0.1
        civ.expansion_radius = min(civ.expansion_radius, max_radius)

        # 2. 位置漂移（随机方向）
        angle = random.uniform(0.0, 2.0 * math.pi)
        drift = civ.expansion_radius * 0.1 * random.uniform(0.5, 1.0)
        civ.x = (civ.x + math.cos(angle) * drift) % config.universe_size
        civ.y = (civ.y + math.sin(angle) * drift) % config.universe_size

        # 3. 坐标暴露判定
        exposure_prob = (
            config.base_exposure_prob
            + (civ.expansion_radius / config.exposure_threshold)
            + (0.2 if civ.communication_active else 0.0)
            - (civ.stealth * 0.3)
        )
        exposure_prob = max(0.0, min(1.0, exposure_prob))

        if random.random() < exposure_prob:
            civ.communication_active = True
