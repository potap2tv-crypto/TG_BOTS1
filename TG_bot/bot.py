#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from database import Database
from scheduler import ReminderScheduler

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
db = Database()
scheduler = ReminderScheduler(bot)

async def on_startup():
    """Действия при запуске бота"""
    logger.info("Бот запускается...")
    
    # Восстанавливаем напоминания
    await scheduler.restore_reminders(db)
    
    # Запускаем планировщик
    scheduler.start()
    
    logger.info("Бот успешно запущен!")

async def on_shutdown():
    """Действия при остановке бота"""
    logger.info("Бот останавливается...")
    
    # Останавливаем планировщик
    scheduler.shutdown()
    
    # Закрываем соединение с БД
    db.close()
    
    logger.info("Бот остановлен")

async def main():
    """Главная функция"""
    # Регистрируем роутеры
    from handlers import common, user, admin, callbacks
    
    dp.include_router(common.router)
    dp.include_router(user.router)
    dp.include_router(admin.router)
    dp.include_router(callbacks.router)
    
    # Запускаем
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main())