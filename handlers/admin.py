import re
import difflib
from datetime import date, timedelta

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Импортируем функции из базы данных и сервисов
from db.database import add_homework, delete_homework, get_homework_for_date, get_weekly_schedule, toggle_is_done, get_all_weekly_schedule
from services.homework_service import get_next_lesson_date, get_all_known_subjects

router = Router()

# ==========================================
# ГЕНЕРАТОР КЛАВИАТУРЫ (5 ДНЕЙ + ПЕРЕКЛЮЧЕНИЕ)
# ==========================================
def get_week_keyboard(week_offset: int, action_prefix: str) -> InlineKeyboardMarkup:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    start_date = monday + timedelta(weeks=week_offset)
    
    builder = InlineKeyboardBuilder()
    weekdays_names = ["Пн", "Вт", "Ср", "Чт", "Пт"]
    
    for i in range(5):
        day_date = start_date + timedelta(days=i)
        btn_text = f"{weekdays_names[i]} ({day_date.strftime('%d.%m')})"
        cb_data = f"{action_prefix}_{day_date.isoformat()}"
        builder.button(text=btn_text, callback_data=cb_data)
        
    builder.adjust(2, 2, 1)
    
    if week_offset == 0:
        builder.row(InlineKeyboardButton(text="➡️ След. неделя", callback_data=f"{action_prefix}_week_1"))
    else:
        builder.row(InlineKeyboardButton(text="⬅️ Тек. неделя", callback_data=f"{action_prefix}_week_0"))
        
    return builder.as_markup()


# ==========================================
# ШАГ 2: ИНТЕРАКТИВНОЕ ДОБАВЛЕНИЕ (/add)
# ==========================================
class AddDzState(StatesGroup):
    choosing_date = State()
    choosing_subject = State()
    writing_task = State()

@router.message(Command("add"))
async def cmd_add_interactive(message: Message, state: FSMContext):
    kb = get_week_keyboard(week_offset=0, action_prefix="add_date")
    await message.answer("📅 На какой день добавляем домашку?", reply_markup=kb)
    await state.set_state(AddDzState.choosing_date)

@router.callback_query(AddDzState.choosing_date, F.data.startswith("add_date_week_"))
async def process_add_week_toggle(callback: CallbackQuery):
    offset = int(callback.data.split("_")[-1])
    kb = get_week_keyboard(week_offset=offset, action_prefix="add_date")
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer()

@router.callback_query(AddDzState.choosing_date, F.data.startswith("add_date_"))
async def process_add_date(callback: CallbackQuery, state: FSMContext):
    date_str = callback.data.replace("add_date_", "")
    target_date = date.fromisoformat(date_str)
        
    await state.update_data(target_date=target_date.isoformat())
    
    weekday = target_date.weekday()
    subjects = await get_weekly_schedule(weekday)
    
    if not subjects:
        await callback.message.edit_text(
            f"На {target_date.strftime('%d.%m')} нет уроков по расписанию.\n"
            f"Напиши название предмета вручную текстом:"
        )
        await state.set_state(AddDzState.choosing_subject)
        await callback.answer()
        return
        
    kb_builder = InlineKeyboardBuilder()
    # ИСПОЛЬЗУЕМ ИНДЕКСЫ ВМЕСТО НАЗВАНИЙ, ЧТОБЫ НЕ ПРЕВЫСИТЬ ЛИМИТ TELEGRAM
    for i, subj in enumerate(subjects):
        kb_builder.button(text=subj, callback_data=f"add_subj_{i}")
    kb_builder.adjust(2)
        
    await callback.message.edit_text(f"📅 Дата: <b>{target_date.strftime('%d.%m')}</b>\n📚 Выбери предмет:", reply_markup=kb_builder.as_markup(), parse_mode=ParseMode.HTML)
    await state.set_state(AddDzState.choosing_subject)
    await callback.answer()

@router.callback_query(AddDzState.choosing_subject, F.data.startswith("add_subj_"))
async def process_add_subject(callback: CallbackQuery, state: FSMContext):
    subj_index = int(callback.data.replace("add_subj_", ""))
    
    # Достаем предмет по индексу из расписания
    data = await state.get_data()
    target_date = date.fromisoformat(data['target_date'])
    subjects = await get_weekly_schedule(target_date.weekday())
    subject = subjects[subj_index]
    
    await state.update_data(subject=subject)
    
    await callback.message.edit_text(
        f"📚 Предмет: <b>{subject}</b>\n\n"
        f"✍️ Напиши задание текстом ИЛИ отправь фотографию (можно сразу с подписью):",
        parse_mode=ParseMode.HTML
    )
    await state.set_state(AddDzState.writing_task)
    await callback.answer()

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
# ШАГ 3: ИНТЕРАКТИВНЫЙ ПРОСМОТР И ГАЛОЧКИ (/dz)
# ==========================================
# ==========================================
# ШАГ 3: ИНТЕРАКТИВНЫЙ ПРОСМОТР И ГАЛОЧКИ (/dz)
# ==========================================

# Умное вычисление завтрашнего учебного дня
def get_smart_tomorrow() -> date:
    today = date.today()
    # Если сегодня пятница (4) или суббота (5), то "завтра" для школы — это понедельник
    if today.weekday() == 4:
        return today + timedelta(days=3)
    elif today.weekday() == 5:
        return today + timedelta(days=2)
    else:
        return today + timedelta(days=1)

