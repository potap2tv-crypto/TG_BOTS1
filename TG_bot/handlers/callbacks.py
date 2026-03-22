from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import datetime
import logging

from database import Database
from config import ADMIN_ID
from keyboards import Keyboards

router = Router()
db = Database()

@router.callback_query(F.data == "back")
async def back_callback(callback: CallbackQuery, state: FSMContext):
    """Универсальный обработчик кнопки назад"""
    await state.clear()
    await callback.message.delete()
    await callback.message.answer(
        "Главное меню:",
        reply_markup=Keyboards.main_menu(callback.from_user.id == ADMIN_ID)
    )

@router.callback_query(F.data.startswith("cancel_appointment:"))
async def cancel_appointment_callback(callback: CallbackQuery):
    """Отмена записи через inline-кнопку"""
    try:
        appointment_id = int(callback.data.split(":")[1])
        appointment = db.get_appointment_by_id(appointment_id)
        
        if not appointment:
            await callback.answer("❌ Запись не найдена", show_alert=True)
            return
        
        if appointment['user_id'] != callback.from_user.id:
            await callback.answer("❌ Это не ваша запись", show_alert=True)
            return
        
        if appointment['status'] != 'active':
            await callback.answer("❌ Запись уже отменена", show_alert=True)
            return
        
        if db.cancel_appointment(appointment_id):
            # Удаляем напоминание из планировщика
            from bot import scheduler
            scheduler.remove_reminder(appointment_id)
            
            # Форматируем дату для сообщения
            date_obj = datetime.strptime(appointment['date'], '%Y-%m-%d')
            formatted_date = date_obj.strftime('%d.%m.%Y')
            
            await callback.message.edit_text(
                f"✅ Запись на {formatted_date} в {appointment['time']} отменена!"
            )
            await callback.answer("Запись успешно отменена")
        else:
            await callback.answer("❌ Не удалось отменить запись", show_alert=True)
    except Exception as e:
        logging.error(f"Ошибка при отмене записи: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)