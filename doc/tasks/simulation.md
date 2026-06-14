# 模拟引擎模块 - 最小可执行任务列表

## 文件：`src/simulation.py`

### 任务清单

- [ ] **SM1. 定义 `Simulation` 类与初始化**
  - `__init__`：接收 `SimulationConfig`，初始化核心状态（current_step, civilizations, next_id）
  - 初始化子模块占位（spatial_index, factory, stats_collector, data_saver）
  - 运行控制状态（is_paused, is_running, speed_multiplier）
  - 回调列表（_on_step_callbacks, _on_pause_callbacks, _on_stop_callbacks）
  - 编写单元测试验证初始化后状态正确

- [ ] **SM2. 实现 `initialize()` 方法**
  - 使用 `CivilizationFactory.create_initial_batch()` 创建初始文明
  - 初始化 `SpatialIndex`（如 cell_size 为 0，调用 `auto_select_cell_size()`）
  - 重建空间索引
  - 初始化 `StatsCollector` 和 `DataSaver`
  - 设置 current_step=0, is_running=True
  - 编写单元测试验证初始化创建了正确数量的文明

- [ ] **SM3. 定义 `StepResult` 和 `SimEvent` 数据结构**
  - `StepResult`：包含 step, stats, new_civs_count, destroyed_count, skipped, events
  - `SimEvent`：包含 event_type, civ_id, detail, step
  - 提供 `has_data` 便捷属性
  - 编写单元测试验证数据结构

- [ ] **SM4. 实现 `step()` 完整流程编排**
  - 阶段 0：暂停检测（is_paused 时返回 skipped=True）
  - 阶段 1：重建空间索引
  - 阶段 2：文明诞生（调用 `_apply_birth_rules()`）
  - 阶段 3：文明发展 + 技术爆炸（调用 `_apply_development_rules()`）
  - 阶段 4：扩张（调用 `_apply_expansion_rules()`）
  - 阶段 5：探测与接触（调用 `_apply_detection_rules()`）
  - 阶段 6：黑暗森林处理（调用 `_apply_dark_forest_rules()`）
  - 阶段 7：宇宙打击（调用 `_apply_cosmic_strike()`）
  - 阶段 8：清理死亡文明（调用 `_cleanup_dead_civilizations()`）
  - 阶段 9：统计与数据保存
  - 阶段 10：推进时间步 + 触发回调
  - 编写单元测试验证：步数增加、文明数量变化、暂停返回 skipped

- [ ] **SM5. 实现各内部规则调用方法**
  - `_apply_birth_rules()`：出生率计算、max_civ_count 限制、创建新文明
  - `_apply_development_rules()`：委托 `rules.tech_bomb.apply_development()`
  - `_apply_expansion_rules()`：委托 `rules.expansion.apply_expansion()`
  - `_apply_detection_rules()`：委托 `rules.detection.detect_contacts()`
  - `_apply_dark_forest_rules()`：委托 `rules.dark_forest.apply_dark_forest()`
  - `_apply_cosmic_strike()`：委托 `rules.dark_forest.apply_cosmic_strike()`
  - `_cleanup_dead_civilizations()`：移除已毁灭文明
  - 编写集成测试验证完整 step 流程

- [ ] **SM6. 实现 `run()` 方法**
  - 循环调用 `step()` 直到达到 total_steps 或 is_running=False
  - 在循环中处理各模式的差异（图表更新速度等）
  - 编写测试验证完整运行流程

- [ ] **SM7. 实现 `run_single_step()` 方法**
  - 用于交互模式的"单步执行"按钮
  - 执行一步后自动暂停
  - 编写单元测试验证

- [ ] **SM8. 实现状态保存与加载**
  - `save_state()`：导出为 JSON（包含 config, current_step, next_id, civilizations）
  - `load_state()` 类方法：从 JSON 加载并重建状态
  - 编写单元测试验证保存再加载后状态一致性

- [ ] **SM9. 实现回调机制**
  - `register_step_callback()`：注册每步完成后回调
  - `_notify_step_callbacks()`：触发所有回调
  - 编写单元测试验证回调被正确触发
