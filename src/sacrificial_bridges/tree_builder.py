"""Генератор tree supports для опасных overhangs."""
from __future__ import annotations

import math

import numpy as np
import trimesh

from .strategist import StrategyDecision


def create_tree_support(
    target: np.ndarray,
    base_z: float = 0.0,
    trunk_radius: float = 0.6,
    trunk_height: float | None = None,
    branch_length: float = 1.5,
    branch_radius: float = 0.3,
    depth: int = 2,
) -> trimesh.Trimesh:
    """Создаёт mesh tree support.

    Args:
        target: точка (x, y, z) где overhang требует поддержки
        base_z: Z стола (обычно 0)
        trunk_radius: радиус ствола (мм)
        trunk_height: высота ствола до первой ветки (если None — авто)
        branch_length: длина веток (мм)
        branch_radius: радиус веток (мм)
        depth: глубина ветвления (2-3 норм)

    Returns:
        trimesh.Trimesh — mesh tree support
    """
    x, y, z = target
    if z <= base_z:
        # Overhang уже на столе
        return trimesh.Trimesh()

    trunk_h = trunk_height or (z - base_z) * 0.5

    meshes = []

    # Ствол — цилиндр
    trunk = trimesh.creation.cylinder(
        radius=trunk_radius,
        height=trunk_h,
        sections=8,
    )
    # Позиция: середина ствола
    trunk.apply_translation([x, y, base_z + trunk_h / 2])
    meshes.append(trunk)

    # Ветки на разных высотах
    branch_heights = []
    if depth >= 1:
        branch_heights.append(base_z + trunk_h)
    if depth >= 2:
        branch_heights.append(base_z + trunk_h + (z - base_z - trunk_h) * 0.5)
    if depth >= 3:
        branch_heights.append(z - branch_length * 0.5)

    # Углы для веток (равномерно вокруг)
    for i, bh in enumerate(branch_heights):
        if bh >= z:
            continue

        n_branches = 4 if i == 0 else 3
        for j in range(n_branches):
            angle = (2 * math.pi * j / n_branches) + (i * 0.5)
            # Ветка растёт от ствола наружу
            direction = np.array([math.cos(angle), math.sin(angle), 0])
            end_point = np.array([x, y, bh]) + direction * branch_length * (1.5 if i == 0 else 1.2)
            end_point[2] = min(end_point[2], z - 0.5)  # не выше target

            branch = trimesh.creation.cylinder(
                radius=branch_radius * (1.0 - i * 0.2),
                height=branch_length,
                sections=6,
            )

            # Поворачиваем ветку: должна идти от (x, y, bh) в направлении direction
            # Цилиндр по умолчанию по Y. Повернём к direction.
            default_axis = np.array([0.0, 1.0, 0.0])
            target_axis = np.array([direction[0], direction[1], 0.0])
            target_axis_norm = target_axis / (np.linalg.norm(target_axis) + 1e-9)

            v = np.cross(default_axis, target_axis_norm)
            s = np.linalg.norm(v)
            c = np.dot(default_axis, target_axis_norm)

            if s < 1e-6:
                if c > 0:
                    rotation = np.eye(4)
                else:
                    rotation = trimesh.transformations.rotation_matrix(
                        np.pi, [0, 0, 1]
                    )
            else:
                v = v / s
                angle_rad = np.arccos(np.clip(c, -1.0, 1.0))
                rotation = trimesh.transformations.rotation_matrix(angle_rad, v)

            branch.apply_transform(rotation)
            # Центрируем: начало ветки в (x, y, bh), длина branch_length
            # После поворота ветка длиной branch_length идёт от (0,0,0) к (0, branch_length, 0)
            # Новое начало = (x, y, bh), длина = branch_length
            start_point = np.array([x, y, bh])
            center = start_point + target_axis_norm * (branch_length / 2)
            branch.apply_translation(center)
            meshes.append(branch)

    return trimesh.util.concatenate(meshes) if meshes else trimesh.Trimesh()


def build_tree_supports(
    decisions: list[StrategyDecision],
    base_z: float = 0.0,
    trunk_radius: float = 0.6,
    branch_length: float = 1.5,
) -> list[trimesh.Trimesh]:
    """Строит mesh tree supports для всех решений со стратегией tree."""
    trees = []
    for d in decisions:
        if d.strategy != "tree":
            continue
        mesh = create_tree_support(
            target=d.overhang.center,
            base_z=base_z,
            trunk_radius=trunk_radius,
            branch_length=branch_length,
        )
        if len(mesh.vertices) > 0:
            trees.append(mesh)
    return trees


def estimate_material(
    trees: list[trimesh.Trimesh],
    bridges: list[trimesh.Trimesh],
    plastic_density: float = 1.24,
) -> tuple[float, float]:
    """Оценивает массу материала (в граммах).

    Returns:
        (total_mass_g, total_volume_cm3)
    """
    total_volume = 0.0
    for m in trees + bridges:
        total_volume += m.volume

    total_mass = (total_volume / 1000.0) * plastic_density  # мм³ → см³ → г
    return total_mass, total_volume / 1000.0
