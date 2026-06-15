"""DataSaver 模块测试 — 数据保存、文件 IO、错误容错。

覆盖 O3 全部 7 个子任务：
- O3.1: 初始化与目录创建
- O3.2: 分步全量数据保存
- O3.3: 汇总数据保存
- O3.4: JSON 状态保存
- O3.5: 批处理结果保存
- O3.6: 资源清理
- O3.7: IO 错误容错
"""

import csv
import json
from pathlib import Path

from src.config import SimulationConfig
from src.entity import Civilization
from src.output.data_saver import DataSaver
from src.output.stats import StepStats

# =============================================================================
# 辅助函数
# =============================================================================

STUB_STATS_KWARGS: dict = {
    "step": 1,
    "total_civilizations": 100,
    "new_born": 5,
    "destroyed": 2,
    "level_distribution": {1: 40, 2: 30, 3: 20, 4: 8, 5: 2},
    "average_level": 2.2,
    "max_level": 5,
    "average_tech_points": 2500.0,
    "total_tech_points": 250000.0,
    "tech_explosions": 1,
    "average_aggressiveness": 0.5,
    "average_stealth": 0.4,
    "exposed_civilizations": 15,
    "average_detection_range": 200.0,
    "average_expansion_radius": 50.0,
    "total_energy": 1e16,
    "total_population": 1e12,
    "average_energy": 1e14,
    "average_population": 1e10,
    "contacts_count": 10,
    "attacks_count": 3,
    "cosmic_strikes": 1,
}


def stub_stats(**overrides: object) -> StepStats:
    """创建带有填充数据的 StepStats 实例。"""
    kwargs = dict(STUB_STATS_KWARGS)
    kwargs.update(overrides)
    return StepStats(**kwargs)


def stub_civilizations(count: int = 3) -> list[Civilization]:
    """创建指定数量的简单 Civilization 实例。"""
    return [
        Civilization(
            id=i,
            name=f"Civ #{i}",
            x=float(i * 100),
            y=float(i * 200),
            level=(i % 5) + 1,
            tech_points=float(i * 1000),
            tech_explosion_prob=0.01,
            expansion_radius=50.0 + i * 10,
            population=1e6 * (i + 1),
            energy_output=1e12 * (i + 1),
            aggressiveness=0.5,
            stealth=0.3,
            detection_range=200.0 + i * 50,
            is_alive=True,
            birth_time=0,
            communication_active=(i % 2 == 0),
        )
        for i in range(count)
    ]


def make_config(tmp_path: Path, **overrides: object) -> SimulationConfig:
    """使用 tmp_path 作为输出目录创建 SimulationConfig。"""
    kwargs: dict = {
        "output_dir": str(tmp_path),
        "save_step_data": True,
        "save_summary": True,
        "save_interval": 1,
        "run_mode": "standard",
    }
    kwargs.update(overrides)
    return SimulationConfig(**kwargs)


# =============================================================================
# O3.1 — 初始化与目录管理
# =============================================================================


class TestInitAndDirectory:
    """验证 DataSaver 初始化与目录创建。"""

    def test_init_creates_output_dir(self, tmp_path: Path) -> None:
        """验证 __init__ 创建了输出目录。"""
        output_dir = tmp_path / "my_output"
        assert not output_dir.exists()
        config = SimulationConfig(output_dir=str(output_dir))
        DataSaver(config)
        assert output_dir.exists()
        assert output_dir.is_dir()

    def test_init_existing_dir_does_not_fail(self, tmp_path: Path) -> None:
        """验证输出目录已存在时不会报错。"""
        output_dir = tmp_path / "existing"
        output_dir.mkdir(parents=True)
        DataSaver(SimulationConfig(output_dir=str(output_dir)))
        assert output_dir.exists()

    def test_init_nested_dir_creates_parents(self, tmp_path: Path) -> None:
        """验证嵌套的目录路径会递归创建。"""
        output_dir = tmp_path / "a" / "b" / "c"
        assert not output_dir.exists()
        DataSaver(SimulationConfig(output_dir=str(output_dir)))
        assert output_dir.exists()

    def test_init_stores_config(self, tmp_path: Path) -> None:
        """验证 config 被正确存储。"""
        config = make_config(tmp_path)
        saver = DataSaver(config)
        assert saver.config is config

    def test_init_output_dir_path(self, tmp_path: Path) -> None:
        """验证 output_dir 被正确转换为 Path。"""
        config = make_config(tmp_path)
        saver = DataSaver(config)
        assert saver.output_dir == tmp_path

    def test_ensure_output_dir_idempotent(self, tmp_path: Path) -> None:
        """验证 _ensure_output_dir 是幂等的。"""
        saver = DataSaver(make_config(tmp_path))
        # 第二次调用不应抛出异常
        saver._ensure_output_dir()
        assert tmp_path.exists()


