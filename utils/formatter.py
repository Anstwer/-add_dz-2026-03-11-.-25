from datetime import date
from typing import Dict

def format_homework_message(target_date: date, homework: Dict[str, str]) -> str:
    """
    Формирует красивое сообщение со списком предметов и заданий.
    Если словарь пуст, сообщает, что заданий нет.
    """
    if not homework:
        return f"📭 На {target_date.strftime('%d.%m.%Y')} нет домашних заданий."

    lines = [f"📚 <b>Домашнее задание на {target_date.strftime('%d.%m.%Y')}</b>\n"]
    for subject, task in homework.items():
        lines.append(f"🔹 <b>{subject}</b>: {task}")
    lines.append("\nЕсли заметили ошибку, напишите Стёпе.")
    return "\n".join(lines)