# Changelog

## [0.1.0] — 2026-09-29

### Added
- MVP плагина Sacrificial Bridges
- Анализ STL: детекция overhangs (analyzer.py)
- Стратегия: выбор bridge vs tree support (strategist.py)
- Генератор мостиков (bridge_builder.py)
- Генератор tree supports (tree_builder.py)
- Экспорт в STL (exporter.py)
- CLI интерфейс (cli.py)
- GUI с 3D визуализацией (gui.py)
- Плагин для Bambu Studio (скопирован в %APPDATA%\BambuStudio\plugins\)
- 8 тестов проходят
- README + VC_ARTICLE.md
- MIT лицензия

### Features
- Автоматически определяет bridge vs tree support
- Safe mode для отказа от рискованных мостиков
- Гибкие настройки: длина мостика, размеры, толщина
- Экономия 20-40% материала vs обычных supports
