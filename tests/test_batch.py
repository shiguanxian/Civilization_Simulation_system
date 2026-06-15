"""批量运行模块单元测试 —— BatchConfig, BatchRunResult, BatchRunner。"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from src.batch import (
    BatchConfig,
    BatchRunner,
    BatchRunResult,
    _apply_params_to_config,
    _resolve_param_key,
)
from src.config import SimulationConfig


class TestBatchConfig:
    """BatchConfig 数据类测试。"""

    def test_defaults(self) -> None:
        """验证 BatchConfig 默认值与规范一致。"""
        config = BatchConfig()
        assert config.name == ""
        assert config.runs == []
        assert config.output_dir == "output/batch"
        assert config.repeat == 1


class TestBatchRunResult:
    """BatchRunResult 数据类测试。"""

    def test_defaults(self) -> None:
        """验证 BatchRunResult 默认值与规范一致。"""
        result = BatchRunResult()
        assert result.run_name == ""
        assert result.params == {}
        assert result.repeat_index == 0
        assert result.final_stats == {}
        assert result.elapsed_seconds == 0.0
        assert result.success is True
        assert result.error_message == ""


class TestResolveParamKey:
    """_resolve_param_key 工具函数测试。"""

    def test_direct_attribute(self) -> None:
        """已知的 SimulationConfig 属性名原样返回。"""
        assert _resolve_param_key("universe_size") == "universe_size"

    def test_alias_mapping(self) -> None:
        """CLI 风格别名被正确映射。"""
        assert _resolve_param_key("size") == "universe_size"
        assert _resolve_param_key("civs") == "initial_civ_count"
        assert _resolve_param_key("steps") == "total_steps"

    def test_unknown_key_passthrough(self) -> None:
        """未知键直接通过。"""
        assert _resolve_param_key("unknown_key") == "unknown_key"


class TestApplyParamsToConfig:
    """_apply_params_to_config 工具函数测试。"""

    def test_applies_known_params(self) -> None:
        """已知参数被正确应用到 config。"""
        config = SimulationConfig()
        _apply_params_to_config(config, {"universe_size": 5000.0, "total_steps": 50})
        assert config.universe_size == 5000.0
        assert config.total_steps == 50

    def test_applies_aliased_params(self) -> None:
        """CLI 风格别名参数也被正确应用。"""
        config = SimulationConfig()
        _apply_params_to_config(config, {"size": 3000.0, "civs": 100, "steps": 25})
        assert config.universe_size == 3000.0
        assert config.initial_civ_count == 100
        assert config.total_steps == 25

    def test_ignores_unknown_params(self) -> None:
        """未知参数被静默忽略。"""
        config = SimulationConfig()
        _apply_params_to_config(config, {"nonexistent": 42})
        # 不应抛出异常，值不变


class TestBatchRunner:
    """BatchRunner 集成与单元测试。"""

    def test_loads_config_from_json(self, tmp_path: Path) -> None:
        """BatchRunner 从 JSON 文件加载配置。"""
        config_data = {
            "name": "test-batch",
            "runs": [
                {"name": "run1", "universe_size": 1000.0, "total_steps": 10},
            ],
            "output_dir": str(tmp_path / "batch_out"),
            "repeat": 2,
        }
        config_file = tmp_path / "batch_config.json"
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        runner = BatchRunner(str(config_file))
        assert runner.config.name == "test-batch"
        assert len(runner.config.runs) == 1
        assert runner.config.repeat == 2
        assert runner.config.output_dir == str(tmp_path / "batch_out")

    def test_run_single_creates_and_runs_simulation(
        self,
        monkeypatch,
        tmp_path: Path,
    ) -> None:
        """_run_single 创建 Simulation 并执行所有步。"""
        # 模拟 Simulation
        mock_sim = MagicMock()
        mock_sim.stats_collector.get_latest.return_value = None

        mock_sim_class = MagicMock(return_value=mock_sim)
        monkeypatch.setattr("src.simulation.Simulation", mock_sim_class)

        config_data = {
            "name": "single",
            "runs": [
                {"name": "test-run", "total_steps": 5, "initial_civ_count": 10},
            ],
        }
        config_file = tmp_path / "batch_config.json"
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        runner = BatchRunner(str(config_file))
        result = runner._run_single("test-run", {"total_steps": 5}, 0)

        assert result.run_name == "test-run"
        assert result.success is True
        assert result.params == {"total_steps": 5}
        mock_sim.initialize.assert_called_once()
        assert mock_sim.step.call_count == 5

    def test_run_all_processes_multiple_configs(
        self,
        monkeypatch,
        tmp_path: Path,
    ) -> None:
        """run_all 处理多个运行配置和重复。"""
        mock_sim = MagicMock()
        mock_sim.stats_collector.get_latest.return_value = None

        mock_sim_class = MagicMock(return_value=mock_sim)
        monkeypatch.setattr("src.simulation.Simulation", mock_sim_class)

        config_data = {
            "name": "multi",
            "runs": [
                {"name": "a", "total_steps": 1},
                {"name": "b", "total_steps": 2},
            ],
            "repeat": 3,
        }
        config_file = tmp_path / "batch_config.json"
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        runner = BatchRunner(str(config_file))
        results = runner.run_all()

        assert len(results) == 6  # 2 runs × 3 repeats
        names = [(r.run_name, r.repeat_index) for r in results]
        assert ("a", 0) in names
        assert ("a", 2) in names
        assert ("b", 1) in names

    def test_print_summary_does_not_raise(
        self,
        monkeypatch,
        tmp_path: Path,
    ) -> None:
        """print_summary 在有结果时不应抛出异常。"""
        mock_sim = MagicMock()
        mock_sim.stats_collector.get_latest.return_value = None
        mock_sim_class = MagicMock(return_value=mock_sim)
        monkeypatch.setattr("src.simulation.Simulation", mock_sim_class)

        config_data = {
            "runs": [{"name": "p", "total_steps": 1}],
            "output_dir": str(tmp_path / "batch_out"),
        }
        config_file = tmp_path / "batch_config.json"
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        runner = BatchRunner(str(config_file))
        runner.run_all()
        # print_summary 不应抛出异常
        runner.print_summary()

    def test_print_summary_empty(self, tmp_path: Path) -> None:
        """没有结果时 print_summary 也应正常工作。"""
        config_data = {"runs": []}
        config_file = tmp_path / "batch_config.json"
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        runner = BatchRunner(str(config_file))
        runner.results = []
        runner.print_summary()

    def test_save_results_creates_csv_and_json(
        self,
        monkeypatch,
        tmp_path: Path,
    ) -> None:
        """_save_results 创建 CSV 和 JSON 文件。"""
        mock_sim = MagicMock()
        mock_sim.stats_collector.get_latest.return_value = None
        mock_sim_class = MagicMock(return_value=mock_sim)
        monkeypatch.setattr("src.simulation.Simulation", mock_sim_class)

        output_dir = tmp_path / "batch_out"
        config_data = {
            "runs": [
                {"name": "s1", "total_steps": 1},
            ],
            "output_dir": str(output_dir),
        }
        config_file = tmp_path / "batch_config.json"
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        runner = BatchRunner(str(config_file))
        runner.run_all()
        runner._save_results()

        csv_path = output_dir / "batch_results.csv"
        json_path = output_dir / "batch_results.json"
        assert csv_path.exists(), f"CSV 文件不存在: {csv_path}"
        assert json_path.exists(), f"JSON 文件不存在: {json_path}"

        # 验证 JSON 内容
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["run_name"] == "s1"
        assert data[0]["success"] is True

    def test_error_handling_returns_failed_result(
        self,
        monkeypatch,
        tmp_path: Path,
    ) -> None:
        """模拟初始化失败时返回失败结果。"""
        # 让 Simulation 构造函数抛出异常
        def failing_constructor(*args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("模拟初始化失败")

        mock_sim_class = MagicMock(side_effect=failing_constructor)
        monkeypatch.setattr("src.simulation.Simulation", mock_sim_class)

        config_data = {
            "runs": [
                {"name": "fail-run", "total_steps": 1},
            ],
            "output_dir": str(tmp_path / "batch_out"),
        }
        config_file = tmp_path / "batch_config.json"
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        runner = BatchRunner(str(config_file))
        results = runner.run_all()

        assert len(results) == 1
        assert results[0].success is False
        assert results[0].error_message == "模拟初始化失败"
