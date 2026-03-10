from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

import config
from db.database import (
    add_homework, delete_homework, get_homework_for_date,
    set_weekly_schedule, get_all_weekly_schedule, delete_weekly_schedule  # <-- добавлено
)

router = Router()
admin_filter = F.from_user.id == config.ADMIN_ID

# ... остальной код без изменений ...
admin_filter = F.from_user.id == config.ADMIN_ID
def day_name_to_int(day_str: str) -> int | None:
    """Преобразует название дня недели в число 0-6 (пн-вс)"""
    names = {
        'пн': 0, 'понедельник': 0,
        'вт': 1, 'вторник': 1,
        'ср': 2, 'среда': 2,
        'чт': 3, 'четверг': 3,
        'пт': 4, 'пятница': 4,
        'сб': 5, 'суббота': 5,
        'вс': 6, 'воскресенье': 6
    }
    return names.get(day_str.lower().strip())
@router.message(Command("set_weekly"), admin_filter)
async def cmd_set_weekly(message: Message, command: CommandObject):
    """Установить расписание на день недели: /set_weekly пн Математика,Русский,Физика"""
    args = command.args
    if not args:
        await message.answer("Использование: /set_weekly день предмет1,предмет2,...")
        return
    parts = args.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Укажите день и список предметов через запятую.")
        return
    day_str, subjects_str = parts
    day = day_name_to_int(day_str)
    if day is None:
        await message.answer("Неверный день. Используйте: пн, вт, ср, чт, пт, сб, вс или полное название.")
        return
    subjects = [s.strip() for s in subjects_str.split(',') if s.strip()]
    if not subjects:
        await message.answer("Список предметов не может быть пустым.")
        return
    await set_weekly_schedule(day, subjects)
    await message.answer(f"✅ Расписание на {day_str} сохранено: {', '.join(subjects)}")

@router.message(Command("get_weekly"), admin_filter)
async def cmd_get_weekly(message: Message):
    """Показать всё еженедельное расписание"""
    weekly = await get_all_weekly_schedule()
    if not weekly:
        await message.answer("Еженедельное расписание ещё не задано.")
        return
    days = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс']
    lines = ["📅 <b>Постоянное расписание по дням недели:</b>"]
    for day in range(7):
        if day in weekly:
            subjects = weekly[day]
            lines.append(f"<b>{days[day]}:</b> {', '.join(subjects)}")
        else:
            lines.append(f"<b>{days[day]}:</b> не задано")
    await message.answer("\n".join(lines))

@router.message(Command("del_weekly"), admin_filter)
async def cmd_del_weekly(message: Message, command: CommandObject):
    """Удалить расписание на день недели: /del_weekly пн"""
    args = command.args
    if not args:
        await message.answer("Использование: /del_weekly день")
        return
    day = day_name_to_int(args)
    if day is None:
        await message.answer("Неверный день.")
        return
    await delete_weekly_schedule(day)
    await message.answer(f"🗑 Расписание на {args} удалено.")
@router.message(Command("add_dz"), admin_filter)
async def cmd_add_dz(message: Message, command: CommandObject):
    """Добавить/обновить ДЗ: /add_dz Предмет ГГГГ-ММ-ДД Текст задания"""
    args = command.args
    if not args:
        await message.answer("Использование: /add_dz Предмет ГГГГ-ММ-ДД Текст задания")
        return

    # Разбиваем на три части: предмет, дата, всё остальное — текст
    parts = args.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("❌ Нужно указать: предмет, дату и текст задания")
        return

    subject, date_str, task = parts
    # Проверка формата даты
    try:
        hw_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        await message.answer("❌ Неверный формат даты. Используйте ГГГГ-ММ-ДД")
        return

    await add_homework(subject, hw_date, task)
    await message.answer(f"✅ Задание по предмету '{subject}' на {date_str} сохранено.")

@router.message(Command("del_dz"), admin_filter)
async def cmd_del_dz(message: Message, command: CommandObject):
    """Удалить ДЗ: /del_dz Предмет ГГГГ-ММ-ДД"""
    args = command.args
    if not args:
        await message.answer("Использование: /del_dz Предмет ГГГГ-ММ-ДД")
        return

    parts = args.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("❌ Укажите предмет и дату")
        return

    subject, date_str = parts
    try:
        hw_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        await message.answer("❌ Неверный формат даты. Используйте ГГГГ-ММ-ДД")
        return

    await delete_homework(subject, hw_date)
    await message.answer(f"🗑 Запись по предмету '{subject}' на {date_str} удалена (если существовала).")

@router.message(Command("list_dz"), admin_filter)
async def cmd_list_dz(message: Message, command: CommandObject):
    """Показать все ДЗ на дату: /list_dz ГГГГ-ММ-ДД"""
    args = command.args
    if not args:
        await message.answer("Использование: /list_dz ГГГГ-ММ-ДД")
        return

    try:
        hw_date = datetime.strptime(args, "%Y-%m-%d").date()
    except ValueError:
        await message.answer("❌ Неверный формат даты. Используйте ГГГГ-ММ-ДД")
        return

    homework = await get_homework_for_date(hw_date)
    if not homework:
        await message.answer(f"На {args} нет домашних заданий.")
        return

    lines = [f"📋 Задания на {args}:"]
    for subject, task in homework.items():
        lines.append(f"🔸 <b>{subject}</b>: {task}")

    await message.answer("\n".join(lines))

