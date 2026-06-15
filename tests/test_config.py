"""配置模块单元测试 —— SimulationConfig、ComputerCapability 与 load_config。"""

import argparse
from unittest.mock import patch

from src.config import (
    ComputerCapability,
    SimulationConfig,
    detect_computer_capability,
    get_recommended_params,
    load_config,
)


class TestSimulationConfig:
    """SimulationConfig 数据类测试。"""

    def test_default_config_values(self):
        """验证默认配置的所有字段值与规范一致。"""
        config = SimulationConfig()

        # 宇宙参数
        assert config.universe_size == 10000.0

        # 文明参数
        assert config.initial_civ_count == 5000
        assert config.max_civ_count == 20000
        assert config.initial_distribution_mode == "uniform"

        # 聚簇参数
        assert config.cluster_count == 50
        assert config.cluster_radius == 500.0

        # 演化参数
        assert config.total_steps == 1000
        assert config.birth_rate == 0.05
        assert config.tech_explosion_base_prob == 0.01
        assert config.cosmic_strike_prob == 0.001

        # 文明参数范围
        assert config.level_range == (1, 3)
        assert config.aggressiveness_range == (0.1, 0.9)
        assert config.stealth_range == (0.1, 0.9)
        assert config.detection_range_range == (50.0, 500.0)
        assert config.expansion_radius_range == (10.0, 100.0)
        assert config.population_range == (1e6, 1e10)
        assert config.energy_output_range == (1e12, 1e18)

        # 运行参数
        assert config.run_mode == "standard"
        assert config.step_interval_seconds == 0.1

        # 输出参数
        assert config.output_dir == "output"
        assert config.save_step_data is True
        assert config.save_summary is True
        assert config.save_interval == 1
        assert config.plot_update_interval == 5

        # 性能参数
        assert config.spatial_grid_cell_size == 0.0
        assert config.use_spatial_index is True

        # 名称生成
        assert config.name_generator_mode == "auto"

        # 规则模块参数
        assert config.tech_growth_base == 5.0
        assert config.pop_growth_rate == 0.01
        assert config.energy_growth_rate == 0.005
        assert config.expansion_rate_base == 1.0
        assert config.base_exposure_prob == 0.01
        assert config.exposure_threshold == 5.0
        assert config.attack_threshold == 0.65
        assert config.flee_threshold == 0.35

    def test_config_defaults_are_reasonable(self):
        """验证默认值的数值合理性（范围检查）。"""
        config = SimulationConfig()

        # 宇宙大小应为正数
        assert config.universe_size > 0

        # 文明数量
        assert 0 < config.initial_civ_count <= config.max_civ_count
        assert config.max_civ_count > 0

        # 概率值在 [0, 1] 范围内
        assert 0 <= config.birth_rate <= 1
        assert 0 <= config.tech_explosion_base_prob <= 1
        assert 0 <= config.cosmic_strike_prob <= 1

        # 聚簇参数合理
        assert config.cluster_count > 0
        assert config.cluster_radius > 0

        # 总步数为正
        assert config.total_steps > 0

        # 范围参数保证 min <= max
        assert config.level_range[0] <= config.level_range[1]
        assert config.aggressiveness_range[0] <= config.aggressiveness_range[1]
        assert config.stealth_range[0] <= config.stealth_range[1]
        assert config.detection_range_range[0] <= config.detection_range_range[1]
        assert config.expansion_radius_range[0] <= config.expansion_radius_range[1]
        assert config.population_range[0] <= config.population_range[1]
        assert config.energy_output_range[0] <= config.energy_output_range[1]

        # 阈值关系：flee < attack
        assert config.flee_threshold < config.attack_threshold

        # 运行模式有效
        assert config.run_mode in ("fast", "standard", "interactive")

        # 保存间隔为正
        assert config.save_interval >= 1

    def test_config_custom_values(self):
        """验证可以通过构造函数参数覆盖默认值。"""
        config = SimulationConfig(
            universe_size=20000.0,
            initial_civ_count=10000,
            max_civ_count=50000,
            total_steps=2000,
            run_mode="fast",
        )

        assert config.universe_size == 20000.0
        assert config.initial_civ_count == 10000
        assert config.max_civ_count == 50000
        assert config.total_steps == 2000
        assert config.run_mode == "fast"

        # 未覆盖的字段仍使用默认值
        assert config.birth_rate == 0.05
        assert config.save_step_data is True

    def test_field_types(self):
        """验证所有字段的类型正确。"""
        config = SimulationConfig()

        # float 类型
        assert isinstance(config.universe_size, float)
        assert isinstance(config.cluster_radius, float)
        assert isinstance(config.birth_rate, float)
        assert isinstance(config.tech_explosion_base_prob, float)
        assert isinstance(config.cosmic_strike_prob, float)
        assert isinstance(config.step_interval_seconds, float)
        assert isinstance(config.spatial_grid_cell_size, float)
        assert isinstance(config.tech_growth_base, float)
        assert isinstance(config.pop_growth_rate, float)
        assert isinstance(config.energy_growth_rate, float)
        assert isinstance(config.expansion_rate_base, float)
        assert isinstance(config.base_exposure_prob, float)
        assert isinstance(config.exposure_threshold, float)
        assert isinstance(config.attack_threshold, float)
        assert isinstance(config.flee_threshold, float)

        # int 类型
        assert isinstance(config.initial_civ_count, int)
        assert isinstance(config.max_civ_count, int)
        assert isinstance(config.cluster_count, int)
        assert isinstance(config.total_steps, int)
        assert isinstance(config.save_interval, int)
        assert isinstance(config.plot_update_interval, int)

        # bool 类型
        assert isinstance(config.save_step_data, bool)
        assert isinstance(config.save_summary, bool)
        assert isinstance(config.use_spatial_index, bool)

        # str 类型
        assert isinstance(config.initial_distribution_mode, str)
        assert isinstance(config.run_mode, str)
        assert isinstance(config.output_dir, str)
        assert isinstance(config.name_generator_mode, str)

        # tuple 类型
        assert isinstance(config.level_range, tuple)
        assert isinstance(config.aggressiveness_range, tuple)
        assert isinstance(config.stealth_range, tuple)
        assert isinstance(config.detection_range_range, tuple)
        assert isinstance(config.expansion_radius_range, tuple)
        assert isinstance(config.population_range, tuple)
        assert isinstance(config.energy_output_range, tuple)

    def test_range_tuple_types(self):
        """验证范围字段的元组元素类型正确。"""
        config = SimulationConfig()

        # int 元组
        lo, hi = config.level_range
        assert isinstance(lo, int)
        assert isinstance(hi, int)

        # float 元组
        for t in [
            config.aggressiveness_range,
            config.stealth_range,
            config.detection_range_range,
            config.expansion_radius_range,
            config.population_range,
            config.energy_output_range,
        ]:
            a, b = t
            assert isinstance(a, float)
            assert isinstance(b, float)


