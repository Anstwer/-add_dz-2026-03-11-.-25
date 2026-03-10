import aiosqlite
from datetime import date
from typing import Dict, Optional

DB_PATH = "homework.db"

async def init_db():
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
