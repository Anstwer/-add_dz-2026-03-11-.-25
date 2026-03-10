from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

import config
from db.database import add_homework, delete_homework, get_homework_for_date

router = Router()

# Фильтр: только администратор
admin_filter = F.from_user.id == config.ADMIN_ID

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