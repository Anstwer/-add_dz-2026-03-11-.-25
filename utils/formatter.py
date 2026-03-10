from datetime import date
from typing import Dict, Optional  # <-- добавлен Optional

def format_homework_message(target_date: date, homework: Dict[str, Optional[str]]) -> str:
    """
    Формирует сообщение со списком предметов и заданий.
    Если в словаре значение None, значит задания нет.
    """
    if not homework:
        return f"📭 На {target_date.strftime('%d.%m.%Y')} нет домашних заданий."

    lines = [f"📚 <b>Домашнее задание на {target_date.strftime('%d.%m.%Y')}</b>\n"]
    for subject, task in homework.items():
        if task is None:  # <-- проверка
            lines.append(f"🔹 <b>{subject}</b>: Стёпа не добавил данные")
        else:
            lines.append(f"🔹 <b>{subject}</b>: {task}")
    lines.append("\nЕсли заметили ошибку, напишите Стёпе.")
    return "\n".join(lines)
