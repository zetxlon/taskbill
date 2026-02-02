# TaskBill — счета по задачам (без НДС)

Офлайн GUI-программа для фрилансеров в РФ:
- Клиенты → Проекты → Задачи
- По каждой задаче: часы, ставка ₽/час
- Генерация PDF-счёта "без НДС"
- Данные хранятся локально в SQLite (`taskbill.db`)

## Запуск (из исходников)
1) Установи Python 3.10+
2) Установи зависимости:
   python3 -m pip install -r requirements.txt
3) Запусти:
   python3 taskbill.py

## Где лежат данные
Файл базы рядом с программой: `taskbill.db`

## Сборка в .exe (Windows)
Смотри `build_windows.bat`

## Сборка (macOS / Linux)
Смотри `build_linux_mac.sh`

## Лицензия
Смотри `LICENSE.txt`