class TestComputerCapability:
    """ComputerCapability 数据类测试。"""

    def test_init_with_values(self):
        """验证 ComputerCapability 可以使用所有字段初始化。"""
        cap = ComputerCapability(
            cpu_score=8.5,
            memory_gb=32.0,
            recommended_civ_count=12000,
            recommended_grid_size=250.0,
            estimated_step_time_ms=45.0,
        )

        assert cap.cpu_score == 8.5
        assert cap.memory_gb == 32.0
        assert cap.recommended_civ_count == 12000
        assert cap.recommended_grid_size == 250.0
        assert cap.estimated_step_time_ms == 45.0

    def test_init_with_low_end_values(self):
        """验证低端机器的 ComputerCapability 初始化。"""
        cap = ComputerCapability(
            cpu_score=2.0,
            memory_gb=4.0,
            recommended_civ_count=2000,
            recommended_grid_size=500.0,
            estimated_step_time_ms=200.0,
        )

        assert cap.cpu_score == 2.0
        assert cap.memory_gb == 4.0
        assert cap.recommended_civ_count == 2000
        assert cap.recommended_grid_size == 500.0
        assert cap.estimated_step_time_ms == 200.0

    def test_field_types(self):
        """验证 ComputerCapability 字段类型正确。"""
        cap = ComputerCapability(8.5, 32.0, 12000, 250.0, 45.0)

        assert isinstance(cap.cpu_score, float)
        assert isinstance(cap.memory_gb, float)
        assert isinstance(cap.recommended_civ_count, int)
        assert isinstance(cap.recommended_grid_size, float)
        assert isinstance(cap.estimated_step_time_ms, float)

    def test_repr_output(self):
        """验证 __repr__ 包含关键信息。"""
        cap = ComputerCapability(8.5, 32.0, 12000, 250.0, 45.0)
        repr_str = repr(cap)

        assert "ComputerCapability" in repr_str
        assert "cpu_score=8.5" in repr_str
        assert "memory_gb=32.0" in repr_str
        assert "recommended_civ_count=12000" in repr_str

    def test_eq(self):
        """验证相等性比较。"""
        cap1 = ComputerCapability(8.5, 32.0, 12000, 250.0, 45.0)
        cap2 = ComputerCapability(8.5, 32.0, 12000, 250.0, 45.0)
        cap3 = ComputerCapability(2.0, 4.0, 2000, 500.0, 200.0)

        assert cap1 == cap2
        assert cap1 != cap3


