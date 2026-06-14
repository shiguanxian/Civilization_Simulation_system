# 实体模块 - 最小可执行任务列表

## 文件：`src/entity.py`

### 任务清单

- [ ] **E1. 定义 `Civilization` 数据类**
  - 使用 `@dataclass` 装饰器
  - 包含全部 16 个字段（id, name, x, y, level, tech_points, tech_explosion_prob, expansion_radius, population, energy_output, aggressiveness, stealth, detection_range, is_alive, birth_time, communication_active）
  - 所有字段标注完整类型注解
  - 为数值字段提供合理的默认值
  - 编写对应单元测试 `tests/test_entity.py` 检查字段默认值

- [ ] **E2. 定义 `NameGenerator` 类**
  - 实现两种模式: `"auto"`（词库组合）和 `"number"`（纯数字编号）
  - 预设前缀词库（阿尔法、贝塔、伽马等）和后缀词库（仙座、星系、星云等）
  - `auto` 模式先用词库组合，用完后 fallback 到数字编号
  - 编写单元测试验证两种模式的名称生成

- [ ] **E3. 定义 `CivilizationFactory` 类**
  - `__init__` 接收 `SimulationConfig` 和 `NameGenerator`
  - `create_random()` 方法：随机位置 + 随机初始参数生成文明
  - `create_initial_batch()` 方法：根据配置生成初始文明批次
  - 支持均匀随机分布和聚簇分布两种模式
  - 位置生成考虑环形宇宙坐标
  - 编写单元测试验证文明参数在合理范围内、初始批次数量正确

- [ ] **E4. 确保无业务逻辑侵入**
  - `Civilization` 类只包含数据，不包含任何业务逻辑方法
  - 验证所有业务逻辑规则在 `rules/` 目录下实现
  - 编写测试验证 `Civilization` 的行为符合纯数据容器定义
