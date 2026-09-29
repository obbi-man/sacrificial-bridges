"""GUI интерфейс для Sacrificial Bridges с 3D визуализацией через matplotlib."""
from __future__ import annotations

import io
import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

if hasattr(sys.stdout, "buffer"):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

os.chdir(Path(__file__).parent.parent.parent)

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import trimesh

from .analyzer import analyze_model, load_mesh
from .bridge_builder import build_bridges
from .cli import print_colored
from .exporter import export_combined_stl
from .strategist import compute_strategy, SupportStrategy
from .tree_builder import build_tree_supports, estimate_material


class SacrificialBridgesApp:
    """Главное окно GUI."""

    def __init__(self, root):
        self.root = root
        root.title("Sacrificial Bridges v0.1 — мостики вместо supports")
        root.geometry("1100x750")
        root.minsize(900, 600)

        # Переменные
        self.input_file = tk.StringVar()
        self.output_dir = tk.StringVar(value=str(Path.cwd() / "output"))
        self.bridge_max = tk.DoubleVar(value=15.0)
        self.bridge_width = tk.DoubleVar(value=4.0)
        self.bridge_height = tk.DoubleVar(value=0.8)
        self.tree_min_height = tk.DoubleVar(value=5.0)
        self.trunk_radius = tk.DoubleVar(value=0.6)
        self.branch_length = tk.DoubleVar(value=1.5)
        self.safe_mode = tk.BooleanVar(value=True)

        self.mesh = None
        self.stats = None
        self.strategy = None
        self.bridges = []
        self.trees = []

        self.processing = False

        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 6, "pady": 4}

        # Заголовок
        title_frame = ttk.Frame(self.root)
        title_frame.pack(fill="x", padx=10, pady=(10, 4))

        ttk.Label(
            title_frame, text="🌉 Sacrificial Bridges",
            font=("Segoe UI", 18, "bold"),
        ).pack(side="left")

        ttk.Label(
            title_frame,
            text="Мостики вместо support structures",
            font=("Segoe UI", 10),
            foreground="gray",
        ).pack(side="left", padx=20)

        # Main paned window
        main_pane = ttk.PanedWindow(self.root, orient="horizontal")
        main_pane.pack(fill="both", expand=True, padx=10, pady=5)

        # Левая панель — настройки
        left = ttk.Frame(main_pane)
        main_pane.add(left, weight=1)

        # === Файл ===
        file_frame = ttk.LabelFrame(left, text="📂 STL файл")
        file_frame.pack(fill="x", **pad)

        ttk.Entry(file_frame, textvariable=self.input_file).pack(
            side="left", fill="x", expand=True, padx=6, pady=6
        )
        ttk.Button(file_frame, text="Обзор...", command=self._browse_input).pack(
            side="left", padx=4, pady=6
        )

        # === Выход ===
        out_frame = ttk.LabelFrame(left, text="💾 Папка результатов")
        out_frame.pack(fill="x", **pad)
        ttk.Entry(out_frame, textvariable=self.output_dir).pack(
            side="left", fill="x", expand=True, padx=6, pady=6
        )
        ttk.Button(out_frame, text="Обзор...", command=self._browse_output).pack(
            side="left", padx=4, pady=6
        )

        # === Параметры мостиков ===
        bridge_frame = ttk.LabelFrame(left, text="🌉 Мостики")
        bridge_frame.pack(fill="x", **pad)

        ttk.Label(bridge_frame, text="Макс. длина (мм):").grid(row=0, column=0, sticky="w", padx=6, pady=2)
        ttk.Spinbox(
            bridge_frame, from_=5.0, to=50.0, increment=1.0,
            textvariable=self.bridge_max, width=10,
        ).grid(row=0, column=1, sticky="w", padx=6, pady=2)

        ttk.Label(bridge_frame, text="Ширина (мм):").grid(row=1, column=0, sticky="w", padx=6, pady=2)
        ttk.Spinbox(
            bridge_frame, from_=2.0, to=10.0, increment=0.5,
            textvariable=self.bridge_width, width=10,
        ).grid(row=1, column=1, sticky="w", padx=6, pady=2)

        ttk.Label(bridge_frame, text="Высота (мм):").grid(row=2, column=0, sticky="w", padx=6, pady=2)
        ttk.Spinbox(
            bridge_frame, from_=0.4, to=2.0, increment=0.1,
            textvariable=self.bridge_height, width=10,
        ).grid(row=2, column=1, sticky="w", padx=6, pady=2)

        # === Параметры tree supports ===
        tree_frame = ttk.LabelFrame(left, text="🌲 Tree supports")
        tree_frame.pack(fill="x", **pad)

        ttk.Label(tree_frame, text="Мин. высота для мостика (мм):").grid(row=0, column=0, sticky="w", padx=6, pady=2)
        ttk.Spinbox(
            tree_frame, from_=1.0, to=20.0, increment=0.5,
            textvariable=self.tree_min_height, width=10,
        ).grid(row=0, column=1, sticky="w", padx=6, pady=2)

        ttk.Label(tree_frame, text="Радиус ствола (мм):").grid(row=1, column=0, sticky="w", padx=6, pady=2)
        ttk.Spinbox(
            tree_frame, from_=0.2, to=3.0, increment=0.1,
            textvariable=self.trunk_radius, width=10,
        ).grid(row=1, column=1, sticky="w", padx=6, pady=2)

        ttk.Label(tree_frame, text="Длина веток (мм):").grid(row=2, column=0, sticky="w", padx=6, pady=2)
        ttk.Spinbox(
            tree_frame, from_=0.5, to=5.0, increment=0.5,
            textvariable=self.branch_length, width=10,
        ).grid(row=2, column=1, sticky="w", padx=6, pady=2)

        # === Опции ===
        opts_frame = ttk.LabelFrame(left, text="⚙️ Опции")
        opts_frame.pack(fill="x", **pad)
        ttk.Checkbutton(
            opts_frame, text="Safe mode (не делать мостики в опасных местах)",
            variable=self.safe_mode,
        ).pack(anchor="w", padx=6, pady=4)

        # === Кнопки ===
        btn_frame = ttk.Frame(left)
        btn_frame.pack(fill="x", **pad)

        self.btn_analyze = ttk.Button(
            btn_frame, text="📐 Анализ", command=self._analyze
        )
        self.btn_analyze.pack(side="left", padx=2)

        self.btn_run = ttk.Button(
            btn_frame, text="🚀 Обработать", command=self._run
        )
        self.btn_run.pack(side="left", padx=2)

        ttk.Button(btn_frame, text="📂 Открыть", command=self._open_output).pack(
            side="left", padx=2
        )

        # === Статистика ===
        stats_frame = ttk.LabelFrame(left, text="📊 Статистика")
        stats_frame.pack(fill="both", expand=True, **pad)
        self.stats_label = ttk.Label(
            stats_frame, text="Загрузите STL для анализа", foreground="gray"
        )
        self.stats_label.pack(anchor="w", padx=6, pady=4)

        # Правая панель — 3D визуализация
        right = ttk.Frame(main_pane)
        main_pane.add(right, weight=2)

        # === 3D viewer ===
        viz_frame = ttk.LabelFrame(right, text="🎨 3D визуализация")
        viz_frame.pack(fill="both", expand=True, **pad)

        self.fig = plt.Figure(figsize=(8, 6), dpi=100)
        self.fig.patch.set_facecolor('#1a1a24')
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.ax.set_facecolor('#1a1a24')
        self.ax.set_xlim(0, 100)
        self.ax.set_ylim(0, 100)
        self.ax.set_zlim(0, 100)
        self.ax.set_xlabel("X", color='white')
        self.ax.set_ylabel("Y", color='white')
        self.ax.set_zlabel("Z", color='white')
        self.ax.tick_params(colors='white')
        self.ax.xaxis.pane.fill = False
        self.ax.yaxis.pane.fill = False
        self.ax.zaxis.pane.fill = False

        self.canvas = FigureCanvasTkAgg(self.fig, viz_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # Кнопки под 3D
        viz_btns = ttk.Frame(right)
        viz_btns.pack(fill="x", **pad)

        self.show_original = tk.BooleanVar(value=True)
        self.show_bridges = tk.BooleanVar(value=True)
        self.show_trees = tk.BooleanVar(value=True)
        self.show_overhangs = tk.BooleanVar(value=False)

        ttk.Checkbutton(viz_btns, text="Модель", variable=self.show_original, command=self._redraw).pack(side="left", padx=4)
        ttk.Checkbutton(viz_btns, text="Мостики (красные)", variable=self.show_bridges, command=self._redraw).pack(side="left", padx=4)
        ttk.Checkbutton(viz_btns, text="Tree (синие)", variable=self.show_trees, command=self._redraw).pack(side="left", padx=4)
        ttk.Checkbutton(viz_btns, text="Overhangs", variable=self.show_overhangs, command=self._redraw).pack(side="left", padx=4)

        # === Лог внизу ===
        log_frame = ttk.LabelFrame(self.root, text="📝 Лог")
        log_frame.pack(fill="x", padx=10, pady=(0, 6))

        self.log = scrolledtext.ScrolledText(log_frame, height=5, font=("Consolas", 9))
        self.log.pack(fill="x", padx=4, pady=4)

        # === Статус ===
        self.status = ttk.Label(self.root, text="Готов", foreground="gray")
        self.status.pack(fill="x", padx=10, pady=(0, 6))

    def _browse_input(self):
        path = filedialog.askopenfilename(
            title="Выбери STL",
            filetypes=[("STL files", "*.stl"), ("All files", "*.*")],
        )
        if path:
            self.input_file.set(path)
            self._log(f"📂 Загружен: {path}")

    def _browse_output(self):
        path = filedialog.askdirectory(title="Куда сохранить результаты")
        if path:
            self.output_dir.set(path)

    def _log(self, msg: str):
        def append():
            self.log.insert("end", msg + "\n")
            self.log.see("end")
        self.root.after(0, append)

    def _set_status(self, msg: str, color: str = "gray"):
        def update():
            self.status.config(text=msg, foreground=color)
        self.root.after(0, update)

    def _set_processing(self, processing: bool):
        def update():
            self.processing = processing
            state = "disabled" if processing else "normal"
            self.btn_run.config(state=state)
            self.btn_analyze.config(state=state)
        self.root.after(0, update)

    def _analyze(self):
        path = self.input_file.get().strip()
        if not path or not Path(path).exists():
            messagebox.showwarning("Нет файла", "Сначала выбери STL файл")
            return
        try:
            self._log(f"📐 Анализ {Path(path).name}...")
            self.stats = analyze_model(path)
            self.mesh = self.stats._mesh

            text = (
                f"Файл: {self.stats.file_path.name}\n"
                f"Объём: {self.stats.volume:.1f} мм³\n"
                f"Высота: {self.stats.z_height:.2f} мм\n"
                f"Overhangs: {len(self.stats.overhangs)} групп "
                f"({self.stats.overhang_percent:.1f}% граней)"
            )
            self.stats_label.config(text=text, foreground="black")

            self._log(f"  ✅ Найдено {len(self.stats.overhangs)} групп overhangs")

            self._redraw()
        except Exception as e:
            self._log(f"  ❌ Ошибка: {e}")
            messagebox.showerror("Ошибка", str(e))

    def _run(self):
        if self.processing:
            return
        path = self.input_file.get().strip()
        if not path or not Path(path).exists():
            messagebox.showwarning("Нет файла", "Сначала выбери STL файл")
            return

        output = self.output_dir.get().strip() or str(Path.cwd() / "output")
        Path(output).mkdir(parents=True, exist_ok=True)

        threading.Thread(
            target=self._run_thread,
            args=(path, output),
            daemon=True,
        ).start()

    def _run_thread(self, path, output):
        try:
            self._set_processing(True)
            self._set_status("Обработка...", "blue")

            self.mesh = load_mesh(path)
            self.stats = analyze_model(path)

            self._set_status("Выбор стратегии...", "blue")
            self.strategy = compute_strategy(
                self.stats.overhangs,
                self.mesh,
                bridge_max_length=self.bridge_max.get(),
                tree_min_height=self.tree_min_height.get(),
                safe_mode=self.safe_mode.get(),
            )

            self._set_status("Генерация mesh-ей...", "blue")
            self.bridges = build_bridges(
                self.strategy.decisions,
                bridge_width=self.bridge_width.get(),
                bridge_height=self.bridge_height.get(),
            )
            self.trees = build_tree_supports(
                self.strategy.decisions,
                trunk_radius=self.trunk_radius.get(),
                branch_length=self.branch_length.get(),
            )

            mass, volume = estimate_material(self.trees, self.bridges)
            self._log(f"🌉 Мостиков: {len(self.bridges)}")
            self._log(f"🌲 Tree supports: {len(self.trees)}")
            self._log(f"📦 Масса: ~{mass:.2f}г ({volume:.2f}см³)")
            self._log(f"💰 Экономия: ~{self.strategy.estimated_material_save_percent:.1f}%")

            # Экспорт
            output_path = Path(output) / f"{Path(path).stem}_with_supports.stl"
            export_combined_stl(self.mesh, self.bridges, self.trees, output_path)
            self._log(f"💾 Сохранено: {output_path.name}")

            self._redraw()

            self._set_status(
                f"✅ Готово! Мостиков: {len(self.bridges)}, Tree: {len(self.trees)}",
                "green",
            )

            messagebox.showinfo(
                "Готово!",
                f"Создано:\n\n"
                f"• {len(self.bridges)} мостиков\n"
                f"• {len(self.trees)} tree supports\n"
                f"• Экономия: ~{self.strategy.estimated_material_save_percent:.1f}%\n\n"
                f"Файл: {output_path}",
            )

        except Exception as e:
            self._log(f"❌ Ошибка: {e}")
            self._set_status(f"Ошибка: {e}", "red")
            messagebox.showerror("Ошибка", str(e))
        finally:
            self._set_processing(False)

    def _open_output(self):
        path = Path(self.output_dir.get())
        if path.exists():
            try:
                import subprocess
                subprocess.Popen(["explorer", str(path)])
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

    def _redraw(self):
        """Перерисовывает 3D визуализацию."""
        self.ax.clear()

        if self.mesh is None:
            self.ax.text(
                0.5, 0.5, 0.5, "Загрузите STL для 3D визуализации",
                transform=self.ax.transAxes, ha="center", color="white", fontsize=14,
            )
            self.canvas.draw()
            return

        # Подгоняем границы
        bounds = self.mesh.bounds
        center = (bounds[0] + bounds[1]) / 2
        size = float((bounds[1] - bounds[0]).max()) / 2 * 1.2
        self.ax.set_xlim(center[0] - size, center[0] + size)
        self.ax.set_ylim(center[1] - size, center[1] + size)
        self.ax.set_zlim(bounds[0][2], bounds[1][2] + size * 0.3)
        self.ax.set_xlabel("X", color='white')
        self.ax.set_ylabel("Y", color='white')
        self.ax.set_zlabel("Z", color='white')
        self.ax.tick_params(colors='white')
        self.ax.xaxis.pane.fill = False
        self.ax.yaxis.pane.fill = False
        self.ax.zaxis.pane.fill = False
        self.ax.set_facecolor('#1a1a24')

        # Модель
        if self.show_original.get():
            self._draw_mesh(self.mesh, color='#7c5cff', alpha=0.6, edgecolor='none')

        # Overhangs
        if self.show_overhangs.get() and self.stats:
            for oh in self.stats.overhangs:
                verts = self.mesh.vertices[self.mesh.faces[oh.face_indices]].reshape(-1, 3)
                tris = verts.reshape(-1, 3, 3)
                coll = Poly3DCollection(tris, alpha=0.8, facecolor='orange', edgecolor='none')
                self.ax.add_collection3d(coll)

        # Мостики (красные)
        if self.show_bridges.get():
            for mesh in self.bridges:
                self._draw_mesh(mesh, color='#ff5252', alpha=0.9, edgecolor='red')

        # Tree supports (синие)
        if self.show_trees.get():
            for mesh in self.trees:
                self._draw_mesh(mesh, color='#4fc3f7', alpha=0.7, edgecolor='blue')

        self.canvas.draw()

    def _draw_mesh(self, mesh, color='gray', alpha=0.5, edgecolor='none'):
        """Отрисовка одного mesh в 3D."""
        verts = mesh.vertices[mesh.faces].reshape(-1, 3, 3)
        coll = Poly3DCollection(
            verts, alpha=alpha, facecolor=color,
            edgecolor=edgecolor if edgecolor != 'none' else None,
            linewidth=0.2 if edgecolor != 'none' else 0,
        )
        self.ax.add_collection3d(coll)


def main():
    root = tk.Tk()
    try:
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
        elif "clam" in style.theme_names():
            style.theme_use("clam")
    except Exception:
        pass

    app = SacrificialBridgesApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
