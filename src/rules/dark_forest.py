"""黑暗森林模块 —— 猜疑链、攻击、毁灭与宇宙打击。

此模块实现黑暗森林法则相关的所有规则：
- 威胁感知计算（猜测对方意图）
- 行动选择（攻击／规避／观察）
- 攻击判定与执行
- 暴露处理
- 宇宙公理级打击

依赖:
- src.entity.Civilization: 文明数据容器
- src.rules.detection.ContactEvent: 接触事件
- src.spatial.ring_distance: 环形宇宙距离计算
- src.config.SimulationConfig: 模拟配置
"""

import random

from src.config import SimulationConfig
from src.entity import Civilization
from src.rules.detection import ContactEvent
from src.spatial import ring_distance


def _calculate_threat(observer: Civilization, target: Civilization) -> float:
    """计算 *observer* 对 *target* 的威胁感知。

    公式::

        threat = 0.3                              # 基础
               + 0.2 * (target.level - observer.level) / 5.0  # 等级差
               + 0.3 * target.aggressiveness                 # 对方攻击性
               + 0.2 * (1 - target.stealth)                  # 对方不隐蔽
               + 0.2 * (1 if target.communication_active else 0)  # 通信中
               + random.uniform(-0.1, 0.1)                   # 猜疑链扰动

    结果被 clamp 到 [0, 1] 区间，值越大越倾向于发动攻击。

    Args:
        observer: 进行威胁感知评估的文明。
        target: 被评估的文明。

    Returns:
        威胁感知值，范围 [0, 1]。
    """
    threat = 0.3
    level_diff = (target.level - observer.level) / 5.0
    threat += 0.2 * level_diff
    threat += 0.3 * target.aggressiveness
    threat += 0.2 * (1 - target.stealth)
    if target.communication_active:
        threat += 0.2
    threat += random.uniform(-0.1, 0.1)
    return max(0.0, min(1.0, threat))


def _decide_action(threat: float, config: SimulationConfig) -> str:
    """根据威胁感知做出行动选择。

    ======================== ===========
    条件                      行动
    ======================== ===========
    ``threat >= attack_threshold``  攻击
    ``threat <= flee_threshold``    规避
    中间值                        观察
    ======================== ===========

    Args:
        threat: 威胁感知值 (0~1)。
        config: 模拟配置，包含 ``attack_threshold`` 和 ``flee_threshold``。

    Returns:
        行动选择: ``"attack"``, ``"flee"``, 或 ``"observe"``。
    """
    if threat >= config.attack_threshold:
        return "attack"
    elif threat <= config.flee_threshold:
        return "flee"
    else:
        return "observe"


def _attempt_attack(attacker: Civilization, defender: Civilization) -> bool:
    """尝试一次攻击。

    攻击成功概率::

        prob = 0.5
             + 0.1 * (attacker.level - defender.level)
             - 0.2 * defender.stealth
             + 0.1 * (1 if attacker.energy_output > defender.energy_output else 0)

    **成功时** — *defender* 被毁灭，*attacker* 获取其 10% 能量输出。

    **失败时** — *defender* 的反击暴露了 *attacker* 的坐标
    （``attacker.communication_active = True``）。

    Args:
        attacker: 攻击方文明。
        defender: 防御方文明。

    Returns:
        ``True`` 表示攻击成功，``False`` 表示攻击失败或目标已死亡。
    """
    if not defender.is_alive:
        return False

    success_prob = 0.5
    success_prob += 0.1 * (attacker.level - defender.level)
    success_prob -= 0.2 * defender.stealth
    if attacker.energy_output > defender.energy_output:
        success_prob += 0.1

    success_prob = max(0.1, min(0.95, success_prob))

    if random.random() < success_prob:
        defender.is_alive = False
        attacker.energy_output += defender.energy_output * 0.1
        return True
    else:
        attacker.communication_active = True
        return False


def _expose_civilization(civ: Civilization) -> None:
    """暴露一个文明。

    效果：
    - ``communication_active = True``（坐标暴露）
    - ``stealth *= 0.8``（永久降低隐蔽性）

    Args:
        civ: 被暴露的文明。
    """
    civ.communication_active = True
    civ.stealth *= 0.8


def apply_dark_forest(
    civilizations: list[Civilization],
    contacts: list[ContactEvent],
    config: SimulationConfig,
) -> tuple[int, int]:
    """处理所有接触事件中的黑暗森林法则。

    对每个 ``ContactEvent`` 依次执行：

    1. **威胁感知** — 双方各自计算对对方的威胁感知
    2. **行动选择** — 根据威胁值选择攻击／规避／观察
    3. **攻击判定** — 若某方选择攻击则执行攻击逻辑
    4. **暴露处理** — 被探测到的存活文明坐标被暴露

    Args:
        civilizations: 所有文明列表（仅用于接口一致性，实际通过 *contacts* 中的引用处理）。
        contacts: 接触事件列表。
        config: 模拟配置，包含阈值参数。

    Returns:
        ``(attacks_count, destroyed_count)`` 元组。
    """
    attacks_count = 0
    destroyed_count = 0

    for contact in contacts:
        a, b = contact.civ_a, contact.civ_b

        # 如果任意一方已死亡，跳过
        if not a.is_alive or not b.is_alive:
            continue

        # A 对 B 的威胁感知
        threat_a = _calculate_threat(a, b)
        # B 对 A 的威胁感知
        threat_b = _calculate_threat(b, a)

        # 行动选择
        action_a = _decide_action(threat_a, config)
        action_b = _decide_action(threat_b, config)

        # 处理攻击
        if action_a == "attack":
            attacks_count += 1
            if _attempt_attack(a, b):
                destroyed_count += 1
        if action_b == "attack":
            attacks_count += 1
            if _attempt_attack(b, a):
                destroyed_count += 1

        # 暴露处理：被探测到的存活文明坐标暴露
        if contact.detected_by_a and b.is_alive:
            _expose_civilization(b)
        if contact.detected_by_b and a.is_alive:
            _expose_civilization(a)

    return attacks_count, destroyed_count


def apply_cosmic_strike(
    civilizations: list[Civilization],
    config: SimulationConfig,
) -> int:
    """宇宙公理级打击（黑暗森林打击）。

    逻辑：
    1. 每步以 ``config.cosmic_strike_prob`` 概率触发
    2. 若触发：
       a. 随机选择打击中心 ``(strike_x, strike_y)``
       b. 打击半径 = ``universe_size * random.uniform(0.02, 0.1)``
       c. 使用 ``ring_distance`` 判定命中，毁灭半径内所有文明

    这是一种"清理"机制，防止文明过度密集。

    Args:
        civilizations: 所有文明列表。
        config: 模拟配置，包含 ``cosmic_strike_prob`` 和 ``universe_size``。

    Returns:
        被毁灭的文明数量。
    """
    if random.random() >= config.cosmic_strike_prob:
        return 0

    # 选择打击中心与半径
    strike_x = random.uniform(0, config.universe_size)
    strike_y = random.uniform(0, config.universe_size)
    strike_radius = config.universe_size * random.uniform(0.02, 0.1)

    destroyed_count = 0
    for civ in civilizations:
        if not civ.is_alive:
            continue
        distance = ring_distance(
            strike_x, strike_y, civ.x, civ.y, config.universe_size,
        )
        if distance <= strike_radius:
            civ.is_alive = False
            destroyed_count += 1

    return destroyed_count
