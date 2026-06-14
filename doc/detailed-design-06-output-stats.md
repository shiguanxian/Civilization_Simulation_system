# 详细设计文档 — 第6部分：输出与统计模块

## 1. 模块概述

### 1.1 模块职责

`src/output/` 目录下包含两个模块：

| 模块 | 文件 | 职责 |
|------|------|------|
| **StatsCollector** | `stats.py` | 收集并计算每步的统计数据 |
| **DataSaver** | `data_saver.py` | 将统计数据保存到文件（CSV），管理输出目录 |

### 1.2 设计原则

- **模拟引擎不直接处理输出**：引擎只管计算，输出由独立的模块处理
- **数据格式统一**：所有输出数据使用相同的字段名和类型
- **增量保存**：汇总数据逐行追加，不重写整个文件
- **容错**：文件写入失败不中断模拟，仅输出告警

---

## 2. 统计模块 (`src/output/stats.py`)

### 2.1 StepStats 数据结构

```python
@dataclass
class StepStats:
    """一个时间步的完整统计数据。"""
    # 基本信息
    step: int                          # 时间步
    total_civilizations: int           # 存活文明总数
    new_born: int                      # 本步新生文明数
    destroyed: int                     # 本步被毁灭文明数

    # 等级分布
    level_distribution: dict[int, int] # {等级: 数量}
    average_level: float               # 平均等级
    max_level: int                     # 最高等级

    # 科技水平
    average_tech_points: float         # 平均科技点数
    total_tech_points: float           # 总科技点数
    tech_explosions: int               # 本步技术爆炸次数

    # 行为统计
    average_aggressiveness: float      # 平均攻击性
    average_stealth: float             # 平均隐蔽性
    exposed_civilizations: int         # 暴露坐标的文明数

    # 空间分布
    average_detection_range: float     # 平均探测范围
    average_expansion_radius: float    # 平均扩张半径

    # 能量与人口
    total_energy: float                # 总能量输出
    total_population: float            # 总人口
    average_energy: float              # 平均能量输出
    average_population: float          # 平均人口

    # 接触与攻击
    contacts_count: int                # 本步接触事件数
    attacks_count: int                 # 本步攻击事件数
    cosmic_strikes: int                # 本步宇宙打击次数
```

### 2.2 StatsCollector 类设计

