from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
import logging

from config import ADMIN_ID
from database import Database
from keyboards import Keyboards

router = Router()
db = Database()

# Фильтр для проверки админа
async def is_admin(message: Message) -> bool:
    return message.from_user.id == ADMIN_ID

class AdminStates(StatesGroup):
    adding_slot = State()
    removing_slot = State()
    adding_workday = State()
    closing_day = State()
    viewing_date = State()
    cancelling_appointment = State()

@router.message(F.text == "⚙️ Админ панель")
async def admin_panel(message: Message):
    """Открытие админ-панели"""
    if not await is_admin(message):
        await message.answer("❌ У вас нет доступа к админ-панели.")
        return
    
    await message.answer(
        "⚙️ <b>Административная панель</b>\n\nВыберите действие:",
        reply_markup=Keyboards.admin_menu(),
        parse_mode='HTML'
    )

@router.callback_query(F.data == "admin_days")
async def admin_days_menu(callback: CallbackQuery):
    """Меню управления рабочими днями"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен")
        return
    
    text = (
        "📅 <b>Управление рабочими днями</b>\n\n"
        "Доступные команды:\n"
        "• Добавить рабочий день\n"
        "• Закрыть день\n"
        "• Просмотреть статус дня\n\n"
        "Введите дату в формате ГГГГ-ММ-ДД\n"
        "Например: 2024-12-25"
    )
    
    await callback.message.edit_text(text, parse_mode='HTML')
    await AdminStates.adding_workday.set()

@router.message(StateFilter(AdminStates.adding_workday))
async def process_workday(message: Message, state: FSMContext):
    """Обработка добавления рабочего дня"""
    if message.from_user.id != ADMIN_ID:
        await state.clear()
        return
    
    date_str = message.text.strip()
    
    try:
        # Проверяем формат даты
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Проверяем, что дата не в прошлом
        if date_obj < datetime.now().date():
            await message.answer("❌ Нельзя настроить день в прошлом. Введите другую дату:")
            return
        
        # Получаем информацию о дне
        workday_info = db.get_workday_info(date_str)
        
        if workday_info:
            status = "рабочий" if workday_info['is_working'] else "нерабочий"
            note = f"\nПримечание: {workday_info['note']}" if workday_info['note'] else ""
            await message.answer(
                f"ℹ️ Информация о дне {date_str}:\n"
                f"Статус: {status}{note}\n\n"
                f"Хотите изменить статус? (да/нет)"
            )
            await state.update_data(date=date_str)
        else:
            await message.answer(
                f"День {date_str} не настроен. Сделать его рабочим? (да/нет)"
            )
            await state.update_data(date=date_str)
            
    except ValueError:
        await message.answer("❌ Неверный формат даты. Используйте ГГГГ-ММ-ДД:")

@router.callback_query(F.data == "admin_slots")
async def admin_slots_menu(callback: CallbackQuery):
    """Меню управления временными слотами"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен")
        return
    
    slots = db.get_all_time_slots()
    await callback.message.edit_text(
        "⏰ <b>Управление временными слотами</b>\n\n"
        "✅ - слот активен\n"
        "❌ - слот отключен\n\n"
        "Нажмите на слот, чтобы изменить его статус:",
        reply_markup=Keyboards.slot_management(slots),
        parse_mode='HTML'
    )

@router.callback_query(F.data.startswith("toggle_slot:"))
async def toggle_slot(callback: CallbackQuery):
    """Включение/отключение временного слота"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен")
        return
    
    time = callback.data.split(":")[1]
    
    # Получаем текущий статус слота
    slots = db.get_all_time_slots()
    current_slot = next((s for s in slots if s['time'] == time), None)
    
    if current_slot:
        if current_slot['is_active']:
            db.remove_time_slot(time)
            await callback.answer(f"Слот {time} отключен")
        else:
            db.restore_time_slot(time)
            await callback.answer(f"Слот {time} включен")
    
    # Обновляем клавиатуру
    updated_slots = db.get_all_time_slots()
    await callback.message.edit_reply_markup(
        reply_markup=Keyboards.slot_management(updated_slots)
    )

@router.callback_query(F.data == "add_slot")
async def add_slot_start(callback: CallbackQuery, state: FSMContext):
    """Начало добавления нового слота"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен")
        return
    
    await callback.message.edit_text(
        "⏰ Введите время нового слота в формате ЧЧ:ММ\n"
        "Например: 09:30"
    )
    await state.set_state(AdminStates.adding_slot)

