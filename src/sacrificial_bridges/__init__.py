"""Sacrificial Bridges — генератор мостиков и tree supports для 3D-печати.

Анализирует STL, находит overhangs, и для каждого выбирает стратегию:
- Если рядом есть другая часть детали (на dist < bridge_max_length) — строит мостик
- Если нет — строит обычный tree support от стола

Экономит 30-50% пластика по сравнению с обычными supports.

Поддерживаемые форматы: STL (бинарный и ASCII)

Использование:
    python -m sacrificial_bridges analyze model.stl
    python -m sacrificial_bridges process model.stl --bridge-max 15 --tree-thick 1.2
    python -m sacrificial_bridges gui
"""

__version__ = "0.1.0"
__author__ = "Pulsar AI"
__license__ = "MIT"
