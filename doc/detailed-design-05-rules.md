# 详细设计文档 — 第5部分：规则模块

## 1. 模块概述

### 1.1 模块职责

`src/rules/` 目录下存放所有模拟规则，每个文件实现一组相关的规则。

每个规则模块**没有自己的状态**——它们都是纯函数，接收文明列表和配置，修改文明的状态。

### 1.2 规则模块列表

| 文件 | 主要函数 | 职责 |
|------|---------|------|
| `tech_bomb.py` | `apply_development()` | 文明发展 + 技术爆炸 |
| `expansion.py` | `apply_expansion()` | 扩张 + 坐标暴露 |
| `detection.py` | `detect_contacts()` | 探测与接触事件生成 |
| `dark_forest.py` | `apply_dark_forest()`, `apply_cosmic_strike()` | 猜疑链/攻击/毁灭/宇宙打击 |

---

## 2. 技术爆炸模块 (`src/rules/tech_bomb.py`)

### 2.1 设计

```python
def apply_development(civilizations: list[Civilization],
                      config: SimulationConfig) -> None:
    """
    每个文明的内政发展。
    
    对所有存活文明同步执行，不修改列表结构。
    
    发展规则：
    
    1. 科技点自然积累
       每步增加量 = base_growth * (1 + level * 0.5)
       base_growth = config.tech_growth_base
        
    2. 人口增长（逻辑斯蒂增长模型）
       增长率 = population_growth_rate * (1 - population / carrying_capacity)
       carrying_capacity 与 energy_output 和 level 相关
       
    3. 能量输出增长
       增长率 = energy_growth_rate * (1 + tech_points * 1e-6)
       受限于 level 上限
       
    4. 技术爆炸判定
       触发条件：
         a) tech_points >= tech_needed_for_next_level
         b) random() < tech_explosion_prob（文明自身的概率）
       触发效果：
         - level += 1（上限为 5）
         - tech_points 重置（或消耗掉）
         - energy_output *= 2~5（随机倍数）
         - detection_range *= 1.5~3
         - expansion_radius *= 2~4
         - population *= 1.5~3
         - tech_explosion_prob *= 0.5（越高级越难再次爆炸）
    """
    import random

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

        # 3. 人口增长
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
    """达到下一等级所需的科技点数。"""
    return 100.0 * (level ** 2)  # 等级越高需求越大


def _trigger_tech_explosion(civ: Civilization, 
                            config: SimulationConfig) -> None:
    """
    触发文明的技术爆炸。
    
    效果（全属性暴涨）：
    - 等级+1（不超过5）
    - 科技点减半（代表消耗）
    - 能量输出 × 随机 2~5 倍
    - 探测范围 × 随机 1.5~3 倍
    - 扩张半径 × 随机 2~4 倍
    - 人口 × 随机 1.5~3 倍
    - 技术爆炸概率减半
    """
    import random

    civ.level = min(civ.level + 1, 5)
    civ.tech_points *= 0.5
    civ.energy_output *= random.uniform(2.0, 5.0)
    civ.detection_range *= random.uniform(1.5, 3.0)
    civ.expansion_radius *= random.uniform(2.0, 4.0)
    civ.population *= random.uniform(1.5, 3.0)
    civ.tech_explosion_prob *= 0.5
```

---

## 3. 扩张模块 (`src/rules/expansion.py`)

### 3.1 设计

