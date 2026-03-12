import aiosqlite
from datetime import date
from typing import Dict, Optional

WEEKLY_SCHEDULE = {
    0: ["Разговоры о важном", "Биология", "Английский язык", "История", "Русский язык", "Вероятность и статистика", "Литература"],
    1: ["Химия", "Английский язык", "Геометрия", "Информатика", "Физика", "Алгебра", "Общество"],
    2: ["Биология", "ОБЗР", "Геометрия", "Физика", "Русский язык", "Алгебра"],
    3: ["Литература", "История", "Классный час", "География", "Английский язык", "Русский язык", "Алгебра", "Физкультура"],
    4: ["География", "Литература", "Физкультура", "Химия",  "Физика", "Русский язык", "Труд"],
    5: [],
    6: []
}

DB_PATH = "homework.db"

async def init_weekly_schedule():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('CREATE TABLE IF NOT EXISTS weekly_schedule (day INTEGER PRIMARY KEY, subjects TEXT NOT NULL)')
        await db.commit()

async def init_db():
    await init_weekly_schedule()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS homework (subject TEXT NOT NULL, date TEXT NOT NULL, task TEXT NOT NULL, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (subject, date))''')
        try: await db.execute('ALTER TABLE homework ADD COLUMN photo_id TEXT')
        except Exception: pass
        try: await db.execute('ALTER TABLE homework ADD COLUMN is_done INTEGER DEFAULT 0')
        except Exception: pass
        await db.execute('CREATE TABLE IF NOT EXISTS schedule (date TEXT PRIMARY KEY, subjects TEXT NOT NULL)')
        await db.commit()

async def add_homework(subject: str, hw_date: date, task: str, photo_id: str = None):
    date_str = hw_date if isinstance(hw_date, str) else hw_date.isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''INSERT INTO homework (subject, date, task, photo_id) VALUES (?, ?, ?, ?) ON CONFLICT(subject, date) DO UPDATE SET task = excluded.task, photo_id = excluded.photo_id, updated_at = CURRENT_TIMESTAMP''', (subject, date_str, task, photo_id))
        await db.commit()

async def delete_homework(subject: str, hw_date: date):
    date_str = hw_date if isinstance(hw_date, str) else hw_date.isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('DELETE FROM homework WHERE subject = ? AND date = ?', (subject, date_str))
        await db.commit()

async def get_homework_for_date(hw_date: date) -> Dict[str, dict]:
    date_str = hw_date if isinstance(hw_date, str) else hw_date.isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT subject, task, photo_id, is_done FROM homework WHERE date = ? ORDER BY subject', (date_str,)) as cursor:
            rows = await cursor.fetchall()
            return {row[0]: {"task": row[1], "photo_id": row[2], "is_done": row[3] or 0} for row in rows}

get_all_manual_homework_for_date = get_homework_for_date

async def get_weekly_schedule(day_of_week: int) -> list[str]:
    return WEEKLY_SCHEDULE.get(day_of_week, [])

async def get_all_weekly_schedule() -> dict:
    return WEEKLY_SCHEDULE

async def toggle_is_done(subject: str, hw_date: date):
    date_str = hw_date if isinstance(hw_date, str) else hw_date.isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT is_done FROM homework WHERE subject = ? AND date = ?', (subject, date_str)) as cursor:
            row = await cursor.fetchone()
        if row is None:
            await db.execute('INSERT INTO homework (subject, date, task, is_done) VALUES (?, ?, ?, ?)', (subject, date_str, "Не задано", 1))
        else:
            await db.execute('UPDATE homework SET is_done = CASE WHEN is_done = 1 THEN 0 ELSE 1 END WHERE subject = ? AND date = ?', (subject, date_str))
        await db.commit()
