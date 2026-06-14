# 详细设计文档 — 第8部分：命令行接口与批处理模块

## 1. 模块概述

### 1.1 模块职责

| 文件 | 类/函数 | 职责 |
|------|---------|------|
| `src/cli.py` | `parse_args()`, `main()` | 命令行参数解析，运行模式分发 |
| `src/batch.py` | `BatchRunner` | 批处理模式：多组参数依次运行，结果对比 |
| `main.py` | `entry point` | 程序入口，调用 cli.main() |

---

## 2. 命令行接口模块 (`src/cli.py`)

### 2.1 参数设计

```python
import argparse


def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="宇宙文明模拟器",
        description="模拟二维宇宙中智慧文明的黑暗森林演化",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  uv run python main.py --fast                  # 高性能模式
  uv run python main.py --standard              # 标准模式（默认）
  uv run python main.py --interactive           # 交互模式
  uv run python main.py --fast --steps 500      # 只跑500步
  uv run python main.py --fast --civs 10000     # 10000个初始文明
  uv run python main.py --batch batch_config.json   # 批处理模式
  uv run python main.py --load state.json       # 从存档继续
  uv run python main.py --detect-only           # 只检测性能，不运行
        """
    )

    # ── 运行模式（互斥） ──
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--fast", action="store_true",
        help="高性能模式（仅终端输出，无图表）"
    )
    mode_group.add_argument(
        "--standard", action="store_true", default=True,
        help="标准模式（显示实时图表，默认）"
    )
    mode_group.add_argument(
        "--interactive", action="store_true",
        help="交互模式（图形界面控制面板 + 图表）"
    )
    mode_group.add_argument(
        "--batch", type=str, metavar="CONFIG_FILE",
        help="批处理模式，传入 JSON 配置文件路径"
    )

    # ── 宇宙参数 ──
    parser.add_argument(
        "--size", type=float, metavar="L",
        help="宇宙空间边长（光年），默认 10000"
    )
    parser.add_argument(
        "--civs", "--initial-civs", type=int, metavar="N",
        dest="initial_civ_count",
        help="初始文明数量，默认 5000"
    )
    parser.add_argument(
        "--max-civs", type=int, metavar="N",
        help="最大文明数量上限"
    )

    # ── 演化参数 ──
    parser.add_argument(
        "--steps", type=int, metavar="N",
        help="总模拟步数，默认 1000"
    )
    parser.add_argument(
        "--birth-rate", type=float, metavar="R",
        help="文明诞生率，默认 0.05"
    )

    # ── 分布模式 ──
    parser.add_argument(
        "--distribution", choices=["uniform", "cluster"],
        help="初始文明分布模式: uniform（均匀）/ cluster（聚簇）"
    )
    parser.add_argument(
        "--clusters", type=int, metavar="N",
        help="聚簇数量（聚簇模式下使用）"
    )

    # ── 输出控制 ──
    parser.add_argument(
        "--output-dir", type=str, metavar="DIR",
        help="输出目录，默认 output/"
    )
    parser.add_argument(
        "--no-step-data", action="store_true",
        help="不保存每步全量数据"
    )

    # ── 存档控制 ──
    parser.add_argument(
        "--load", type=str, metavar="STATE_FILE",
        help="从保存的状态文件加载并继续模拟"
    )
    parser.add_argument(
        "--save-interval", type=int, metavar="N",
        help="每隔 N 步自动保存状态，默认 0（不自动保存）"
    )

    # ── 性能检测 ──
    parser.add_argument(
        "--detect-only", action="store_true",
        help="只检测计算机性能并推荐参数，不运行模拟"
    )

    # ── 名称生成 ──
    parser.add_argument(
        "--name-mode", choices=["auto", "number"],
        help="文明名称生成模式: auto（词库+数字）/ number（纯数字）"
    )

    return parser
```

### 2.2 主入口函数

```python
def main(argv: list[str] | None = None) -> int:
    """
    程序主入口。
    
    返回值：0 表示正常退出，非 0 表示错误。
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    # ── 1. 加载配置 ──
    config = load_config(args)

    # ── 2. 性能检测 ──
    cap = detect_computer_capability()
    print(cap.format_report())

    if args.detect_only:
        print("\n（仅检测模式，模拟未运行）")
        return 0

    # 如果配置要求自动推荐，应用推荐值
    if config.spatial_grid_cell_size == 0:
        recommended = get_recommended_params(cap)
        config.spatial_grid_cell_size = recommended.recommended_grid_size
        if config.initial_civ_count > recommended.recommended_civ_count:
            print(
                f"[提示] 初始文明数量 {config.initial_civ_count} "
                f"超过推荐值 {recommended.recommended_civ_count}，"
                f"可能影响性能"
            )

    # ── 3. 初始化模拟 ──
    from src.simulation import Simulation
    from src.entity import CivilizationFactory, NameGenerator
    from src.spatial import SpatialIndex

    if args.load:
        # 从存档加载
        simulation = Simulation.load_state(args.load)
        print(f"已从 {args.load} 加载状态，继续模拟...")
    else:
        simulation = Simulation(config)
        simulation.initialize()
        print("模拟初始化完成。")

    # ── 4. 根据模式运行 ──
    if args.fast or config.run_mode == "fast":
        from src.visualization.plotter import run_fast
        run_fast(simulation, config)
    elif args.interactive or config.run_mode == "interactive":
        from src.visualization.interactive import run_interactive
        run_interactive(simulation, config)
    else:
        from src.visualization.plotter import run_standard
        run_standard(simulation, config)

    # ── 5. 完成 ──
    print(f"\n模拟完成！数据已保存至: {config.output_dir}/")
    return 0
```

