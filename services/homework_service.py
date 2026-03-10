from datetime import date  # <-- добавлено
from db.database import (
    get_schedule_for_date,
    get_weekly_schedule,
    get_homework_for_date  # <-- используем эту функцию
)

async def get_full_homework_with_weekly(target_date: date) -> dict:
    """
    Возвращает словарь предмет -> задание (None, если нет) для указанной даты.
    """
    # Получаем ручные записи
    manual = await get_homework_for_date(target_date)  # <-- изменено
    
    # Пытаемся получить переопределённое расписание на дату
    subjects = await get_schedule_for_date(target_date)
    
    # Если нет переопределения, пробуем получить из еженедельного
    if not subjects:
        day_of_week = target_date.weekday()
        subjects = await get_weekly_schedule(day_of_week)
    
    # Если и еженедельного нет, возвращаем только ручные
    if not subjects:
        return manual
    
    # Формируем результат
    result = {}
    for subject in subjects:
        result[subject] = manual.get(subject)  # None, если нет задания
    return result
async def get_week_homework(start_date: date) -> dict[date, dict[str, Optional[str]]]:
    """
    Возвращает словарь {дата: {предмет: задание}} для 7 дней, начиная с start_date.
    """
    week = {}
    for i in range(7):
        current_date = start_date + timedelta(days=i)
        homework = await get_full_homework_with_weekly(current_date)
        week[current_date] = homework
    return week
