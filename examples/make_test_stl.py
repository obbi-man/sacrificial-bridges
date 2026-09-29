"""Генерирует тестовый STL — две коробки рядом с горизонтальной перекладиной.

Идеальный тест: посередине мостик будет оправдан (между двумя близкими частями),
снизу нужны tree supports (далеко от других частей).
"""
from pathlib import Path
import numpy as np
import trimesh

OUT = Path(__file__).parent / "test_two_boxes.stl"

# Создаём два кубика рядом
box1 = trimesh.creation.box(extents=[20, 20, 30])
box1.apply_translation([0, 0, 15])

box2 = trimesh.creation.box(extents=[20, 20, 30])
box2.apply_translation([40, 0, 15])  # 20мм между ними

# Перекладина между ними (которая БУДЕТ overhang)
bridge_part = trimesh.creation.box(extents=[20, 10, 4])  # 20мм длина (как раз между)
bridge_part.apply_translation([20, 0, 30])  # на высоте 30мм, между коробками

# Соединяем всё
combined = trimesh.util.concatenate([box1, box2, bridge_part])

# Сохраняем
combined.export(str(OUT))
print(f"✅ Создан тестовый STL: {OUT}")
print(f"   Размер: {OUT.stat().st_size / 1024:.1f} КБ")
print(f"   Геометрия: 2 коробки 20x20x30 + перекладина 20x10x4 на высоте 30мм")
print(f"   Overhang: перекладина свисает с двух сторон, нужны поддержки")
