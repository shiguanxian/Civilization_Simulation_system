# 详细设计文档 — 第1部分：总体架构与模块概览

## 1. 文档说明

本文档系列是整个宇宙文明模拟软件的详细设计说明。本篇为总纲，定义软件的整体架构、模块划分、数据流和接口规范。

---

## 2. 总体架构

### 2.1 分层架构

采用**三层架构**，下层为上层提供服务，层内模块高度内聚、层间松耦合：

```
┌─────────────────────────────────────────────────────────┐
│                    应用层 (Application)                   │
│  main.py / cli.py / batch_runner.py                     │
│  命令行解析、模式选择、批处理调度                           │
├─────────────────────────────────────────────────────────┤
│                     可视化层 (Visualization)              │
│  plotter.py / interactive.py                            │
│  实时图表、交互控制、文明详情查看                          │
├─────────────────────────────────────────────────────────┤
│                     核心层 (Core)                        │
│  ┌──────────┐ ┌────────────┐ ┌───────────────────┐     │
│  │ config   │ │ simulation │ │ rules             │     │
│  │ .py      │ │ .py        │ │ ├ dark_forest.py  │     │
│  │          │ │            │ │ ├ tech_bomb.py    │     │
│  │          │ │            │ │ ├ expansion.py    │     │
│  │          │ │            │ │ └ detection.py    │     │
│  └──────────┘ └────────────┘ └───────────────────┘     │
│  ┌──────────┐ ┌────────────┐ ┌───────────────────┐     │
│  │ entity   │ │ spatial    │ │ output            │     │
│  │ .py      │ │ .py        │ │ ├ data_saver.py   │     │
│  │          │ │            │ │ └ stats.py        │     │
│  │          │ │            │ │                   │     │
│  └──────────┘ └────────────┘ └───────────────────┘     │
└─────────────────────────────────────────────────────────┘
```

### 2.2 模块一览

| 模块 | 文件 | 职责 |
|------|------|------|
| **entity** | `src/entity.py` | 文明类 `Civilization` 定义，纯数据容器 |
| **config** | `src/config.py` | 全局配置、参数校验、性能检测 |
| **spatial** | `src/spatial.py` | 空间索引（网格索引），加速距离查询 |
| **simulation** | `src/simulation.py` | 模拟引擎，管理时间步推进、生命周期 |
| **rules.dark_forest** | `src/rules/dark_forest.py` | 猜疑链、打击即毁灭、暴露即死亡等规则 |
| **rules.tech_bomb** | `src/rules/tech_bomb.py` | 技术爆炸规则 |
| **rules.expansion** | `src/rules/expansion.py` | 文明扩张规则 |
| **rules.detection** | `src/rules/detection.py` | 探测与接触规则 |
| **output.data_saver** | `src/output/data_saver.py` | 数据文件保存（CSV） |
| **output.stats** | `src/output/stats.py` | 统计计算 |
| **visualization.plotter** | `src/visualization/plotter.py` | 实时图表绘制 |
| **visualization.interactive** | `src/visualization/interactive.py` | 交互模式 GUI |
| **cli** | `src/cli.py` | 命令行参数解析 |
| **batch** | `src/batch.py` | 批处理模式 |
| **main** | `main.py` | 程序入口 |

---

## 3. 项目文件结构

```
simulation-game/
├── main.py                        # 程序入口
├── pyproject.toml
├── README.md
├── doc/
│   ├── proposal.md                # 需求文档
│   ├── detailed-design-01-overview.md        # 本文档
│   ├── detailed-design-02-entity-config.md   # 实体与配置
│   ├── detailed-design-03-spatial-index.md   # 空间索引
│   ├── detailed-design-04-simulation.md      # 模拟引擎
│   ├── detailed-design-05-rules.md           # 规则模块
│   ├── detailed-design-06-output-stats.md    # 输出与统计
│   ├── detailed-design-07-visualization.md   # 可视化
│   └── detailed-design-08-cli-batch.md       # CLI与批处理
├── src/
│   ├── __init__.py
│   ├── entity.py
│   ├── config.py
│   ├── spatial.py
│   ├── simulation.py
│   ├── cli.py
│   ├── batch.py
│   ├── rules/
│   │   ├── __init__.py
│   │   ├── dark_forest.py
│   │   ├── tech_bomb.py
│   │   ├── expansion.py
│   │   └── detection.py
│   ├── output/
│   │   ├── __init__.py
│   │   ├── data_saver.py
│   │   └── stats.py
│   └── visualization/
│       ├── __init__.py
│       ├── plotter.py
│       └── interactive.py
├── tests/
│   ├── __init__.py
│   ├── test_entity.py
│   ├── test_config.py
│   ├── test_spatial.py
│   ├── test_simulation.py
│   ├── test_rules_dark_forest.py
│   ├── test_rules_tech_bomb.py
│   ├── test_rules_expansion.py
│   ├── test_rules_detection.py
│   ├── test_output_stats.py
│   └── test_output_data_saver.py
└── output/                        # 运行时自动生成
    └── .gitkeep
```

---

## 4. 核心数据流

### 4.1 单步模拟数据流

