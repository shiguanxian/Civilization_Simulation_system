# 命令行与批处理模块 - 最小可执行任务列表

## 文件清单
- `src/cli.py`     — 命令行参数解析与模式分发
- `src/batch.py`   — 批处理模式运行器
- `main.py`        — 程序主入口

---

## 任务清单

### CB1. 实现命令行接口 (`cli.py`)

- [ ] **CB1.1 构建参数解析器 `build_parser()`**
  - 运行模式互斥组：`--fast` / `--standard` / `--interactive` / `--batch`
  - 宇宙参数：`--size`, `--civs`(`--initial-civs`), `--max-civs`
  - 演化参数：`--steps`, `--birth-rate`
  - 分布模式：`--distribution`(uniform/cluster), `--clusters`
  - 输出控制：`--output-dir`, `--no-step-data`
  - 存档控制：`--load`, `--save-interval`
  - 性能检测：`--detect-only`
  - 名称生成：`--name-mode`(auto/number)
  - 详细帮助信息和示例（epilog）
  - 编写单元测试验证各参数解析正确性

- [ ] **CB1.2 实现 `main()` 主入口函数**
  - 解析命令行参数
  - 调用 `load_config()` 加载配置
  - 调用 `detect_computer_capability()` 性能检测并打印报告
  - `--detect-only` 模式处理（检测后退出）
  - 如果配置要求自动推荐，应用推荐值并检查文明数是否超限
  - 从存档加载或新建模拟
  - 根据模式分发到 `run_fast()` / `run_standard()` / `run_interactive()` / `BatchRunner`
  - 返回退出码（0 正常，非 0 错误）
  - 编写集成测试验证各模式分发

### CB2. 实现批处理模块 (`batch.py`)

- [ ] **CB2.1 定义 `BatchConfig` 和 `BatchRunResult` 数据类**
  - `BatchConfig`: name, runs(list[dict]), output_dir, repeat
  - `BatchRunResult`: run_name, params, repeat_index, final_stats, elapsed_seconds, success, error_message
  - 编写单元测试验证数据结构

- [ ] **CB2.2 实现 `BatchRunner.__init__()`**
  - 从 JSON 文件加载批处理配置
  - 解析 `BatchConfig`
  - 初始化结果列表和基准配置
  - 编写单元测试验证配置加载正确性

- [ ] **CB2.3 实现 `run_all()` 主方法**
  - 遍历每组参数
  - 每组重复 repeat 次
  - 依次调用 `_run_single()`
  - 收集结果
  - 调用 `_save_results()` 保存
  - 调用 `print_summary()` 输出摘要
  - 编写集成测试验证完整批处理运行

- [ ] **CB2.4 实现单次运行 `_run_single()`**
  - 基于基准配置 + 覆盖参数创建配置
  - 强制使用 `--fast` 模式
  - 初始化模拟
  - 运行 `total_steps` 步
  - 收集最终统计信息
  - 计时
  - 异常处理
  - 编写单元测试验证单次运行逻辑

- [ ] **CB2.5 实现结果保存 `_save_results()`**
  - 保存 `batch_summary.csv` 对比表
  - 保存 `batch_results.json` 完整结果
  - 编写单元测试验证文件创建和内容

- [ ] **CB2.6 实现终端摘要 `print_summary()`**
  - 对齐打印所有运行结果（名称、重复次数、耗时、最终文明数、成功状态）
  - 编写单元测试验证输出格式

### CB3. 实现 `main.py` 程序入口

- [ ] **CB3.1 实现 `main.py`**
  - 导入 `src.cli.main` 作为 `cli_main`
  - `sys.exit(cli_main())` 传递退出码
  - `if __name__ == "__main__": main()` 入口保护
  - 编写测试验证入口可正常调用

### CB4. 实现 `pyproject.toml` 配置集成

- [ ] **CB4.1 更新 `pyproject.toml`**
  - 添加 `[tool.simulation]` 配置节（可选覆盖默认值）
  - 添加 ruff 和 mypy 配置
  - 添加 pytest 配置
  - 编写单元测试验证 TOML 配置读取正确
