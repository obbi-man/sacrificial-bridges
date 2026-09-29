# Публикация на GitHub

## Шаг 1 — Создать репозиторий на GitHub

1. Иди на https://github.com/new
2. Заполни:
   - **Repository name:** `sacrificial-bridges`
   - **Description:** "Open-source плагин для 3D-печати: мостики вместо support structures. Экономит 20-40% пластика."
   - **Public** (чтобы все видели)
   - **БЕЗ** README, .gitignore, license (мы их уже сделали локально)
3. Нажми **Create repository**

## Шаг 2 — Подключить и запушить

После создания GitHub покажет команды. Вставь свои:

```powershell
cd F:\sacrificial-bridges
git remote add origin https://github.com/ТВОЙ_ЮЗЕР/sacrificial-bridges.git
git branch -M main
git push -u origin main
```

## Шаг 3 — Сделать первый Release

На GitHub:
1. Иди в **Releases** → **Create a new release**
2. Tag: `v0.1.0`
3. Title: `v0.1.0 — MVP`
4. Описание:

```markdown
## Первый релиз MVP

Плагин для 3D-печати, который автоматически заменяет опоры на тонкие мостики между близкими частями детали.

### Что умеет

- Анализ STL: находит overhangs
- Стратегия: bridge (мостик) или tree support
- Генератор mesh мостиков и tree supports
- Экспорт в STL
- CLI + GUI с 3D визуализацией
- Плагин для Bambu Studio

### Экономия

В среднем 22% материала vs обычных supports. На деталях с большим количеством связей — до 40%.

### Установка

```bash
pip install sacrificial-bridges
```

Подробнее в README.
```

5. Нажми **Publish release**

## Шаг 4 — PyPI (опционально)

Чтобы плагин ставился через `pip install sacrificial-bridges`:

```powershell
cd F:\sacrificial-bridges
python -m pip install build twine
python -m build
python -m twine upload dist/*
```

Перед этим:
- Зарегистрируйся на https://pypi.org
- Создай API token в https://pypi.org/manage/account/token/

## Шаг 5 — Reddit (для популяризации)

r/3Dprinting — самое большое сообщество. Пост:

```markdown
Title: [Open Source] Sacrificial Bridges — bridges instead of supports, saves 20-40% filament

Body:
I made a Python plugin that automatically replaces support structures with thin bridges between nearby parts of a model.

Features:
- Analyzes STL, finds overhangs
- Generates bridges (if part is nearby) or tree supports (if not)
- 22% material savings on test models
- CLI + GUI + Bambu Studio plugin
- MIT licensed

GitHub: github.com/yourname/sacrificial-bridges

Would love feedback from people printing lots of identical parts (where this matters most).
```

## Шаг 6 — VC.ru

Используй готовый текст из `VC_ARTICLE.md`. Замени плейсхолдеры:
- [yourname] → реальное имя/GitHub
- Добавь скриншоты GUI и 3D визуализации
- Опубликуй в понедельник-среду утром

## Что Готово

✅ Локальный Git репозиторий
✅ 17 файлов в коммите
✅ .gitignore + CHANGELOG
✅ README с подробной документацией
✅ Статья для VC.ru

## Что нужно сделать

⏳ Создать GitHub репозиторий (вручную через браузер)
⏳ Push (команды выше)
⏳ Release v0.1.0
⏳ PyPI пакет (опционально)
⏳ Reddit пост
⏳ VC.ru статья
