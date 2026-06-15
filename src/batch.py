"""批量运行模块 —— BatchRunner 用于批量执行模拟并汇总结果。

提供：
- BatchConfig: 批量配置数据类
- BatchRunResult: 单次运行结果数据类
- BatchRunner: 批量运行编排器
"""

from __future__ import annotations

import csv
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from src.config import SimulationConfig

# CLI 参数名 → SimulationConfig 属性名映射（_CLI_MAPPING 的逆映射 + 扩展）
_PARAM_ALIASES: dict[str, str] = {
    "size": "universe_size",
    "civs": "initial_civ_count",
    "steps": "total_steps",
    "birth_rate": "birth_rate",
    "mode": "name_generator_mode",
    "max_civs": "max_civ_count",
    "distribution": "initial_distribution_mode",
    "clusters": "cluster_count",
    "output_dir": "output_dir",
    "name_mode": "name_generator_mode",
    "seed": "seed",
}


def _resolve_param_key(key: str) -> str:
    """将可能的 CLI 风格参数名解析为 SimulationConfig 属性名。

    如果 *key* 直接是 SimulationConfig 的属性则原样返回，
    否则查找 ``_PARAM_ALIASES`` 映射。
    """
    if hasattr(SimulationConfig, key):
        return key
    return _PARAM_ALIASES.get(key, key)


def _apply_params_to_config(
    config: SimulationConfig,
    params: dict[str, Any],
) -> None:
    """将参数字典应用到 SimulationConfig 实例。

    通过 ``_resolve_param_key`` 支持 CLI 风格别名（如 size → universe_size）。
    忽略 config 中不存在的属性。
    """
    for key, value in params.items():
        resolved = _resolve_param_key(key)
        if hasattr(config, resolved) and value is not None:
            setattr(config, resolved, value)


@dataclass
class BatchConfig:
    """批量运行配置。

    Attributes:
        name: 批量运行名称。
        runs: 每次运行的参数字典列表。
        output_dir: 结果输出目录。
        repeat: 每个配置重复运行次数。
    """

    name: str = ""
    runs: list[dict[str, Any]] = field(default_factory=list)
    output_dir: str = "output/batch"
    repeat: int = 1


@dataclass
class BatchRunResult:
    """单次批量运行的结果。

    Attributes:
        run_name: 运行名称。
        params: 该次运行使用的参数。
        repeat_index: 重复索引（从 0 开始）。
        final_stats: 最终步的统计字典。
        elapsed_seconds: 运行耗时（秒）。
        success: 是否成功完成。
        error_message: 失败时的错误信息。
    """

    run_name: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    repeat_index: int = 0
    final_stats: dict[str, Any] = field(default_factory=dict)
    elapsed_seconds: float = 0.0
    success: bool = True
    error_message: str = ""


class BatchRunner:
    """批量运行编排器。

    从 JSON 配置文件加载批量运行计划，按顺序执行每个配置，
    收集结果并保存为 CSV 和 JSON 汇总文件。
    """

    def __init__(self, config_path: str) -> None:
        """从 JSON 文件加载批量配置。

        Args:
            config_path: JSON 配置文件路径。

        Raises:
            FileNotFoundError: 配置文件不存在。
            json.JSONDecodeError: JSON 格式无效。
        """
        self.config_path: str = config_path
        with open(config_path, encoding="utf-8") as f:
            raw: dict[str, Any] = json.load(f)
        self.config = BatchConfig(
            name=raw.get("name", ""),
            runs=raw.get("runs", []),
            output_dir=raw.get("output_dir", "output/batch"),
            repeat=raw.get("repeat", 1),
        )
        self.results: list[BatchRunResult] = []

    def run_all(self) -> list[BatchRunResult]:
        """运行所有批量配置。

        遍历 ``self.config.runs`` 中的每个配置，对每个配置重复
        ``self.config.repeat`` 次，收集结果。

        Returns:
            所有运行结果的列表。
        """
        self.results = []
        for run_cfg in self.config.runs:
            run_name = run_cfg.get("name", "unnamed")
            params = {k: v for k, v in run_cfg.items() if k != "name"}
            for rep_idx in range(self.config.repeat):
                result = self._run_single(run_name, params, rep_idx)
                self.results.append(result)
        return self.results

    def _run_single(
        self,
        run_name: str,
        params: dict[str, Any],
        repeat_index: int,
    ) -> BatchRunResult:
        """执行单次模拟运行。

        Args:
            run_name: 运行名称。
            params: 模拟参数字典。
            repeat_index: 重复索引。

        Returns:
            运行结果（含耗时和最终统计）。
        """
        from src.simulation import Simulation

        t0 = time.perf_counter()
        try:
            config = SimulationConfig()
            _apply_params_to_config(config, params)

            sim = Simulation(config)
            sim.initialize()

            for _ in range(config.total_steps):
                sim.step()

            elapsed = time.perf_counter() - t0

            latest = sim.stats_collector.get_latest() if sim.stats_collector else None
            final_stats = asdict(latest) if latest else {}

            return BatchRunResult(
                run_name=run_name,
                params=params,
                repeat_index=repeat_index,
                final_stats=final_stats,
                elapsed_seconds=elapsed,
                success=True,
            )
        except Exception as e:
            elapsed = time.perf_counter() - t0
            return BatchRunResult(
                run_name=run_name,
                params=params,
                repeat_index=repeat_index,
                elapsed_seconds=elapsed,
                success=False,
                error_message=str(e),
            )

    def _save_results(self) -> None:
        """将结果保存为 CSV 和 JSON 文件到 ``self.config.output_dir``。"""
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # CSV 格式
        csv_path = output_dir / "batch_results.csv"
        fieldnames = [
            "run_name",
            "repeat_index",
            "success",
            "elapsed_seconds",
            "error_message",
            "final_step",
            "total_civilizations",
        ]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in self.results:
                writer.writerow({
                    "run_name": r.run_name,
                    "repeat_index": r.repeat_index,
                    "success": r.success,
                    "elapsed_seconds": f"{r.elapsed_seconds:.3f}",
                    "error_message": r.error_message,
                    "final_step": r.final_stats.get("step", ""),
                    "total_civilizations": r.final_stats.get(
                        "total_civilizations", ""
                    ),
                })

        # JSON 格式
        json_path = output_dir / "batch_results.json"
        data = [asdict(r) for r in self.results]
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def print_summary(self) -> None:
        """在终端打印对齐的结果汇总表格。"""
        if not self.results:
            print("（无批量运行结果）")
            return

        header = (
            f"{'Run Name':<20} {'Repeat':<7} {'Steps':<8} {'Time(s)':<10} "
            f"{'Civs':<8} {'Status':<8}"
        )
        print(f"\n{'═' * len(header)}")
        print(f"  批量运行结果汇总 — {self.config.name or self.config_path}")
        print(f"{'═' * len(header)}")
        print(header)
        print(f"{'─' * len(header)}")
        for r in self.results:
            status = "✓ OK" if r.success else "✗ FAIL"
            steps = r.final_stats.get("step", "-")
            civs = r.final_stats.get("total_civilizations", "-")
            print(
                f"{r.run_name:<20} {r.repeat_index:<7} {str(steps):<8} "
                f"{r.elapsed_seconds:<10.3f} {str(civs):<8} {status:<8}"
            )
        print(f"{'─' * len(header)}")
        success_count = sum(1 for r in self.results if r.success)
        print(
            f"  合计: {len(self.results)} 次运行, "
            f"{success_count} 成功, "
            f"{len(self.results) - success_count} 失败"
        )
        print()
