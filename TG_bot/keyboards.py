from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Optional
import datetime

class Keyboards:
    
    @staticmethod
    def main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
        """Главное меню"""
        keyboard = [
            [KeyboardButton(text="📅 Записаться")],
            [KeyboardButton(text="💰 Прайс"), KeyboardButton(text="📸 Портфолио")],
            [KeyboardButton(text="📋 Мои записи"), KeyboardButton(text="❌ Отменить запись")]
        ]
        
        if is_admin:
            keyboard.append([KeyboardButton(text="⚙️ Админ панель")])
        
        return ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True
        )
    
    @staticmethod
    def portfolio() -> InlineKeyboardMarkup:
        """Клавиатура для портфолио"""
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(
            text="📸 Смотреть портфолио",
            url="https://ru.pinterest.com/crystalwithluv/_created/"
        ))
        return keyboard.as_markup()
    
    @staticmethod
    def prices() -> str:
        """Текст с прайсом"""
        return """
<b>💰 ПРАЙС-ЛИСТ</b>

💅 <b>Френч</b> — 1000₽
💅 <b>Квадрат</b> — 500₽

По всем вопросам обращаться к администратору.
        """
    
    @staticmethod
    def appointment_actions(appointment_id: int) -> InlineKeyboardMarkup:
        """Кнопки действий с записью"""
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(
            text="❌ Отменить запись",
            callback_data=f"cancel_appointment:{appointment_id}"
        ))
        return keyboard.as_markup()
    
    @staticmethod
    def admin_menu() -> InlineKeyboardMarkup:
        """Админ меню"""
        keyboard = InlineKeyboardBuilder()
        keyboard.row(
            InlineKeyboardButton(text="📅 Управление днями", callback_data="admin_days"),
            InlineKeyboardButton(text="⏰ Управление слотами", callback_data="admin_slots")
        )
        keyboard.row(
            InlineKeyboardButton(text="📋 Просмотр записей", callback_data="admin_view"),
            InlineKeyboardButton(text="❌ Отменить запись", callback_data="admin_cancel")
        )
        keyboard.row(
            InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")
        )
        return keyboard.as_markup()
    
    @staticmethod
    def slot_management(slots: List[dict]) -> InlineKeyboardMarkup:
        """Управление временными слотами"""
        keyboard = InlineKeyboardBuilder()
        
        for slot in slots:
            status = "✅" if slot['is_active'] else "❌"
            keyboard.row(InlineKeyboardButton(
                text=f"{status} {slot['time']}",
                callback_data=f"toggle_slot:{slot['time']}"
            ))
        
        keyboard.row(
            InlineKeyboardButton(text="➕ Добавить слот", callback_data="add_slot"),
            InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")
        )
        
        return keyboard.as_markup()
    
    @staticmethod
    def back_button() -> InlineKeyboardMarkup:
        """Кнопка назад"""
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(
            text="🔙 Назад",
            callback_data="back"
        ))
        return keyboard.as_markup()
    
    @staticmethod
    def confirmation_keyboard() -> InlineKeyboardMarkup:
        """Клавиатура подтверждения"""
        keyboard = InlineKeyboardBuilder()
        keyboard.row(
            InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm"),
            InlineKeyboardButton(text="❌ Отменить", callback_data="cancel")
        )
        return keyboard.as_markup()