class TestDetectComputerCapability:
    """detect_computer_capability() 函数测试。"""

    def test_detect_runs_and_returns_reasonable_values(self):
        """验证函数能正常执行且返回合理值。"""
        cap = detect_computer_capability()
        assert 0.5 <= cap.cpu_score <= 10.0
        assert cap.memory_gb > 0
        assert isinstance(cap.recommended_civ_count, int)
        assert 100 <= cap.recommended_civ_count <= 200_000
        assert cap.recommended_grid_size >= 50.0
        assert cap.estimated_step_time_ms > 0

    def test_psutil_failure_graceful_degradation(self):
        """验证 psutil 失败时降级返回默认值，不崩溃。"""
        with patch("src.config.psutil.cpu_count", side_effect=RuntimeError("mock")):
            with patch("src.config.psutil.cpu_freq", side_effect=RuntimeError("mock")):
                with patch(
                    "src.config.psutil.virtual_memory",
                    side_effect=RuntimeError("mock"),
                ):
                    cap = detect_computer_capability()
                    assert 0.5 <= cap.cpu_score <= 10.0
                    assert cap.memory_gb > 0
                    assert cap.recommended_civ_count > 0

    def test_format_report_contains_expected_fields(self):
        """验证 format_report 包含关键字段。"""
        cap = ComputerCapability(8.5, 32.0, 12000, 250.0, 45.0)
        report = cap.format_report()
        assert isinstance(report, str)
        assert "8.5" in report
        assert "12,000" in report or "12000" in report
        assert "250" in report
        assert "45" in report


class TestGetRecommendedParams:
    """get_recommended_params() 函数测试。"""

    def test_returns_config_with_recommended_values(self):
        """验证返回的 SimulationConfig 包含推荐值。"""

        cap = ComputerCapability(8.5, 32.0, 12000, 250.0, 45.0)
        config = get_recommended_params(cap)
        assert isinstance(config, SimulationConfig)
        assert config.max_civ_count == 12000
        assert config.spatial_grid_cell_size == 250.0
        assert config.initial_civ_count <= 12000

    def test_low_end_machine_gets_conservative_params(self):
        """验证低端机器的推荐参数较保守。"""

        cap = ComputerCapability(2.0, 4.0, 2000, 500.0, 200.0)
        config = get_recommended_params(cap)
        assert config.max_civ_count == 2000
        assert config.spatial_grid_cell_size == 500.0


