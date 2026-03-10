import os
from aiohttp import web
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.session.aiohttp import AiohttpSession
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

import config
from db.database import init_db
from handlers import common, dz, admin
from services.daily import send_daily_homework

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)

# Создаём сессию с увеличенным таймаутом (60 секунд)
session = AiohttpSession(timeout=60)
bot = Bot(token=config.BOT_TOKEN, parse_mode=ParseMode.HTML, session=session)
dp = Dispatcher(storage=MemoryStorage())

async def on_startup():
    """Действия при запуске бота"""
    await init_db()
    logger.info("Бот запущен, база данных инициализирована")
    try:
        await bot.send_message(config.ADMIN_ID, "✅ Бот запущен и готов к работе!")
    except Exception as e:
        logger.error(f"Не удалось уведомить админа: {e}")

async def on_shutdown():
    logger.info("Бот останавливается...")
# --- ВЕБ-СЕРВЕР ЗАГЛУШКА ДЛЯ RENDER ---
async def handle_ping(request):
    return web.Response(text="Бот Стёпы работает!")

async def start_dummy_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    # Render автоматически задает переменную окружения PORT
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"Веб-заглушка запущена на порту {port}")
async def main():
    await start_dummy_server()
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Регистрация роутеров
    dp.include_router(common.router)
    dp.include_router(dz.router)
    dp.include_router(admin.router)

    # Планировщик для ежедневной рассылки (каждый день в 16:00)
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")  # Укажите свой часовой пояс
    scheduler.add_job(
        send_daily_homework,
        trigger=CronTrigger(hour=16, minute=0),
        kwargs={"bot": bot, "chat_id": config.CHAT_ID}
    )
    scheduler.start()
    logger.info("Планировщик запущен, рассылка запланирована на 16:00")
    

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

