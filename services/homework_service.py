from datetime import date, timedelta
from typing import Optional
from db.database import get_weekly_schedule, get_homework_for_date

async def get_full_homework_with_weekly(target_date: date) -> dict:
    # ИСПРАВЛЕНИЕ: Убрали .isoformat(), передаем дату как есть!
    manual = await get_homework_for_date(target_date)
    
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

# ИСПРАВЛЕНИЕ: Добавили недостающую функцию для умного поиска предметов
async def get_all_known_subjects() -> list[str]:
    """Собирает все уникальные предметы, которые есть в расписании на неделю"""
    subjects = set()
    for i in range(7):
        day_schedule = await get_weekly_schedule(i)
        if day_schedule:
            for subj in day_schedule:
                subjects.add(subj)
    return list(subjects)