# =============================================================================
# O3.2 — 分步全量数据保存
# =============================================================================


class TestSaveStepFullData:
    """验证分步全量数据文件保存。"""

    def test_save_step_creates_step_file(self, tmp_path: Path) -> None:
        """验证 save_step 创建了 step_000001.csv 文件。"""
        config = make_config(tmp_path, save_summary=False)
        saver = DataSaver(config)
        saver.save_step(stub_stats(step=1), step=1)
        assert (tmp_path / "step_000001.csv").exists()

    def test_save_step_file_content(self, tmp_path: Path) -> None:
        """验证步文件包含正确的列头和数据行。"""
        config = make_config(tmp_path, save_summary=False)
        saver = DataSaver(config)
        stats = stub_stats(
            step=42,
            total_civilizations=500,
            average_level=3.5,
            max_level=5,
        )
        saver.save_step(stats, step=42)

        filepath = tmp_path / "step_000042.csv"
        assert filepath.exists()

        with open(filepath, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        assert len(rows) == 2  # header + 1 data row
        # 验证列头
        assert rows[0][0] == "step"
        assert rows[0][1] == "total"
        assert rows[0][3] == "destroyed"
        # 验证数据
        assert rows[1][0] == "42"
        assert rows[1][1] == "500"
        assert rows[1][4] == "3.50"  # avg_level formatted
        assert rows[1][5] == "5"  # max_level

    def test_save_step_disabled_by_config(self, tmp_path: Path) -> None:
        """验证 save_step_data=False 时不创建步文件。"""
        config = make_config(tmp_path, save_step_data=False, save_summary=False)
        saver = DataSaver(config)
        saver.save_step(stub_stats(step=1), step=1)
        assert not (tmp_path / "step_000001.csv").exists()

    def test_save_step_fast_mode_skips_non_multiple_10(self, tmp_path: Path) -> None:
        """验证 fast 模式下非 10 倍数步不保存。"""
        config = make_config(
            tmp_path, run_mode="fast", save_summary=False,
        )
        saver = DataSaver(config)
        saver.save_step(stub_stats(step=3), step=3)
        assert not (tmp_path / "step_000003.csv").exists()

    def test_save_step_fast_mode_saves_step_10(self, tmp_path: Path) -> None:
        """验证 fast 模式下第 10 步会保存。"""
        config = make_config(
            tmp_path, run_mode="fast", save_summary=False,
        )
        saver = DataSaver(config)
        saver.save_step(stub_stats(step=10), step=10)
        assert (tmp_path / "step_000010.csv").exists()

    def test_save_step_fast_mode_saves_step_0(self, tmp_path: Path) -> None:
        """验证 fast 模式下第 0 步（初始步）会保存。"""
        config = make_config(
            tmp_path, run_mode="fast", save_summary=False,
        )
        saver = DataSaver(config)
        saver.save_step(stub_stats(step=0), step=0)
        assert (tmp_path / "step_000000.csv").exists()

    def test_save_step_multiple_steps(self, tmp_path: Path) -> None:
        """验证连续保存多步，每步生成独立文件。"""
        config = make_config(tmp_path, save_summary=False)
        saver = DataSaver(config)
        for step in range(1, 4):
            saver.save_step(stub_stats(step=step), step=step)

        assert (tmp_path / "step_000001.csv").exists()
        assert (tmp_path / "step_000002.csv").exists()
        assert (tmp_path / "step_000003.csv").exists()


# =============================================================================
# O3.3 — 汇总数据保存
# =============================================================================


class TestSaveSummary:
    """验证汇总数据文件创建与内容。"""

    def test_save_summary_creates_summary_file(self, tmp_path: Path) -> None:
        """验证保存汇总创建了 summary.csv。"""
        config = make_config(tmp_path, save_step_data=False)
        saver = DataSaver(config)
        saver.save_step(stub_stats(step=1), step=1)
        assert (tmp_path / "summary.csv").exists()

    def test_save_summary_has_header(self, tmp_path: Path) -> None:
        """验证汇总文件包含正确的 CSV 表头。"""
        config = make_config(tmp_path, save_step_data=False)
        saver = DataSaver(config)
        saver.save_step(stub_stats(step=1), step=1)

        with open(tmp_path / "summary.csv", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)

        assert "step" in header
        assert "total" in header
        assert "avg_level" in header
        assert "max_level" in header
        assert "level_1" in header
        assert "level_2" in header
        assert "level_3" in header
        assert "level_4" in header
        assert "level_5" in header
        assert "avg_tech_points" in header
        assert "exposed_civilizations" in header
        assert "contacts_count" in header
        assert "cosmic_strikes" in header

    def test_save_summary_disabled_by_config(self, tmp_path: Path) -> None:
        """验证 save_summary=False 时不创建汇总文件。"""
        config = make_config(tmp_path, save_summary=False, save_step_data=False)
        saver = DataSaver(config)
        saver.save_step(stub_stats(step=1), step=1)
        assert not (tmp_path / "summary.csv").exists()

    def test_save_summary_multiple_rows(self, tmp_path: Path) -> None:
        """验证多次保存追加多行数据。"""
        config = make_config(tmp_path, save_step_data=False)
        saver = DataSaver(config)
        for step in range(1, 5):
            saver.save_step(stub_stats(step=step, total_civilizations=step * 10), step=step)

        with open(tmp_path / "summary.csv", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 4
        assert rows[0]["step"] == "1"
        assert rows[0]["total"] == "10"
        assert rows[3]["step"] == "4"
        assert rows[3]["total"] == "40"

    def test_save_summary_content_values(self, tmp_path: Path) -> None:
        """验证汇总行包含正确的字段值。"""
        config = make_config(tmp_path, save_step_data=False)
        saver = DataSaver(config)
        stats = stub_stats(
            step=5,
            total_civilizations=250,
            new_born=12,
            destroyed=3,
            level_distribution={1: 100, 2: 80, 3: 50, 4: 15, 5: 5},
            average_level=2.5,
            max_level=5,
            average_tech_points=3000.0,
            total_tech_points=750000.0,
            tech_explosions=2,
            average_aggressiveness=0.6,
            average_stealth=0.35,
            exposed_civilizations=20,
            average_detection_range=250.0,
            average_expansion_radius=60.0,
            total_energy=2e16,
            total_population=2e12,
            average_energy=8e13,
            average_population=8e9,
            contacts_count=15,
            attacks_count=5,
            cosmic_strikes=0,
        )
        saver.save_step(stats, step=5)

        with open(tmp_path / "summary.csv", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 1
        row = rows[0]
        assert row["step"] == "5"
        assert row["total"] == "250"
        assert row["new_born"] == "12"
        assert row["destroyed"] == "3"
        assert row["level_1"] == "100"
        assert row["level_2"] == "80"
        assert row["level_3"] == "50"
        assert row["level_4"] == "15"
        assert row["level_5"] == "5"
        assert row["avg_level"] == "2.50"
        assert row["max_level"] == "5"
        assert row["tech_explosions"] == "2"
        assert row["exposed_civilizations"] == "20"
        assert row["contacts_count"] == "15"
        assert row["attacks_count"] == "5"
        assert row["cosmic_strikes"] == "0"

    def test_save_summary_init_file_idempotent(self, tmp_path: Path) -> None:
        """验证 _init_summary_file 幂等 — 多次调用不重复写表头。"""
        config = make_config(tmp_path, save_step_data=False)
        saver = DataSaver(config)
        saver._init_summary_file()
        saver._init_summary_file()  # 第二次调用

        with open(tmp_path / "summary.csv", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        # 只有一行表头（没有重复）
        assert len(rows) == 1


# =============================================================================
# O3.4 — JSON 状态保存
# =============================================================================


class TestSaveSimulationState:
    """验证 JSON 状态保存。"""

    def test_save_state_creates_json(self, tmp_path: Path) -> None:
        """验证 save_simulation_state 创建了 state.json。"""
        config = make_config(tmp_path)
        saver = DataSaver(config)
        saver.save_simulation_state(
            civilizations=stub_civilizations(),
            current_step=42,
            next_id=100,
        )
        assert (tmp_path / "state.json").exists()

    def test_save_state_valid_json(self, tmp_path: Path) -> None:
        """验证文件内容是合法的 JSON。"""
        config = make_config(tmp_path)
        saver = DataSaver(config)
        saver.save_simulation_state(
            civilizations=stub_civilizations(),
            current_step=42,
            next_id=100,
        )
        with open(tmp_path / "state.json", encoding="utf-8") as f:
            data = json.load(f)

        assert "config" in data
        assert "current_step" in data
        assert "next_id" in data
        assert "civilizations" in data

    def test_save_state_contains_config(self, tmp_path: Path) -> None:
        """验证状态 JSON 包含配置信息。"""
        config = make_config(tmp_path, universe_size=5000.0, total_steps=200)
        saver = DataSaver(config)
        saver.save_simulation_state(
            civilizations=stub_civilizations(),
            current_step=10,
            next_id=50,
        )
        with open(tmp_path / "state.json", encoding="utf-8") as f:
            data = json.load(f)

        assert data["config"]["universe_size"] == 5000.0
        assert data["config"]["total_steps"] == 200

    def test_save_state_contains_step_and_next_id(self, tmp_path: Path) -> None:
        """验证状态 JSON 包含当前步和 next_id。"""
        config = make_config(tmp_path)
        saver = DataSaver(config)
        saver.save_simulation_state(
            civilizations=stub_civilizations(),
            current_step=99,
            next_id=500,
        )
        with open(tmp_path / "state.json", encoding="utf-8") as f:
            data = json.load(f)

        assert data["current_step"] == 99
        assert data["next_id"] == 500

    def test_save_state_contains_civilizations(self, tmp_path: Path) -> None:
        """验证状态 JSON 包含文明列表。"""
        config = make_config(tmp_path)
        saver = DataSaver(config)
        civs = stub_civilizations(count=3)
        saver.save_simulation_state(
            civilizations=civs,
            current_step=1,
            next_id=10,
        )
        with open(tmp_path / "state.json", encoding="utf-8") as f:
            data = json.load(f)

        assert len(data["civilizations"]) == 3
        for i, civ_data in enumerate(data["civilizations"]):
            assert civ_data["id"] == i
            assert civ_data["name"] == f"Civ #{i}"
            assert civ_data["is_alive"] is True
            assert isinstance(civ_data["x"], float)
            assert isinstance(civ_data["population"], float)
            assert isinstance(civ_data["level"], int)

    def test_save_state_with_empty_civs(self, tmp_path: Path) -> None:
        """验证空文明列表也能保存。"""
        config = make_config(tmp_path)
        saver = DataSaver(config)
        saver.save_simulation_state(
            civilizations=[],
            current_step=0,
            next_id=0,
        )
        with open(tmp_path / "state.json", encoding="utf-8") as f:
            data = json.load(f)

        assert data["civilizations"] == []
        assert data["current_step"] == 0

    def test_save_state_custom_filename(self, tmp_path: Path) -> None:
        """验证支持自定义文件名。"""
        config = make_config(tmp_path)
        saver = DataSaver(config)
        saver.save_simulation_state(
            civilizations=[],
            current_step=0,
            next_id=0,
            filename="checkpoint.json",
        )
        assert (tmp_path / "checkpoint.json").exists()
        assert not (tmp_path / "state.json").exists()


# =============================================================================
# O3.5 — 批处理结果保存
# =============================================================================


class TestSaveBatchSummary:
    """验证批处理结果 CSV 保存。"""

    def test_save_batch_summary_creates_csv(self, tmp_path: Path) -> None:
        """验证 save_batch_summary 创建了 CSV。"""
        config = make_config(tmp_path)
        saver = DataSaver(config)
        saver.save_batch_summary([
            {"run": 1, "survived": 500, "avg_level": 3.2},
        ])
        assert (tmp_path / "batch_summary.csv").exists()

    def test_save_batch_summary_header_and_rows(self, tmp_path: Path) -> None:
        """验证批处理 CSV 包含正确的表头和数据。"""
        config = make_config(tmp_path)
        saver = DataSaver(config)
        results = [
            {"run": 1, "survived": 500, "avg_level": 3.2, "steps": 1000},
            {"run": 2, "survived": 300, "avg_level": 4.1, "steps": 800},
        ]
        saver.save_batch_summary(results)

        with open(tmp_path / "batch_summary.csv", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 2
        assert rows[0]["run"] == "1"
        assert rows[0]["survived"] == "500"
        assert rows[1]["run"] == "2"
        assert rows[1]["avg_level"] == "4.1"

    def test_save_batch_summary_empty_results(self, tmp_path: Path) -> None:
        """验证空结果列表不创建文件。"""
        config = make_config(tmp_path)
        saver = DataSaver(config)
        saver.save_batch_summary([])
        assert not (tmp_path / "batch_summary.csv").exists()

    def test_save_batch_summary_uses_fieldnames_from_first_dict(
        self, tmp_path: Path,
    ) -> None:
        """验证 CSV 列头使用第一个字典的键。"""
        config = make_config(tmp_path)
        saver = DataSaver(config)
        results = [
            {"run_id": 1, "metric_a": 10.5, "metric_b": "yes"},
            {"run_id": 2, "metric_a": 20.3, "metric_b": "no"},
        ]
        saver.save_batch_summary(results)

        with open(tmp_path / "batch_summary.csv", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)

        assert header == ["run_id", "metric_a", "metric_b"]

    def test_save_batch_summary_custom_filename(self, tmp_path: Path) -> None:
        """验证支持自定义批处理文件名。"""
        config = make_config(tmp_path)
        saver = DataSaver(config)
        saver.save_batch_summary(
            [{"run": 1}],
            filename="batch_results.csv",
        )
        assert (tmp_path / "batch_results.csv").exists()
        assert not (tmp_path / "batch_summary.csv").exists()


# =============================================================================
# O3.6 — 资源清理
# =============================================================================


class TestClose:
    """验证 close() 释放资源。"""

    def test_close_releases_file_handle(self, tmp_path: Path) -> None:
        """验证 close 后内部文件句柄为 None。"""
        config = make_config(tmp_path, save_step_data=False)
        saver = DataSaver(config)
        saver.save_step(stub_stats(step=1), step=1)
        assert saver._summary_file is not None

        saver.close()
        assert saver._summary_file is None
        assert saver._summary_writer is None

    def test_close_allows_reopen(self, tmp_path: Path) -> None:
        """验证 close 后再次写入可正确重建文件。"""
        config = make_config(tmp_path, save_step_data=False)
        saver = DataSaver(config)
        saver.save_step(stub_stats(step=1), step=1)
        saver.close()

        # 关闭后再次写入应重新初始化
        saver.save_step(stub_stats(step=2), step=2)

        with open(tmp_path / "summary.csv", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 2
        assert rows[0]["step"] == "1"
        assert rows[1]["step"] == "2"

    def test_close_idempotent(self, tmp_path: Path) -> None:
        """验证 close 多次调用不会报错。"""
        config = make_config(tmp_path)
        saver = DataSaver(config)
        saver.close()
        saver.close()  # 第二次调用
        # 不应抛出异常


# =============================================================================
# O3.7 — IO 错误容错
# =============================================================================


class TestIOErrorTolerance:
    """验证 IO 错误不导致模拟崩溃。"""

    def test_save_step_io_error_does_not_crash(self, tmp_path: Path) -> None:
        """验证步文件写入 IOError 时打印警告不崩溃。"""
        config = make_config(tmp_path, save_summary=False)
        saver = DataSaver(config)

        # 将输出目录替换为不可写的文件路径来触发 OSError
        bad_path = tmp_path / "not_a_dir"
        bad_path.write_text("i am a file, not a directory")
        saver.output_dir = bad_path

        # 不应抛出异常
        saver.save_step(stub_stats(step=1), step=1)
        # 执行到此处即表示通过

    def test_save_summary_io_error_does_not_crash(self, tmp_path: Path) -> None:
        """验证汇总写入 IOError 时打印警告不崩溃。"""
        config = make_config(tmp_path, save_step_data=False)
        saver = DataSaver(config)

        # 将输出目录替换为不可写路径
        bad_path = tmp_path / "not_a_dir"
        bad_path.write_text("i am a file, not a directory")
        saver.output_dir = bad_path

        saver.save_step(stub_stats(step=1), step=1)
        # 执行到此处即表示通过

    def test_save_state_io_error_does_not_crash(self, tmp_path: Path) -> None:
        """验证状态保存 IOError 时打印警告不崩溃。"""
        config = make_config(tmp_path)
        saver = DataSaver(config)

        bad_path = tmp_path / "not_a_dir"
        bad_path.write_text("i am a file, not a directory")
        saver.output_dir = bad_path

        saver.save_simulation_state(
            civilizations=stub_civilizations(),
            current_step=1,
            next_id=10,
        )
        # 执行到此处即表示通过

    def test_save_batch_io_error_does_not_crash(self, tmp_path: Path) -> None:
        """验证批处理保存 IOError 时打印警告不崩溃。"""
        config = make_config(tmp_path)
        saver = DataSaver(config)

        bad_path = tmp_path / "not_a_dir"
        bad_path.write_text("i am a file, not a directory")
        saver.output_dir = bad_path

        saver.save_batch_summary([{"run": 1}])
        # 执行到此处即表示通过

    def test_close_io_error_does_not_crash(self, tmp_path: Path) -> None:
        """验证 close 中 IOError 不崩溃。"""
        config = make_config(tmp_path)
        saver = DataSaver(config)

        # 先让 summary_file 打开
        saver.save_step(stub_stats(step=1), step=1)

        # 手动注入一个已关闭的文件句柄来触发 close 时的异常
        if saver._summary_file is not None:
            saver._summary_file.close()  # 提前关闭

        saver.close()  # 再次 close 不应崩溃
        # 执行到此处即表示通过


# =============================================================================
# 综合 / 边界情况
# =============================================================================


class TestEdgeCases:
    """验证边界情况。"""

    def test_save_step_with_both_disabled(self, tmp_path: Path) -> None:
        """验证 save_step_data=False & save_summary=False 时 save_step 安全跳过。"""
        config = make_config(
            tmp_path, save_step_data=False, save_summary=False,
        )
        saver = DataSaver(config)
        # 不应抛出异常
        saver.save_step(stub_stats(step=1), step=1)
        # 不应创建任何文件
        assert not list(tmp_path.iterdir())

    def test_save_step_called_without_init_file(self, tmp_path: Path) -> None:
        """验证先调 save_step（含汇总）再关闭后重新写入以追加模式工作。"""
        config = make_config(tmp_path, save_step_data=False)
        saver = DataSaver(config)

        saver.save_step(stub_stats(step=1), step=1)
        saver.close()

        # 重新创建 saver（模拟新会话），应以追加模式写入
        saver2 = DataSaver(config)
        saver2.save_step(stub_stats(step=2, total_civilizations=200), step=2)
        saver2.close()

        with open(tmp_path / "summary.csv", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # 追加模式：旧数据保留，新数据追加
        assert len(rows) == 2
        assert rows[0]["step"] == "1"
        assert rows[0]["total"] == "100"
        assert rows[1]["step"] == "2"
        assert rows[1]["total"] == "200"

    def test_output_dir_is_default_string_path(self) -> None:
        """验证使用默认字符串路径也能工作。"""
        # 使用系统临时目录避免污染实际输出
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            config = SimulationConfig(output_dir=tmp)
            saver = DataSaver(config)
            saver.save_step(stub_stats(step=1), step=1)
            assert Path(tmp, "step_000001.csv").exists()
            saver.close()
