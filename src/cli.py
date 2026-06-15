"""CLI 模块 —— 命令行参数解析与主调度入口。

提供：
- build_parser(): 构建 ArgumentParser 实例
- main(): 主调度函数，根据参数选择运行模式
"""

from __future__ import annotations

import argparse
import random
import sys

from src.config import SimulationConfig, detect_computer_capability, load_config


def build_parser() -> argparse.ArgumentParser:
    """构建并返回配置完成的 ArgumentParser。

    Returns:
        包含所有 CLI 参数的 ArgumentParser 实例。
    """
    parser = argparse.ArgumentParser(
        prog="simulation",
        description="宇宙文明模拟器 — 黑暗森林宇宙模拟",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "使用示例:\n"
            "  %(prog)s --fast --size 5000 --civs 100 --steps 100\n"
            "  %(prog)s --interactive --size 2000 --civs 50\n"
            "  %(prog)s --batch batch_config.json\n"
            "  %(prog)s --load save_state.json --fast\n"
            "  %(prog)s --detect-only\n"
        ),
    )

    # ── 运行模式（互斥） ─────────────────────────────────────────────────────
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--fast",
        action="store_true",
        default=False,
        dest="fast",
        help="高性能模式（无图表，仅终端输出）",
    )
    mode_group.add_argument(
        "--standard",
        action="store_true",
        default=False,
        dest="standard",
        help="标准模式（实时图表 + 终端输出，默认）",
    )
    mode_group.add_argument(
        "--interactive",
        action="store_true",
        default=False,
        dest="interactive",
        help="交互模式（tkinter 控制面板 + 实时图表）",
    )

    # ── 批量模式 ─────────────────────────────────────────────────────────────
    parser.add_argument(
        "--batch",
        type=str,
        default=None,
        dest="batch",
        metavar="CONFIG_FILE",
        help="批量模式，指定 JSON 配置文件路径",
    )

    # ── 宇宙参数 ─────────────────────────────────────────────────────────────
    parser.add_argument(
        "--size",
        type=float,
        default=None,
        dest="size",
        help="宇宙空间边长（光年）",
    )
    parser.add_argument(
        "--civs",
        "--initial-civs",
        type=int,
        default=None,
        dest="civs",
        help="初始文明数量",
    )
    parser.add_argument(
        "--max-civs",
        type=int,
        default=None,
        dest="max_civs",
        help="最大文明数量",
    )

    # ── 演化参数 ─────────────────────────────────────────────────────────────
    parser.add_argument(
        "--steps",
        type=int,
        default=None,
        dest="steps",
        help="总模拟步数",
    )
    parser.add_argument(
        "--birth-rate",
        type=float,
        default=None,
        dest="birth_rate",
        help="每步新文明诞生概率因子",
    )

    # ── 分布参数 ─────────────────────────────────────────────────────────────
    parser.add_argument(
        "--distribution",
        type=str,
        default=None,
        dest="distribution",
        choices=["uniform", "cluster"],
        help="初始文明分布模式",
    )
    parser.add_argument(
        "--clusters",
        type=int,
        default=None,
        dest="clusters",
        help="聚簇数量（distribution=cluster 时使用）",
    )

    # ── 输出参数 ─────────────────────────────────────────────────────────────
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        dest="output_dir",
        help="输出目录",
    )
    parser.add_argument(
        "--no-step-data",
        action="store_true",
        default=False,
        dest="no_step_data",
        help="禁止保存每步全量数据",
    )

    # ── 保存 / 加载 ──────────────────────────────────────────────────────────
    parser.add_argument(
        "--load",
        type=str,
        default=None,
        dest="load",
        metavar="STATE_FILE",
        help="从 JSON 状态文件加载模拟",
    )
    parser.add_argument(
        "--save-interval",
        type=int,
        default=None,
        dest="save_interval",
        help="每 N 步保存一次（默认 1）",
    )

    # ── 杂项 ─────────────────────────────────────────────────────────────────
    parser.add_argument(
        "--detect-only",
        action="store_true",
        default=False,
        dest="detect_only",
        help="仅检测计算机性能并输出报告，不运行模拟",
    )
    parser.add_argument(
        "--name-mode",
        type=str,
        default=None,
        dest="name_mode",
        choices=["auto", "number"],
        help="文明名称生成模式",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        dest="seed",
        help="随机种子（用于可复现模拟）",
    )

    return parser