### 2.3 使用示例汇总

```bash
# 基本用法
uv run python main.py                         # 标准模式，默认参数
uv run python main.py --fast                  # 高性能模式
uv run python main.py --interactive           # 交互模式

# 自定义参数
uv run python main.py --fast --civs 8000 --steps 500 --size 20000
uv run python main.py --interactive --distribution cluster --clusters 30

# 从存档继续
uv run python main.py --load output/state_20240101_120000.json

# 仅检测性能
uv run python main.py --detect-only

# 批处理
uv run python main.py --batch batch_configs/experiment_1.json
```

---

## 3. 批处理模块 (`src/batch.py`)

### 3.1 设计思路

批处理模式用于一次性运行多组不同参数的模拟，便于对比分析。

```
输入：JSON 配置文件（指定多组参数）
               │
               ▼
     ┌─────────────────────┐
     │    BatchRunner      │
     │                     │
     │ 对于每组参数:       │
     │  1. 创建 Config     │
     │  2. 初始化模拟      │
     │  3. 运行（--fast）  │
     │  4. 收集最终结果    │
     │  5. 保存到文件      │
     └─────────────────────┘
               │
               ▼
输出：output/batch_summary.csv
      （每组一行，含参数和最终统计）
```

### 3.2 BatchRunner 类设计

```python
import json
import copy
import time
from pathlib import Path
from dataclasses import dataclass


@dataclass
class BatchConfig:
    """一次批处理运行的完整配置。"""
    name: str                                 # 本次运行的名称标识
    runs: list[dict]                          # 多组参数（覆盖 SimulationConfig 字段）
    output_dir: str = "output/batch"          # 批处理输出目录
    repeat: int = 1                           # 每组参数重复次数（用于统计稳定性）


@dataclass
class BatchRunResult:
    """一次运行的结果。"""
    run_name: str
    params: dict
    repeat_index: int
    final_stats: dict                         # 最终步的 StepStats 的字典表示
    elapsed_seconds: float
    success: bool
    error_message: str = ""


class BatchRunner:
    """
    批处理运行器。
    
    按配置依次运行多组模拟，收集结果并保存。
    所有运行使用 --fast 模式（无图表）。
    """

    def __init__(self, config_path: str):
        """
        从 JSON 文件加载批处理配置。
        
        JSON 格式示例：
        {
            "name": "文明初始数量对比实验",
            "output_dir": "output/batch/exp1",
            "repeat": 3,
            "runs": [
                {"name": "稀疏", "initial_civ_count": 1000, "birth_rate": 0.03},
                {"name": "中等", "initial_civ_count": 5000, "birth_rate": 0.05},
                {"name": "密集", "initial_civ_count": 10000, "birth_rate": 0.08}
            ]
        }
        """
        with open(config_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        self.config = BatchConfig(**raw)
        self.results: list[BatchRunResult] = []
        self._base_config = SimulationConfig()

    def run_all(self) -> list[BatchRunResult]:
        """
        运行所有参数组合。
        
        流程：
        1. 对每组参数
        2. 重复 repeat 次
        3. 创建 Simulation，初始化，运行
        4. 收集最终结果
        """
        for run_params in self.config.runs:
            run_name = run_params.pop("name", "unnamed")
            
            for i in range(self.config.repeat):
                print(f"\n{'='*60}")
                print(f"运行: {run_name} (第 {i+1}/{self.config.repeat} 次)")
                print(f"{'='*60}")
                
                result = self._run_single(run_name, run_params, i)
                self.results.append(result)
                
                if result.success:
                    print(f"  完成，耗时 {result.elapsed_seconds:.2f}s")
                else:
                    print(f"  失败: {result.error_message}")

        # 保存汇总结果
        self._save_results()
        return self.results

    def _run_single(self, run_name: str, params: dict,
                    repeat_index: int) -> BatchRunResult:
        """运行一组参数的单次模拟。"""
        start_time = time.time()

        try:
            # 创建配置（基于基础配置 + 覆盖参数）
            config = copy.deepcopy(self._base_config)
            for key, value in params.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            config.run_mode = "fast"  # 批处理强制使用高性能模式

            # 初始化模拟
            from src.simulation import Simulation
            simulation = Simulation(config)
            simulation.initialize()

            # 运行
            for _ in range(config.total_steps):
                simulation.step()

            # 收集最终统计
            final_stats = simulation.stats_collector.get_latest()
            
            elapsed = time.time() - start_time
            return BatchRunResult(
                run_name=run_name,
                params=params,
                repeat_index=repeat_index,
                final_stats=dataclasses.asdict(final_stats) 
                    if final_stats else {},
                elapsed_seconds=elapsed,
                success=True,
            )

        except Exception as e:
            elapsed = time.time() - start_time
            return BatchRunResult(
                run_name=run_name,
                params=params,
                repeat_index=repeat_index,
                final_stats={},
                elapsed_seconds=elapsed,
                success=False,
                error_message=str(e),
            )

    def _save_results(self) -> None:
        """保存批处理结果。"""
        if not self.results:
            return

        # 保存为 CSV 格式的对比表
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 参数对比表
        rows = []
        for r in self.results:
            row = {
                "run_name": r.run_name,
                "repeat": r.repeat_index + 1,
                "elapsed_seconds": f"{r.elapsed_seconds:.2f}",
                "success": r.success,
            }
            if r.success and r.final_stats:
                row.update({
                    "final_civ_count": r.final_stats.get("total_civilizations", 0),
                    "avg_level": r.final_stats.get("average_level", 0),
                    "max_level": r.final_stats.get("max_level", 0),
                    "total_energy": r.final_stats.get("total_energy", 0),
                    "total_population": r.final_stats.get("total_population", 0),
                })
            else:
                row.update({
                    "final_civ_count": 0,
                    "error": r.error_message,
                })
            rows.append(row)

        # 保存 CSV
        import csv
        filepath = output_dir / "batch_summary.csv"
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            if rows:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)

        # 同时保存 JSON 完整结果
        json_path = output_dir / "batch_results.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump([
                dataclasses.asdict(r) for r in self.results
            ], f, indent=2, ensure_ascii=False, default=str)

        print(f"\n批处理结果已保存至: {output_dir}/")

    def print_summary(self) -> None:
        """打印批处理结果摘要到终端。"""
        print("\n" + "=" * 60)
        print("批处理结果汇总")
        print("=" * 60)
        print(f"{'名称':<20} {'重复':<6} {'耗时(s)':<10} {'最终文明数':<12} {'成功':<6}")
        print("-" * 60)

        for r in self.results:
            status = "✅" if r.success else "❌"
            civ_count = r.final_stats.get("total_civilizations", "-") if r.success else "-"
            print(f"{r.run_name:<20} {r.repeat_index+1:<6} {r.elapsed_seconds:<10.2f} {civ_count:<12} {status:<6}")
```

