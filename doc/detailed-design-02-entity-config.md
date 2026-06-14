# 详细设计文档 — 第2部分：实体模块与配置模块

## 1. 实体模块 (`src/entity.py`)

### 1.1 模块职责

- 定义 `Civilization` 类——文明的数据容器
- 定义 `CivilizationFactory` 类——批量创建文明
- 提供文明参数的校验逻辑

### 1.2 Civilization 类设计

```python
@dataclass
class Civilization:
    """一个文明的所有参数。纯数据容器，不包含业务逻辑。"""
    # === 标识 ===
    id: int                         # 唯一标识，由 Simulation 分配
    name: str                       # 文明名称

    # === 空间位置 ===
    x: float                        # 二维 X 坐标（光年）
    y: float                        # 二维 Y 坐标（光年）

    # === 发展水平 ===
    level: int                      # 文明等级 1~5
    tech_points: float              # 科技点数
    tech_explosion_prob: float      # 技术爆炸概率（0~1）

    # === 规模与能量 ===
    expansion_radius: float         # 扩张半径（光年）
    population: float               # 人口规模
    energy_output: float            # 能量输出

    # === 行为倾向 ===
    aggressiveness: float           # 攻击性（0~1）
    stealth: float                  # 隐蔽性（0~1）
    detection_range: float          # 探测范围（光年）

    # === 状态 ===
    is_alive: bool                  # 是否存活
    birth_time: int                 # 诞生时间步
    communication_active: bool      # 是否正在主动通信
```

**设计决策说明**：

1. **使用 `@dataclass`**：Python 原生数据类，自动生成 `__init__`、`__repr__`、`__eq__` 等，代码简洁且性能良好
2. **不使用 `NamedTuple`**：`dataclass` 更灵活，支持默认值、可变字段
3. **类型注解完整**：便于 mypy 静态类型检查

### 1.3 CivilizationFactory 类设计

```python
class CivilizationFactory:
    """文明工厂，负责按照配置生成文明实例。"""

    def __init__(self, config: 'SimulationConfig', 
                 name_generator: 'NameGenerator'):
        self.config = config
        self.name_generator = name_generator

    def create_random(self, civ_id: int, 
                      birth_time: int,
                      universe_size: float,
                      cluster_center: tuple[float, float] | None = None,
                      cluster_radius: float | None = None) -> Civilization:
        """
        在宇宙中随机位置生成一个文明。
        
        参数：
            civ_id: 文明唯一 ID
            birth_time: 当前时间步
            universe_size: 宇宙空间边长（光年）
            cluster_center: 聚簇中心（如果启用聚簇分布）
            cluster_radius: 聚簇半径（如果启用聚簇分布）
        """
        ...

    def create_initial_batch(self, universe_size: float) -> list[Civilization]:
        """
        创建初始文明批次。
        根据 config.initial_civ_count 和 config.initial_distribution_mode
        决定是均匀随机分布还是聚簇分布。
        """
        ...

    def _random_position(self, universe_size: float,
                         cluster_center, cluster_radius) -> tuple[float, float]:
        """生成随机位置（支持环形宇宙坐标）。"""
        ...

    def _random_initial_params(self) -> dict:
        """根据配置的范围随机生成文明初始参数。"""
        ...
```

### 1.4 NameGenerator 类设计

```python
class NameGenerator:
    """文明名称生成器。"""

    # 预设词库
    PREFIXES = ["阿尔法", "贝塔", "伽马", "德尔塔", "伊普西龙",
                "泽塔", "伊塔", "西塔", "约塔", "卡帕"]
    SUFFIXES = ["仙座", "星系", "星云", "星域", "星团",
                "恒星系", "星区", "星环"]

    def __init__(self, mode: str = "auto"):
        """
        mode:
          - "auto": 先用词库，词库用完后切换到数字编号
          - "number": 纯数字编号
        """
        self.mode = mode
        self._prefix_index = 0
        self._suffix_index = 0

    def generate(self, civ_id: int) -> str:
        """生成文明名称。"""
        if self.mode == "number":
            return f"文明 #{civ_id:06d}"
        else:
            return self._generate_named(civ_id)

    def _generate_named(self, civ_id: int) -> str:
        """从词库组合生成名称，用完后 fallback 到数字编号。"""
        ...
```

