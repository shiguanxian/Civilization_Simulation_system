# 规则模块 - 最小可执行任务列表

## 目录：`src/rules/`

### 文件清单
- `src/rules/__init__.py`
- `src/rules/tech_bomb.py`    — 文明发展 + 技术爆炸
- `src/rules/expansion.py`    — 扩张 + 坐标暴露
- `src/rules/detection.py`    — 探测与接触事件生成
- `src/rules/dark_forest.py`  — 猜疑链/攻击/毁灭/宇宙打击

---

## 任务清单

### R1. 创建 `src/rules/` 包结构和 __init__.py
- 创建 `src/rules/__init__.py`（可为空或导出主要函数）
- 确保各个模块可以被 `from src.rules import *` 导入

### R2. 实现技术爆炸模块 (`tech_bomb.py`)

- [ ] **R2.1 实现 `apply_development()` 主函数**
  - 遍历所有存活文明，执行以下子步骤
  - 函数签名：`apply_development(civilizations, config) -> None`

- [ ] **R2.2 科技点自然积累**
  - 每步增加量 = `tech_growth_base * (1 + level * 0.5)`
  - 编写单元测试验证科技点随时间增长

- [ ] **R2.3 人口增长（逻辑斯蒂增长模型）**
  - 增长率 = `pop_growth_rate * (1 - population / carrying_capacity)`
  - carrying_capacity 与 energy_output 和 level 相关
  - 编写单元测试验证人口增长逻辑

- [ ] **R2.4 能量输出增长**
  - 增长率 = `energy_growth_rate * (1 + tech_points * 1e-6)`
  - 编写单元测试验证能量增长逻辑

- [ ] **R2.5 技术爆炸判定与触发**
  - `_tech_needed(level)`：计算达到下一等级所需科技点 = `100.0 * (level²)`
  - 判定条件：科技点达标 + 随机概率命中
  - `_trigger_tech_explosion()`：触发效果（level+1、科技点减半、能量×2~5、探测范围×1.5~3、扩张半径×2~4、人口×1.5~3、爆炸概率减半）
  - 等级上限为 5
  - 编写单元测试验证：技术爆炸触发时等级提升、等级上限为 5

### R3. 实现扩张模块 (`expansion.py`)

- [ ] **R3.1 实现 `apply_expansion()` 主函数**
  - 遍历所有存活文明
  - 函数签名：`apply_expansion(civilizations, config) -> None`

- [ ] **R3.2 扩张半径增长**
  - 每步增长 = `expansion_rate_base * level * energy_factor`
  - energy_factor = `log10(energy_output) / 18.0`（归一化）
  - 半径上限为宇宙大小的 10%
  - 编写单元测试验证扩张半径增长

- [ ] **R3.3 位置漂移**
  - 随机方向，漂移距离 = `expansion_radius * 0.1 * random(0.5, 1.0)`
  - 坐标模宇宙大小（环形宇宙）
  - 编写单元测试验证位置漂移和环形坐标处理

- [ ] **R3.4 坐标暴露判定**
  - 基础暴露概率 + 阈值加成 + 通信加成 - 隐蔽性减免
  - 暴露后 `communication_active = True`
  - 编写单元测试验证暴露概率逻辑

### R4. 实现探测模块 (`detection.py`)

- [ ] **R4.1 定义 `ContactEvent` 数据类**
  - 包含 civ_a, civ_b, distance, detected_by_a, detected_by_b

- [ ] **R4.2 实现 `detect_contacts()` 主函数**
  - 遍历所有存活文明，使用 `spatial_index.query_neighbors()` 查询
  - 函数签名：`detect_contacts(civilizations, spatial_index, config) -> list[ContactEvent]`

- [ ] **R4.3 实际探测距离修正**
  - 有效探测范围 = `detection_range * (1 - target.stealth * 0.5)`
  - 通信中文明更容易被探测：`effective_range *= 1.5`
  - 只有至少一方探测到对方才生成 ContactEvent

- [ ] **R4.4 去重逻辑**
  - 使用 `(min_id, max_id)` 集合避免重复接触事件
  - 编写单元测试验证：范围内探测到、隐蔽性影响、通信加成、无重复事件

### R5. 实现黑暗森林模块 (`dark_forest.py`)

- [ ] **R5.1 实现威胁感知计算 `_calculate_threat()`**
  - 公式：基础 0.3 + 等级差 0.2 + 对方攻击性 0.3 + 不隐蔽性 0.2 + 通信中 0.2 + 随机扰动 ±0.1
  - 返回范围 [0, 1]
  - 编写单元测试验证威胁感知计算正确

- [ ] **R5.2 实现行动选择 `_decide_action()`**
  - threat >= attack_threshold(0.65) → "attack"
  - threat <= flee_threshold(0.35) → "flee"
  - 中间 → "observe"
  - 编写单元测试验证各阈值行为

- [ ] **R5.3 实现攻击判定 `_attempt_attack()`**
  - 成功概率 = 0.5 + 0.1*等级差 - 0.2*防御方隐蔽性 + 0.1*能量优势
  - 成功：目标 is_alive=False，攻击方获取 10% 能量
  - 失败：防御方暴露攻击者坐标
  - 编写单元测试验证：攻击成功/失败逻辑

- [ ] **R5.4 实现暴露处理 `_expose_civilization()`**
  - communication_active = True
  - stealth *= 0.8（永久降低隐蔽性）
  - 编写单元测试验证

- [ ] **R5.5 实现 `apply_dark_forest()` 主函数**
  - 遍历所有 ContactEvent，处理猜疑链和攻击
  - 如果任意一方已死亡则跳过
  - 调用威胁感知计算、行动选择、攻击判定、暴露处理
  - 编写单元测试验证完整黑暗森林处理流程

- [ ] **R5.6 实现 `apply_cosmic_strike()` 宇宙打击**
  - 每步以 `cosmic_strike_prob` 概率触发
  - 随机选择打击中心，打击半径 = `universe_size * random(0.02, 0.1)`
  - 毁灭半径内所有文明
  - 编写单元测试验证：打击毁灭半径内文明、打击概率很低
