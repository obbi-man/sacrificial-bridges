"""Генератор мостиков между близкими частями детали."""
from __future__ import annotations

from typing import Optional

import numpy as np
import trimesh

from .strategist import StrategyDecision


def create_bridge(
    start: np.ndarray,
    end: np.ndarray,
    width: float = 4.0,
    height: float = 0.8,
) -> trimesh.Trimesh:
    """Создаёт mesh мостика (тонкий параллелепипед) между двумя точками.

    Args:
        start: начало мостика
        end: конец мостика
        width: ширина мостика (мм)
        height: высота мостика (мм)

    Returns:
        trimesh.Trimesh — mesh мостика
    """
    direction = end - start
    length = float(np.linalg.norm(direction))
    if length < 0.1:
        # Слишком короткий — игнорируем
        return trimesh.Trimesh()

    direction = direction / length

    # Создаём брусок
    box = trimesh.creation.box(extents=[length, width, height])

    # Поворачиваем брусок так, чтобы X ось совпала с направлением мостика
    # Box по умолчанию вытянут по X
    if abs(direction[0]) > 0.999:
        # Уже вдоль X
        rotation = np.eye(4)
    else:
        # Вычисляем поворот от (1,0,0) к direction
        x_axis = np.array([1.0, 0.0, 0.0])
        # Поворот через axis-angle
        v = np.cross(x_axis, direction)
        s = np.linalg.norm(v)
        c = np.dot(x_axis, direction)

        if s < 1e-6:
            # Параллельно или антипараллельно
            if c > 0:
                rotation = np.eye(4)
            else:
                # 180° поворот
                rotation = trimesh.transformations.rotation_matrix(
                    np.pi, [0, 0, 1]
                )
        else:
            v = v / s
            angle = np.arccos(np.clip(c, -1.0, 1.0))
            rotation = trimesh.transformations.rotation_matrix(angle, v)

    # Центрируем брусок: его начало должно быть в start
    # После поворота брусок центрирован в (0,0,0), ось X направлена вдоль direction
    # Нам нужно: левый край в start, правый в end

    # 1. Поворачиваем
    box.apply_transform(rotation)
    # 2. Сдвигаем: теперь центр бруска в (length/2, 0, 0) вдоль direction
    #    Нам нужен центр в start + (length/2) * direction
    new_center = start + direction * (length / 2)
    box.apply_translation(new_center)

    # Слегка поднимаем мостик, чтобы он лежал на верху детали
    # (Y-плоскость мостика должна совпадать с верхней поверхностью target)
    # Просто оставляем как есть — мостик будет на Z координате target

    return box


def build_bridges(
    decisions: list[StrategyDecision],
    tree_thickness: float = 1.0,
    bridge_width: float = 4.0,
    bridge_height: float = 0.8,
) -> list[trimesh.Trimesh]:
    """Строит mesh мостиков для всех решений со стратегией bridge."""
    bridges = []
    for d in decisions:
        if d.strategy != "bridge" or d.bridge_target is None:
            continue
        mesh = create_bridge(
            d.overhang.center,
            d.bridge_target,
            width=bridge_width,
            height=bridge_height,
        )
        if len(mesh.vertices) > 0:
            bridges.append(mesh)
    return bridges


def merge_meshes(meshes: list[trimesh.Trimesh]) -> trimesh.Trimesh:
    """Объединяет несколько meshes в один."""
    if not meshes:
        return trimesh.Trimesh()
    if len(meshes) == 1:
        return meshes[0]
    return trimesh.util.concatenate(meshes)