---

## 2. 配置模块 (`src/config.py`)

### 2.1 模块职责

- 定义 `SimulationConfig` —— 全局配置数据类
- 提供 `detect_computer_capability()` —— 性能检测
- 提供 `get_recommended_params()` —— 根据性能推荐模拟参数
- 提供 `parse_config()` —— 从命令行参数 + pyproject.toml 合并配置

### 2.2 SimulationConfig 类设计

```python
@dataclass
class SimulationConfig:
    """模拟全局配置。在模拟开始前确定，运行时只读。"""

    # ============ 宇宙参数 ============
    universe_size: float = 10000.0        # 宇宙空间边长（光年）

    # ============ 文明参数 ============
    initial_civ_count: int = 5000         # 初始文明数量
    max_civ_count: int = 20000            # 最大文明数量（防止性能爆炸）
    initial_distribution_mode: str = "uniform"  
    # "uniform" = 均匀随机, "cluster" = 聚簇分布

    # 聚簇分布参数（仅 distribution_mode = "cluster" 时使用）
    cluster_count: int = 50               # 聚簇数量
    cluster_radius: float = 500.0         # 每个聚簇的半径（光年）

    # ============ 演化参数 ============
    total_steps: int = 1000               # 总模拟步数
    birth_rate: float = 0.05              # 每步新文明诞生概率因子
    tech_explosion_base_prob: float = 0.01  # 技术爆炸基础概率
    cosmic_strike_prob: float = 0.001     # 黑暗森林打击每步概率

    # ============ 文明参数范围（用于随机生成） ============
    level_range: tuple = (1, 3)           # 初始等级范围
    aggressiveness_range: tuple = (0.1, 0.9)
    stealth_range: tuple = (0.1, 0.9)
    detection_range_range: tuple = (50.0, 500.0)  # 探测范围（光年）
    expansion_radius_range: tuple = (10.0, 100.0) # 扩张半径（光年）
    population_range: tuple = (1e6, 1e10)
    energy_output_range: tuple = (1e12, 1e18)

    # ============ 运行参数 ============
    run_mode: str = "standard"  
    # "fast" = 高性能, "standard" = 标准, "interactive" = 交互
    step_interval_seconds: float = 0.1    
    # 交互模式下每步间隔（秒），用户可调速

    # ============ 输出参数 ============
    output_dir: str = "output"
    save_step_data: bool = True            # 是否保存每步全量数据
    save_summary: bool = True              # 是否保存汇总数据
    save_interval: int = 1                 # 每 N 步保存一次
    plot_update_interval: int = 5          # 标准模式下每 N 步更新图表

    # ============ 性能参数 ============
    spatial_grid_cell_size: float = 0.0   
    # 0.0 表示自动计算，由性能检测结果决定
    use_spatial_index: bool = True

    # ============ 名称生成 ============
    name_generator_mode: str = "auto"     
    # "auto" 或 "number"
```

### 2.3 性能检测设计

