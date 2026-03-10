from datetime import date, timedelta
from typing import Optional
from db.database import get_weekly_schedule, get_homework_for_date

async def get_full_homework_with_weekly(target_date: date) -> dict:
    """
    Возвращает словарь предмет -> задание (None, если нет) для указанной даты.
    """
    # 1. Получаем добавленные ДЗ из базы
    manual = await get_homework_for_date(target_date)
    
    # 2. Получаем базовое расписание на этот день недели
    day_of_week = target_date.weekday()
    subjects = await get_weekly_schedule(day_of_week)
    
    # Если расписания на этот день нет (например, в воскресенье)
    if not subjects:
        subjects = []
        
    result = {}
    
    # 3. Сначала выстраиваем предметы по расписанию
    for subject in subjects:
        result[subject] = manual.get(subject)
        
    # 4. Если добавили ДЗ по предмету, которого вдруг нет в расписании,
    # добавляем его в конец списка, чтобы оно не потерялось
    for subject, task in manual.items():
        if subject not in result:
            result[subject] = task
            
    return result

async def get_week_homework(start_date: date) -> dict[date, dict[str, Optional[str]]]:
    """
    Возвращает словарь {дата: {предмет: задание}} для 7 дней.
    """
    week = {}
    for i in range(7):
        current_date = start_date + timedelta(days=i)
        homework = await get_full_homework_with_weekly(current_date)
        week[current_date] = homework
    return week
