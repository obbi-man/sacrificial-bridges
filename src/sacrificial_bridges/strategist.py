"""Стратег: для каждого overhang решает — bridge (мостик) или tree support."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from scipy.spatial import KDTree

from .analyzer import Overhang


class SupportStrategy(str):
    BRIDGE = "bridge"
    TREE = "tree"


@dataclass
class StrategyDecision:
    """Решение стратега по одному overhang."""
    overhang: Overhang
    strategy: str
    # Для bridge:
    bridge_target: Optional[np.ndarray] = None  # куда крепить мостик
    bridge_length: float = 0.0
    # Для tree:
    tree_thickness: float = 1.0
    tree_height: float = 0.0
    reason: str = ""


@dataclass
class StrategyResult:
    """Результат работы стратега по всем overhang."""
    decisions: list[StrategyDecision] = field(default_factory=list)
    total_bridges: int = 0
    total_trees: int = 0
    estimated_material_save_percent: float = 0.0  # экономия по сравнению с обычными supports

    def summary(self) -> str:
        return (
            f"Стратегия:\n"
            f"  Мостиков: {self.total_bridges}\n"
            f"  Tree supports: {self.total_trees}\n"
            f"  Экономия материала: ~{self.estimated_material_save_percent:.1f}%"
        )


def find_nearby_parts(
    overhangs: list[Overhang],
    all_face_centers: np.ndarray,
    all_face_normals: np.ndarray,
    max_bridge_length: float,
) -> list[Optional[np.ndarray]]:
    """Для каждого overhang ищет ближайшую часть детали (для мостика).

    Возвращает список точек: для каждого overhang — куда вести мостик, или None.
    """
    # Индексы граней, которые НЕ в overhangs (это "надёжные" части детали)
    overhang_face_indices = set()
    for oh in overhangs:
        overhang_face_indices.update(oh.face_indices.tolist())

    targets = []
    for oh in overhangs:
        # Берём точки всех граней детали кроме текущего overhang
        mask = np.ones(len(all_face_centers), dtype=bool)
        for fi in oh.face_indices:
            mask[fi] = False

        other_centers = all_face_centers[mask]

        if len(other_centers) == 0:
            targets.append(None)
            continue

        # KDTree для быстрого поиска ближайшей точки
        tree = KDTree(other_centers)
        distances, indices = tree.query(oh.center, k=min(5, len(other_centers)))

        # Ищем ближайшую, которая:
        # 1. На расстоянии < max_bridge_length
        # 2. С нормалью, направленной вверх (можно на неё ставить мостик)
        best_target = None
        best_distance = float("inf")

        # Получаем оригинальные индексы граней (не в текущем overhang)
        original_indices = np.where(mask)[0]

        for dist, idx in zip(distances, indices):
            if dist > max_bridge_length:
                break

            # Берём нормаль этой грани (по оригинальному индексу)
            original_idx = original_indices[idx]
            target_normal = all_face_normals[original_idx]

            # Если нормаль направлена вверх (Z > 0.3) — это верхняя поверхность
            if target_normal[2] > 0.3:
                if dist < best_distance:
                    best_target = other_centers[idx]
                    best_distance = dist

        targets.append(best_target if best_target is not None else None)

    return targets


def decide_strategy(
    overhangs: list[Overhang],
    mesh_center_z: float,
    mesh_max_z: float,
    bridge_max_length: float = 15.0,
    tree_min_height: float = 5.0,
) -> list[StrategyDecision]:
    """Решает стратегию для каждого overhang.

    Логика:
    - Если overhang далеко от стола (выше tree_min_height) и есть nearby part — bridge
    - Если overhang низко над столом — tree support
    - Иначе — tree support (опасно)
    """
    # Подготовим данные для поиска ближайших частей
    # Нам нужны центры граней детали (не в overhangs) и нормали

    decisions = []

    for oh in overhangs:
        z_from_floor = oh.min_z - 0.0  # приблизительно высота от стола

        # Стратегия по умолчанию: tree support
        strategy = SupportStrategy.TREE
        target = None
        bridge_length = 0.0

        # Условие для bridge: есть близкая часть детали в радиусе bridge_max_length
        # Это обрабатывается в более высокоуровневой функции find_nearby_parts

        reason = ""

        if z_from_floor > tree_min_height:
            reason = f"Overhang на высоте {z_from_floor:.1f}мм — пробуем bridge"
        else:
            reason = f"Низко над столом ({z_from_floor:.1f}мм) — tree support"

        decisions.append(StrategyDecision(
            overhang=oh,
            strategy=strategy,
            bridge_target=target,
            bridge_length=bridge_length,
            tree_thickness=1.0,
            tree_height=z_from_floor,
            reason=reason,
        ))

    return decisions


def compute_strategy(
    overhangs: list[Overhang],
    mesh,
    bridge_max_length: float = 15.0,
    tree_min_height: float = 5.0,
    safe_mode: bool = True,
) -> StrategyResult:
    """Главная функция: анализ + решение стратегии для всех overhangs.

    Args:
        overhangs: список overhangs (из analyzer)
        mesh: trimesh.Trimesh
        bridge_max_length: максимальная длина мостика (мм)
        tree_min_height: минимальная высота для мостика (мм) — ниже делаем tree
        safe_mode: если True, мостики только в "безопасных" местах
    """
    if not overhangs:
        return StrategyResult()

    # Центры граней и нормали (для поиска nearby parts)
    face_centers = mesh.triangles_center
    face_normals = mesh.face_normals

    mesh_max_z = float(mesh.bounds[1][2])
    mesh_min_z = float(mesh.bounds[0][2])

    # Находим nearby parts для каждого overhang
    targets = find_nearby_parts(overhangs, face_centers, face_normals, bridge_max_length)

    decisions = []

    for oh, target in zip(overhangs, targets):
        z_from_floor = oh.min_z - mesh_min_z

        # Решаем стратегию
        if target is not None and z_from_floor >= tree_min_height:
            # Расстояние от overhang до target
            distance = float(np.linalg.norm(oh.center - target))

            # Проверка safe_mode: мостик только в безопасных местах
            use_bridge = True
            if safe_mode:
                # Не делаем мостик если overhang очень тонкий
                # (мостик может провиснуть при печати)
                if oh.area < 5.0:  # меньше 5 мм²
                    use_bridge = False
                    reason = "Overhang слишком маленький (<5мм²) — tree support"
                # Не делаем мостик если угол слишком крутой
                elif oh.angle_from_vertical > 30:
                    use_bridge = False
                    reason = f"Угол {oh.angle_from_vertical:.0f}° — tree support"
                else:
                    reason = f"Мостик {distance:.1f}мм (safe mode)"
            else:
                reason = f"Мостик {distance:.1f}мм"

            if use_bridge:
                strategy = SupportStrategy.BRIDGE
                decisions.append(StrategyDecision(
                    overhang=oh,
                    strategy=strategy,
                    bridge_target=target,
                    bridge_length=distance,
                    tree_thickness=1.0,
                    tree_height=z_from_floor,
                    reason=reason,
                ))
                continue

        # Иначе — tree support
        decisions.append(StrategyDecision(
            overhang=oh,
            strategy=SupportStrategy.TREE,
            bridge_target=None,
            bridge_length=0.0,
            tree_thickness=1.0,
            tree_height=z_from_floor,
            reason=f"Tree support (высота {z_from_floor:.1f}мм)",
        ))

    # Подсчёт статистики
    bridges_count = sum(1 for d in decisions if d.strategy == SupportStrategy.BRIDGE)
    trees_count = sum(1 for d in decisions if d.strategy == SupportStrategy.TREE)

    # Оценка экономии:
    # Bridge: примерно в 3 раза меньше материала чем tree support
    # (мостик это тонкая перемычка, tree support это объёмная структура)
    if (bridges_count + trees_count) > 0:
        bridge_fraction = bridges_count / (bridges_count + trees_count)
        # Каждый bridge экономит ~66% материала по сравнению с tree
        # baseline = 100% все tree
        # bridge = 33% от tree (экономия 66%)
        save_percent = bridge_fraction * 66.0
    else:
        save_percent = 0.0

    return StrategyResult(
        decisions=decisions,
        total_bridges=bridges_count,
        total_trees=trees_count,
        estimated_material_save_percent=save_percent,
    )
