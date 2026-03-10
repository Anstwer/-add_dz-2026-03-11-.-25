from datetime import date, timedelta
from aiogram import Bot
import logging

from db.database import get_full_homework_with_weekly
from utils.formatter import format_homework_message

logger = logging.getLogger(__name__)

async def send_daily_homework(bot: Bot, chat_id: int):
    """Отправляет ДЗ на завтра в указанный чат"""
    target_date = date.today() + timedelta(days=1)  # завтра
    try:
        homework = await get_full_homework_with_weekly(target_date)
        text = format_homework_message(target_date, homework)
        await bot.send_message(chat_id, text, disable_web_page_preview=True)
        logger.info(f"Рассылка на {target_date} отправлена в чат {chat_id}")
    except Exception as e:
        logger.exception(f"Ошибка при отправке рассылки: {e}")
        # Попробуем уведомить админа
        try:
            await bot.send_message(chat_id, f"❌ Не удалось отправить ДЗ на завтра. Ошибка: {e}")
        except:

            pass
