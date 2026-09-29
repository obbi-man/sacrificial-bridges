"""CLI интерфейс для sacrificial-bridges."""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

if hasattr(sys.stdout, "buffer"):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

from . import __version__
from .analyzer import analyze_model
from .bridge_builder import build_bridges
from .exporter import export_combined_stl, export_separate_stls
from .strategist import compute_strategy, SupportStrategy
from .tree_builder import build_tree_supports, estimate_material


def print_colored(text: str, color: str = "") -> str:
    colors = {
        "green": "\033[92m", "yellow": "\033[93m", "red": "\033[91m",
        "cyan": "\033[96m", "bold": "\033[1m", "reset": "\033[0m",
    }
    c = colors.get(color, "")
    return f"{c}{text}{colors['reset']}" if c else text


def cmd_analyze(args: argparse.Namespace) -> int:
    """Анализ модели: overhangs, статистика."""
    file_path = Path(args.file)
    print(print_colored(f"\n📐 Анализ {file_path.name}", "cyan"))

    stats = analyze_model(file_path, overhang_angle=args.angle)
    print(stats.summary())
    print()
    print(f"Найдено {len(stats.overhangs)} групп overhangs:")
    for i, oh in enumerate(stats.overhangs[:15], 1):
        print(f"  #{i}: {len(oh.face_indices)} граней, "
              f"угол={oh.angle_from_vertical:.1f}°, "
              f"Z=[{oh.min_z:.1f}, {oh.max_z:.1f}], "
              f"площадь={oh.area:.1f}мм²")
    if len(stats.overhangs) > 15:
        print(f"  ... и ещё {len(stats.overhangs) - 15} групп")
    return 0


def cmd_process(args: argparse.Namespace) -> int:
    """Обработка модели: анализ + стратегия + генерация + экспорт."""
    file_path = Path(args.file)
    if not file_path.exists():
        print(print_colored(f"❌ Файл не найден: {file_path}", "red"))
        return 1

    print(print_colored(f"\n🔧 Обработка {file_path.name}", "cyan"))

    # 1. Анализ
    stats = analyze_model(file_path, overhang_angle=args.angle)
    print(f"  {len(stats.overhangs)} групп overhangs найдено")

    if not stats.overhangs:
        print(print_colored("  ✅ Overhangs не найдены — поддержки не нужны!", "green"))
        return 0

    # 2. Стратегия
    print(f"\n{print_colored('📐 Стратегия:', 'cyan')}")
    strategy = compute_strategy(
        stats.overhangs,
        stats._mesh if hasattr(stats, "_mesh") else None,
        bridge_max_length=args.bridge_max,
        tree_min_height=args.tree_min_height,
        safe_mode=not args.no_safe_mode,
    )
    print(strategy.summary())

    # 3. Генерация
    print(f"\n{print_colored('🛠️  Генерация:', 'cyan')}")

    bridges = build_bridges(
        strategy.decisions,
        bridge_width=args.bridge_width,
        bridge_height=args.bridge_height,
    )
    trees = build_tree_supports(
        strategy.decisions,
        trunk_radius=args.trunk_radius,
        branch_length=args.branch_length,
    )

    # Статистика материала
    mass, volume = estimate_material(trees, bridges)
    print(f"  Мостиков:    {len(bridges)}")
    print(f"  Tree supports: {len(trees)}")
    print(f"  Масса материала: ~{mass:.2f}г ({volume:.2f}см³)")

    # 4. Экспорт
    output_dir = Path(args.output) if args.output else file_path.parent / "sacrificial_output"
    output_dir.mkdir(parents=True, exist_ok=True)

    prefix = args.prefix or file_path.stem

    if args.separate:
        paths = export_separate_stls(
            stats._mesh if hasattr(stats, "_mesh") else None,
            bridges, trees, output_dir, prefix
        )
    else:
        # Перезагрузим mesh для экспорта
        from .analyzer import load_mesh
        mesh = load_mesh(file_path)
        combined_path = output_dir / f"{prefix}_with_supports.stl"
        export_combined_stl(mesh, bridges, trees, combined_path)
        paths = {"combined": combined_path}

    print(f"\n{print_colored('💾 Экспортировано:', 'cyan')}")
    for name, path in paths.items():
        size_kb = path.stat().st_size / 1024
        print(f"  {name:10} → {path.name}  ({size_kb:.1f} КБ)")

    print(f"\n{print_colored('🎉 Готово!', 'green')}")
    print(f"  Открой {paths.get('combined', list(paths.values())[0])} в PrusaSlicer/Cura/Bambu Studio.")
    print(f"  Уже нарезанный G-code готов к печати — поддержки добавлены автоматически.")

    return 0


