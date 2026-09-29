"""Тесты для sacrificial_bridges."""
import unittest
from pathlib import Path

from sacrificial_bridges.analyzer import (
    load_mesh,
    detect_overhangs,
    analyze_model,
)
from sacrificial_bridges.strategist import compute_strategy, SupportStrategy
from sacrificial_bridges.bridge_builder import create_bridge
import numpy as np


TEST_FILE = Path(__file__).parent.parent / "examples" / "test_two_boxes.stl"


class TestAnalyzer(unittest.TestCase):
    """Тесты анализатора STL."""

    def test_load_mesh(self):
        if not TEST_FILE.exists():
            self.skipTest(f"Тестовый файл не найден: {TEST_FILE}")
        mesh = load_mesh(TEST_FILE)
        self.assertGreater(len(mesh.faces), 0)
        self.assertGreater(len(mesh.vertices), 0)

    def test_detect_overhangs(self):
        if not TEST_FILE.exists():
            self.skipTest(f"Тестовый файл не найден: {TEST_FILE}")
        mesh = load_mesh(TEST_FILE)
        overhangs = detect_overhangs(mesh, overhang_angle=45.0)
        self.assertGreater(len(overhangs), 0)

    def test_analyze_model(self):
        if not TEST_FILE.exists():
            self.skipTest(f"Тестовый файл не найден: {TEST_FILE}")
        stats = analyze_model(TEST_FILE)
        self.assertGreater(stats.volume, 0)
        self.assertGreater(stats.surface_area, 0)
        self.assertGreater(stats.total_faces, 0)


class TestStrategist(unittest.TestCase):
    """Тесты стратега."""

    def test_compute_strategy(self):
        if not TEST_FILE.exists():
            self.skipTest(f"Тестовый файл не найден: {TEST_FILE}")
        stats = analyze_model(TEST_FILE)
        strategy = compute_strategy(
            stats.overhangs,
            stats._mesh,
            bridge_max_length=25.0,
            tree_min_height=5.0,
            safe_mode=True,
        )
        self.assertGreater(len(strategy.decisions), 0)

    def test_strategy_has_bridge_or_tree(self):
        if not TEST_FILE.exists():
            self.skipTest(f"Тестовый файл не найден: {TEST_FILE}")
        stats = analyze_model(TEST_FILE)
        strategy = compute_strategy(
            stats.overhangs, stats._mesh, bridge_max_length=25.0,
        )
        has_any = any(
            d.strategy in (SupportStrategy.BRIDGE, SupportStrategy.TREE)
            for d in strategy.decisions
        )
        self.assertTrue(has_any)


class TestBridgeBuilder(unittest.TestCase):
    """Тесты генератора мостиков."""

    def test_create_simple_bridge(self):
        start = np.array([0.0, 0.0, 10.0])
        end = np.array([20.0, 0.0, 10.0])
        mesh = create_bridge(start, end, width=4.0, height=0.8)
        self.assertGreater(len(mesh.vertices), 0)
        self.assertGreater(mesh.volume, 0)

    def test_create_bridge_zero_length(self):
        start = np.array([0.0, 0.0, 10.0])
        end = np.array([0.0, 0.0, 10.0])
        mesh = create_bridge(start, end)
        self.assertEqual(len(mesh.vertices), 0)


class TestTreeBuilder(unittest.TestCase):
    """Тесты генератора tree supports."""

    def test_create_tree(self):
        from sacrificial_bridges.tree_builder import create_tree_support
        mesh = create_tree_support(
            target=np.array([10.0, 10.0, 15.0]),
            base_z=0.0,
        )
        self.assertGreater(len(mesh.vertices), 0)


if __name__ == "__main__":
    unittest.main()
