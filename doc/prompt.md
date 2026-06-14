# 宇宙文明模拟器 — Vibe Coding 主 Prompt

## 项目概述

这是一个基于 Python 的模拟软件，将宇宙间智慧文明抽象为二维平面上的"点"，每个点由一组参数描述。通过离散时间步推进，模拟大量文明在"黑暗森林"法则下的诞生、演化、接触与毁灭过程。

灵感来源：刘慈欣《三体 II：黑暗森林》。

---

## 总体架构

三层架构：

```
┌─────────────────────────────────────────────┐
│             应用层 (Application)              │
│  main.py / cli.py / batch_runner.py         │
├─────────────────────────────────────────────┤
│           可视化层 (Visualization)            │
│  plotter.py / interactive.py                │
├─────────────────────────────────────────────┤
│              核心层 (Core)                    │
│  config / entity / spatial / simulation     │
│  rules (tech_bomb / expansion / detection   │
│         / dark_forest)                      │
│  output (stats / data_saver)                │
└─────────────────────────────────────────────┘
```

---

## 技术栈要求

| 组件 | 要求 |
|------|------|
| 语言 | Python ≥ 3.12 |
| 模拟引擎 | 纯 Python（numpy 可选加速矩阵运算） |
| 数据存储 | CSV（csv 标准库） |
| 图表 | matplotlib |
| 图形界面交互 | tkinter（标准库）+ matplotlib widgets |
| 性能检测 | psutil + platform |
| 包管理 | uv |
| 测试 | pytest |
| 代码质量 | ruff + mypy（宽松配置） |
| 数据结构 | dataclasses（标准库） |

所有代码必须：
1. 通过完整的 **pytest 单元测试**
2. 通过 **mypy** 类型检查（宽松模式）
3. 通过 **ruff** 代码规范检查（标准配置）
4. 类型注解完整

---

## 模块依赖关系与开发阶段

```
阶段 1（核心数据层 — 可并行）
  ├── entity     (无依赖)
  └── config     (依赖 psutil)

阶段 2（底层基础设施）
  └── spatial    (依赖 entity, config)

阶段 3（业务规则 — 可并行）
  ├── rules.tech_bomb     (依赖 entity)
  ├── rules.expansion     (依赖 entity)
  ├── rules.detection     (依赖 entity, spatial)
  └── rules.dark_forest   (依赖 entity, spatial)

阶段 4（引擎与输出 — 可并行）
  ├── output.stats        (依赖 entity)
  ├── output.data_saver   (依赖 config)
  └── simulation          (依赖 entity, config, spatial, rules, output)

阶段 5（可视化）
  ├── visualization.plotter       (依赖 entity, output.stats)
  └── visualization.interactive   (依赖 simulation, plotter)

阶段 6（入口与批处理 — 可并行）
  ├── cli          (依赖 config, simulation, visualization)
  ├── batch        (依赖 config, simulation)
  └── main.py      (依赖 cli)
```

---

## Sub-Agent 工作模式

### 工作流程

主 Agent → 按阶段依次分派 Sub-Agent → 每个 Sub-Agent 实现一个最小任务单元 → 编写代码 + 测试 → 代码审查 → 提交

### Sub-Agent 规则

1. **一个 Sub-Agent 只负责一个最小任务单元**（如 E1.定义 Civilization 数据类）
2. 每个 Sub-Agent 必须：
   - 实现功能代码
   - 编写对应的 pytest 单元测试
   - 确保通过 mypy 和 ruff 检查
3. Sub-Agent 完成后通知主 Agent，主 Agent 进行集成验证
4. 整个过程无人工参与

---

## 开发总步骤

```
Step 0: 初始化项目结构（pyproject.toml, 目录结构, .gitignore）
Step 1: 阶段1 — 实体模块（4个任务）+ 配置模块（5个任务）
Step 2: 阶段2 — 空间索引模块（7个任务）
Step 3: 阶段3 — 规则模块（17个任务）
Step 4: 阶段4 — 输出统计（11个任务）+ 模拟引擎（9个任务）
Step 5: 阶段5 — 可视化（20个任务）
Step 6: 阶段6 — CLI与批处理（14个任务）
Step 7: 集成测试与最终验证
```

---

## 项目目录结构

```
simulation-game/
├── main.py                        # 程序入口
├── pyproject.toml
├── README.md
├── doc/
│   ├── proposal.md                # 需求文档
│   ├── prompt.md                  # 本文件
│   ├── detailed-design-*.md       # 详细设计文档（8篇）
│   └── tasks/
│       ├── progress.md            # 总体进度
│       ├── entity.md              # 实体模块任务
│       ├── config.md              # 配置模块任务
│       ├── spatial.md             # 空间索引任务
│       ├── simulation.md          # 模拟引擎任务
│       ├── rules.md               # 规则模块任务
│       ├── output.md              # 输出统计任务
│       ├── visualization.md       # 可视化任务
│       └── cli-batch.md           # CLI与批处理任务
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
│   │   ├── tech_bomb.py
│   │   ├── expansion.py
│   │   ├── detection.py
│   │   └── dark_forest.py
│   ├── output/
│   │   ├── __init__.py
│   │   ├── stats.py
│   │   └── data_saver.py
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
│   ├── test_rules_tech_bomb.py
│   ├── test_rules_expansion.py
│   ├── test_rules_detection.py
│   ├── test_rules_dark_forest.py
│   ├── test_output_stats.py
│   ├── test_output_data_saver.py
│   ├── test_cli.py
│   ├── test_batch.py
│   └── test_main.py
└── output/                        # 运行时自动创建
```

