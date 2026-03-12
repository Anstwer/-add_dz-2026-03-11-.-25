import re
from datetime import date, timedelta

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db.database import add_homework, delete_homework, get_homework_for_date, get_weekly_schedule, toggle_is_done, get_all_weekly_schedule

router = Router()

# ==========================================
# КОМАНДА /week (РАБОТАЕТ ВСЕГДА)
# ==========================================
@router.message(Command("week"))
async def cmd_week(message: Message, state: FSMContext):
    await state.clear() # Сбрасываем любые зависания
    
    schedule = await get_all_weekly_schedule()
    if not schedule:
        await message.answer("Расписание пока пустое!")
        return
        
    weekdays = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    text = "📅 <b>Расписание на неделю:</b>\n\n"
    
    has_lessons = False
    for day_num in range(7):
        subjects = schedule.get(day_num, [])
        if subjects:
            has_lessons = True
            text += f"🔹 <b>{weekdays[day_num]}</b>\n"
            for i, subj in enumerate(subjects, 1):
                text += f"  {i}. {subj}\n"
            text += "\n"
            
    if not has_lessons:
        await message.answer("Расписание пока пустое!")
        return
        
    await message.answer(text, parse_mode=ParseMode.HTML)


# ==========================================
# ШАГ 3: УМНЫЙ ПРОСМОТР ДЗ (/dz) - ВСЁ В ОДНОМ
# ==========================================
def get_smart_tomorrow() -> date:
    today = date.today()
    if today.weekday() == 4: return today + timedelta(days=3) # Пт -> Пн
    elif today.weekday() == 5: return today + timedelta(days=2) # Сб -> Пн
    elif today.weekday() == 6: return today + timedelta(days=1) # Вс -> Пн
    return today + timedelta(days=1)

async def render_dz_message(target_date: date):
    homework = await get_homework_for_date(target_date)
    kb_builder = InlineKeyboardBuilder()
    
    # 1. ТЕКСТ И ГАЛОЧКИ
    if not homework:
        text = f"🎉 На <b>{target_date.strftime('%d.%m')}</b> домашки нет!"
        photo_id_to_send = None
    else:
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
            
            # Кнопка-галочка
            kb_builder.button(text=f"{status} {subj}", callback_data=f"t_{target_date.isoformat()}_{i}")
            
            if not photo_id_to_send and hw_data.get("photo_id"):
                photo_id_to_send = hw_data["photo_id"]
                
        text = "\n".join(lines)
        kb_builder.adjust(2) # Галочки по 2 в ряд

    # 2. КНОПКИ ДНЕЙ НЕДЕЛИ (Пн-Пт)
    monday = target_date - timedelta(days=target_date.weekday())
    weekdays_names = ["Пн", "Вт", "Ср", "Чт", "Пт"]
    
    day_buttons = []
    for i in range(5):
        day_date = monday + timedelta(days=i)
        marker = "🔘 " if day_date == target_date else ""
        btn_text = f"{marker}{weekdays_names[i]} ({day_date.strftime('%d.%m')})"
        day_buttons.append(InlineKeyboardButton(text=btn_text, callback_data=f"get_date_{day_date.isoformat()}"))
    
    kb_builder.row(*day_buttons[:2])
    kb_builder.row(*day_buttons[2:4])
    kb_builder.row(day_buttons[4])
    
    # 3. КНОПКИ ПЕРЕКЛЮЧЕНИЯ НЕДЕЛЬ
    today_monday = date.today() - timedelta(days=date.today().weekday())
    week_offset = (monday - today_monday).days // 7
    
    if week_offset <= 0:
        kb_builder.row(InlineKeyboardButton(text="➡️ След. неделя", callback_data=f"get_week_{week_offset + 1}"))
    else:
        kb_builder.row(InlineKeyboardButton(text="⬅️ Тек. неделя", callback_data=f"get_week_{week_offset - 1}"))
        
    return text, kb_builder.as_markup(), photo_id_to_send

@router.message(Command("dz", "zavtra", "завтра"))
async def cmd_get_dz_interactive(message: Message, state: FSMContext):
    await state.clear() # Сбрасываем зависания
    target_date = get_smart_tomorrow()
    text, kb, photo_id = await render_dz_message(target_date)
    
    if photo_id:
        await message.answer_photo(photo=photo_id, caption=text, reply_markup=kb, parse_mode=ParseMode.HTML)
    else:
        await message.answer(text, reply_markup=kb, parse_mode=ParseMode.HTML)