```python
def apply_expansion(civilizations: list[Civilization],
                    config: SimulationConfig) -> None:
    """
    文明扩张规则。
    
    1. 扩张半径增长
       每步增长 = base_expansion_rate * level * energy_factor
       其中 energy_factor = log10(energy_output) / 18（归一化）
       受 universe_size 限制
       
    2. 扩张方向
       随机方向，使中心坐标 (x, y) 缓慢漂移
       漂移距离 = expansion_radius * 0.1 * random_direction
       
    3. 坐标暴露判定
       暴露概率：
         base = 0.01（基础暴露风险）
         + 如果 expansion_radius 增长超过阈值：+0.02
         + 如果 communication_active：+0.05
         - stealth 减免：* (1 - civ.stealth * 0.8)
       
       如果暴露，communication_active = True
       暴露后文明更容易被探测到
    """
    import random
    import math

    for civ in civilizations:
        if not civ.is_alive:
            continue

        # 1. 扩张半径增长
        energy_factor = math.log10(max(civ.energy_output, 1)) / 18.0
        radius_growth = (config.expansion_rate_base * 
                         civ.level * energy_factor)
        civ.expansion_radius += radius_growth

        # 限制半径不超过宇宙大小的 10%
        max_radius = config.universe_size * 0.1
        civ.expansion_radius = min(civ.expansion_radius, max_radius)

        # 2. 位置漂移（向随机方向扩张）
        angle = random.uniform(0, 2 * math.pi)
        drift = civ.expansion_radius * 0.1 * random.uniform(0.5, 1.0)
        civ.x = (civ.x + math.cos(angle) * drift) % config.universe_size
        civ.y = (civ.y + math.sin(angle) * drift) % config.universe_size

        # 3. 坐标暴露判定
        exposure_prob = config.base_exposure_prob
        if radius_growth > config.exposure_threshold:
            exposure_prob += 0.02
        if civ.communication_active:
            exposure_prob += 0.05
        # 隐蔽性减免
        exposure_prob *= (1 - civ.stealth * 0.8)

        if random.random() < exposure_prob:
            civ.communication_active = True
```

---

## 4. 探测模块 (`src/rules/detection.py`)

### 4.1 设计

```python
from src.rules.expansion import apply_expansion


@dataclass
class ContactEvent:
    """两个文明之间的接触事件。"""
    civ_a: Civilization
    civ_b: Civilization
    distance: float
    detected_by_a: bool   # A 是否探测到了 B
    detected_by_b: bool   # B 是否探测到了 A


def detect_contacts(
    civilizations: list[Civilization],
    spatial_index: SpatialIndex,
    config: SimulationConfig,
) -> list[ContactEvent]:
    """
    探测与接触逻辑。
    
    对所有存活文明，使用空间索引查询其探测范围内的其他文明。
    
    探测规则：
    1. 实际探测范围受目标隐蔽性影响：
       effective_range = civ.detection_range * (1 - target.stealth * 0.5)
       
    2. 正在通信的文明更容易被探测到：
       如果 target.communication_active:
         effective_range *= 1.5
       
    3. 返回所有 ContactEvent，由 dark_forest 模块处理
       
    4. 避免重复：每对文明只生成一个事件
       使用 (min_id, max_id) 集合去重
    """
    contacts = []
    processed_pairs: set[tuple[int, int]] = set()

    alive_civs = [c for c in civilizations if c.is_alive]

    for civ in alive_civs:
        # 查询探测范围内的所有文明
        neighbors = spatial_index.query_neighbors(
            civ.x, civ.y, civ.detection_range
        )

        for neighbor in neighbors:
            if neighbor.id == civ.id:
                continue

            # 去重
            pair = (min(civ.id, neighbor.id), max(civ.id, neighbor.id))
            if pair in processed_pairs:
                continue
            processed_pairs.add(pair)

            # 计算实际距离
            distance = ring_distance(
                civ.x, civ.y, neighbor.x, neighbor.y,
                config.universe_size
            )

            # 判断双方是否能探测到对方
            # A 探测 B
            effective_range_a = civ.detection_range * (
                1 - neighbor.stealth * 0.5
            )
            if neighbor.communication_active:
                effective_range_a *= 1.5
            detected_by_a = distance <= effective_range_a

            # B 探测 A
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
```

---

## 5. 黑暗森林模块 (`src/rules/dark_forest.py`)

### 5.1 设计

