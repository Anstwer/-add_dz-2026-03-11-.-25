from datetime import date
from typing import Dict, Optional

def format_homework_message(target_date: date, homework: Dict[str, Optional[str]]) -> str:
    """
    Формирует сообщение в виде моноширинного блока.
    """
    if not homework:
        return f"📭 На {target_date.strftime('%d.%m.%Y')} нет домашних заданий."

    lines = [f"Домашнее задание на {target_date.strftime('%d.%m.%Y')}"]
    lines.append("-" * 30)  # разделитель

    for subject, task in homework.items():
        if task is None:
            lines.append(f"🔸 {subject}: Стёпа не добавил данные")
        else:
            lines.append(f"🔸 {subject}: {task}")

    lines.append("-" * 30)
    lines.append("Если заметили ошибку, напишите Стёпе.")

    # Оборачиваем всё в <pre> для моноширинного блока
    return f"<pre>{chr(10).join(lines)}</pre>"
def format_week_message(week_data: dict[date, dict[str, Optional[str]]]) -> str:
    lines = ["<b>📅 Домашние задания на текущую неделю</b>"]
    for day_date, homework in week_data.items():
        day_str = day_date.strftime("%A, %d.%m.%Y")
        lines.append(f"\n<b>{day_str}</b>")
        if not homework:
            lines.append("   Нет заданий")
        else:
            for subject, task in homework.items():
                if task is None:
                    lines.append(f"   🔸 {subject}: Стёпа не добавил данные")
                else:
                    lines.append(f"   🔸 {subject}: {task}")
    # Объединяем строки с переносом и оборачиваем в <pre>
    return "<pre>" + "\n".join(lines) + "</pre>"