```python
class ComputerCapability:
    """描述当前电脑计算能力的量化结果。"""
    cpu_score: float          # CPU 基准分数
    memory_gb: float          # 可用内存（GB）
    recommended_civ_count: int    # 推荐的文明数量上限
    recommended_grid_size: float  # 推荐的空间网格单元大小
    estimated_step_time_ms: float # 预估每步耗时（毫秒）


def detect_computer_capability() -> ComputerCapability:
    """
    检测当前电脑计算水平。
    
    检测内容：
    1. CPU 核心数 + 频率（通过 psutil / platform）
    2. 可用的物理内存总量（psutil.virtual_memory()）
    3. 运行一个微型基准测试：
       - 创建 N 个文明对象并执行简单的距离计算
       - 测量耗时，推算大规模模拟的预估时间
    
    返回值：ComputerCapability 结构体
    """
    ...


def get_recommended_params(cap: ComputerCapability) -> SimulationConfig:
    """
    根据性能检测结果推荐模拟参数。
    
    推荐逻辑：
    - 根据内存估算最大文明数（每个文明约 200 bytes）
    - 根据 CPU 分数推荐网格单元大小
    - 根据基准测试估算每步耗时并给出友好提示
    """
    ...


def auto_detect_and_print() -> SimulationConfig:
    """
    完整流程：检测 → 打印 → 返回推荐配置
    
    终端输出示例：
    ┌─────────────────────────────────────────┐
    │   🖥 计算机性能检测报告                    │
    ├─────────────────────────────────────────┤
    │   CPU: Intel Core i7-12700H (14核)      │
    │   内存: 32.0 GB (可用 24.5 GB)           │
    │   CPU基准评分: 8.5/10                    │
    │                                         │
    │   📊 推荐模拟参数:                        │
    │   文明数量上限: 12,000                    │
    │   网格单元大小: 250 光年                  │
    │   预估每步耗时: 45 ms                    │
    │   建议运行模式: standard                  │
    └─────────────────────────────────────────┘
    """
    ...
```

### 2.4 配置加载流程

```python
def load_config(args: argparse.Namespace | None = None) -> SimulationConfig:
    """
    加载配置，优先级：命令行 > pyproject.toml > 默认值
    
    流程：
    1. 创建默认 SimulationConfig
    2. 读取 pyproject.toml 中 [tool.simulation] 节（如果存在），覆盖默认值
    3. 解析命令行参数，覆盖配置
    4. 如果 config.spatial_grid_cell_size == 0.0，自动检测性能并计算推荐值
    5. 返回最终配置
    """
    ...
```

### 2.5 配置的 TOML 格式

```toml
# pyproject.toml 中的模拟配置节
[tool.simulation]
universe_size = 10000.0
initial_civ_count = 5000
max_civ_count = 20000
birth_rate = 0.05
total_steps = 1000
name_generator_mode = "auto"
```

---

## 3. 模块的独立可测试性

### 3.1 entity 模块测试要点

```python
# tests/test_entity.py

def test_civilization_default_values():
    """验证 Civilization 的默认值正确。"""
    ...

def test_civilization_immutable_no_business():
    """验证 Civilization 只包含数据，不包含业务逻辑方法。"""
    ...

def test_factory_create_random():
    """验证 CivilizationFactory.create_random() 返回的文明参数在合理范围内。"""
    ...

def test_factory_initial_batch_count():
    """验证 create_initial_batch 生成正确数量的文明。"""
    ...

def test_name_generator_mode_number():
    """验证数字编号模式生成正确格式的名称。"""
    ...

def test_name_generator_mode_auto():
    """验证 auto 模式先用词库后用数字。"""
    ...
```

### 3.2 config 模块测试要点

```python
# tests/test_config.py

def test_default_config():
    """验证默认配置的合理性。"""
    ...

def test_config_from_toml():
    """验证从 pyproject.toml 读取配置。"""
    ...

def test_detect_computer_capability_runs():
    """验证性能检测函数能正常执行且返回合理值。"""
    ...

def test_get_recommended_params():
    """验证根据性能推荐参数在合理范围内。"""
    ...
```

---

## 4. 依赖关系

```
entity.py     → 无依赖（纯数据类）
config.py     → psutil, platform, json/tomllib
```

`entity.py` 不依赖任何其他模块，可以独立测试。
`config.py` 只依赖标准库和 psutil，可以独立测试。

---

*下一篇：`detailed-design-03-spatial-index.md` — 空间索引模块详细设计*
