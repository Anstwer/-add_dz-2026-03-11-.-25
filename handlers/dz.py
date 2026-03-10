from datetime import date, timedelta
import re
from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from db.database import get_full_homework_with_weekly
from utils.formatter import format_homework_message

router = Router()

def parse_date_arg(arg: str | None) -> date | None:
    """Преобразует аргумент команды в объект date"""
    if not arg:
        return date.today()
    arg = arg.lower().strip()
    if arg == "сегодня":
        return date.today()
    if arg == "завтра":
        return date.today() + timedelta(days=1)
    # Проверка формата YYYY-MM-DD
    if re.match(r"^\d{4}-\d{2}-\d{2}$", arg):
        try:
            return date.fromisoformat(arg)
        except ValueError:
            return None
    return None

@router.message(Command("dz"))
async def cmd_dz(message: Message, command: CommandObject):
    target_date = parse_date_arg(command.args)
    if target_date is None:
        await message.answer("❌ Неверный формат даты. Используйте: /dz, /dz завтра, /dz ГГГГ-ММ-ДД")
        return

    homework = await get_full_homework_with_weekly(target_date)
    text = format_homework_message(target_date, homework)

    await message.answer(text)
