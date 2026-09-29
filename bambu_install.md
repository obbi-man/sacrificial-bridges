# Установка в Bambu Studio

## ✅ Готово

Плагин уже установлен в:
```
%APPDATA%\BambuStudio\plugins\sacrificial_bridges\
```

## Как использовать

### Вариант 1 — через CLI (самый быстрый)

```powershell
sacrificial-bridges analyze ваша_модель.stl
sacrificial-bridges process ваша_модель.stl
```

Получаете `ваша_модель_with_supports.stl` — импортируете в Bambu Studio как обычную модель.

### Вариант 2 — через Python

```powershell
python -m sacrificial_bridges analyze ваша_модель.stl
python -m sacrificial_bridges process ваша_модель.stl --bridge-max 25
```

### Вариант 3 — через Bambu Studio напрямую (в разработке)

В будущем — кнопка в меню Bambu Studio. Пока — используй CLI + импорт STL.

## Тестовая модель

В комплекте:
- `F:\sacrificial-bridges\examples\test_two_boxes.stl` — 2 коробки + перекладина

Запусти:
```powershell
sacrificial-bridges analyze F:\sacrificial-bridges\examples\test_two_boxes.stl
sacrificial-bridges process F:\sacrificial-bridges\examples\test_two_boxes.stl
```

Должен найти 1 bridge (для перекладины) + 2 tree supports (для дна коробок).

## Если не работает

### Команда не найдена

Добавь Python в PATH или используй полный путь:
```powershell
$env:PATH += ";C:\Users\Artem Savinykh\AppData\Local\Python\pythoncore-3.14-64"
sacrificial-bridges analyze model.stl
```

### "ModuleNotFoundError: sacrificial_bridges"

Переустанови:
```powershell
python -m pip install -e F:\sacrificial-bridges --force-reinstall
```

### Bambu Studio не видит плагин

Проверь что папка существует:
```
C:\Users\Artem Savinykh\AppData\Roaming\BambuStudio\plugins\sacrificial_bridges\
```

Перезапусти Bambu Studio.

## Удаление

```powershell
Remove-Item "$env:APPDATA\BambuStudio\plugins\sacrificial_bridges" -Recurse
python -m pip uninstall sacrificial-bridges
```