@router.callback_query(F.data.startswith("get_date_") | F.data.startswith("get_week_") | F.data.startswith("t_"))
async def process_dz_callbacks(callback: CallbackQuery):
    # Определяем, что нажал пользователь
    if callback.data.startswith("get_date_"):
        target_date = date.fromisoformat(callback.data.replace("get_date_", ""))
    elif callback.data.startswith("get_week_"):
        offset = int(callback.data.replace("get_week_", ""))
        today_monday = date.today() - timedelta(days=date.today().weekday())
        target_date = today_monday + timedelta(weeks=offset) # Показываем понедельник выбранной недели
    elif callback.data.startswith("t_"):
        parts = callback.data.split("_")
        target_date = date.fromisoformat(parts[1])
        subj_index = int(parts[2])
        
        homework = await get_homework_for_date(target_date)
        subjects = list(homework.keys())
        subjects.sort()
        if subj_index < len(subjects):
            await toggle_is_done(subjects[subj_index], target_date)

    # Перерисовываем сообщение
    text, kb, photo_id = await render_dz_message(target_date)
    
    try:
        if photo_id:
            if callback.message.photo:
                await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode=ParseMode.HTML)
            else:
                await callback.message.delete()
                await callback.message.answer_photo(photo=photo_id, caption=text, reply_markup=kb, parse_mode=ParseMode.HTML)
        else:
            if callback.message.photo:
                await callback.message.delete()
                await callback.message.answer(text, reply_markup=kb, parse_mode=ParseMode.HTML)
            else:
                await callback.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception:
        pass 
        
    await callback.answer()


# ==========================================
# ШАГ 2: ИНТЕРАКТИВНОЕ ДОБАВЛЕНИЕ (/add)
# ==========================================
class AddDzState(StatesGroup):
    choosing_date = State()
    choosing_subject = State()
    writing_task = State()

def get_add_week_keyboard(week_offset: int) -> InlineKeyboardMarkup:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    start_date = monday + timedelta(weeks=week_offset)
    
    builder = InlineKeyboardBuilder()
    weekdays_names = ["Пн", "Вт", "Ср", "Чт", "Пт"]
    
    for i in range(5):
        day_date = start_date + timedelta(days=i)
        btn_text = f"{weekdays_names[i]} ({day_date.strftime('%d.%m')})"
        builder.button(text=btn_text, callback_data=f"add_date_{day_date.isoformat()}")
        
    builder.adjust(2, 2, 1)
    
    if week_offset == 0:
        builder.row(InlineKeyboardButton(text="➡️ След. неделя", callback_data="add_week_1"))
    else:
        builder.row(InlineKeyboardButton(text="⬅️ Тек. неделя", callback_data="add_week_0"))
        
    return builder.as_markup()

@router.message(Command("add"))
async def cmd_add_interactive(message: Message, state: FSMContext):
    await state.clear()
    kb = get_add_week_keyboard(week_offset=0)
    await message.answer("📅 На какой день добавляем домашку?", reply_markup=kb)
    await state.set_state(AddDzState.choosing_date)

@router.callback_query(AddDzState.choosing_date, F.data.startswith("add_week_"))
async def process_add_week_toggle(callback: CallbackQuery):
    offset = int(callback.data.split("_")[-1])
    kb = get_add_week_keyboard(week_offset=offset)
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
    for i, subj in enumerate(subjects):
        kb_builder.button(text=subj, callback_data=f"add_subj_{i}")
    kb_builder.adjust(2)
        
    await callback.message.edit_text(f"📅 Дата: <b>{target_date.strftime('%d.%m')}</b>\n📚 Выбери предмет:", reply_markup=kb_builder.as_markup(), parse_mode=ParseMode.HTML)
    await state.set_state(AddDzState.choosing_subject)
    await callback.answer()

@router.callback_query(AddDzState.choosing_subject, F.data.startswith("add_subj_"))
async def process_add_subject(callback: CallbackQuery, state: FSMContext):
    subj_index = int(callback.data.replace("add_subj_", ""))
    
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
# СТАРЫЕ КОМАНДЫ (Оставлены как заглушки)
# ==========================================
@router.message(Command("add_dz", "del_dz", "list_dz"))
async def cmd_old_commands(message: Message):
    await message.answer("❌ Эти команды устарели.\nИспользуйте удобные кнопки:\n/add — добавить ДЗ\n/dz — посмотреть ДЗ")
