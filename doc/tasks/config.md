# 配置模块 - 最小可执行任务列表

## 文件：`src/config.py`

### 任务清单

- [ ] **C1. 定义 `SimulationConfig` 数据类**
  - 所有配置分类定义：宇宙参数、文明参数、演化参数、文明参数范围、运行参数、输出参数、性能参数、名称生成参数
  - 每个字段提供合理的默认值（如 universe_size=10000.0, initial_civ_count=5000 等）
  - 添加规则模块所需配置（tech_growth_base, pop_growth_rate, energy_growth_rate, expansion_rate_base, base_exposure_prob, attack_threshold, flee_threshold 等）
  - 添加完善类型注解
  - 编写单元测试验证默认配置合理性

- [ ] **C2. 实现 `ComputerCapability` 数据结构**
  - 定义包含 cpu_score, memory_gb, recommended_civ_count, recommended_grid_size, estimated_step_time_ms 的数据结构
  - 编写单元测试验证初始化逻辑

- [ ] **C3. 实现 `detect_computer_capability()` 性能检测**
  - 使用 `psutil` 获取 CPU 核心数、频率、可用物理内存
  - 使用 `platform` 获取系统信息（非必须，用于友好显示）
  - 运行微型基准测试：创建 N 个文明对象并执行简单的距离计算，测量耗时
  - 推算大规模模拟的预估每步耗时
  - 错误时降级返回默认值 + 告警（不崩溃）
  - 提供 `format_report()` 方法输出友好报告
  - 编写单元测试验证函数正常执行且返回合理值

- [ ] **C4. 实现 `get_recommended_params()` 推荐参数**
  - 根据可用内存估算最大文明数（每个文明约 200 bytes）
  - 根据 CPU 分数推荐网格单元大小
  - 根据基准测试估算每步耗时并给出友好提示
  - 编写单元测试验证推荐参数在合理范围内

- [ ] **C5. 实现 `load_config()` 配置加载**
  - 读取命令行参数覆盖（通过 `argparse.Namespace`）
  - 可选读取 `pyproject.toml` 中 `[tool.simulation]` 节覆盖默认值
  - 如果 `spatial_grid_cell_size == 0.0`，调用性能检测自动计算推荐值
  - 配置优先级：命令行 > pyproject.toml > 代码默认值
  - 编写单元测试验证配置加载优先级
