# 详细设计文档 — 第4部分：模拟引擎模块

## 1. 模块概述

### 1.1 模块职责

`src/simulation.py` 是整个模拟系统的核心——它负责：
1. 管理模拟生命周期（初始化 → 每步推进 → 结束）
2. 编排每步的演化流程（调用各规则模块）
3. 管理全局状态（时间步、文明列表、统计信息）
4. 向可视化层提供状态接口

### 1.2 核心设计原则

- **单步可暂停/可恢复**：交互模式下每一步之间可暂停
- **状态可导出/可导入**：支持保存和恢复模拟进度
- **规则可插拔**：规则模块可独立替换或禁用

---

## 2. Simulation 类设计

### 2.1 类结构

```python
class Simulation:
    """
    模拟引擎主类。
    管理整个模拟的生命周期和状态。
    """

    def __init__(self, config: SimulationConfig):
        self.config = config

        # === 核心状态 ===
        self.current_step: int = 0           # 当前时间步
        self.civilizations: list[Civilization] = []  # 所有文明
        self.next_id: int = 0                # 下一个文明 ID

        # === 子模块 ===
        self.spatial_index: SpatialIndex     # 空间索引
        self.factory: CivilizationFactory    # 文明工厂
        self.stats_collector: StatsCollector # 统计收集器
        self.data_saver: DataSaver           # 数据保存器

        # === 运行控制 ===
        self.is_paused: bool = False         # 是否暂停
        self.is_running: bool = False        # 是否正在运行
        self.speed_multiplier: float = 1.0   # 速度倍率

        # === 回调（用于可视化层） ===
        self._on_step_callbacks: list[callable] = []
        self._on_pause_callbacks: list[callable] = []
        self._on_stop_callbacks: list[callable] = []

    def initialize(self) -> None:
        """
        初始化模拟。
        
        流程：
        1. 创建初始文明批次
        2. 初始化空间索引
        3. 初始化统计收集器和数据保存器
        4. 输出初始状态
        """
        # 创建初始文明
        self.civilizations = self.factory.create_initial_batch(
            self.config.universe_size
        )
        self.next_id = len(self.civilizations) + 1

        # 初始化空间索引
        cell_size = self.config.spatial_grid_cell_size
        if cell_size <= 0:
            # 自动计算
            avg_detection = (self.config.detection_range_range[0] +
                             self.config.detection_range_range[1]) / 2
            cell_size = auto_select_cell_size(
                self.config.universe_size,
                len(self.civilizations),
                avg_detection,
                5.0  # 默认 CPU 评分
            )
        self.spatial_index = SpatialIndex(
            self.config.universe_size, cell_size
        )
        self.spatial_index.rebuild(self.civilizations)

        # 初始化统计和数据保存
        self.stats_collector = StatsCollector()
        self.data_saver = DataSaver(self.config)

        self.current_step = 0
        self.is_running = True

    def step(self) -> StepResult:
        """
        执行一个时间步的演化。
        
        返回值 StepResult 包含本步的统计信息和事件记录。
        
        流程（对应需求文档的 7 个阶段）：
        """
        # ── 阶段 0：暂停检测 ──
        if self.is_paused:
            return StepResult(skipped=True)

        # ── 阶段 1：重建空间索引 ──
        # （上一步可能改变了文明的位置或存活状态）
        self.spatial_index.rebuild(self.civilizations)

        # ── 阶段 2：文明诞生 ──
        new_civs = self._apply_birth_rules()
        self.civilizations.extend(new_civs)
        if new_civs:
            self.spatial_index.rebuild(self.civilizations)

        # ── 阶段 3：文明发展 + 技术爆炸 ──
        self._apply_development_rules()

        # ── 阶段 4：扩张 ──
        self._apply_expansion_rules()

        # ── 阶段 5：探测与接触 ──
        contacts = self._apply_detection_rules()

        # ── 阶段 6：黑暗森林处理（猜疑链/攻击） ──
        self._apply_dark_forest_rules(contacts)

        # ── 阶段 7：黑暗森林打击 ──
        self._apply_cosmic_strike()

        # ── 阶段 8：清理与统计 ──
        self._cleanup_dead_civilizations()
        stats = self.stats_collector.collect(
            self.civilizations, self.current_step
        )

        # ── 阶段 9：数据保存 ──
        if self.current_step % self.config.save_interval == 0:
            self.data_saver.save_step(stats, self.current_step)

        # ── 阶段 10：推进时间步 ──
        self.current_step += 1

        # ── 触发回调 ──
        self._notify_step_callbacks(stats)

        return StepResult(
            step=self.current_step,
            stats=stats,
            new_civs_count=len(new_civs),
            destroyed_count=stats.destroyed_count,
        )

    def run(self) -> None:
        """
        运行完整模拟（直到达到总步数或手动停止）。
        
        高性能模式：直接循环调用 step()
        标准模式：循环调用 step() + 每隔 N 步更新图表
        交互模式：使用定时器驱动 step()，UI 线程负责暂停/调速
        """
        ...

    def run_single_step(self) -> StepResult:
        """执行一步（用于交互模式的"单步执行"按钮）。"""
        self.is_paused = False
        result = self.step()
        self.is_paused = True
        return result
```

