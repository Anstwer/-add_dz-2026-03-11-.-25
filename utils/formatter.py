from datetime import date

# Дни недели на русском
WEEKDAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

def format_homework_message(target_date: date, homework: dict) -> str:
    """Красивый вывод ДЗ на один день"""
    weekday_str = WEEKDAYS[target_date.weekday()]
    date_str = target_date.strftime("%d.%m.%Y")
    
    if not homework:
        return f"🏖 <b>{weekday_str} ({date_str})</b>\nУроков нет! Можно отдыхать."

    lines = [f"📅 <b>{weekday_str} ({date_str})</b>\n"]
    
    for i, (subject, task) in enumerate(homework.items(), 1):
        # Если задание есть, пишем его курсивом, если нет — пишем "Не задано"
        task_text = f"<i>{task}</i>" if task else "<i>Не задано</i>"
        lines.append(f"<b>{i}. {subject}</b>\n   └ {task_text}")
        
    return "\n".join(lines)

def format_week_message(week_data: dict) -> str:
    """Красивый вывод ДЗ на всю неделю"""
    lines = ["🗓 <b>РАСПИСАНИЕ НА НЕДЕЛЮ</b>\n"]
    
    for current_date, homework in week_data.items():
        # Пропускаем воскресенье, если там нет уроков и ДЗ
        if current_date.weekday() == 6 and not homework:
            continue
            
        weekday_str = WEEKDAYS[current_date.weekday()]
        date_str = current_date.strftime("%d.%m")
        
        lines.append(f"🔹 <b>{weekday_str} ({date_str})</b>")
        
        if not homework:
            lines.append("   └ <i>Уроков нет</i>\n")
            continue
            
        for subject, task in homework.items():
            task_text = task if task else "Не задано"
            # Используем разные эмодзи: 📝 если есть ДЗ, ➖ если нет
            icon = "📝" if task else "➖"
            lines.append(f"   {icon} <b>{subject}:</b> {task_text}")
            
        lines.append("") # Пустая строка между днями для красоты
        
    return "\n".join(lines)
