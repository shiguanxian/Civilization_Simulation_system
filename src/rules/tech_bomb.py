"""技术爆炸模块 —— 文明发展（科技点积累、人口增长、能量增长）与技术爆炸判定。

此模块包含以下函数：
- apply_development(): 主函数，遍历所有存活文明并执行发展逻辑
- _tech_needed(): 计算升级所需科技点
- _calc_carrying_capacity(): 计算文明的人口承载上限
- _trigger_tech_explosion(): 触发技术爆炸，文明属性暴涨
"""

import random

from src.config import SimulationConfig
from src.entity import Civilization


def apply_development(
    civilizations: list[Civilization],
    config: SimulationConfig,
) -> None:
    """对所有存活文明执行一回合的发展更新。

    发展规则（按顺序执行）：
    1. 科技点自然积累 — tech_growth = tech_growth_base * (1 + level * 0.5)
    2. 技术爆炸判定 — 若科技点达标且概率命中，触发爆炸并跳过后续步骤
    3. 人口增长（逻辑斯蒂模型）— 受承载上限约束
    4. 能量输出增长 — 与科技点正相关

    Args:
        civilizations: 所有文明实例的列表（会被原地修改）。
        config: 模拟全局配置。
    """
    for civ in civilizations:
        if not civ.is_alive:
            continue

        # 1. 科技点积累
        tech_growth = config.tech_growth_base * (1 + civ.level * 0.5)
        civ.tech_points += tech_growth

        # 2. 技术爆炸判定
        if civ.tech_points >= _tech_needed(civ.level):
            if random.random() < civ.tech_explosion_prob:
                _trigger_tech_explosion(civ, config)
                continue  # 技术爆炸后跳过常规发展

        # 3. 人口增长（逻辑斯蒂增长模型）
        carrying_capacity = _calc_carrying_capacity(civ)
        pop_growth = config.pop_growth_rate * (
            1 - civ.population / carrying_capacity
        )
        civ.population *= (1 + pop_growth)

        # 4. 能量输出增长
        energy_growth = config.energy_growth_rate * (
            1 + civ.tech_points * 1e-6
        )
        civ.energy_output *= (1 + energy_growth)


def _tech_needed(level: int) -> float:
    """计算达到下一等级所需的科技点数。

    公式：100.0 * level²，等级越高需求越大。

    Args:
        level: 当前文明等级（1~5）。

    Returns:
        所需科技点数。
    """
    return 100.0 * (level**2)


def _calc_carrying_capacity(civ: Civilization) -> float:
    """计算文明的人口承载上限（逻辑斯蒂模型的 K 值）。

    公式：energy_output * level * 1e6
    能量输出越高、等级越高，承载上限越大。

    Args:
        civ: 目标文明。

    Returns:
        承载上限（人口单位）。
    """
    return civ.energy_output * civ.level * 1e6


def _trigger_tech_explosion(
    civ: Civilization,
    config: SimulationConfig,  # noqa: ARG001 — 保留参数以备后续扩展
) -> None:
    """触发文明的技术爆炸。

    技术爆炸效果（全属性暴涨）：
    - 等级 +1（上限为 5）
    - 科技点减半（代表消耗）
    - 能量输出 × 随机 2~5 倍
    - 探测范围 × 随机 1.5~3 倍
    - 扩张半径 × 随机 2~4 倍
    - 人口 × 随机 1.5~3 倍
    - 技术爆炸概率减半（越高级越难再次爆炸）

    Args:
        civ: 目标文明（会被原地修改）。
        config: 模拟全局配置（保留用于未来扩展）。
    """
    civ.level = min(civ.level + 1, 5)
    civ.tech_points *= 0.5
    civ.energy_output *= random.uniform(2.0, 5.0)
    civ.detection_range *= random.uniform(1.5, 3.0)
    civ.expansion_radius *= random.uniform(2.0, 4.0)
    civ.population *= random.uniform(1.5, 3.0)
    civ.tech_explosion_prob *= 0.5
