"""CLI 模块单元测试 —— build_parser 与 main。"""

from __future__ import annotations

from unittest.mock import MagicMock

from src.cli import build_parser
from src.cli import main as cli_main
from src.config import ComputerCapability


class TestBuildParser:
    """build_parser 返回的 ArgumentParser 测试。"""

    def test_build_parser_returns_parser(self) -> None:
        """验证 build_parser 返回 ArgumentParser 实例。"""
        parser = build_parser()
        assert parser is not None
        assert parser.prog == "simulation"

    def test_fast_flag(self) -> None:
        """--fast 设置 fast=True。"""
        parser = build_parser()
        args = parser.parse_args(["--fast"])
        assert args.fast is True
        assert args.standard is False
        assert args.interactive is False

    def test_standard_flag(self) -> None:
        """--standard 设置 standard=True。"""
        parser = build_parser()
        args = parser.parse_args(["--standard"])
        assert args.standard is True
        assert args.fast is False
        assert args.interactive is False

    def test_interactive_flag(self) -> None:
        """--interactive 设置 interactive=True。"""
        parser = build_parser()
        args = parser.parse_args(["--interactive"])
        assert args.interactive is True
        assert args.fast is False
        assert args.standard is False

    def test_batch_path(self) -> None:
        """--batch path 设置 batch 为路径字符串。"""
        parser = build_parser()
        args = parser.parse_args(["--batch", "my_config.json"])
        assert args.batch == "my_config.json"

    def test_size_param(self) -> None:
        """--size 5000 设置 size=5000。"""
        parser = build_parser()
        args = parser.parse_args(["--size", "5000"])
        assert args.size == 5000.0

    def test_civs_param(self) -> None:
        """--civs 100 设置 civs=100。"""
        parser = build_parser()
        args = parser.parse_args(["--civs", "100"])
        assert args.civs == 100

    def test_steps_param(self) -> None:
        """--steps 500 设置 steps=500。"""
        parser = build_parser()
        args = parser.parse_args(["--steps", "500"])
        assert args.steps == 500

    def test_detect_only_flag(self) -> None:
        """--detect-only 设置 detect_only=True。"""
        parser = build_parser()
        args = parser.parse_args(["--detect-only"])
        assert args.detect_only is True

    def test_distribution_cluster(self) -> None:
        """--distribution cluster 设置 distribution='cluster'。"""
        parser = build_parser()
        args = parser.parse_args(["--distribution", "cluster"])
        assert args.distribution == "cluster"

    def test_mutually_exclusive_modes(self) -> None:
        """验证互斥组中只能设置一个模式。"""
        parser = build_parser()
        # 同时指定 --fast 和 --standard 应报错
        try:
            parser.parse_args(["--fast", "--standard"])
            assert False, "Expected SystemExit for mutually exclusive args"
        except SystemExit:
            pass

    def test_initial_civs_alias(self) -> None:
        """--initial-civs 是 --civs 的别名。"""
        parser = build_parser()
        args = parser.parse_args(["--initial-civs", "200"])
        assert args.civs == 200


class TestMain:
    """main() 主调度测试（使用 monkeypatch 避免实际执行）。"""

    def test_main_detect_only_returns_zero(self, monkeypatch) -> None:
        """main() 使用 --detect-only 应返回 0。"""
        mock_cap = ComputerCapability(
            cpu_score=8.0,
            memory_gb=16.0,
            recommended_civ_count=5000,
            recommended_grid_size=200.0,
            estimated_step_time_ms=50.0,
        )
        monkeypatch.setattr(
            "src.cli.detect_computer_capability",
            lambda: mock_cap,
        )
        result = cli_main(["--detect-only"])
        assert result == 0

    def test_main_fast_creates_sim_and_runs(self, monkeypatch) -> None:
        """main() 使用 --fast 应创建 Simulation 并调用 run_fast。"""
        # 模拟 Simulation
        mock_sim = MagicMock()
        mock_sim.stats_collector.get_latest.return_value = None

        mock_sim_class = MagicMock(return_value=mock_sim)
        monkeypatch.setattr("src.simulation.Simulation", mock_sim_class)

        # 拦截 run_fast
        run_fast_called = False

        def mock_run_fast(sim) -> None:  # type: ignore[no-untyped-def]
            nonlocal run_fast_called
            run_fast_called = True

        monkeypatch.setattr(
            "src.visualization.run_modes.run_fast",
            mock_run_fast,
        )

        result = cli_main(
            ["--fast", "--steps", "1", "--civs", "1", "--size", "100"]
        )
        assert result == 0
        assert run_fast_called, "run_fast was not called"

    def test_main_exits_zero_on_success(self, monkeypatch) -> None:
        """main() 成功时返回 0。"""
        mock_sim = MagicMock()
        mock_sim.stats_collector.get_latest.return_value = None

        mock_sim_class = MagicMock(return_value=mock_sim)
        monkeypatch.setattr("src.simulation.Simulation", mock_sim_class)

        def mock_run_fast(sim) -> None:  # type: ignore[no-untyped-def]
            pass

        monkeypatch.setattr(
            "src.visualization.run_modes.run_fast",
            mock_run_fast,
        )

        result = cli_main(
            ["--fast", "--steps", "1", "--civs", "1", "--size", "100"]
        )
        assert result == 0

    def test_main_interactive_fallback(self, monkeypatch) -> None:
        """交互模式导入失败时返回非零值。"""
        mock_sim = MagicMock()
        mock_sim_class = MagicMock(return_value=mock_sim)
        monkeypatch.setattr("src.simulation.Simulation", mock_sim_class)

        # 模拟 run_interactive 导入失败
        original_import = __import__

        def broken_import(name, *args, **kwargs):  # type: ignore[no-untyped-def]
            if "interactive" in name:
                raise ImportError("模拟导入失败")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", broken_import)

        result = cli_main(
            [
                "--interactive",
                "--steps",
                "1",
                "--civs",
                "1",
                "--size",
                "100",
            ]
        )
        assert result == 1
