import re
import difflib
from datetime import date, timedelta

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.enums import ParseMode

# Импортируем функции из базы данных и сервисов
from db.database import add_homework, delete_homework, get_homework_for_date, get_weekly_schedule
from services.homework_service import get_next_lesson_date, get_all_known_subjects

router = Router()

# ==========================================
# ШАГ 2: ИНТЕРАКТИВНОЕ ДОБАВЛЕНИЕ (/add)
# ==========================================

class AddDzState(StatesGroup):
    choosing_date = State()
    choosing_subject = State()
    writing_task = State()

@router.message(Command("add"))
async def cmd_add_interactive(message: Message, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="На завтра", callback_data="add_date_tomorrow")],
        [InlineKeyboardButton(text="На послезавтра", callback_data="add_date_aftertomorrow")],
        [InlineKeyboardButton(text="На понедельник", callback_data="add_date_monday")]
    ])
    await message.answer("📅 На какой день добавляем домашку?", reply_markup=kb)
    await state.set_state(AddDzState.choosing_date)

@router.callback_query(AddDzState.choosing_date, F.data.startswith("add_date_"))
async def process_add_date(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split("_")[2]
    today = date.today()
    
    if action == "tomorrow":
        target_date = today + timedelta(days=1)
    elif action == "aftertomorrow":
        target_date = today + timedelta(days=2)
    elif action == "monday":
        days_ahead = 0 - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        target_date = today + timedelta(days=days_ahead)
        
    await state.update_data(target_date=target_date.isoformat())
    
    weekday = target_date.weekday()
    subjects = await get_weekly_schedule(weekday)
    
    if not subjects:
        await callback.message.edit_text(
            f"На {target_date.strftime('%d.%m')} нет уроков по расписанию.\n"
            f"Напиши название предмета вручную текстом:"
        )
        await state.set_state(AddDzState.choosing_subject)
        return
        
    kb_builder = []
    for subj in subjects:
        kb_builder.append([InlineKeyboardButton(text=subj, callback_data=f"add_subj_{subj}")])
        
    kb = InlineKeyboardMarkup(inline_keyboard=kb_builder)
    await callback.message.edit_text(f"📅 Дата: <b>{target_date.strftime('%d.%m')}</b>\n📚 Выбери предмет:", reply_markup=kb, parse_mode=ParseMode.HTML)
    await state.set_state(AddDzState.choosing_subject)

@router.callback_query(AddDzState.choosing_subject, F.data.startswith("add_subj_"))
async def process_add_subject(callback: CallbackQuery, state: FSMContext):
    subject = callback.data.replace("add_subj_", "")
    await state.update_data(subject=subject)
    
    await callback.message.edit_text(
        f"📚 Предмет: <b>{subject}</b>\n\n"
        f"✍️ Напиши задание текстом ИЛИ отправь фотографию (можно сразу с подписью):",
        parse_mode=ParseMode.HTML
    )
    await state.set_state(AddDzState.writing_task)

@router.message(AddDzState.choosing_subject, F.text)
async def process_manual_subject(message: Message, state: FSMContext):
    subject = message.text.strip()
    await state.update_data(subject=subject)
    
    await message.answer(
        f"📚 Предмет: <b>{subject}</b>\n\n"
        f"✍️ Напиши задание текстом ИЛИ отправь фотографию (можно сразу с подписью):",
        parse_mode=ParseMode.HTML
    )
    await state.set_state(AddDzState.writing_task)

@router.message(AddDzState.writing_task, F.photo | F.text)
async def process_add_task(message: Message, state: FSMContext):
    data = await state.get_data()
    target_date_str = data['target_date']
    subject = data['subject']
    
    target_date = date.fromisoformat(target_date_str)
    
    if message.photo:
        photo_id = message.photo[-1].file_id
        task_text = message.caption or "Фотография"
    else:
        photo_id = None
        task_text = message.text
        
    await add_homework(subject, target_date, task_text, photo_id)
    
    await message.answer(
        f"✅ Домашка по предмету <b>{subject}</b> на {target_date.strftime('%d.%m')} успешно сохранена!",
        parse_mode=ParseMode.HTML
    )
    await state.clear()


# ==========================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ И СТАРЫЕ КОМАНДЫ
# ==========================================

def parse_smart_date(date_str: str) -> date | None:
    date_str = date_str.lower()
    today = date.today()
    
    if date_str == "сегодня": return today
    if date_str == "завтра": return today + timedelta(days=1)
    if date_str == "послезавтра": return today + timedelta(days=2)
    
    weekdays = {"пн": 0, "вт": 1, "ср": 2, "чт": 3, "пт": 4, "сб": 5, "вс": 6}
    if date_str in weekdays:
        target_wd = weekdays[date_str]
        current_wd = today.weekday()
        days_ahead = target_wd - current_wd
        if days_ahead <= 0:
            days_ahead += 7
        return today + timedelta(days=days_ahead)
        
    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        try: return date.fromisoformat(date_str)
        except ValueError: return None
        
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

    raw_text = command.args.strip()
    known_subjects = await get_all_known_subjects()
    
    subject = None
    rest_text = ""
    
    if known_subjects:
        known_subjects.sort(key=len, reverse=True)
        for known_subj in known_subjects:
            if raw_text.lower().startswith(known_subj.lower()):
                subject = known_subj
                rest_text = raw_text[len(known_subj):].strip()
                break
                
    if not subject and known_subjects:
        first_word = raw_text.split()[0]
        known_subjects_lower = {s.lower(): s for s in known_subjects}
        matches = difflib.get_close_matches(first_word.lower(), known_subjects_lower.keys(), n=1, cutoff=0.5)
        
        if matches:
            subject = known_subjects_lower[matches[0]]
            rest_text = raw_text[len(first_word):].strip()
            
    if not subject:
        subjects_list = ", ".join(known_subjects) if known_subjects else "Расписание пустое!"
        await message.answer(
            f"❌ <b>Предмет не распознан!</b> Вы ввели несуществующий предмет.\n\n"
            f"📚 <b>Доступные предметы из расписания:</b>\n{subjects_list}\n\n"
            f"<i>Пожалуйста, выберите предмет из списка.</i>", 
            parse_mode=ParseMode.HTML
        )
        return

    if not rest_text:
        await message.answer("❌ Вы указали предмет, но забыли написать само задание!")
        return

    rest_parts = rest_text.split(maxsplit=1)
    target_date = None
    task = rest_text
    
    if len(rest_parts) == 2:
        possible_date_str = rest_parts[0]
        parsed_date = parse_smart_date(possible_date_str)
        if parsed_date:
            target_date = parsed_date
            task = rest_parts[1]
            
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
        # ИСПРАВЛЕНО: добавлена передача target_date
        await add_homework(subject, target_date, task)
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
        
    raw_text = command.args.strip()
    known_subjects = await get_all_known_subjects()
    subject = None
    rest_text = ""
    
    if known_subjects:
        known_subjects.sort(key=len, reverse=True)
        for known_subj in known_subjects:
            if raw_text.lower().startswith(known_subj.lower()):
                subject = known_subj
                rest_text = raw_text[len(known_subj):].strip()
                break
                
    if not subject and known_subjects:
        first_word = raw_text.split()[0]
        known_subjects_lower = {s.lower(): s for s in known_subjects}
        matches = difflib.get_close_matches(first_word.lower(), known_subjects_lower.keys(), n=1, cutoff=0.5)
        if matches:
            subject = known_subjects_lower[matches[0]]
            rest_text = raw_text[len(first_word):].strip()
            
    if not subject:
        subject = raw_text.split()[0]
    
    target_date = None
    if rest_text:
        target_date = parse_smart_date(rest_text)
        
    if not target_date:
        target_date = await get_next_lesson_date(subject)
        if not target_date:
            await message.answer("❌ Не удалось определить дату для удаления. Укажите её вручную (например: /del_dz Химия пт).")
            return
            
    try:
        await delete_homework(subject, target_date)
        await message.answer(f"🗑 Запись по предмету <b>{subject}</b> на <b>{target_date.strftime('%d.%m.%Y')}</b> удалена.", parse_mode=ParseMode.HTML)
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@router.message(Command("list_dz"))
async def cmd_list_dz(message: Message, command: CommandObject):
    target_date = parse_smart_date(command.args) if command.args else date.today()
    if not target_date:
        await message.answer("❌ Неверный формат даты. Используйте: пн, завтра, 15.05")
        return
        
    homework = await get_homework_for_date(target_date)
    if not homework:
        await message.answer(f"На {target_date.strftime('%d.%m.%Y')} в базе нет добавленных вручную заданий.")
        return
        
    lines = [f"📋 Задания в базе на <b>{target_date.strftime('%d.%m.%Y')}</b>:"]
    
    # ИСПРАВЛЕНО: теперь мы получаем словарь со словарями (где есть task, photo_id, is_done)
    for subj, hw_data in homework.items():
        task = hw_data["task"]
        lines.append(f"🔸 <b>{subj}</b>: {task}")
        
    await message.answer("\n".join(lines), parse_mode=ParseMode.HTML)