@router.message(StateFilter(AdminStates.adding_slot))
async def add_slot_process(message: Message, state: FSMContext):
    """Обработка добавления нового слота"""
    if message.from_user.id != ADMIN_ID:
        await state.clear()
        return
    
    time_str = message.text.strip()
    
    # Проверяем формат времени
    try:
        datetime.strptime(time_str, '%H:%M')
        
        if db.add_time_slot(time_str):
            await message.answer(f"✅ Слот {time_str} успешно добавлен!")
        else:
            await message.answer("❌ Такой слот уже существует")
            
    except ValueError:
        await message.answer("❌ Неверный формат времени. Используйте ЧЧ:ММ")
        return
    
    await state.clear()

@router.callback_query(F.data == "admin_view")
async def admin_view_menu(callback: CallbackQuery, state: FSMContext):
    """Меню просмотра записей"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен")
        return
    
    await callback.message.edit_text(
        "📋 Введите дату для просмотра записей (ГГГГ-ММ-ДД):"
    )
    await state.set_state(AdminStates.viewing_date)

@router.message(StateFilter(AdminStates.viewing_date))
async def admin_view_appointments(message: Message, state: FSMContext):
    """Просмотр записей на дату"""
    if message.from_user.id != ADMIN_ID:
        await state.clear()
        return
    
    date_str = message.text.strip()
    
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        appointments = db.get_appointments_by_date(date_str)
        
        if not appointments:
            await message.answer(f"📭 На {date_str} записей нет.")
        else:
            text = f"<b>📅 Записи на {date_str}:</b>\n\n"
            
            for apt in appointments:
                text += (
                    f"⏰ {apt['time']}\n"
                    f"👤 {apt['client_name']}\n"
                    f"📞 {apt['phone']}\n"
                    f"🆔 {apt['user_id']}\n"
                    f"─────────────\n"
                )
            
            await message.answer(text, parse_mode='HTML')
            
    except ValueError:
        await message.answer("❌ Неверный формат даты")
    
    await state.clear()

@router.callback_query(F.data == "admin_cancel")
async def admin_cancel_start(callback: CallbackQuery, state: FSMContext):
    """Начало отмены записи админом"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен")
        return
    
    await callback.message.edit_text(
        "❌ Введите ID записи для отмены:"
    )
    await state.set_state(AdminStates.cancelling_appointment)

@router.message(StateFilter(AdminStates.cancelling_appointment))
async def admin_cancel_appointment(message: Message, state: FSMContext):
    """Отмена записи админом"""
    if message.from_user.id != ADMIN_ID:
        await state.clear()
        return
    
    try:
        appointment_id = int(message.text.strip())
        appointment = db.get_appointment_by_id(appointment_id)
        
        if not appointment:
            await message.answer("❌ Запись с таким ID не найдена")
        elif appointment['status'] != 'active':
            await message.answer("❌ Эта запись уже отменена")
        else:
            if db.cancel_appointment(appointment_id):
                # Уведомляем клиента об отмене
                try:
                    await message.bot.send_message(
                        appointment['user_id'],
                        f"❌ Ваша запись на {appointment['date']} в {appointment['time']} была отменена администратором."
                    )
                except:
                    pass
                
                await message.answer(f"✅ Запись #{appointment_id} успешно отменена")
            else:
                await message.answer("❌ Не удалось отменить запись")
                
    except ValueError:
        await message.answer("❌ Введите корректный ID (число)")
    
    await state.clear()

@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    """Возврат в админ-меню"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен")
        return
    
    await callback.message.edit_text(
        "⚙️ <b>Административная панель</b>\n\nВыберите действие:",
        reply_markup=Keyboards.admin_menu(),
        parse_mode='HTML'
    )