def cmd_info(args: argparse.Namespace) -> int:
    """Информация о плагине."""
    print(print_colored("\n🌉 Sacrificial Bridges", "cyan"))
    print(f"  Версия: {__version__}")
    print(f"  Лицензия: MIT")
    print()
    print(f"  {print_colored('Что умеет:', 'green')}")
    print(f"  • Анализирует STL — находит overhangs")
    print(f"  • Решает: bridge (мостик) или tree support")
    print(f"  • Мостик если рядом есть деталь (экономия 60-70%)")
    print(f"  • Tree support в опасных местах")
    print(f"  • Экспортирует STL с поддержками")
    print()
    print(f"  {print_colored('В планах:', 'yellow')}")
    print(f"  • GUI с 3D визуализацией")
    print(f"  • Плагин для PrusaSlicer / Cura / Bambu")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="sacrificial-bridges",
        description="Мостики и tree supports для 3D-печати",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  sacrificial-bridges analyze model.stl                       # только анализ
  sacrificial-bridges process model.stl                      # обработать
  sacrificial-bridges process model.stl --bridge-max 20      # длиннее мостики
  sacrificial-bridges process model.stl --no-safe-mode       # без проверок
        """,
    )
    subparsers = parser.add_subparsers(dest="command", help="Команды")

    # process
    p_proc = subparsers.add_parser(
        "process",
        help="Обработать модель: мостики + tree supports",
    )
    p_proc.add_argument("file", help="Путь к STL файлу")
    p_proc.add_argument("--output", "-o", help="Папка для результатов")
    p_proc.add_argument("--prefix", "-p", help="Префикс для имён файлов")
    p_proc.add_argument("--angle", type=float, default=45.0,
                        help="Угол overhang (градусы, по умолчанию 45)")
    p_proc.add_argument("--bridge-max", type=float, default=15.0,
                        help="Макс. длина мостика (мм, по умолчанию 15)")
    p_proc.add_argument("--bridge-width", type=float, default=4.0,
                        help="Ширина мостика (мм, по умолчанию 4)")
    p_proc.add_argument("--bridge-height", type=float, default=0.8,
                        help="Высота мостика (мм, по умолчанию 0.8)")
    p_proc.add_argument("--tree-min-height", type=float, default=5.0,
                        help="Мин. высота для мостика (мм, ниже — tree)")
    p_proc.add_argument("--trunk-radius", type=float, default=0.6,
                        help="Радиус ствола tree support (мм)")
    p_proc.add_argument("--branch-length", type=float, default=1.5,
                        help="Длина веток (мм)")
    p_proc.add_argument("--no-safe-mode", action="store_true",
                        help="Без проверок безопасности (больше мостиков)")
    p_proc.add_argument("--separate", action="store_true",
                        help="Сохранять bridge/tree отдельно (для слайсера)")
    p_proc.set_defaults(func=cmd_process)

    # analyze
    p_an = subparsers.add_parser("analyze", help="Только анализ")
    p_an.add_argument("file", help="Путь к STL файлу")
    p_an.add_argument("--angle", type=float, default=45.0,
                      help="Угол overhang (градусы)")
    p_an.set_defaults(func=cmd_analyze)

    # info
    p_info = subparsers.add_parser("info", help="Информация о плагине")
    p_info.set_defaults(func=cmd_info)

    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    args = parser.parse_args()

    if not hasattr(args, "func"):
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
