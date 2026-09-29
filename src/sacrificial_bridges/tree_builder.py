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
    branch_angle: float = 45.0,
) -> trimesh.Trimesh:
    """Создаёт mesh tree support.

    Архитектура:
        - Ствол (цилиндр) от стола до первой развилки
        - На каждом уровне — N веток под углом branch_angle
        - Каждая ветка может иметь свои sub-ветки (depth)

    Args:
        target: точка (x, y, z) где overhang требует поддержки
        base_z: Z стола
        trunk_radius: радиус ствола
        trunk_height: высота до первой развилки (None = авто)
        branch_length: длина веток
        branch_radius: радиус веток
        depth: количество уровней ветвления (1-3)
        branch_angle: угол веток относительно вертикали (градусы)
    """
    x, y, z = target
    if z <= base_z + 1.0:
        # Overhang слишком близко к столу — не нужен tree support
        return trimesh.Trimesh()

    # Авто-высота ствола: ~50% от высоты до target
    trunk_h = trunk_height or (z - base_z) * 0.5
    # Ствол не ниже 5мм и не выше половины
    trunk_h = max(min(trunk_h, (z - base_z) * 0.7), 3.0)

    meshes = []

    # === Ствол ===
    trunk = trimesh.creation.cylinder(
        radius=trunk_radius,
        height=trunk_h,
        sections=10,
    )
    # Цилиндр по умолчанию по Y. Развернём по Z.
    trunk.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    # Позиция: центр ствола
    trunk.apply_translation([x, y, base_z + trunk_h / 2])
    meshes.append(trunk)

    # === Ветки ===
    # Уровни ветвления
    branch_levels = []
    if depth >= 1:
        # Первая развилка — наверху ствола
        branch_levels.append({
            "height": base_z + trunk_h,
            "count": 4,
            "radius": branch_radius,
            "length": branch_length,
        })
    if depth >= 2:
        # Вторая развилка — посередине между стволом и target
        mid = base_z + trunk_h + (z - base_z - trunk_h) * 0.5
        if mid < z - branch_length:
            branch_levels.append({
                "height": mid,
                "count": 4,
                "radius": branch_radius * 0.75,
                "length": branch_length * 0.8,
            })
    if depth >= 3:
        # Третья — у самого target
        if z - branch_length * 0.5 > base_z + trunk_h:
            branch_levels.append({
                "height": z - branch_length * 0.5,
                "count": 3,
                "radius": branch_radius * 0.5,
                "length": branch_length * 0.5,
            })

    for level_idx, level in enumerate(branch_levels):
        n_branches = level["count"]
        bh = level["height"]
        b_rad = level["radius"]
        b_len = level["length"]

        for j in range(n_branches):
            # Угол вокруг вертикали
            phi = (2 * math.pi * j / n_branches) + (level_idx * 0.7)
            # Наклон ветки
            theta = math.radians(branch_angle)  # от вертикали

            # Направление ветки (в сферических координатах)
            direction = np.array([
                math.sin(theta) * math.cos(phi),
                math.sin(theta) * math.sin(phi),
                math.cos(theta),
            ])

            # Создаём ветку как цилиндр по Y
            branch = trimesh.creation.cylinder(
                radius=b_rad,
                height=b_len,
                sections=6,
            )

            # Поворачиваем: ось Y → direction
            default_axis = np.array([0.0, 1.0, 0.0])
            v = np.cross(default_axis, direction)
            s = np.linalg.norm(v)
            c = np.dot(default_axis, direction)

            if s < 1e-6:
                rotation = np.eye(4) if c > 0 else trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0])
            else:
                v = v / s
                angle = math.acos(max(-1.0, min(1.0, c)))
                rotation = trimesh.transformations.rotation_matrix(angle, v)

            branch.apply_transform(rotation)

            # Позиция: начало ветки в (x, y, bh), ветка растёт в направлении direction
            start_point = np.array([x, y, bh])
            center = start_point + direction * (b_len / 2)
            branch.apply_translation(center)
            meshes.append(branch)

            # Sub-ветки (на концах основных)
            if depth >= 2 and level_idx == 0:
                # Добавляем маленькие "листочки" — маленькие цилиндры в конце
                tip = start_point + direction * b_len
                for k in range(2):
                    sub_angle = math.radians(30 + 30 * k)
                    sub_direction = direction.copy()
                    # Слегка поворачиваем
                    if k == 0:
                        sub_direction[2] += 0.3
                    else:
                        sub_direction[2] -= 0.3
                    sub_direction = sub_direction / np.linalg.norm(sub_direction)

                    sub_branch = trimesh.creation.cylinder(
                        radius=b_rad * 0.6,
                        height=b_len * 0.4,
                        sections=5,
                    )

                    v2 = np.cross(default_axis, sub_direction)
                    s2 = np.linalg.norm(v2)
                    c2 = np.dot(default_axis, sub_direction)

                    if s2 < 1e-6:
                        rot2 = np.eye(4) if c2 > 0 else trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0])
                    else:
                        v2 = v2 / s2
                        angle2 = math.acos(max(-1.0, min(1.0, c2)))
                        rot2 = trimesh.transformations.rotation_matrix(angle2, v2)

                    sub_branch.apply_transform(rot2)
                    sub_center = tip + sub_direction * (b_len * 0.2)
                    sub_branch.apply_translation(sub_center)
                    meshes.append(sub_branch)

    return trimesh.util.concatenate(meshes) if meshes else trimesh.Trimesh()


def build_tree_supports(
    decisions: list[StrategyDecision],
    base_z: float = 0.0,
    trunk_radius: float = 0.6,
    branch_length: float = 1.5,
    depth: int = 2,
    branch_angle: float = 45.0,
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
            depth=depth,
            branch_angle=branch_angle,
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
