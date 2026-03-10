from datetime import date
import html

WEEKDAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

def format_homework_message(target_date: date, homework: dict) -> str:
    weekday_str = WEEKDAYS[target_date.weekday()]
    date_str = target_date.strftime("%d.%m.%Y")
    
    if not homework:
        return f"🏖 <b>{weekday_str} ({date_str})</b>\nУроков нет! Можно отдыхать."

    lines = [f"📅 <b>{weekday_str} ({date_str})</b>\n"]
    
    for i, (subject, task) in enumerate(homework.items(), 1):
        # Экранируем текст, чтобы Telegram не выдавал ошибку из-за спецсимволов
        safe_subj = html.escape(subject)
        if task:
            safe_task = html.escape(task)
            lines.append(f"<b>{i}. {safe_subj}</b>\n   └ <i>{safe_task}</i>")
        else:
            lines.append(f"<b>{i}. {safe_subj}</b>\n   └ <i>Не задано</i>")
        
    return "\n".join(lines)

def format_week_message(week_data: dict) -> str:
    lines = ["🗓 <b>РАСПИСАНИЕ НА НЕДЕЛЮ</b>\n"]
    
    for current_date, homework in week_data.items():
        if current_date.weekday() == 6 and not homework:
            continue
            
        weekday_str = WEEKDAYS[current_date.weekday()]
        date_str = current_date.strftime("%d.%m")
        
        lines.append(f"🔹 <b>{weekday_str} ({date_str})</b>")
        
        if not homework:
            lines.append("   └ <i>Уроков нет</i>\n")
            continue
            
        for subject, task in homework.items():
            safe_subj = html.escape(subject)
            if task:
                safe_task = html.escape(task)
                lines.append(f"   📝 <b>{safe_subj}:</b> {safe_task}")
            else:
                lines.append(f"   ➖ <b>{safe_subj}:</b> Не задано")
            
        lines.append("")
        
    return "\n".join(lines)
