# 输出与统计模块 - 最小可执行任务列表

## 目录：`src/output/`

### 文件清单
- `src/output/__init__.py`
- `src/output/stats.py`       — 统计信息收集
- `src/output/data_saver.py`  — 数据文件保存

---

## 任务清单

### O1. 创建 `src/output/` 包结构
- 创建 `src/output/__init__.py`

### O2. 实现统计模块 (`stats.py`)

- [ ] **O2.1 定义 `StepStats` 数据类**
  - 包含所有统计字段：step, total_civilizations, new_born, destroyed
  - 等级分布：level_distribution, average_level, max_level
  - 科技水平：average_tech_points, total_tech_points, tech_explosions
  - 行为统计：average_aggressiveness, average_stealth, exposed_civilizations
  - 空间分布：average_detection_range, average_expansion_radius
  - 能量与人口：total_energy, total_population, average_energy, average_population
  - 接触与攻击：contacts_count, attacks_count, cosmic_strikes
  - 编写单元测试验证数据结构完整性

- [ ] **O2.2 实现 `StatsCollector` 类**
  - `__init__`：维护 `self.history: list[StepStats]` 历史记录
  - `collect()`：从文明列表收集统计信息
    - 处理空列表情况
    - 计算等级分布、平均值、总值
    - 从 `step_events` 统计增量数据（新生、毁灭、技术爆炸等）
    - 可选从 previous_stats 计算增量
  - `get_latest()`：获取最新统计
  - `get_history_since(step)`：获取指定步数后历史
  - `clear()`：清空历史
  - 编写单元测试验证：空列表、单个文明、多个文明、等级分布、历史记录追加

- [ ] **O2.3 实现终端输出格式化 `format_step_summary()`**
  - 格式化时间步概要信息
  - 包含：存活文明数、新生、毁灭、最高/平均等级、科技爆炸、暴露文明、接触/攻击次数、能量/人口
  - 输出格式整齐对齐
  - 编写单元测试验证输出字符串格式正确

### O3. 实现数据保存模块 (`data_saver.py`)

- [ ] **O3.1 实现 `DataSaver.__init__()` 和目录管理**
  - `__init__`：接收 `SimulationConfig`，创建 `output_dir` 路径
  - `_ensure_output_dir()`：确保输出目录存在（mkdir parents）
  - 编写单元测试验证目录创建

- [ ] **O3.2 实现分步全量数据保存 `save_step()`**
  - `_save_step_full_data()`：保存到 `step_{step:06d}.csv`
  - 高性能模式下每 10 步保存一次（减少 IO）
  - 包含所有核心统计指标的摘要行
  - 编写单元测试验证文件创建和内容正确性

- [ ] **O3.3 实现汇总数据保存**
  - `_init_summary_file()`：初始化 `summary.csv` 文件头
  - `_save_summary_row()`：每步追加一行（包含等级分布分列）
  - 使用 `csv.DictWriter` 写入，每步 flush 确保持久化
  - 编写单元测试验证汇总文件创建和内容正确性

- [ ] **O3.4 实现状态保存 `save_simulation_state()`**
  - 将模拟状态保存为 JSON 文件
  - 包含配置、当前步数、所有文明参数
  - 异常处理：IO 错误不崩溃，仅输出警告
  - 编写单元测试验证 JSON 文件格式正确

- [ ] **O3.5 实现批处理结果保存 `save_batch_summary()`**
  - 将批处理对比结果保存为 CSV
  - 每行对应一次运行
  - 编写单元测试验证

- [ ] **O3.6 实现资源清理 `close()`**
  - 关闭所有打开的文件句柄
  - 确保数据写入磁盘
  - 编写单元测试验证 clean 后文件句柄释放

- [ ] **O3.7 IO 错误容错**
  - 文件写入失败不中断模拟，仅输出告警
  - 编写单元测试验证 IOError 场景