async def render_dz_message(target_date: date):
    homework = await get_homework_for_date(target_date)
    kb_builder = InlineKeyboardBuilder()
    
    if not homework:
        kb_builder.row(InlineKeyboardButton(text="📅 Выбрать другой день", callback_data="back_to_dz_dates"))
        return f"🎉 На <b>{target_date.strftime('%d.%m')}</b> домашки нет!", kb_builder.as_markup(), None
        
    lines = [f"📋 <b>Домашка на {target_date.strftime('%d.%m')}</b>:\n"]
    photo_id_to_send = None
    
    subjects = list(homework.keys())
    subjects.sort()
    
    for i, subj in enumerate(subjects):
        hw_data = homework[subj]
        task = hw_data["task"]
        is_done = hw_data.get("is_done", 0)
        status = "✅" if is_done else "❌"
        lines.append(f"{status} <b>{subj}</b>: {task}")
        
        btn_text = f"{status} {subj}"
        cb_data = f"t_{target_date.isoformat()}_{i}"
        kb_builder.button(text=btn_text, callback_data=cb_data)
        
        if not photo_id_to_send and hw_data.get("photo_id"):
            photo_id_to_send = hw_data["photo_id"]
            
    kb_builder.adjust(2)
    # Кнопка для перехода к выбору недели
    kb_builder.row(InlineKeyboardButton(text="📅 Выбрать другой день", callback_data="back_to_dz_dates"))
    
    return "\n".join(lines), kb_builder.as_markup(), photo_id_to_send

# Теперь /dz СРАЗУ показывает завтрашний день
@router.message(Command("dz", "zavtra", "завтра"))
async def cmd_get_dz_interactive(message: Message):
    target_date = get_smart_tomorrow()
    text, kb, photo_id = await render_dz_message(target_date)
    
    if photo_id:
        await message.answer_photo(photo=photo_id, caption=text, reply_markup=kb, parse_mode=ParseMode.HTML)
    else:
        await message.answer(text, reply_markup=kb, parse_mode=ParseMode.HTML)

@router.callback_query(F.data.startswith("get_date_week_"))
async def process_get_week_toggle(callback: CallbackQuery):
    offset = int(callback.data.split("_")[-1])
    kb = get_week_keyboard(week_offset=offset, action_prefix="get_date")
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("get_date_"))
async def process_get_date(callback: CallbackQuery):
    date_str = callback.data.replace("get_date_", "")
    target_date = date.fromisoformat(date_str)
    
    text, kb, photo_id = await render_dz_message(target_date)
    
    if photo_id:
        await callback.message.delete()
        await callback.message.answer_photo(photo=photo_id, caption=text, reply_markup=kb, parse_mode=ParseMode.HTML)
    else:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await callback.answer()

@router.callback_query(F.data.startswith("t_"))
async def process_toggle_done(callback: CallbackQuery):
    parts = callback.data.split("_")
    target_date = date.fromisoformat(parts[1])
    subj_index = int(parts[2])
    
    homework = await get_homework_for_date(target_date)
    subjects = list(homework.keys())
    subjects.sort()
    
    if subj_index < len(subjects):
        subject = subjects[subj_index]
        await toggle_is_done(subject, target_date)
    
    text, kb, _ = await render_dz_message(target_date)
    
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode=ParseMode.HTML)
        else:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception:
        pass 
        
    await callback.answer()

@router.callback_query(F.data == "back_to_dz_dates")
async def process_back_to_dz_dates(callback: CallbackQuery):
    kb = get_week_keyboard(week_offset=0, action_prefix="get_date")
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer("📅 На какой день показать домашку?", reply_markup=kb)
    else:
        await callback.message.edit_text("📅 На какой день показать домашку?", reply_markup=kb)
    await callback.answer()


# ==========================================
# СТАРЫЕ КОМАНДЫ (Оставлены для совместимости)
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
        if days_ahead <= 0: days_ahead += 7
        return today + timedelta(days=days_ahead)
    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        try: return date.fromisoformat(date_str)
        except ValueError: return None
    match = re.match(r"^(\d{2})\.(\d{2})$", date_str)
    if match:
        day, month = int(match.group(1)), int(match.group(2))
        try: return date(today.year, month, day)
        except ValueError: return None
    return None

@router.message(Command("add_dz"))
async def cmd_add_dz(message: Message, command: CommandObject):
    await message.answer("Пожалуйста, используйте новую удобную команду /add с кнопками!")

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
                
    if not subject:
        subject = raw_text.split()[0]
    
    target_date = parse_smart_date(rest_text) if rest_text else await get_next_lesson_date(subject)
        
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
    await message.answer("Пожалуйста, используйте новую удобную команду /dz с кнопками!")

@router.message(Command("week"))
async def cmd_week(message: Message):
    schedule = await get_all_weekly_schedule()
    if not schedule:
        await message.answer("Расписание пока пустое!")
        return
        
    weekdays = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    text = "📅 <b>Расписание на неделю:</b>\n\n"
    
    for day_num in range(7):
        subjects = schedule.get(day_num, [])
        if subjects:
            text += f"🔹 <b>{weekdays[day_num]}</b>\n"
            for i, subj in enumerate(subjects, 1):
                text += f"  {i}. {subj}\n"
            text += "\n"
            
    await message.answer(text, parse_mode=ParseMode.HTML)

