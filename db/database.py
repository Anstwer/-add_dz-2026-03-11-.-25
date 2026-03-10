import aiosqlite
from datetime import date
from typing import Dict, Optional
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
DB_PATH = "homework.db"

async def init_db():
    await init_weekly_schedule()
    """Создание таблицы, если её нет"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS homework (
                subject TEXT NOT NULL,
                date TEXT NOT NULL,
                task TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (subject, date)
            )
        ''')
        await db.commit()

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
async def set_weekly_schedule(day: int, subjects_list: list):
    """Сохранить расписание на конкретный день недели (заменить существующее)"""
    subjects_str = ','.join(subjects_list)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            INSERT OR REPLACE INTO weekly_schedule (day, subjects)
            VALUES (?, ?)
        ''', (day, subjects_str))
        await db.commit()

async def get_weekly_schedule(day: int) -> list:
    """Получить список предметов для дня недели (пустой список, если нет)"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT subjects FROM weekly_schedule WHERE day = ?
        ''', (day,)) as cursor:
            row = await cursor.fetchone()
            if row and row[0]:
                return row[0].split(',')
            return []

async def get_all_weekly_schedule() -> dict:
    """Получить всё еженедельное расписание в виде словаря {день: [предметы]}"""
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


