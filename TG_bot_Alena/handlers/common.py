from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import datetime
import logging

from config import ADMIN_ID
from database import Database
from keyboards import Keyboards

router = Router()
db = Database()

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    db.add_user(
        user_id, 
        message.from_user.username, 
        message.from_user.first_name, 
        message.from_user.last_name
    )
    
    is_admin = (user_id == ADMIN_ID)
    
    await message.answer(
        f"👋 Добро пожаловать, {message.from_user.first_name}!\n\n"
        f"Я бот для записи к мастеру маникюра. "
        f"С моей помощью вы можете записаться на удобное время.",
        reply_markup=Keyboards.main_menu(is_admin)
    )

@router.message(F.text == "💰 Прайс")
async def show_prices(message: Message):
    """Показ прайс-листа"""
    await message.answer(Keyboards.prices(), parse_mode='HTML')

@router.message(F.text == "📸 Портфолио")
async def show_portfolio(message: Message):
    """Показ портфолио"""
    await message.answer(
        "📸 Серега писю сосал:", 
        reply_markup=Keyboards.portfolio()
    )

@router.message(F.text == "📋 Мои записи")
async def show_my_appointments(message: Message):
    """Показ записей пользователя"""
    appointments = db.get_user_appointments(message.from_user.id)
    
    if not appointments:
        await message.answer("📭 У вас нет активных записей.")
        return
    
    text = "<b>📋 Ваши записи:</b>\n\n"
    for apt in appointments:
        date_obj = datetime.datetime.strptime(apt['date'], '%Y-%m-%d')
        formatted_date = date_obj.strftime('%d.%m.%Y')
        text += f"📅 {formatted_date} в {apt['time']}\n"
        text += f"👤 {apt['client_name']}\n"
        text += f"📞 {apt['phone']}\n\n"
    
    await message.answer(text, parse_mode='HTML')

@router.message(F.text == "❌ Отменить запись")
async def choose_appointment_to_cancel(message: Message, state: FSMContext):
    """Выбор записи для отмены"""
    user_id = message.from_user.id
    appointments = db.get_user_appointments(user_id)
    
    if not appointments:
        await message.answer("📭 У вас нет активных записей для отмены.")
        return
    
    text = "<b>Выберите запись для отмены:</b>\n\n"
    
    for apt in appointments:
        date_obj = datetime.datetime.strptime(apt['date'], '%Y-%m-%d')
        formatted_date = date_obj.strftime('%d.%m.%Y')
        text += f"ID: {apt['id']} - {formatted_date} в {apt['time']}\n"
    
    text += "\n<i>Введите ID записи, которую хотите отменить:</i>"
    
    await message.answer(text, parse_mode='HTML')
    await state.set_state("waiting_for_cancel_id")

@router.message(StateFilter("waiting_for_cancel_id"))
async def process_cancel_appointment(message: Message, state: FSMContext):
    """Обработка отмены записи по ID"""
    try:
        appointment_id = int(message.text.strip())
        appointment = db.get_appointment_by_id(appointment_id)
        
        if not appointment:
            await message.answer("❌ Запись с таким ID не найдена.")
            await state.clear()
            return
        
        if appointment['user_id'] != message.from_user.id:
            await message.answer("❌ Это не ваша запись.")
            await state.clear()
            return
        
        if appointment['status'] != 'active':
            await message.answer("❌ Эта запись уже отменена.")
            await state.clear()
            return
        
        if db.cancel_appointment(appointment_id):
            # Удаляем напоминание из планировщика
            from bot import scheduler
            scheduler.remove_reminder(appointment_id)
            
            date_obj = datetime.datetime.strptime(appointment['date'], '%Y-%m-%d')
            formatted_date = date_obj.strftime('%d.%m.%Y')
            
            await message.answer(
                f"✅ Запись на {formatted_date} в {appointment['time']} успешно отменена!"
            )
        else:
            await message.answer("❌ Не удалось отменить запись. Попробуйте позже.")
        
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректный ID (число).")
    except Exception as e:
        logging.error(f"Ошибка при отмене записи: {e}")
        await message.answer("❌ Произошла ошибка при отмене записи.")
    finally:
        await state.clear()