### 2.2 StepResult 数据结构

```python
@dataclass
class StepResult:
    """一个时间步的执行结果。"""
    step: int = 0                    # 当前时间步
    stats: 'StepStats' | None = None # 统计信息
    new_civs_count: int = 0          # 新生文明数
    destroyed_count: int = 0         # 被毁灭文明数
    skipped: bool = False            # 是否因暂停而跳过
    events: list['SimEvent'] = None  # 本步发生的重大事件记录

    @property
    def has_data(self) -> bool:
        return not self.skipped and self.stats is not None


@dataclass
class SimEvent:
    """模拟中的重大事件。"""
    event_type: str       # "birth", "destruction", "contact", "strike"
    civ_id: int           # 相关文明 ID
    detail: str           # 事件描述
    step: int             # 发生的时间步
```

---

## 3. 内部规则调用方法

### 3.1 文明诞生

```python
def _apply_birth_rules(self) -> list[Civilization]:
    """
    按照配置的出生率生成新文明。
    
    逻辑：
    1. 如果当前文明数 >= max_civ_count，跳过
    2. 计算本步应诞生的新文明数：
        base = max(1, int(birth_rate * current_count))
        受 max_civ_count 限制
    3. 随机决定每个新文明的位置：
       - 如果是聚簇模式，参考已有的聚簇中心
       - 否则完全随机
    4. 使用 CivilizationFactory 创建
    """
    if len(self.civilizations) >= self.config.max_civ_count:
        return []

    # 计算新生数量
    target_new = max(1, int(self.config.birth_rate * 
                            len(self.civilizations)))
    target_new = min(target_new,
                     self.config.max_civ_count - len(self.civilizations))

    new_civs = []
    for _ in range(target_new):
        civ = self.factory.create_random(
            civ_id=self.next_id,
            birth_time=self.current_step,
            universe_size=self.config.universe_size
        )
        new_civs.append(civ)
        self.next_id += 1

    return new_civs
```

### 3.2 文明发展

```python
def _apply_development_rules(self) -> None:
    """
    每个文明的发展演化。
    
    逻辑（委托给 rules.tech_bomb 模块）：
    1. 科技点自然增长（与 level 相关，高级增长快）
    2. 人口增长（受能量输出限制，逻辑斯蒂增长模型）
    3. 能量输出增长（与科技点正相关）
    4. 技术爆炸判定：
       - 每个文明每步有 tech_explosion_prob 概率触发
       - 触发条件：科技点达到阈值 + 概率判定通过
       - 触发效果：level +1，各项属性暴涨
    """
    from src.rules.tech_bomb import apply_development
    apply_development(self.civilizations, self.config)
```

### 3.3 扩张

```python
def _apply_expansion_rules(self) -> None:
    """
    文明扩张。
    
    逻辑（委托给 rules.expansion 模块）：
    1. 每个文明的 expansion_radius 根据 level 和 energy_output 增长
    2. 扩张方向偏向随机+资源丰富方向
    3. 扩张可能暴露坐标：
       - 每步根据 stealth 和 expansion 幅度计算暴露概率
       - 暴露后 communication_active = True
    """
    from src.rules.expansion import apply_expansion
    apply_expansion(self.civilizations, self.config)
```

### 3.4 探测与接触

```python
def _apply_detection_rules(self) -> list[ContactEvent]:
    """
    文明之间的探测与接触。
    
    逻辑（委托给 rules.detection 模块）：
    1. 遍历所有文明
    2. 使用 spatial_index.query_neighbors() 查找探测范围内的其他文明
    3. 对于发现的每一对文明，生成 ContactEvent
    4. 考虑 stealth 对探测距离的影响：
       实际探测范围 = detection_range * (1 - target.stealth * 0.5)
    5. 正在通信的文明更容易被探测到
    """
    from src.rules.detection import detect_contacts
    return detect_contacts(
        self.civilizations, self.spatial_index, self.config
    )


@dataclass
class ContactEvent:
    """两个文明之间的接触事件。"""
    civ_a: Civilization
    civ_b: Civilization
    distance: float
```

### 3.5 黑暗森林处理