```python
class StatsCollector:
    """
    统计信息收集器。
    
    每步由 Simulation 调用 collect()，传入当前文明列表和本步事件记录。
    维护历史统计数据列表（用于生成汇总和图表）。
    """

    def __init__(self):
        self.history: list[StepStats] = []

    def collect(self, 
                civilizations: list[Civilization],
                step: int,
                step_events: list[SimEvent] | None = None,
                previous_stats: StepStats | None = None,
                ) -> StepStats:
        """
        从当前文明列表收集统计信息。
        
        参数：
            civilizations: 当前所有存活文明列表
            step: 当前时间步
            step_events: 本步发生的事件列表（可选）
            previous_stats: 上一步的统计数据（用于计算增量，可选）
        
        返回值：StepStats 实例
        """
        alive_civs = [c for c in civilizations if c.is_alive]
        total = len(alive_civs)

        if total == 0:
            return StepStats(step=step, total_civilizations=0, ...)

        # 等级分布
        level_dist = {}
        for civ in alive_civs:
            level_dist[civ.level] = level_dist.get(civ.level, 0) + 1

        # 平均值计算（使用 numpy 加速，如果可用）
        avg_level = sum(c.level for c in alive_civs) / total
        avg_tech = sum(c.tech_points for c in alive_civs) / total
        avg_aggr = sum(c.aggressiveness for c in alive_civs) / total
        avg_stealth = sum(c.stealth for c in alive_civs) / total
        avg_detect = sum(c.detection_range for c in alive_civs) / total
        avg_expand = sum(c.expansion_radius for c in alive_civs) / total
        avg_energy = sum(c.energy_output for c in alive_civs) / total
        avg_pop = sum(c.population for c in alive_civs) / total

        # 从事件中统计增量数据
        new_born = 0
        destroyed = 0
        tech_explosions = 0
        contacts_count = 0
        attacks_count = 0
        cosmic_strikes = 0

        if step_events:
            for event in step_events:
                if event.event_type == "birth":
                    new_born += 1
                elif event.event_type == "destruction":
                    destroyed += 1
                elif event.event_type == "tech_explosion":
                    tech_explosions += 1
                elif event.event_type == "contact":
                    contacts_count += 1
                elif event.event_type == "attack":
                    attacks_count += 1
                elif event.event_type == "cosmic_strike":
                    cosmic_strikes += 1

        # 或者通过比较上一步的数据计算（如果 step_events 未提供）
        if previous_stats:
            new_born = total - previous_stats.total_civilizations + destroyed

        stats = StepStats(
            step=step,
            total_civilizations=total,
            new_born=new_born,
            destroyed=destroyed,
            level_distribution=level_dist,
            average_level=avg_level,
            max_level=max(level_dist.keys()) if level_dist else 0,
            average_tech_points=avg_tech,
            total_tech_points=sum(c.tech_points for c in alive_civs),
            tech_explosions=tech_explosions,
            average_aggressiveness=avg_aggr,
            average_stealth=avg_stealth,
            exposed_civilizations=sum(
                1 for c in alive_civs if c.communication_active
            ),
            average_detection_range=avg_detect,
            average_expansion_radius=avg_expand,
            total_energy=sum(c.energy_output for c in alive_civs),
            total_population=sum(c.population for c in alive_civs),
            average_energy=avg_energy,
            average_population=avg_pop,
            contacts_count=contacts_count,
            attacks_count=attacks_count,
            cosmic_strikes=cosmic_strikes,
        )

        self.history.append(stats)
        return stats

    def get_latest(self) -> StepStats | None:
        """获取最新的统计信息。"""
        return self.history[-1] if self.history else None

    def get_history_since(self, step: int) -> list[StepStats]:
        """获取从指定步数到现在的统计信息。"""
        return [s for s in self.history if s.step >= step]

    def clear(self) -> None:
        """清空历史。"""
        self.history.clear()
```

---

## 3. 数据保存模块 (`src/output/data_saver.py`)

### 3.1 DataSaver 类设计