```python
import random
import math


def apply_dark_forest(contacts: list[ContactEvent],
                      config: SimulationConfig) -> None:
    """
    处理所有接触事件中的黑暗森林法则。
    
    猜疑链处理流程（对每个 ContactEvent）：
    
    1. 威胁感知计算（双方各自计算）
       civ_a 对 civ_b 的威胁感知：
         threat = base_threat
         + level_diff_factor（等级差越大威胁越大）
         + aggressiveness_factor（对方攻击性）
         - stealth_factor（对方隐蔽，来历不明更可怕）
         + communication_factor（对方在通信 -> 可能已暴露位置）
    
    2. 行动选择
       威胁感知 > attack_threshold → 攻击
       威胁感知 < flee_threshold → 规避（双方各走各路）
       中间值 → 观察（暂不行动，但记录对方存在）
    
    3. 攻击判定
       攻击成功概率 = 0.5 + 0.1 * (attacker.level - defender.level)
                      - 0.2 * defender.stealth
                      + 0.1 * (attacker.energy_output > defender.energy_output)
       
       若成功：
         - defender.is_alive = False
         - 触发 "打击即毁灭" 事件记录
       若失败：
         - 可能触发反击（由另一方的威胁感知决定）
         - defender 的坐标被暴露
    
    4. 暴露即死亡
       被攻击/被探测到的文明，如果存活：
         - communication_active = True（坐标暴露）
         - stealth 永久降低 20%（暴露后难以再隐藏）
    """
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
            _attempt_attack(a, b, config)
        if action_b == "attack":
            _attempt_attack(b, a, config)

        # 暴露处理
        if contact.detected_by_a and b.is_alive:
            _expose_civilization(b)
        if contact.detected_by_b and a.is_alive:
            _expose_civilization(a)


def _calculate_threat(observer: Civilization,
                      target: Civilization) -> float:
    """
    计算 observer 对 target 的威胁感知。
    
    公式：
    threat = 0.3  (基础)
           + 0.2 * (target.level - observer.level) / 5.0  (等级差)
           + 0.3 * target.aggressiveness  (对方攻击性)
           + 0.2 * (1 - target.stealth)   (对方不隐蔽 -> 可见即威胁)
           + 0.2 * (1 if target.communication_active else 0) (通信中)
           + 随机扰动 [-0.1, +0.1]  (猜疑链的不确定性)
    
    范围 [0, 1]，越大越倾向于攻击。
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
    """
    根据威胁感知做出行动选择。
    
    threat >= attack_threshold (0.65) → "attack"
    threat <= flee_threshold (0.35)   → "flee"
    中间 → "observe"
    """
    if threat >= config.attack_threshold:
        return "attack"
    elif threat <= config.flee_threshold:
        return "flee"
    else:
        return "observe"


def _attempt_attack(attacker: Civilization,
                    defender: Civilization,
                    config: SimulationConfig) -> None:
    """
    尝试一次攻击。
    
    攻击成功概率（约 0.3~0.9）：
      base = 0.5
      + 0.1 * (attacker.level - defender.level)
      - 0.2 * defender.stealth
      + 0.1 * (1 if attacker.energy_output > defender.energy_output else 0)
    """
    if not defender.is_alive:
        return  # 目标已死亡

    success_prob = 0.5
    success_prob += 0.1 * (attacker.level - defender.level)
    success_prob -= 0.2 * defender.stealth
    if attacker.energy_output > defender.energy_output:
        success_prob += 0.1

    success_prob = max(0.1, min(0.95, success_prob))

    if random.random() < success_prob:
        defender.is_alive = False
        # 攻击成功，攻击方可能获取资源
        attacker.energy_output += defender.energy_output * 0.1
    else:
        # 攻击失败，防御方暴露攻击者坐标
        attacker.communication_active = True


def _expose_civilization(civ: Civilization) -> None:
    """暴露一个文明。"""
    civ.communication_active = True
    civ.stealth *= 0.8  # 永久降低隐蔽性


def apply_cosmic_strike(
    civilizations: list[Civilization],
    spatial_index: SpatialIndex,
    config: SimulationConfig,
) -> None:
    """
    宇宙公理级打击（黑暗森林打击）。
    
    逻辑：
    1. 每步以 config.cosmic_strike_prob 概率触发
    2. 若触发：
       a. 随机选择打击中心 (x, y)
       b. 打击半径 = universe_size * random.uniform(0.02, 0.1)
       c. 半径内所有文明被毁灭
       d. 记录打击区域（用于后续阻止新文明在此诞生）
    
    这是一种"清理"机制，防止文明过度密集。
    """
    if random.random() >= config.cosmic_strike_prob:
        return

    # 选择打击中心
    strike_x = random.uniform(0, config.universe_size)
    strike_y = random.uniform(0, config.universe_size)
    strike_radius = config.universe_size * random.uniform(0.02, 0.1)

    # 查找并毁灭打击范围内的文明
    victims = spatial_index.query_neighbors(
        strike_x, strike_y, strike_radius
    )
    for civ in victims:
        civ.is_alive = False

    # 记录打击区域（可选，用于未来阻止重生）
    # 这个功能可以后续扩展
```

