import aiosqlite
from datetime import date
from typing import Dict, Optional

DB_PATH = "homework.db"  # <-- перенесено в начало

async def init_weekly_schedule():
    """Создание таблицы еженедельного расписания"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS weekly_schedule (
                day INTEGER PRIMARY KEY,  -- 0=пн, 1=вт, ..., 6=вс
                subjects TEXT NOT NULL
            )
        ''')
        await db.commit()

async def init_db():
    """Создание всех таблиц"""
    await init_weekly_schedule()
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблица homework
        await db.execute('''
            CREATE TABLE IF NOT EXISTS homework (
                subject TEXT NOT NULL,
                date TEXT NOT NULL,
                task TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (subject, date)
            )
        ''')
        # Таблица schedule (переопределение на конкретную дату)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS schedule (
                date TEXT PRIMARY KEY,
                subjects TEXT NOT NULL
            )
        ''')
        await db.commit()

# ---------- Homework ----------
async def add_homework(subject: str, hw_date: date, task: str):
    """Добавить или обновить запись"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            INSERT INTO homework (subject, date, task)
            VALUES (?, ?, ?)
            ON CONFLICT(subject, date) DO UPDATE SET
                task = excluded.task,
                updated_at = CURRENT_TIMESTAMP
        ''', (subject, hw_date.isoformat(), task))
        await db.commit()

async def delete_homework(subject: str, hw_date: date):
    """Удалить запись по предмету и дате"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            DELETE FROM homework
            WHERE subject = ? AND date = ?
        ''', (subject, hw_date.isoformat()))
        await db.commit()

async def get_homework_for_date(hw_date: date) -> Dict[str, str]:
    """Получить все задания на конкретную дату в виде словаря {предмет: задание}"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT subject, task FROM homework
            WHERE date = ?
            ORDER BY subject
        ''', (hw_date.isoformat(),)) as cursor:
            rows = await cursor.fetchall()
            return {row[0]: row[1] for row in rows}

# Псевдоним для совместимости с homework_service
get_all_manual_homework_for_date = get_homework_for_date

# ---------- Schedule (переопределение на дату) ----------
async def set_schedule_for_date(sch_date: date, subjects_list: list):
    """Сохранить расписание на конкретную дату (заменить существующее)"""
    subjects_str = ','.join(subjects_list)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            INSERT OR REPLACE INTO schedule (date, subjects)
            VALUES (?, ?)
        ''', (sch_date.isoformat(), subjects_str))
        await db.commit()

async def get_schedule_for_date(sch_date: date) -> list:
    """Получить список предметов на дату (пустой список, если нет)"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT subjects FROM schedule WHERE date = ?
        ''', (sch_date.isoformat(),)) as cursor:
            row = await cursor.fetchone()
            if row and row[0]:
                return row[0].split(',')
            return []

async def delete_schedule_for_date(sch_date: date):
    """Удалить расписание на конкретную дату"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            DELETE FROM schedule WHERE date = ?
        ''', (sch_date.isoformat(),))
        await db.commit()

# ---------- Weekly schedule ----------
async def set_weekly_schedule(day: int, subjects_list: list):
    """Сохранить расписание на конкретный день недели"""
    subjects_str = ','.join(subjects_list)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            INSERT OR REPLACE INTO weekly_schedule (day, subjects)
            VALUES (?, ?)
        ''', (day, subjects_str))
        await db.commit()

async def get_weekly_schedule(day: int) -> list:
    """Получить список предметов для дня недели"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT subjects FROM weekly_schedule WHERE day = ?
        ''', (day,)) as cursor:
            row = await cursor.fetchone()
            if row and row[0]:
                return row[0].split(',')
            return []

async def get_all_weekly_schedule() -> dict:
    """Получить всё еженедельное расписание"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT day, subjects FROM weekly_schedule ORDER BY day
        ''') as cursor:
            rows = await cursor.fetchall()
            return {day: subjects.split(',') for day, subjects in rows}

async def delete_weekly_schedule(day: int):
    """Удалить расписание для дня недели"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            DELETE FROM weekly_schedule WHERE day = ?
        ''', (day,))
        await db.commit()
