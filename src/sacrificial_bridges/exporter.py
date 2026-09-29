"""Экспорт результата в STL."""
from __future__ import annotations

from pathlib import Path

import trimesh

from .bridge_builder import merge_meshes
from .strategist import StrategyResult


def export_combined_stl(
    original_mesh: trimesh.Trimesh,
    bridges: list[trimesh.Trimesh],
    trees: list[trimesh.Trimesh],
    output_path: Path | str,
) -> Path:
    """Объединяет оригинальную модель + мостики + tree supports и сохраняет в STL.

    Args:
        original_mesh: исходная модель
        bridges: список mesh-ей мостиков
        trees: список mesh-ей tree supports
        output_path: куда сохранить

    Returns:
        Path к сохранённому файлу
    """
    output_path = Path(output_path)

    meshes_to_merge = [original_mesh]
    meshes_to_merge.extend(bridges)
    meshes_to_merge.extend(trees)

    combined = merge_meshes(meshes_to_merge)

    combined.export(str(output_path))
    return output_path


def export_separate_stls(
    original_mesh: trimesh.Trimesh,
    bridges: list[trimesh.Trimesh],
    trees: list[trimesh.Trimesh],
    output_dir: Path | str,
    prefix: str = "model",
) -> dict[str, Path]:
    """Сохраняет отдельно: оригинал, мостики, tree supports.

    Returns:
        dict с путями к файлам
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = {}

    # Оригинал
    orig_path = output_dir / f"{prefix}_original.stl"
    original_mesh.export(str(orig_path))
    paths["original"] = orig_path

    # Мостики (все вместе)
    if bridges:
        bridges_path = output_dir / f"{prefix}_bridges.stl"
        bridges_merged = merge_meshes(bridges)
        bridges_merged.export(str(bridges_path))
        paths["bridges"] = bridges_path

    # Tree supports (все вместе)
    if trees:
        trees_path = output_dir / f"{prefix}_trees.stl"
        trees_merged = merge_meshes(trees)
        trees_merged.export(str(trees_path))
        paths["trees"] = trees_path

    # Комбинированный (для импорта в слайсер)
    combined_path = output_dir / f"{prefix}_with_supports.stl"
    combined = merge_meshes([original_mesh] + bridges + trees)
    combined.export(str(combined_path))
    paths["combined"] = combined_path

    return paths