### 3.3 批处理配置文件示例

```json
{
    "name": "初始文明数量影响实验",
    "output_dir": "output/batch/population_experiment",
    "repeat": 3,
    "runs": [
        {
            "name": "低密度-1000",
            "initial_civ_count": 1000,
            "max_civ_count": 5000,
            "birth_rate": 0.03,
            "total_steps": 200
        },
        {
            "name": "中密度-5000",
            "initial_civ_count": 5000,
            "max_civ_count": 20000,
            "birth_rate": 0.05,
            "total_steps": 200
        },
        {
            "name": "高密度-10000",
            "initial_civ_count": 10000,
            "max_civ_count": 50000,
            "birth_rate": 0.08,
            "total_steps": 200
        }
    ]
}
```

---

## 4. main.py 入口

```python
"""
宇宙文明模拟器 — 主入口

使用方式：
  uv run python main.py --help
  uv run python main.py --fast
  uv run python main.py --standard
  uv run python main.py --interactive
  uv run python main.py --batch config.json
"""

import sys


def main():
    """程序入口。"""
    from src.cli import main as cli_main
    sys.exit(cli_main())


if __name__ == "__main__":
    main()
```

---

## 5. 模块的独立可测试性

### 5.1 测试要点

```python
# tests/test_cli.py

def test_parse_args_default():
    """验证默认参数解析正确。"""
    args = parse_args(["--fast"])
    assert args.fast == True

def test_parse_args_custom():
    """验证自定义参数解析正确。"""
    args = parse_args(["--fast", "--civs", "8000", "--steps", "500"])
    assert args.initial_civ_count == 8000
    assert args.steps == 500

def test_parse_args_mutually_exclusive():
    """验证互斥参数正确处理。"""
    ...


# tests/test_batch.py

def test_batch_config_loading(tmp_path):
    """验证批处理配置加载正确。"""
    config_file = tmp_path / "batch_config.json"
    config_file.write_text(json.dumps({
        "name": "test",
        "runs": [{"name": "run1", "initial_civ_count": 1000}]
    }))
    runner = BatchRunner(str(config_file))
    assert runner.config.name == "test"
    assert len(runner.config.runs) == 1

def test_batch_run_single():
    """验证单次批处理运行正常。"""
    ...

def test_batch_results_saved(tmp_path):
    """验证批处理结果被保存。"""
    ...
```

---

## 6. 依赖关系

```
cli.py    → config.py（使用 load_config）
cli.py    → simulation.py（使用 Simulation）
cli.py    → visualization/*.py（调用各模式主循环）
cli.py    → batch.py（调用 BatchRunner）

batch.py  → config.py（使用 SimulationConfig）
batch.py  → simulation.py（使用 Simulation）
```

---

*至此，8 篇详细设计文档全部完成。*
