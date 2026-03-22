from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta
from typing import Dict, Any
import logging

class ReminderScheduler:
    def __init__(self, bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler(
            jobstores={'default': MemoryJobStore()},
            executors={'default': AsyncIOExecutor()},
            timezone='Europe/Moscow'
        )
        self.jobs: Dict[int, str] = {}  # appointment_id -> job_id
        
    def start(self):
        """Запуск планировщика"""
        self.scheduler.start()
        logging.info("Планировщик напоминаний запущен")
    
    def shutdown(self):
        """Остановка планировщика"""
        self.scheduler.shutdown()
    
    async def schedule_reminder(self, appointment_id: int, user_id: int, 
                               appointment_date: str, appointment_time: str):
        """Планирование напоминания за 24 часа до записи"""
        
        # Парсим дату и время
        dt_str = f"{appointment_date} {appointment_time}"
        appointment_dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M')
        
        # Время напоминания (за 24 часа)
        reminder_time = appointment_dt - timedelta(hours=24)
        now = datetime.now()
        
        # Если до записи меньше 24 часов, не создаем напоминание
        if reminder_time <= now:
            logging.info(f"Запись #{appointment_id} создана менее чем за 24 часа, напоминание не создано")
            return False
        
        # Создаем задачу
        job = self.scheduler.add_job(
            self.send_reminder,
            trigger=DateTrigger(run_date=reminder_time),
            args=[appointment_id, user_id, appointment_date, appointment_time],
            id=f"reminder_{appointment_id}",
            replace_existing=True
        )
        
        self.jobs[appointment_id] = job.id
        logging.info(f"Напоминание для записи #{appointment_id} запланировано на {reminder_time}")
        return True
    
    async def send_reminder(self, appointment_id: int, user_id: int, 
                           appointment_date: str, appointment_time: str):
        """Отправка напоминания"""
        try:
            # Форматируем дату для сообщения
            date_obj = datetime.strptime(appointment_date, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%d.%m.%Y')
            
            text = (
                f"⏰ <b>НАПОМИНАНИЕ</b>\n\n"
                f"Вы записаны на завтра, {formatted_date} в {appointment_time}.\n"
                f"Ждём вас! 💅"
            )
            
            await self.bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode='HTML'
            )
            
            logging.info(f"Напоминание для записи #{appointment_id} отправлено пользователю {user_id}")
            
            # Здесь можно отметить в БД, что напоминание отправлено
            # Но это будет делать обработчик после отправки
            
        except Exception as e:
            logging.error(f"Ошибка при отправке напоминания: {e}")
    
    def remove_reminder(self, appointment_id: int):
        """Удаление напоминания (при отмене записи)"""
        if appointment_id in self.jobs:
            try:
                self.scheduler.remove_job(self.jobs[appointment_id])
                del self.jobs[appointment_id]
                logging.info(f"Напоминание для записи #{appointment_id} удалено")
                return True
            except Exception as e:
                logging.error(f"Ошибка при удалении напоминания: {e}")
        return False
    
    async def restore_reminders(self, db):
        """Восстановление напоминаний после перезапуска бота"""
        appointments = db.get_upcoming_appointments()
        
        for apt in appointments:
            # Проверяем, не было ли уже отправлено напоминание
            if apt['reminder_sent']:
                continue
            
            # Планируем напоминание
            await self.schedule_reminder(
                apt['id'],
                apt['user_id'],
                apt['date'],
                apt['time']
            )
        
        logging.info(f"Восстановлено {len(appointments)} напоминаний")