class TestLoadConfig:
    """load_config() 配置加载函数测试。"""

    # ----------------------------------------------------------------
    # 默认 / 无配置测试
    # ----------------------------------------------------------------

    def test_default_config_no_toml(self, tmp_path, monkeypatch):
        """验证无 pyproject.toml 时返回完整的默认配置。"""
        monkeypatch.chdir(tmp_path)  # 空目录，没有 pyproject.toml
        config = load_config()
        assert config.universe_size == 10000.0
        assert config.initial_civ_count == 5000
        assert config.max_civ_count == 20000
        assert config.birth_rate == 0.05
        assert config.total_steps == 1000
        assert config.name_generator_mode == "auto"
        # spatial_grid_cell_size 从 0.0 被 auto-detect 设置了推荐值
        assert config.spatial_grid_cell_size > 0

    def test_default_config_with_matching_toml(self):
        """验证真实 pyproject.toml 中值与默认值一致时，结果不变。"""
        config = load_config()
        assert config.universe_size == 10000.0
        assert config.initial_civ_count == 5000
        assert config.max_civ_count == 20000
        assert config.birth_rate == 0.05
        assert config.total_steps == 1000

    def test_none_args_equivalent_to_no_args(self):
        """验证 args=None 等同于不传参数。"""
        config1 = load_config()
        config2 = load_config(None)
        assert config1 == config2

    # ----------------------------------------------------------------
    # pyproject.toml 覆盖测试
    # ----------------------------------------------------------------

    def test_toml_overrides_defaults(self, tmp_path, monkeypatch):
        """验证 pyproject.toml [tool.simulation] 能覆盖代码默认值。"""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            "[tool.simulation]\n"
            "universe_size = 25000.0\n"
            "initial_civ_count = 12000\n"
            "total_steps = 3000\n"
        )
        config = load_config()
        assert config.universe_size == 25000.0
        assert config.initial_civ_count == 12000
        assert config.total_steps == 3000
        # 未在 toml 中指定的字段保持默认值
        assert config.birth_rate == 0.05
        assert config.max_civ_count == 20000

    def test_toml_section_missing(self, tmp_path, monkeypatch):
        """验证 pyproject.toml 存在但无 [tool.simulation] 时不报错。"""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text("[tool.other]\nfoo = 1\n")
        config = load_config()  # 不应抛出异常
        assert config.universe_size == 10000.0

    def test_toml_file_missing(self, tmp_path, monkeypatch):
        """验证 pyproject.toml 不存在时不报错。"""
        monkeypatch.chdir(tmp_path)  # 空目录，无 pyproject.toml
        config = load_config()  # 不应抛出异常
        assert config.universe_size == 10000.0

    def test_toml_invalid_syntax(self, tmp_path, monkeypatch):
        """验证 TOML 格式错误时不报错，静默回退。"""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text("[[[invalid\n")
        config = load_config()  # 不应抛出异常
        assert config.universe_size == 10000.0

    # ----------------------------------------------------------------
    # CLI 覆盖测试
    # ----------------------------------------------------------------

    def test_cli_overrides_defaults(self):
        """验证 CLI 参数能覆盖代码默认值。"""
        ns = argparse.Namespace(size=30000.0, civs=15000, steps=3000)
        config = load_config(ns)
        assert config.universe_size == 30000.0
        assert config.initial_civ_count == 15000
        assert config.total_steps == 3000

    def test_cli_partial_override(self):
        """验证 CLI 可以只覆盖部分字段，其余保持默认。"""
        ns = argparse.Namespace(size=5000.0)  # 只覆盖 universe_size
        config = load_config(ns)
        assert config.universe_size == 5000.0
        assert config.initial_civ_count == 5000  # 默认值
        assert config.total_steps == 1000  # 默认值

    def test_cli_none_value_skipped(self):
        """验证 CLI 字段为 None 时被跳过，不覆盖默认值。"""
        ns = argparse.Namespace(size=None, civs=None)
        config = load_config(ns)
        assert config.universe_size == 10000.0  # 默认值，未被 None 覆盖
        assert config.initial_civ_count == 5000

    # ----------------------------------------------------------------
    # 优先级测试：CLI > toml > 默认值
    # ----------------------------------------------------------------

    def test_cli_overrides_toml(self, tmp_path, monkeypatch):
        """验证 CLI 优先级高于 pyproject.toml。"""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            "[tool.simulation]\n" "universe_size = 9999.0\n"
        )
        ns = argparse.Namespace(size=7777.0)
        config = load_config(ns)
        assert config.universe_size == 7777.0  # CLI 胜出

    def test_toml_overrides_defaults_when_no_cli(self, tmp_path, monkeypatch):
        """验证无 CLI 时 toml 覆盖默认值。"""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            "[tool.simulation]\n"
            "universe_size = 20000.0\n"
            "birth_rate = 0.1\n"
        )
        config = load_config()  # 无 CLI 参数
        assert config.universe_size == 20000.0  # toml 值
        assert config.birth_rate == 0.1  # toml 值

    def test_full_priority_chain(self, tmp_path, monkeypatch):
        """验证完整优先级链：CLI 部分覆盖 toml，toml 部分覆盖默认值。"""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            "[tool.simulation]\n"
            "universe_size = 111.0\n"
            "initial_civ_count = 2222\n"
            "max_civ_count = 33333\n"
        )
        # CLI 只覆盖 universe_size，其他字段应继承 toml / 默认值
        ns = argparse.Namespace(size=999.0)
        config = load_config(ns)
        assert config.universe_size == 999.0  # CLI 胜出
        assert config.initial_civ_count == 2222  # toml 胜出（无 CLI）
        assert config.max_civ_count == 33333  # toml 胜出（无 CLI）
        assert config.total_steps == 1000  # 默认值（无 CLI / toml）

    # ----------------------------------------------------------------
    # auto-detect spatial_grid_cell_size 测试
    # ----------------------------------------------------------------

    def test_auto_detect_cell_size(self):
        """验证 spatial_grid_cell_size=0.0 时 auto-detect 设置推荐值。"""
        config = load_config()
        # auto-detect 函数可用时返回检测推荐值
        assert config.spatial_grid_cell_size > 0

    def test_auto_detect_cell_size_calls_functions(self):
        """验证 auto-detect 确实调用 detect_computer_capability。"""
        mock_cap = ComputerCapability(
            cpu_score=7.5,
            memory_gb=16.0,
            recommended_civ_count=10000,
            recommended_grid_size=120.0,
            estimated_step_time_ms=80.0,
        )
        # get_recommended_params 返回 SimulationConfig（设 spatial_grid_cell_size）
        mock_recommended_config = SimulationConfig(spatial_grid_cell_size=120.0)

        with patch(
            "src.config.detect_computer_capability",
            return_value=mock_cap,
            create=True,
        ) as mock_detect, patch(
            "src.config.get_recommended_params",
            return_value=mock_recommended_config,
            create=True,
        ) as mock_recommend:
            config = load_config()

        assert config.spatial_grid_cell_size == 120.0
        mock_detect.assert_called_once()
        mock_recommend.assert_called_once_with(mock_cap)

    def test_auto_detect_skipped_when_cell_size_set(self, tmp_path, monkeypatch):
        """验证 spatial_grid_cell_size 已设置（非 0.0）时跳过 auto-detect。"""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            "[tool.simulation]\n" "spatial_grid_cell_size = 500.0\n"
        )
        config = load_config()
        assert config.spatial_grid_cell_size == 500.0  # 直接使用 toml 值
