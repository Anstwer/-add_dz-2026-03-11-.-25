


# Убедись, что у тебя правильно импортирована база данных. 
# Если твой файл называется database.py и лежит в папке db, то импорт выглядит так:
# import db.database as db 
# (или как он у тебя уже импортирован)
from datetime import date, timedelta
import re
import difflib

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from datetime import date, timedelta

# Убедись, что у тебя правильно импортирована база данных. 
# Если твой файл называется database.py и лежит в папке db, то импорт выглядит так:
# import db.database as db 
# (или как он у тебя уже импортирован)
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from aiogram.enums import ParseMode

from db.database import add_homework, delete_homework, get_homework_for_date
from services.homework_service import get_next_lesson_date, get_all_known_subjects

router = Router()

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
    
    # 1. Ищем точное совпадение предмета (даже если он из двух слов, например "Русский язык")
    if known_subjects:
        # Сортируем от длинных к коротким, чтобы "Русский язык" проверялся раньше "Русский"
        known_subjects.sort(key=len, reverse=True)
        for known_subj in known_subjects:
            if raw_text.lower().startswith(known_subj.lower()):
                subject = known_subj
                # Отрезаем название предмета, оставляем только дату и текст ДЗ
                rest_text = raw_text[len(known_subj):].strip()
                break
                
    # 2. Если точного совпадения нет, пробуем найти опечатку по первому слову
    if not subject and known_subjects:
        first_word = raw_text.split()[0]
        known_subjects_lower = {s.lower(): s for s in known_subjects}
        matches = difflib.get_close_matches(first_word.lower(), known_subjects_lower.keys(), n=1, cutoff=0.5)
        
        if matches:
            subject = known_subjects_lower[matches[0]]
            rest_text = raw_text[len(first_word):].strip()
            
    # 3. Если предмет всё равно не найден (ввели абракадабру)
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

    # Пробуем вытащить дату из оставшегося текста
    rest_parts = rest_text.split(maxsplit=1)
    target_date = None
    task = rest_text
    
    if len(rest_parts) == 2:
        possible_date_str = rest_parts[0]
        parsed_date = parse_smart_date(possible_date_str)
        if parsed_date:
            target_date = parsed_date
            task = rest_parts[1]
            
    # Если дату не указали, ищем следующий урок по расписанию
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
        await add_homework(subject, task)
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
        subject = raw_text.split()[0] # Если не нашли, берем первое слово как есть
    
    target_date = None
    if rest_text:
        target_date = parse_smart_date(rest_text)
        
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
# --- ШАГ 2: ИНТЕРАКТИВНОЕ ДОБАВЛЕНИЕ ДОМАШКИ ---

# Создаем "состояния" (шаги), по которым пойдет пользователь
class AddDzState(StatesGroup):
    choosing_date = State()
    choosing_subject = State()
    writing_task = State()

# 1. Пользователь пишет /add
@router.message(Command("add"))
async def cmd_add_interactive(message: Message, state: FSMContext):
    # Создаем кнопки с датами
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="На завтра", callback_data="add_date_tomorrow")],
        [InlineKeyboardButton(text="На послезавтра", callback_data="add_date_aftertomorrow")],
        [InlineKeyboardButton(text="На понедельник", callback_data="add_date_monday")]
    ])
    await message.answer("📅 На какой день добавляем домашку?", reply_markup=kb)
    # Переводим бота в режим ожидания выбора даты
    await state.set_state(AddDzState.choosing_date)

# 2. Пользователь нажал кнопку с датой
@router.callback_query(AddDzState.choosing_date, F.data.startswith("add_date_"))
async def process_add_date(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split("_")[2] # получаем 'tomorrow', 'aftertomorrow' или 'monday'
    today = date.today()
    
    # Вычисляем нужную дату
    if action == "tomorrow":
        target_date = today + timedelta(days=1)
    elif action == "aftertomorrow":
        target_date = today + timedelta(days=2)
    elif action == "monday":
        days_ahead = 0 - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        target_date = today + timedelta(days=days_ahead)
        
    # Запоминаем дату в памяти бота
    await state.update_data(target_date=target_date.isoformat())
    
    # Получаем предметы на этот день недели из базы данных
    weekday = target_date.weekday()
    subjects = await db.get_weekly_schedule(weekday)
    
    if not subjects:
        await callback.message.edit_text(
            f"На {target_date.strftime('%d.%m')} нет уроков по расписанию.\n"
            f"Напиши название предмета вручную текстом:"
        )
        await state.set_state(AddDzState.choosing_subject)
        return
        
    # Генерируем кнопки с предметами
    kb_builder = []
    for subj in subjects:
        kb_builder.append([InlineKeyboardButton(text=subj, callback_data=f"add_subj_{subj}")])
        
    kb = InlineKeyboardMarkup(inline_keyboard=kb_builder)
    await callback.message.edit_text(f"📅 Дата: {target_date.strftime('%d.%m')}\n📚 Выбери предмет:", reply_markup=kb)
    # Переводим бота в режим ожидания выбора предмета
    await state.set_state(AddDzState.choosing_subject)

# 3. Пользователь нажал кнопку с предметом
@router.callback_query(AddDzState.choosing_subject, F.data.startswith("add_subj_"))
async def process_add_subject(callback: CallbackQuery, state: FSMContext):
    subject = callback.data.replace("add_subj_", "")
    await state.update_data(subject=subject) # Запоминаем предмет
    
    await callback.message.edit_text(
        f"📚 Предмет: <b>{subject}</b>\n\n"
        f"✍️ Напиши задание текстом ИЛИ отправь фотографию (можно сразу с подписью):",
        parse_mode="HTML"
    )
    # Переводим бота в режим ожидания текста или фото
    await state.set_state(AddDzState.writing_task)

# 3.1. Если расписания нет, и пользователь написал предмет вручную
@router.message(AddDzState.choosing_subject, F.text)
async def process_manual_subject(message: Message, state: FSMContext):
    subject = message.text.strip()
    await state.update_data(subject=subject)
    
    await message.answer(
        f"📚 Предмет: <b>{subject}</b>\n\n"
        f"✍️ Напиши задание текстом ИЛИ отправь фотографию (можно сразу с подписью):",
        parse_mode="HTML"
    )
    await state.set_state(AddDzState.writing_task)

# 4. Пользователь прислал текст или фото с заданием
@router.message(AddDzState.writing_task, F.photo | F.text)
async def process_add_task(message: Message, state: FSMContext):
    # Достаем сохраненные дату и предмет из памяти
    data = await state.get_data()
    target_date_str = data['target_date']
    subject = data['subject']
    
    # Разбираемся, что прислал пользователь: фото или текст
    if message.photo:
        photo_id = message.photo[-1].file_id # Берем фото в лучшем качестве
        task_text = message.caption or "Фотография" # Если есть подпись - берем ее
    else:
        photo_id = None
        task_text = message.text
        
    # Сохраняем в базу данных!
    await db.add_homework(subject, target_date_str, task_text, photo_id)
    
    await message.answer(
        f"✅ Домашка по предмету <b>{subject}</b> на {target_date_str} успешно сохранена!",
        parse_mode="HTML"
    )
    # Очищаем память бота, завершаем процесс
    await state.clear()