```python
import csv
import os
import json
from pathlib import Path


class DataSaver:
    """
    数据保存器。
    
    负责在模拟过程中将统计数据保存到文件。
    所有模式下都在运行。
    """

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.output_dir = Path(config.output_dir)
        self._ensure_output_dir()

        # 文件句柄（延迟打开）
        self._summary_file: TextIO | None = None
        self._summary_writer: csv.DictWriter | None = None

    def _ensure_output_dir(self) -> None:
        """确保输出目录存在。"""
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ────────── 分步全量数据保存 ──────────

    def save_step(self, stats: StepStats, step: int) -> None:
        """
        保存当前步的统计数据到 CSV 文件。
        
        如果 config.save_step_data 为 True：
          生成文件 output/step_{step:06d}.csv
          包含本步所有存活文明的完整参数
          
        如果 config.save_summary 为 True：
          追加一行到 output/summary.csv
        """
        if self.config.save_step_data:
            self._save_step_full_data(stats, step)

        if self.config.save_summary:
            self._save_summary_row(stats)

    def _save_step_full_data(self, stats: StepStats, step: int) -> None:
        """
        保存本步的全量文明数据。
        
        文件名：step_000042.csv（6位数编号）
        格式：CSV，每行一个文明
        列：id, name, x, y, level, tech_points, population, ...
        """
        # 只在高性能模式下每隔 N 步保存全量数据
        # （避免大量小文件）
        if (self.config.run_mode == "fast" and 
            step % 10 != 0):  # 高性能模式每10步保存一次
            return

        filename = f"step_{step:06d}.csv"
        filepath = self.output_dir / filename

        # 从 Simulation 获取文明数据的方式：
        # 这里只保存统计摘要，全量数据通过 Simulation.save_state() 保存
        # 但为了满足需求，我们在 Simulation 中会传递文明列表
        # 这里用 stats 中的汇总数据保存一个摘要文件
        # 实际全量数据保存在 summary.csv 中

        # 每步全量数据过于庞大（几千文明 × 几百步 = 百万行量级）
        # 设计决策：仅保存摘要，全量数据通过 save_state() 按需保存
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "step", "total", "new_born", "destroyed",
                "avg_level", "max_level",
                "avg_tech", "avg_aggressiveness", "avg_stealth",
                "avg_detection_range", "avg_expansion_radius",
                "total_energy", "total_population",
                "exposed", "contacts", "attacks"
            ])
            writer.writerow([
                stats.step, stats.total_civilizations,
                stats.new_born, stats.destroyed,
                f"{stats.average_level:.2f}", stats.max_level,
                f"{stats.average_tech_points:.2f}",
                f"{stats.average_aggressiveness:.3f}",
                f"{stats.average_stealth:.3f}",
                f"{stats.average_detection_range:.1f}",
                f"{stats.average_expansion_radius:.1f}",
                f"{stats.total_energy:.2e}",
                f"{stats.total_population:.2e}",
                stats.exposed_civilizations,
                stats.contacts_count, stats.attacks_count,
            ])

    # ────────── 汇总数据保存 ──────────

    def _init_summary_file(self) -> None:
        """
        初始化汇总文件。
        
        文件：output/summary.csv
        格式：每步一行，包含所有关键指标
        """
        if self._summary_file is not None:
            return

        filepath = self.output_dir / "summary.csv"
        self._summary_file = open(filepath, "w", newline="", 
                                  encoding="utf-8")
        
        fieldnames = [
            "step", "total", "new_born", "destroyed",
            "avg_level", "max_level",
            "level_1", "level_2", "level_3", "level_4", "level_5",
            "avg_tech_points", "tech_explosions",
            "avg_aggressiveness", "avg_stealth",
            "avg_detection_range", "avg_expansion_radius",
            "total_energy", "total_population",
            "exposed_civilizations",
            "contacts_count", "attacks_count", "cosmic_strikes",
        ]
        self._summary_writer = csv.DictWriter(
            self._summary_file, fieldnames=fieldnames
        )
        self._summary_writer.writeheader()

    def _save_summary_row(self, stats: StepStats) -> None:
        """向汇总文件追加一行。"""
        try:
            if self._summary_file is None:
                self._init_summary_file()

            if self._summary_writer and self._summary_file:
                row = {
                    "step": stats.step,
                    "total": stats.total_civilizations,
                    "new_born": stats.new_born,
                    "destroyed": stats.destroyed,
                    "avg_level": f"{stats.average_level:.2f}",
                    "max_level": stats.max_level,
                    "level_1": stats.level_distribution.get(1, 0),
                    "level_2": stats.level_distribution.get(2, 0),
                    "level_3": stats.level_distribution.get(3, 0),
                    "level_4": stats.level_distribution.get(4, 0),
                    "level_5": stats.level_distribution.get(5, 0),
                    "avg_tech_points": f"{stats.average_tech_points:.2f}",
                    "tech_explosions": stats.tech_explosions,
                    "avg_aggressiveness": f"{stats.average_aggressiveness:.3f}",
                    "avg_stealth": f"{stats.average_stealth:.3f}",
                    "avg_detection_range": f"{stats.average_detection_range:.1f}",
                    "avg_expansion_radius": f"{stats.average_expansion_radius:.1f}",
                    "total_energy": f"{stats.total_energy:.2e}",
                    "total_population": f"{stats.total_population:.2e}",
                    "exposed_civilizations": stats.exposed_civilizations,
                    "contacts_count": stats.contacts_count,
                    "attacks_count": stats.attacks_count,
                    "cosmic_strikes": stats.cosmic_strikes,
                }
                self._summary_writer.writerow(row)
                self._summary_file.flush()  # 确保数据写入磁盘
        except IOError as e:
            print(f"[警告] 写入汇总文件失败: {e}")

    def save_simulation_state(self, simulation_state: dict, 
                              filename: str = "state.json") -> None:
        """
        保存模拟完整状态（用于断点续跑）。
        
        格式：JSON
        包含：配置、当前步数、所有文明参数
        """
        filepath = self.output_dir / filename
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(simulation_state, f, indent=2, 
                         ensure_ascii=False, default=str)
        except IOError as e:
            print(f"[警告] 保存状态文件失败: {e}")

    def save_batch_summary(self, batch_results: list[dict],
                           filename: str = "batch_summary.csv") -> None:
        """
        保存批处理模式的多组模拟汇总对比结果。
        
        每行对应一次运行，包含参数配置和最终统计。
        """
        filepath = self.output_dir / filename
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            if not batch_results:
                return
            writer = csv.DictWriter(f, fieldnames=batch_results[0].keys())
            writer.writeheader()
            writer.writerows(batch_results)

    def close(self) -> None:
        """关闭所有打开的文件句柄。"""
        if self._summary_file:
            self._summary_file.close()
            self._summary_file = None
            self._summary_writer = None
```

