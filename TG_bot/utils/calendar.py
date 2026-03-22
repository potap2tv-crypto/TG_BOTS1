from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import calendar
import datetime
from typing import Optional, List
from database import Database

class AppointmentCalendar:
    
    def __init__(self, db: Database):
        self.db = db
    
    async def get_calendar(self, year: Optional[int] = None, 
                          month: Optional[int] = None) -> InlineKeyboardMarkup:
        """Создание календаря с доступными датами"""
        
        now = datetime.datetime.now()
        
        if year is None:
            year = now.year
        if month is None:
            month = now.month
        
        # Создаем календарь на месяц
        cal = calendar.monthcalendar(year, month)
        
        # Создаем клавиатуру
        keyboard = InlineKeyboardBuilder()
        
        # Заголовок с месяцем и годом
        month_name = calendar.month_name[month]
        keyboard.row(InlineKeyboardButton(
            text=f"{month_name} {year}",
            callback_data="ignore"
        ))
        
        # Дни недели
        week_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        keyboard.row(*[
            InlineKeyboardButton(text=day, callback_data="ignore")
            for day in week_days
        ])
        
        # Добавляем дни месяца
        for week in cal:
            row = []
            for day in week:
                if day == 0:
                    row.append(InlineKeyboardButton(
                        text=" ",
                        callback_data="ignore"
                    ))
                else:
                    date_str = f"{year}-{month:02d}-{day:02d}"
                    dt = datetime.date(year, month, day)
                    
                    # Проверяем, доступна ли дата
                    is_available = self._is_date_available(dt)
                    
                    if is_available:
                        row.append(InlineKeyboardButton(
                            text=str(day),
                            callback_data=f"date:{date_str}"
                        ))
                    else:
                        row.append(InlineKeyboardButton(
                            text=f"❌{day}",
                            callback_data="ignore"
                        ))
            keyboard.row(*row)
        
        # Кнопки навигации
        nav_buttons = []
        
        # Предыдущий месяц
        prev_month = month - 1
        prev_year = year
        if prev_month == 0:
            prev_month = 12
            prev_year = year - 1
        
        if self._is_month_available(prev_year, prev_month):
            nav_buttons.append(InlineKeyboardButton(
                text="◀️",
                callback_data=f"calendar:{prev_year}:{prev_month}"
            ))
        
        # Следующий месяц
        next_month = month + 1
        next_year = year
        if next_month == 13:
            next_month = 1
            next_year = year + 1
        
        if self._is_month_available(next_year, next_month):
            nav_buttons.append(InlineKeyboardButton(
                text="▶️",
                callback_data=f"calendar:{next_year}:{next_month}"
            ))
        
        if nav_buttons:
            keyboard.row(*nav_buttons)
        
        # Кнопка отмены
        keyboard.row(InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="cancel"
        ))
        
        return keyboard.as_markup()
    
    def _is_date_available(self, date: datetime.date) -> bool:
        """Проверка, доступна ли дата для записи"""
        now = datetime.datetime.now().date()
        
        # Дата должна быть не раньше сегодняшнего дня
        if date < now:
            return False
        
        # Дата не должна быть дальше месяца от сегодня
        max_date = now + datetime.timedelta(days=30)
        if date > max_date:
            return False
        
        # Проверяем, рабочий ли день
        date_str = date.strftime('%Y-%m-%d')
        if not self.db.is_workday(date_str):
            return False
        
        # Проверяем, есть ли свободные слоты
        available_slots = self.db.get_available_slots(date_str)
        return len(available_slots) > 0
    
    def _is_month_available(self, year: int, month: int) -> bool:
        """Проверка, есть ли доступные дни в месяце"""
        now = datetime.datetime.now().date()
        max_date = now + datetime.timedelta(days=30)
        
        # Проверяем первый день месяца
        first_day = datetime.date(year, month, 1)
        
        # Если месяц полностью в прошлом или дальше максимума
        if first_day > max_date:
            return False
        
        last_day = datetime.date(year, month, calendar.monthrange(year, month)[1])
        if last_day < now:
            return False
        
        return True
    
    async def get_time_slots_keyboard(self, date: str) -> InlineKeyboardMarkup:
        """Создание клавиатуры с доступными временными слотами"""
        available_slots = self.db.get_available_slots(date)
        
        if not available_slots:
            keyboard = InlineKeyboardBuilder()
            keyboard.row(InlineKeyboardButton(
                text="❌ Нет свободного времени",
                callback_data="ignore"
            ))
            keyboard.row(InlineKeyboardButton(
                text="🔙 Назад к календарю",
                callback_data="back_to_calendar"
            ))
            return keyboard.as_markup()
        
        keyboard = InlineKeyboardBuilder()
        
        # Разбиваем слоты по 3 в ряд для удобства
        for i in range(0, len(available_slots), 3):
            row = []
            for time in available_slots[i:i+3]:
                row.append(InlineKeyboardButton(
                    text=time,
                    callback_data=f"time:{date}:{time}"
                ))
            keyboard.row(*row)
        
        keyboard.row(InlineKeyboardButton(
            text="🔙 Назад к календарю",
            callback_data="back_to_calendar"
        ))
        
        return keyboard.as_markup()