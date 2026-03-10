from datetime import date
import html

WEEKDAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

def format_homework_message(target_date: date, homework: dict) -> str:
    """Стильный вывод ДЗ на один день (черный фон)"""
    weekday_str = WEEKDAYS[target_date.weekday()].upper()
    date_str = target_date.strftime("%d.%m.%Y")
    
    if not homework:
        return f"🏖 <b>{weekday_str} ({date_str})</b>\n<code>Уроков нет! Можно отдыхать.</code>"

    # Заголовок (день недели) обычным жирным шрифтом
    lines = [f"📅 <b>{weekday_str} ({date_str})</b>"]
    
    # Собираем само расписание
    day_schedule = []
    for i, (subject, task) in enumerate(homework.items(), 1):
        safe_subj = html.escape(subject)
        if task:
            safe_task = html.escape(task)
            day_schedule.append(f"{i}. {safe_subj}\n   └ {safe_task}")
        else:
            day_schedule.append(f"{i}. {safe_subj}\n   └ Не задано")
            
    # Оборачиваем расписание в тег <pre> (даст черный фон и мелкий шрифт)
    schedule_text = "\n".join(day_schedule)
    lines.append(f"<pre>{schedule_text}</pre>")
        
    return "\n".join(lines)

def format_week_message(week_data: dict) -> str:
    """Стильный вывод ДЗ на всю неделю (черный фон)"""
    lines = ["🗓 <b>РАСПИСАНИЕ НА НЕДЕЛЮ</b>\n"]
    
    for current_date, homework in week_data.items():
        # Пропускаем воскресенье, если нет уроков
        if current_date.weekday() == 6 and not homework:
            continue
            
        weekday_str = WEEKDAYS[current_date.weekday()].upper()
        date_str = current_date.strftime("%d.%m")
        
        # Выделяем день недели жирным шрифтом (он будет вне черного блока)
        lines.append(f"🔹 <b>{weekday_str} ({date_str})</b>")
        
        if not homework:
            lines.append("<code>Уроков нет</code>\n")
            continue
            
        # Собираем предметы для черного блока
        day_schedule = []
        for subject, task in homework.items():
            safe_subj = html.escape(subject)
            if task:
                safe_task = html.escape(task)
                day_schedule.append(f"{safe_subj}: {safe_task}")
            else:
                day_schedule.append(f"{safe_subj}: -")
        
        # Оборачиваем список уроков в тег <pre> (черный фон, мелкий шрифт)
        schedule_text = "\n".join(day_schedule)
        lines.append(f"<pre>{schedule_text}</pre>")
        
    return "\n".join(lines)
