from datetime import date, timedelta
import re

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from aiogram.enums import ParseMode

from db.database import add_homework, delete_homework, get_homework_for_date
from services.homework_service import get_next_lesson_date

router = Router()

def parse_smart_date(date_str: str) -> date | None:
    """Умный парсер дат: понимает 'завтра', 'пн', '15.05' и '2024-05-15'"""
    date_str = date_str.lower()
    today = date.today()
    
    if date_str == "сегодня": return today
    if date_str == "завтра": return today + timedelta(days=1)
    if date_str == "послезавтра": return today + timedelta(days=2)
    
    # Дни недели
    weekdays = {"пн": 0, "вт": 1, "ср": 2, "чт": 3, "пт": 4, "сб": 5, "вс": 6}
    if date_str in weekdays:
        target_wd = weekdays[date_str]
        current_wd = today.weekday()
        days_ahead = target_wd - current_wd
        if days_ahead <= 0: # Если сегодня вторник, а просят "пн", значит следующий понедельник
            days_ahead += 7
        return today + timedelta(days=days_ahead)
        
    # Формат ГГГГ-ММ-ДД
    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        try: return date.fromisoformat(date_str)
        except ValueError: return None
        
    # Формат ДД.ММ (например 15.05)
    match = re.match(r"^(\d{2})\.(\d{2})$", date_str)
    if match:
        day, month = int(match.group(1)), int(match.group(2))
        try:
            return date(today.year, month, day)
        except ValueError:
            return None
            
    return None

@router.message(Command("add_dz"))
async def cmd_add_dz(message: Message, command: CommandObject):
    if not command.args:
        await message.answer(
            "❌ <b>Как добавлять ДЗ:</b>\n\n"
            "🤖 <b>Автоматически (на след. урок):</b>\n<code>/add_dz Химия параграф 5</code>\n\n"
            "📅 <b>На день недели:</b>\n<code>/add_dz Химия пт параграф 5</code>\n\n"
            "📆 <b>На число:</b>\n<code>/add_dz Химия 15.05 параграф 5</code>",
            parse_mode=ParseMode.HTML
        )
        return

    args = command.args.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ Нужно указать предмет и задание.")
        return
        
    subject = args[0]
    rest = args[1]
    
    # Пробуем вытащить дату из текста после предмета
    rest_parts = rest.split(maxsplit=1)
    target_date = None
    task = rest
    
    if len(rest_parts) == 2:
        possible_date_str = rest_parts[0]
        parsed_date = parse_smart_date(possible_date_str)
        if parsed_date:
            target_date = parsed_date
            task = rest_parts[1]
            
    # Если дату не указали (или написали обычный текст), ищем следующий урок по расписанию
    if not target_date:
        target_date = await get_next_lesson_date(subject)
        if not target_date:
            await message.answer(
                f"❌ Не нашел предмет <b>{subject}</b> в расписании на ближайшие 14 дней.\n"
                f"Укажите дату вручную, например: <code>/add_dz {subject} завтра {task}</code>", 
                parse_mode=ParseMode.HTML
            )
            return

    try:
        await add_homework(subject, target_date.isoformat(), task)
        await message.answer(
            f"✅ Задание по предмету <b>{subject}</b> на <b>{target_date.strftime('%d.%m.%Y')}</b> сохранено:\n<i>{task}</i>", 
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка при сохранении: {e}")

@router.message(Command("del_dz"))
async def cmd_del_dz(message: Message, command: CommandObject):
    if not command.args:
        await message.answer("❌ Использование: <code>/del_dz Предмет [дата/день недели]</code>", parse_mode=ParseMode.HTML)
        return
        
    args = command.args.split(maxsplit=1)
    subject = args[0]
    
    target_date = None
    if len(args) == 2:
        target_date = parse_smart_date(args[1])
        
    if not target_date:
        target_date = await get_next_lesson_date(subject)
        if not target_date:
            await message.answer("❌ Не удалось определить дату для удаления. Укажите её вручную (например: /del_dz Химия пт).")
            return
            
    try:
        await delete_homework(subject, target_date.isoformat())
        await message.answer(f"🗑 Запись по предмету <b>{subject}</b> на <b>{target_date.strftime('%d.%m.%Y')}</b> удалена.", parse_mode=ParseMode.HTML)
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@router.message(Command("list_dz"))
async def cmd_list_dz(message: Message, command: CommandObject):
    target_date = parse_smart_date(command.args) if command.args else date.today()
    if not target_date:
        await message.answer("❌ Неверный формат даты. Используйте: пн, завтра, 15.05")
        return
        
    homework = await get_homework_for_date(target_date.isoformat())
    if not homework:
        await message.answer(f"На {target_date.strftime('%d.%m.%Y')} в базе нет добавленных вручную заданий.")
        return
        
    lines = [f"📋 Задания в базе на <b>{target_date.strftime('%d.%m.%Y')}</b>:"]
    for subj, task in homework.items():
        lines.append(f"🔸 <b>{subj}</b>: {task}")
    await message.answer("\n".join(lines), parse_mode=ParseMode.HTML)