```
            ┌──────────────┐
            │  Config      │  全局配置（单例）
            │  (global)    │
            └──────┬───────┘
                   │ 读取参数
                   ▼
  ┌──────────────────────────────────────────┐
  │           Simulation.step()              │
  │                                          │
  │  1. ──► rules.birth()                   │
  │         新文明诞生                       │
  │                                          │
  │  2. ──► rules.development()             │
  │         文明内政发展 + 技术爆炸判定       │
  │                                          │
  │  3. ──► rules.expansion()               │
  │         扩张 + 坐标暴露判定              │
  │                                          │
  │  4. ──► rules.detection()               │
  │         使用 spatial 索引查询邻近文明     │
  │         触发接触事件列表                 │
  │                                          │
  │  5. ──► rules.dark_forest()             │
  │         处理猜疑链、攻击、毁灭            │
  │                                          │
  │  6. ──► rules.cosmic_strike()           │
  │         黑暗森林打击（低概率全局事件）    │
  │                                          │
  │  7. ──► output.stats().collect()        │
  │         清理死亡文明 + 收集统计数据      │
  │                                          │
  │  8. ──► output.data_saver().save()      │
  │         保存本步数据 + 汇总              │
  └──────────────────────────────────────────┘
                   │
                   ▼
  ┌──────────────────────────────────────────┐
  │  可视化层（标准/交互模式）                │
  │  plotter.update()                        │
  │  或 interactive.update()                 │
  └──────────────────────────────────────────┘
```

### 4.2 三种运行模式的数据流差异

| 阶段 | 高性能模式 | 标准模式 | 交互模式 |
|------|-----------|---------|---------|
| 核心模拟 | ✅ 全速运行 | ✅ 运行 | ✅ 运行 |
| 终端输出 | ✅ 每步打印 | ✅ 每步打印 | ✅ 每步打印 |
| 数据保存 | ✅ 保存 | ✅ 保存 | ✅ 保存 |
| 图表更新 | ❌ 跳过 | ✅ 每N步更新 | ✅ 每步更新 |
| 交互控制 | ❌ 无 | ❌ 无 | ✅ 可暂停/调速/查看 |

---

## 5. 模块间接口规范

所有模块通过**显式参数传递**交互，禁止使用全局变量（Config 除外，Config 作为只读全局配置）。

### 5.1 核心接口签名（伪代码）

```
# Simulation 对外接口
class Simulation:
    def __init__(self, config: SimulationConfig)
    def initialize(self) -> None
    def step(self) -> StepResult
    def get_state(self) -> SimulationState

# 规则模块接口（每个规则模块遵循相同签名）
class BaseRule:
    def apply(self, universe: list[Civilization], 
              spatial_index: SpatialIndex, 
              config: SimulationConfig) -> RuleResult

# 空间索引接口
class SpatialIndex:
    def __init__(self, universe_size: float, cell_size: float)
    def rebuild(self, civilizations: list[Civilization]) -> None
    def query_neighbors(self, pos: tuple[float, float], 
                        radius: float) -> list[Civilization]
    def query_region(self, x_min, x_max, y_min, y_max) -> list[Civilization]

# 统计接口
class StatsCollector:
    def collect(self, universe: list[Civilization], step: int) -> StepStats
    def summary(self) -> SummaryStats

# 数据保存接口
class DataSaver:
    def save_step(self, stats: StepStats, step: int) -> None
    def save_summary(self, all_stats: list[StepStats]) -> None
```

### 5.2 错误处理约定

- 所有模块函数抛出标准异常，不静默吞错误
- 顶层 `main.py` / `Simulation` 负责捕获和报告
- 性能检测失败不影响模拟运行（降级为默认值 + 告警）

---

## 6. 配置系统设计

### 6.1 配置优先级

```
命令行参数  >  配置文件（pyproject.toml 中 [tool.simulation] 节）  >  代码默认值
```

### 6.2 配置分类

| 类别 | 示例 |
|------|------|
| 宇宙参数 | 空间大小、初始文明数、最大文明数 |
| 演化参数 | 文明诞生率、技术爆炸概率、黑暗森林打击概率 |
| 运行参数 | 总步数、运行模式、图表更新间隔 |
| 性能参数 | 网格单元大小（自动计算推荐值） |
| 输出参数 | 输出目录、保存间隔、是否保存全量数据 |

---

## 7. 测试策略

### 7.1 测试层级

| 层级 | 目标 | 工具 | 示例 |
|------|------|------|------|
| **单元测试** | 每个模块独立测试 | pytest | 测试 Civilization 参数初始化、SpatialIndex 查询正确性 |
| **集成测试** | 规则模块与 Simulation 配合 | pytest | 模拟几步后检查文明数量变化、等级分布 |
| **端到端测试** | 完整流程 | 脚本 | 运行 --fast 模式10步，检查输出文件 |

### 7.2 Mock 策略

- 规则模块的测试：传入构造好的文明列表和 SpatialIndex Mock
- Simulation 的测试：传入 Mock 规则模块，验证调用顺序
- Visualization 的测试：不测试（GUI 难以自动化测试）

---

*下一篇：`detailed-design-02-entity-config.md` — 实体与配置模块详细设计*
