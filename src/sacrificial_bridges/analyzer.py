"""Анализ STL: детекция overhangs, статистика, классификация."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
import trimesh


@dataclass
class Overhang:
    """Один overhang (часть, требующая поддержки)."""
    face_indices: np.ndarray  # индексы граней
    center: np.ndarray         # центр тяжести overhang
    normal: np.ndarray         # усреднённая нормаль
    area: float                # площадь в мм²
    angle_from_vertical: float # угол от вертикали (0 = плоский потолок, 90 = стена)
    min_z: float               # минимальная Z координата
    max_z: float               # максимальная Z координата
    needs_support: bool = True # true если нужен мостик или tree support

    def to_dict(self) -> dict:
        return {
            "face_count": int(len(self.face_indices)),
            "center": self.center.tolist(),
            "normal": self.normal.tolist(),
            "area": round(self.area, 2),
            "angle_from_vertical": round(self.angle_from_vertical, 1),
            "min_z": round(self.min_z, 2),
            "max_z": round(self.max_z, 2),
            "needs_support": self.needs_support,
        }


@dataclass
class ModelStats:
    """Общая статистика модели."""
    file_path: Path
    volume: float  # мм³
    surface_area: float  # мм²
    total_faces: int
    overhang_faces: int  # граней в overhangs
    overhang_percent: float  # процент граней в overhang
    overhangs: list[Overhang] = field(default_factory=list)
    bounding_box: tuple[tuple[float, float, float], tuple[float, float, float]] = ((), ())
    z_height: float = 0.0
    _mesh: trimesh.Trimesh = field(default=None, repr=False, compare=False)

    def summary(self) -> str:
        return (
            f"Файл: {self.file_path.name}\n"
            f"Объём: {self.volume:.1f} мм³\n"
            f"Площадь: {self.surface_area:.1f} мм²\n"
            f"Высота: {self.z_height:.2f} мм\n"
            f"Граней: {self.total_faces}\n"
            f"Overhangs: {len(self.overhangs)} групп, {self.overhang_faces} граней "
            f"({self.overhang_percent:.1f}%)"
        )


def load_mesh(file_path: Path | str) -> trimesh.Trimesh:
    """Загружает STL и возвращает mesh."""
    mesh = trimesh.load_mesh(str(file_path))
    if isinstance(mesh, trimesh.Scene):
        # Если сцена — берём все геометрии в одну
        mesh = mesh.dump(concatenate=True)
    return mesh


def detect_overhangs(
    mesh: trimesh.Trimesh,
    overhang_angle: float = 45.0,
) -> list[Overhang]:
    """Находит overhangs — грани, которые свисают вниз больше чем на overhang_angle.

    Overhang — это грань, нормаль которой направлена больше чем на (90° - overhang_angle)
    от вертикали. То есть её «потолок» направлен вниз.
    """
    normals = mesh.face_normals
    # Вектор "вниз" — против гравитации (принтер печатает снизу вверх, Z растёт)
    down = np.array([0.0, 0.0, -1.0])

    # cos между нормалью и down: -1 = грань смотрит строго вниз (потолок)
    # 0 = грань вертикальна (стена)
    # +1 = грань смотрит строго вверх (пол)
    cos = (normals * down).sum(axis=1)

    # Угол от вертикали:
    # angle = 0 → горизонтальный потолок (cos = -1)
    # angle = 90 → вертикальная стена (cos = 0)
    # angle > 90 → наклон вниз (cos > 0) — обычно не печатается без поддержки
    angles = np.degrees(np.arccos(np.clip(cos, -1.0, 1.0)))

    # Overhang — это грань, где angle < overhang_angle (то есть грань "свисает")
    # То есть её нижняя поверхность направлена вниз
    is_overhang = angles < overhang_angle

    if not is_overhang.any():
        return []

    # Группируем связные overhangs (BFS по смежным граням)
    overhang_indices = np.where(is_overhang)[0]
    groups = _group_connected_faces(mesh, overhang_indices)

    overhangs = []
    for group in groups:
        if len(group) == 0:
            continue
        group_normals = normals[group]
        # Средняя нормаль (взвешенная площадью)
        areas = mesh.area_faces[group]
        weights = areas / areas.sum()
        avg_normal = (group_normals * weights[:, None]).sum(axis=0)
        avg_normal = avg_normal / np.linalg.norm(avg_normal)

        # Центр тяжести
        vertices = mesh.vertices[mesh.faces[group]].reshape(-1, 3)
        center = vertices.mean(axis=0)

        # Z координаты
        zs = mesh.vertices[mesh.faces[group], 2].flatten()
        min_z, max_z = float(zs.min()), float(zs.max())

        # Угол от вертикали
        cos_avg = float((avg_normal * down).sum())
        angle = math.degrees(math.acos(np.clip(cos_avg, -1.0, 1.0)))

        overhangs.append(Overhang(
            face_indices=group,
            center=center,
            normal=avg_normal,
            area=float(areas.sum()),
            angle_from_vertical=angle,
            min_z=min_z,
            max_z=max_z,
        ))

    return overhangs


def _group_connected_faces(mesh: trimesh.Trimesh, face_indices: np.ndarray) -> list[np.ndarray]:
    """Группирует связные грани (BFS по смежности)."""
    if len(face_indices) == 0:
        return []

    # Словарь: вершина → список граней
    vertex_faces: dict[int, list[int]] = {}
    for fi in face_indices:
        for vi in mesh.faces[fi]:
            vertex_faces.setdefault(int(vi), []).append(int(fi))

    visited = set()
    groups = []

    face_set = set(face_indices.tolist())
    for start_face in face_indices:
        if int(start_face) in visited:
            continue

        # BFS
        stack = [int(start_face)]
        group = []
        while stack:
            fi = stack.pop()
            if fi in visited:
                continue
            visited.add(fi)
            group.append(fi)
            # Смежные грани через общие вершины
            for vi in mesh.faces[fi]:
                for adj in vertex_faces.get(int(vi), []):
                    if adj not in visited and adj in face_set:
                        stack.append(adj)

        if group:
            groups.append(np.array(group))

    return groups


def analyze_model(
    file_path: Path | str,
    overhang_angle: float = 45.0,
) -> ModelStats:
    """Полный анализ модели."""
    file_path = Path(file_path)
    mesh = load_mesh(file_path)

    overhangs = detect_overhangs(mesh, overhang_angle)

    # Сумма площадей граней в overhangs
    overhang_face_count = sum(len(o.face_indices) for o in overhangs)
    overhang_percent = (overhang_face_count / len(mesh.faces) * 100) if len(mesh.faces) else 0.0

    # Bounding box
    bb_min = mesh.bounds[0]
    bb_max = mesh.bounds[1]

    return ModelStats(
        file_path=file_path,
        volume=mesh.volume,
        surface_area=mesh.area,
        total_faces=len(mesh.faces),
        overhang_faces=overhang_face_count,
        overhang_percent=overhang_percent,
        overhangs=overhangs,
        bounding_box=(tuple(bb_min), tuple(bb_max)),
        z_height=float(bb_max[2] - bb_min[2]),
        _mesh=mesh,
    )


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Использование: python analyzer.py <model.stl>")
        sys.exit(1)

    stats = analyze_model(sys.argv[1])
    print(stats.summary())
    print()
    print(f"Найдено {len(stats.overhangs)} групп overhangs:")
    for i, oh in enumerate(stats.overhangs[:20], 1):
        print(f"  #{i}: {len(oh.face_indices)} граней, "
              f"угол={oh.angle_from_vertical:.1f}°, "
              f"Z=[{oh.min_z:.1f}, {oh.max_z:.1f}], "
              f"площадь={oh.area:.1f}мм²")
    if len(stats.overhangs) > 20:
        print(f"  ... и ещё {len(stats.overhangs) - 20} групп")
