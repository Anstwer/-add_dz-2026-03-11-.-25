from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "👋 Привет! Я бот для домашних заданий.\n"
        "Команды:\n"
        "/dz — ДЗ на сегодня\n"
        "/dz завтра — ДЗ на завтра\n"
        "/dz ГГГГ-ММ-ДД — ДЗ на конкретную дату\n\n"
        "Администратор может добавлять задания с помощью /add_dz."
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    await cmd_start(message)