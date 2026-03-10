from db.database import get_schedule_for_date, get_weekly_schedule, get_all_manual_homework_for_date

async def get_full_homework_with_weekly(target_date: date) -> dict:
    """
    Возвращает словарь предмет -> задание (None, если нет) для указанной даты.
    Приоритет:
    1. Если есть переопределение расписания на конкретную дату (таблица schedule), используем его.
    2. Иначе берём расписание из weekly_schedule по дню недели.
    3. Если и там нет – возвращаем только ручные записи.
    """
    # Получаем ручные записи (они всегда приоритетны для заданий)
    manual = await get_all_manual_homework_for_date(target_date)
    
    # Пытаемся получить переопределённое расписание на дату
    subjects = await get_schedule_for_date(target_date)
    
    # Если нет переопределения, пробуем получить из еженедельного
    if not subjects:
        day_of_week = target_date.weekday()  # 0=пн, 6=вс
        subjects = await get_weekly_schedule(day_of_week)
    
    # Если и еженедельного нет, возвращаем только ручные
    if not subjects:
        return manual
    
    # Формируем результат
    result = {}
    for subject in subjects:
        result[subject] = manual.get(subject)  # None, если нет задания
    return result