def _apply_additional_cli_overrides(
    config: SimulationConfig,
    args: argparse.Namespace,
) -> None:
    """应用 ``_CLI_MAPPING`` 之外的 CLI 参数覆盖。

    ``load_config`` 已处理 ``_CLI_MAPPING``（见 src/config.py），
    此函数处理其余字段（distribution、clusters、output_dir 等）。
    """
    # 分布模式
    if args.distribution is not None:
        config.initial_distribution_mode = args.distribution

    # 聚簇数量
    if args.clusters is not None:
        config.cluster_count = args.clusters

    # 输出目录
    if args.output_dir is not None:
        config.output_dir = args.output_dir

    # 是否保存步数据
    if args.no_step_data:
        config.save_step_data = False

    # 保存间隔
    if args.save_interval is not None:
        config.save_interval = args.save_interval

    # 名称生成模式
    if args.name_mode is not None:
        config.name_generator_mode = args.name_mode

    # 运行模式
    if args.fast:
        config.run_mode = "fast"
    elif args.interactive:
        config.run_mode = "interactive"
    elif args.standard:
        config.run_mode = "standard"


def main(argv: list[str] | None = None) -> int:
    """主调度入口 —— 解析参数、初始化模拟、分发运行模式。

    Args:
        argv: 命令行参数列表。为 ``None`` 时使用 ``sys.argv[1:]``。

    Returns:
        进程退出码（0 表示成功）。
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    # ── 仅检测模式 ───────────────────────────────────────────────────────────
    if args.detect_only:
        cap = detect_computer_capability()
        try:
            print(cap.format_report())
        except UnicodeEncodeError:
            # Windows GBK 终端无法渲染部分 Unicode 字符（如 emoji）
            safe = cap.format_report().encode(
                sys.stdout.encoding or "utf-8", errors="replace"
            ).decode(sys.stdout.encoding or "utf-8")
            print(safe)
        return 0

    # ── 批量模式（不创建 Simulation） ─────────────────────────────────────────
    if args.batch is not None:
        from src.batch import BatchRunner

        runner = BatchRunner(args.batch)
        results = runner.run_all()
        runner.print_summary()
        runner._save_results()
        # 检查是否有失败项
        failures = [r for r in results if not r.success]
        if failures:
            print(
                f"\n⚠ 批量运行完成，{len(failures)} 个运行失败。",
                file=sys.stderr,
            )
        return 0

    # ── 加载配置 ─────────────────────────────────────────────────────────────
    config = load_config(args)
    _apply_additional_cli_overrides(config, args)

    # ── 设置随机种子 ─────────────────────────────────────────────────────────
    if args.seed is not None:
        random.seed(args.seed)

    # ── 创建 / 加载模拟实例 ──────────────────────────────────────────────────
    from src.simulation import Simulation

    if args.load is not None:
        sim = Simulation.load_state(args.load)
    else:
        sim = Simulation(config)
        sim.initialize()

    # ── 分发运行模式 ─────────────────────────────────────────────────────────
    if args.fast:
        from src.visualization.run_modes import run_fast

        run_fast(sim)
    elif args.interactive:
        try:
            from src.visualization.interactive import run_interactive

            run_interactive(sim)
        except ImportError:
            print(
                "错误: 交互模式依赖 tkinter，当前环境可能不支持。\n"
                "请尝试 --standard 或 --fast 模式。",
                file=sys.stderr,
            )
            return 1
    else:
        # 默认标准模式
        from src.visualization.run_modes import run_standard

        run_standard(sim)

    return 0


if __name__ == "__main__":
    sys.exit(main())