---

## 6. 规则模块的配置常量

在 `config.py` 中需要添加以下配置参数（默认值）：

```python
# 技术爆炸相关
tech_growth_base: float = 5.0           # 科技点基础增长
pop_growth_rate: float = 0.01           # 人口增长率
energy_growth_rate: float = 0.005       # 能量输出增长率

# 扩张相关
expansion_rate_base: float = 1.0        # 扩张基础速率
base_exposure_prob: float = 0.01        # 坐标暴露基础概率
exposure_threshold: float = 5.0         # 扩张暴露阈值

# 黑暗森林相关
attack_threshold: float = 0.65          # 攻击阈值
flee_threshold: float = 0.35            # 规避阈值
```

---

## 7. 模块的独立可测试性

### 7.1 测试要点

```python
# tests/test_rules_tech_bomb.py
def test_tech_points_accumulate():
    """验证科技点随时间增长。"""
    civ = Civilization(...)
    apply_development([civ], config)
    assert civ.tech_points > initial_tech

def test_tech_explosion():
    """验证技术爆炸触发时等级提升。"""
    ...

def test_tech_explosion_capped_at_5():
    """验证等级不超过5。"""
    ...


# tests/test_rules_expansion.py
def test_expansion_radius_grows():
    """验证扩张半径增长。"""
    ...

def test_position_drifts():
    """验证文明位置漂移。"""
    ...

def test_exposure_probability():
    """验证暴露概率逻辑。"""
    ...


# tests/test_rules_detection.py
def test_contact_detected():
    """验证范围内的文明被探测到。"""
    ...

def test_stealth_affects_detection():
    """验证隐蔽性影响探测。"""
    ...

def test_communication_increases_detection():
    """验证通信增加被探测概率。"""
    ...

def test_no_duplicate_contacts():
    """验证没有重复的接触事件。"""
    ...


# tests/test_rules_dark_forest.py
def test_high_threat_leads_to_attack():
    """验证高威胁感知导致攻击。"""
    ...

def test_low_threat_leads_to_flee():
    """验证低威胁感知导致规避。"""
    ...

def test_attack_kills_defender():
    """验证攻击成功时目标被毁灭。"""
    ...

def test_attack_failure_exposes_attacker():
    """验证攻击失败暴露攻击者。"""
    ...

def test_cosmic_strike_kills_in_radius():
    """验证宇宙打击毁灭半径内文明。"""
    ...

def test_cosmic_strike_low_probability():
    """验证宇宙打击概率很低。"""
    ...
```

---

## 8. 依赖关系

```
tech_bomb.py   → entity.py（使用 Civilization）
expansion.py   → entity.py
detection.py   → entity.py, spatial.py（使用 SpatialIndex）
dark_forest.py → entity.py, spatial.py
```

所有规则模块**都不依赖 simulation.py**（被 simulation.py 调用，而非相反）。

---

*下一篇：`detailed-design-06-output-stats.md` — 输出与统计模块详细设计*