---

## 详细设计文档索引

所有设计细节见以下 8 篇详细设计文档：

| 文档 | 内容 |
|------|------|
| `doc/detailed-design-01-overview.md` | 总体架构、模块划分、数据流、接口规范 |
| `doc/detailed-design-02-entity-config.md` | Civilization 数据类、CivilizationFactory、NameGenerator、SimulationConfig、性能检测 |
| `doc/detailed-design-03-spatial-index.md` | 空间索引、环形宇宙坐标、网格索引实现 |
| `doc/detailed-design-04-simulation.md` | 模拟引擎、step() 流程编排、状态保存/加载 |
| `doc/detailed-design-05-rules.md` | 技术爆炸、扩张、探测、黑暗森林（猜疑链/打击）规则 |
| `doc/detailed-design-06-output-stats.md` | 统计收集、CSV 数据保存、终端格式化 |
| `doc/detailed-design-07-visualization.md` | 实时图表、交互控制面板、三种运行模式 |
| `doc/detailed-design-08-cli-batch.md` | 命令行参数解析、批处理运行器 |

---

## 运行方式

```bash
# 高性能模式
uv run python main.py --fast

# 标准模式（默认）
uv run python main.py --standard

# 交互模式
uv run python main.py --interactive

# 批处理
uv run python main.py --batch batch_config.json

# 仅检测性能
uv run python main.py --detect-only

# 从存档继续
uv run python main.py --load output/state.json

# 或者通过 pyproject.toml 入口
uv run simulation
```

---

## 代码规范

1. **类型注解**：所有函数参数和返回值必须有完整类型注解
2. **文档字符串**：所有公开函数和类必须有 docstring
3. **错误处理**：不静默吞错误，顶层入口负责捕获报告
4. **模块独立性**：模块间通过显式参数传递交互，禁止全局变量（Config 除外）
5. **纯数据类**：Civilization 只包含数据，不包含业务逻辑方法

## Config 配置

`pyproject.toml` 中的 `[tool.simulation]` 节可以覆盖默认配置：

```toml
[tool.simulation]
universe_size = 10000.0
initial_civ_count = 5000
max_civ_count = 20000
birth_rate = 0.05
total_steps = 1000
name_generator_mode = "auto"
```

Config 优先级：**命令行参数 > pyproject.toml > 代码默认值**

---

## 测试要求

1. 每个最小任务单元都有对应的 pytest 测试
2. 单元测试隔离：mock 外部依赖
3. 可视化 GUI 部分不测试，但非 GUI 逻辑（如最近文明查找函数）需要测试
4. 空间索引需要性能基准测试
5. 测试使用 pytest 标准约定

---

## 任务分配总表

所有 87 个最小任务单元分布在以下模块。每个任务对应 `doc/tasks/` 下的子任务条目。

| 模块 | 任务文件 | 任务数 |
|------|---------|-------|
| 实体 | `tasks/entity.md` | 4 |
| 配置 | `tasks/config.md` | 5 |
| 空间索引 | `tasks/spatial.md` | 7 |
| 规则 | `tasks/rules.md` | 17 |
| 模拟引擎 | `tasks/simulation.md` | 9 |
| 输出统计 | `tasks/output.md` | 11 |
| 可视化 | `tasks/visualization.md` | 20 |
| CLI与批处理 | `tasks/cli-batch.md` | 14 |
| **总计** | | **87** |

---

## 开始指令

主 Agent 现在开始在以下开发阶段中工作：

### Step 0：初始化项目

创建项目骨架，包含：
- `pyproject.toml`（含 ruff、mypy、pytest 配置，[tool.simulation] 节，[project.scripts] 入口点 `simulation = "main:main"`）
- `src/` 目录结构（所有 `__init__.py` 文件）
- `tests/` 目录结构（所有 `__init__.py` 文件）
- `README.md` 占位
- `.gitignore`

### Step 1 ~ Step 6：按阶段依次实现

每个阶段内，主 Agent 按照详细设计和任务清单，将每个最小任务单元分配给 Sub-Agent 实现。

每个 Sub-Agent 要读取：
1. 对应的详细设计文档（了解接口和设计细节）
2. 对应的任务清单文件（了解具体任务要求）
3. 本 Prompt（了解全局要求和规范）

Sub-Agent 实现完后，主 Agent 检查代码质量、运行测试验证，然后进入下一个任务。

### Step 7：集成测试与最终验证

运行完整模拟（--fast 模式，50步），验证：
- 程序正常启动和结束
- 输出目录生成正确文件
- 统计数据合理
- 所有测试通过
- ruff 和 mypy 检查无报错