---

## 4. 终端输出格式化

在 `stats.py` 中添加终端输出格式函数：

```python
def format_step_summary(stats: StepStats) -> str:
    """
    格式化时间步的概要信息，用于终端输出。
    
    输出示例：
    ── 时间步: 0042 ──────────────────────────
    存活文明: 4,238  | 新生: 12  | 毁灭: 8
    最高等级: 4      | 平均等级: 2.1
    科技爆炸: 2      | 暴露文明: 156
    接触: 45 次      | 攻击: 12 次
    总能量: 3.45e18  | 总人口: 2.10e14
    ──────────────────────────────────────────
    """
    lines = [
        f"── 时间步: {stats.step:04d} " + "─" * 40,
        (f"存活文明: {stats.total_civilizations:,d}  "
         f"| 新生: {stats.new_born}  | 毁灭: {stats.destroyed}"),
        (f"最高等级: {stats.max_level}      "
         f"| 平均等级: {stats.average_level:.1f}"),
        (f"科技爆炸: {stats.tech_explosions}      "
         f"| 暴露文明: {stats.exposed_civilizations}"),
        (f"接触: {stats.contacts_count} 次      "
         f"| 攻击: {stats.attacks_count} 次"),
        (f"总能量: {stats.total_energy:.2e}  "
         f"| 总人口: {stats.total_population:.2e}"),
        "─" * 56,
    ]
    return "\n".join(lines)
```

---

## 5. 模块的独立可测试性

### 5.1 测试要点

```python
# tests/test_output_stats.py

def test_collect_empty():
    """验证空文明列表的统计。"""
    stats = StatsCollector()
    result = stats.collect([], step=0)
    assert result.total_civilizations == 0

def test_collect_single():
    """验证单个文明的统计正确。"""
    civ = Civilization(id=1, ..., level=3, ...)
    stats = StatsCollector()
    result = stats.collect([civ], step=1)
    assert result.total_civilizations == 1
    assert result.average_level == 3.0
    assert result.max_level == 3

def test_collect_multiple():
    """验证多个文明的统计正确。"""
    ...

def test_level_distribution():
    """验证等级分布统计正确。"""
    ...

def test_history_tracking():
    """验证历史记录正确追加。"""
    ...


# tests/test_output_data_saver.py

def test_save_summary_creates_file(tmp_path):
    """验证保存汇总文件创建了正确的文件。"""
    config = SimulationConfig(output_dir=str(tmp_path))
    saver = DataSaver(config)
    stats = StepStats(step=1, total_civilizations=100, ...)
    saver.save_step(stats, step=1)
    assert (tmp_path / "summary.csv").exists()

def test_save_summary_content(tmp_path):
    """验证汇总文件内容正确。"""
    ...

def test_save_state_json(tmp_path):
    """验证状态保存为 JSON 格式正确。"""
    ...

def test_close_cleanup():
    """验证关闭后文件句柄释放。"""
    ...

def test_io_error_does_not_crash():
    """验证 IO 错误不导致模拟崩溃。"""
    ...
```

---

## 6. 依赖关系

```
stats.py       → entity.py（使用 Civilization 数据类型）
data_saver.py  → config.py（使用 SimulationConfig）
```

---

*下一篇：`detailed-design-07-visualization.md` — 可视化模块详细设计*
