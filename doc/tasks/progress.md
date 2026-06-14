# 宇宙文明模拟器 - 总体进度

> 更新时间：初始创建

## 总体进展

- [ ] **实体模块** (`doc/tasks/entity.md` — 4 个子任务)
- [ ] **配置模块** (`doc/tasks/config.md` — 5 个子任务)
- [ ] **空间索引模块** (`doc/tasks/spatial.md` — 7 个子任务)
- [ ] **模拟引擎模块** (`doc/tasks/simulation.md` — 9 个子任务)
- [ ] **规则模块** (`doc/tasks/rules.md` — 17 个子任务)
- [ ] **输出与统计模块** (`doc/tasks/output.md` — 11 个子任务)
- [ ] **可视化模块** (`doc/tasks/visualization.md` — 20 个子任务)
- [ ] **命令行与批处理模块** (`doc/tasks/cli-batch.md` — 14 个子任务)

---

## 详细任务计数

| 模块 | 文件 | 子任务数 |
|------|------|---------|
| 实体 | `entity.md` | 4 |
| 配置 | `config.md` | 5 |
| 空间索引 | `spatial.md` | 7 |
| 模拟引擎 | `simulation.md` | 9 |
| 规则 | `rules.md` | 17 |
| 输出与统计 | `output.md` | 11 |
| 可视化 | `visualization.md` | 20 |
| 命令行与批处理 | `cli-batch.md` | 14 |
| **总计** | | **87** |

---

## 模块依赖关系与推荐开发顺序

```
阶段 1（核心数据层）
  └── entity (无依赖)
  └── config (无外部依赖)
  
阶段 2（底层基础设施）
  └── spatial (依赖 entity, config)
  
阶段 3（业务规则）
  └── rules.tech_bomb (依赖 entity)
  └── rules.expansion (依赖 entity)
  └── rules.detection (依赖 entity, spatial)
  └── rules.dark_forest (依赖 entity, spatial)

阶段 4（引擎与输出）
  └── output.stats (依赖 entity)
  └── output.data_saver (依赖 config)
  └── simulation (依赖所有以上模块)

阶段 5（可视化与交互）
  └── visualization.plotter (依赖 entity, output.stats)
  └── visualization.interactive (依赖 simulation, plotter)

阶段 6（入口与批处理）
  └── cli (依赖 config, simulation, visualization)
  └── batch (依赖 config, simulation)
  └── main.py (依赖 cli)
```

---

## 推荐的实施顺序

### 第1步：实体 + 配置 (独立并行)
```
doc/tasks/entity.md   → 全部
doc/tasks/config.md   → 全部
```

### 第2步：空间索引
```
doc/tasks/spatial.md   → 全部
```

### 第3步：规则模块 (可并行)
```
doc/tasks/rules.md    → R1, R2, R3, R4, R5（按序或并行）
```

### 第4步：输出 + 统计
```
doc/tasks/output.md   → 全部
```

### 第5步：模拟引擎
```
doc/tasks/simulation.md → 全部
```

### 第6步：可视化
```
doc/tasks/visualization.md → 全部
```

### 第7步：命令行 + 批处理
```
doc/tasks/cli-batch.md → 全部
```
