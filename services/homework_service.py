from datetime import date, timedelta
from typing import Optional
from db.database import get_weekly_schedule, get_homework_for_date

async def get_full_homework_with_weekly(target_date: date) -> dict:
    # Обязательно передаем дату как строку (isoformat), иначе база данных может глючить
    manual = await get_homework_for_date(target_date.isoformat())
    
    day_of_week = target_date.weekday()
    subjects = await get_weekly_schedule(day_of_week)
    
    if not subjects:
        subjects = []
        
    result = {}
    
    # Создаем словарь предметов в нижнем регистре для умного поиска
    schedule_subjects_lower = {s.lower(): s for s in subjects}
    
    # Сначала заполняем расписание пустыми значениями
    for subject in subjects:
        result[subject] = None
        
    # Теперь накладываем ручные ДЗ
    for manual_subj, task in manual.items():
        manual_subj_lower = manual_subj.lower()
        
        # Если предмет есть в расписании (независимо от регистра)
        if manual_subj_lower in schedule_subjects_lower:
            real_subj = schedule_subjects_lower[manual_subj_lower]
            result[real_subj] = task
        else:
            # Если предмета вообще нет в расписании, добавляем его в конец
            result[manual_subj] = task
            
    return result

async def get_week_homework(start_date: date) -> dict[date, dict[str, Optional[str]]]:
    week = {}
    for i in range(7):
        current_date = start_date + timedelta(days=i)
        homework = await get_full_homework_with_weekly(current_date)
        week[current_date] = homework
    return week

async def get_next_lesson_date(subject: str) -> Optional[date]:
    today = date.today()
    for i in range(1, 15):
        check_date = today + timedelta(days=i)
        schedule = await get_weekly_schedule(check_date.weekday())
        if schedule:
            for sched_subject in schedule:
                if sched_subject.lower() == subject.lower():
                    return check_date
    return None
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
