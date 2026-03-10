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