```python
def _apply_dark_forest_rules(self, contacts: list[ContactEvent]) -> None:
    """
    处理接触事件中的猜疑链和攻击。
    
    逻辑（委托给 rules.dark_forest 模块）：
    对于每个 ContactEvent：
    1. 猜疑链判定：
       - 双方根据 aggressiveness、level 差距、stealth 计算威胁感知
       - 威胁感知超过阈值 → 判定为"敌对"
       - 双方都判定对方为敌对 → 互相攻击
       - 仅一方判定 → 单方面攻击
       - 双方都判定非敌对 → 互相规避
    
    2. 攻击结果：
       - 攻击成功概率 = f(攻击方等级差, 攻击方能量, 防御方隐蔽性)
       - 若成功 → 目标 is_alive = False
       - 若失败 → 可能引发反击
    
    3. 暴露即死亡：
       - 被攻击的文明如果存活，其坐标被暴露
       - 暴露后更容易被其他文明探测到
    """
    from src.rules.dark_forest import apply_dark_forest
    apply_dark_forest(contacts, self.config)
```

### 3.6 黑暗森林打击

```python
def _apply_cosmic_strike(self) -> None:
    """
    宇宙公理级打击事件（二向箔/光粒等）。
    
    逻辑（委托给 rules.dark_forest 模块）：
    1. 每步以 cosmic_strike_prob 的概率触发
    2. 触发时，随机选择一个打击中心 (x, y)
    3. 打击半径内所有文明全部毁灭
    4. 打击区域变为"废墟区域"（记录在案，新文明极低概率在此诞生）
    """
    from src.rules.dark_forest import apply_cosmic_strike
    apply_cosmic_strike(
        self.civilizations, self.spatial_index, self.config
    )
```

### 3.7 清理

```python
def _cleanup_dead_civilizations(self) -> None:
    """
    移除已毁灭的文明。
    
    策略：
    - 从列表中移除 is_alive == False 的文明
    - 重建空间索引
    """
    before = len(self.civilizations)
    self.civilizations = [c for c in self.civilizations if c.is_alive]
    # 不在这里 rebuild，下步开始时 rebuild
```

---

## 4. 保存与读取进度

### 4.1 导出状态

```python
def save_state(self, filepath: str) -> None:
    """
    保存当前模拟状态到文件（JSON 格式）。
    
    保存内容：
    - config（序列化）
    - current_step
    - next_id
    - 所有存活文明的参数
    - 废墟区域列表
    
    用于"断点续跑"功能。
    """
    state = {
        "config": dataclasses.asdict(self.config),
        "current_step": self.current_step,
        "next_id": self.next_id,
        "civilizations": [
            dataclasses.asdict(c) for c in self.civilizations
        ],
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
```

### 4.2 导入状态

```python
@classmethod
def load_state(cls, filepath: str) -> 'Simulation':
    """
    从文件加载模拟状态。
    
    流程：
    1. 读取 JSON
    2. 反序列化 Config
    3. 反序列化 Civilization 列表
    4. 创建 Simulation 实例并设置状态
    5. 重建空间索引
    """
    with open(filepath, "r", encoding="utf-8") as f:
        state = json.load(f)

    config = SimulationConfig(**state["config"])
    sim = cls(config)
    sim.current_step = state["current_step"]
    sim.next_id = state["next_id"]
    sim.civilizations = [
        Civilization(**c) for c in state["civilizations"]
    ]
    sim.spatial_index.rebuild(sim.civilizations)
    return sim
```

---

## 5. 回调机制

```python
def register_step_callback(self, callback: callable) -> None:
    """
    注册每步完成后触发的回调。
    
    回调签名：callback(step_result: StepResult) -> None
    可视化层通过此接口更新图表。
    """
    self._on_step_callbacks.append(callback)

def _notify_step_callbacks(self, stats: StepStats) -> None:
    """触发所有步进回调。"""
    for callback in self._on_step_callbacks:
        callback(stats)
```

---

## 6. 模块的独立可测试性

### 6.1 测试要点

```python
# tests/test_simulation.py

def test_initialize():
    """验证初始化创建了正确数量的文明。"""
    ...

def test_step_increases_step_counter():
    """验证执行一步后时间步加一。"""
    ...

def test_step_birth_increases_count():
    """验证诞生阶段增加了文明数量。"""
    ...

def test_step_destruction_decreases_count():
    """验证毁灭阶段减少了文明数量。"""
    ...

def test_step_max_civ_count_respected():
    """验证文明数不会超过 max_civ_count。"""
    ...

def test_save_and_load_state():
    """验证保存状态后再加载，状态一致。"""
    ...

def test_pause_resume():
    """验证暂停后 step() 返回 skipped=True。"""
    ...

def test_callback_invoked():
    """验证注册的回调被正确触发。"""
    ...
```

---

## 7. 依赖关系

```
simulation.py → entity.py       （使用 Civilization 类型）
simulation.py → config.py       （使用 SimulationConfig）
simulation.py → spatial.py      （使用 SpatialIndex）
simulation.py → rules/*.py      （调用各个规则模块）
simulation.py → output/*.py     （使用 StatsCollector, DataSaver）
```

---

*下一篇：`detailed-design-05-rules.md` — 规则模块详细设计*
