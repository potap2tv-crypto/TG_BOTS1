from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime
import re
import logging

from database import Database
from keyboards import Keyboards
from app_calendar import AppointmentCalendar  # Исправленный импорт

router = Router()  # Добавлено!
db = Database()
calendar = AppointmentCalendar(db)

class AppointmentStates(StatesGroup):
    choosing_date = State()
    choosing_time = State()
    entering_name = State()
    entering_phone = State()
    confirming = State()

@router.message(F.text == "📅 Записаться")
async def start_appointment(message: Message, state: FSMContext):
    """Начало процесса записи"""
    await message.answer(
        "🗓 Выберите дату для записи:",
        reply_markup=await calendar.get_calendar()
    )
    await state.set_state(AppointmentStates.choosing_date)

@router.callback_query(F.data.startswith("calendar:"))
async def process_calendar_navigation(callback: CallbackQuery, state: FSMContext):
    """Обработка навигации по календарю"""
    try:
        parts = callback.data.split(":")
        if len(parts) == 3:
            _, year, month = parts
            await callback.message.edit_text(
                "🗓 Выберите дату для записи:",
                reply_markup=await calendar.get_calendar(int(year), int(month))
            )
        else:
            await callback.answer("Ошибка навигации")
    except Exception as e:
        logging.error(f"Ошибка в навигации календаря: {e}")
        await callback.answer("Произошла ошибка")

@router.callback_query(F.data.startswith("date:"))
async def process_date_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора даты"""
    try:
        parts = callback.data.split(":")
        if len(parts) == 2:
            date = parts[1]
            await state.update_data(selected_date=date)
            
            # Получаем доступные слоты
            available_slots = db.get_available_slots(date)
            
            if not available_slots:
                await callback.message.edit_text(
                    f"❌ На {date} нет свободного времени.\n\nВыберите другую дату:",
                    reply_markup=await calendar.get_calendar()
                )
                await state.set_state(AppointmentStates.choosing_date)
                return
            
            await callback.message.edit_text(
                f"📅 Выбрана дата: {date}\n\nВыберите удобное время:",
                reply_markup=await calendar.get_time_slots_keyboard(date)
            )
            await state.set_state(AppointmentStates.choosing_time)
        else:
            await callback.answer("Ошибка выбора даты")
    except Exception as e:
        logging.error(f"Ошибка при выборе даты: {e}")
        await callback.answer("Произошла ошибка")

@router.callback_query(F.data.startswith("time:"))
async def process_time_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора времени"""
    try:
        # Подробное логирование для отладки
        logging.info(f"=== ОТЛАДКА: получен callback с data: {callback.data} ===")
        
        # Разбиваем максимум на 3 части: префикс, дата, время
        parts = callback.data.split(':', 2)
        
        logging.info(f"Разбито на части (maxsplit=2): {parts}")
        
        if len(parts) != 3:
            logging.error(f"Ожидалось 3 части, получено {len(parts)}")
            await callback.answer("Ошибка формата данных", show_alert=True)
            return
        
        prefix, date, time = parts
        
        logging.info(f"Префикс: {prefix}")
        logging.info(f"Дата: {date}")
        logging.info(f"Время: {time}")
        
        if prefix != "time":
            logging.error(f"Неверный префикс: {prefix}")
            await callback.answer("Неверный формат команды", show_alert=True)
            return
        
        # Проверяем формат даты
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError as e:
            logging.error(f"Неверный формат даты {date}: {e}")
            await callback.answer("Неверный формат даты", show_alert=True)
            return
        
        # Проверяем формат времени
        try:
            datetime.strptime(time, '%H:%M')
        except ValueError as e:
            logging.error(f"Неверный формат времени {time}: {e}")
            await callback.answer("Неверный формат времени", show_alert=True)
            return
        
        # Проверяем, что время еще свободно
        available_slots = db.get_available_slots(date)
        logging.info(f"Доступные слоты на {date}: {available_slots}")
        
        if time not in available_slots:
            logging.warning(f"Время {time} уже занято или недоступно")
            await callback.answer("❌ Это время уже занято!", show_alert=True)
            # Обновляем клавиатуру со свободными слотами
            await callback.message.edit_text(
                f"📅 Выбрана дата: {date}\n\nВыберите другое время:",
                reply_markup=await calendar.get_time_slots_keyboard(date)
            )
            return
        
        # Сохраняем данные
        await state.update_data(selected_date=date, selected_time=time)
        logging.info(f"Данные сохранены: дата={date}, время={time}")
        
        # Переходим к вводу имени
        await callback.message.edit_text("✍️ Введите ваше имя:")
        await state.set_state(AppointmentStates.entering_name)
        
    except Exception as e:
        logging.error(f"Ошибка при выборе времени: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при выборе времени", show_alert=True)

@router.callback_query(F.data == "back_to_calendar")
async def back_to_calendar(callback: CallbackQuery, state: FSMContext):
    """Возврат к календарю"""
    await callback.message.edit_text(
        "🗓 Выберите дату для записи:",
        reply_markup=await calendar.get_calendar()
    )
    await state.set_state(AppointmentStates.choosing_date)

@router.callback_query(F.data == "ignore")
async def ignore_callback(callback: CallbackQuery):
    """Игнорирование нажатий на неактивные кнопки"""
    await callback.answer()

@router.message(AppointmentStates.entering_name)
async def process_name(message: Message, state: FSMContext):
    """Обработка ввода имени"""
    name = message.text.strip()
    if len(name) < 2 or len(name) > 50:
        await message.answer("❌ Имя должно содержать от 2 до 50 символов. Попробуйте снова:")
        return
    await state.update_data(client_name=name)
    await message.answer("📞 Введите ваш номер телефона (в формате +7XXXXXXXXXX или 8XXXXXXXXXX):")
    await state.set_state(AppointmentStates.entering_phone)

@router.message(AppointmentStates.entering_phone)
async def process_phone(message: Message, state: FSMContext):
    """Обработка ввода телефона"""
    phone = message.text.strip()
    phone_pattern = r'^(\+7|8)[0-9]{10}$'
    
    if not re.match(phone_pattern, phone):
        await message.answer("❌ Неверный формат телефона. Используйте +7XXXXXXXXXX или 8XXXXXXXXXX:")
        return
    
    await state.update_data(phone=phone)
    data = await state.get_data()
    
    # Проверяем, что все данные есть
    required_fields = ['selected_date', 'selected_time', 'client_name', 'phone']
    if not all(field in data for field in required_fields):
        await message.answer("❌ Ошибка данных. Начните запись заново.")
        await state.clear()
        return
    
    # Форматируем дату для отображения
    date_obj = datetime.strptime(data['selected_date'], '%Y-%m-%d')
    formatted_date = date_obj.strftime('%d.%m.%Y')
    
    confirm_text = (
        f"<b>📝 Проверьте данные:</b>\n\n"
        f"📅 Дата: {formatted_date}\n"
        f"⏰ Время: {data['selected_time']}\n"
        f"👤 Имя: {data['client_name']}\n"
        f"📞 Телефон: {data['phone']}\n\n"
        f"<i>Всё верно?</i>"
    )
    
    await message.answer(
        confirm_text,
        reply_markup=Keyboards.confirmation_keyboard(),
        parse_mode='HTML'
    )
    await state.set_state(AppointmentStates.confirming)

@router.callback_query(F.data == "confirm", AppointmentStates.confirming)
async def confirm_appointment(callback: CallbackQuery, state: FSMContext):
    """Подтверждение записи"""
    try:
        data = await state.get_data()
        
        # Проверяем наличие всех данных
        required_fields = ['selected_date', 'selected_time', 'client_name', 'phone']
        if not all(field in data for field in required_fields):
            await callback.message.edit_text(
                "❌ Ошибка данных. Пожалуйста, начните запись заново."
            )
            await state.clear()
            await callback.answer()
            return
        
        # Проверяем, не занято ли уже время
        available_slots = db.get_available_slots(data['selected_date'])
        if data['selected_time'] not in available_slots:
            await callback.message.edit_text(
                "❌ К сожалению, это время уже занято. Попробуйте выбрать другое время.",
                reply_markup=await calendar.get_calendar()
            )
            await state.clear()
            await callback.answer()
            return
        
        success = db.create_appointment(
            user_id=callback.from_user.id,
            client_name=data['client_name'],
            phone=data['phone'],
            date=data['selected_date'],
            time=data['selected_time']
        )
        
        if success:
            db.update_user_phone(callback.from_user.id, data['phone'])
            
            # Получаем ID созданной записи
            appointments = db.get_appointments_by_date(data['selected_date'])
            new_appointment = next((a for a in appointments if a['time'] == data['selected_time'] and a['user_id'] == callback.from_user.id), None)
            
            date_obj = datetime.strptime(data['selected_date'], '%Y-%m-%d')
            formatted_date = date_obj.strftime('%d.%m.%Y')
            
            await callback.message.edit_text(
                f"✅ <b>Запись подтверждена!</b>\n\n"
                f"📅 Дата: {formatted_date}\n"
                f"⏰ Время: {data['selected_time']}\n"
                f"👤 Имя: {data['client_name']}\n\n"
                f"Ждём вас! 💅",
                parse_mode='HTML'
            )
            
            # Отправляем уведомления
            from config import ADMIN_ID, SCHEDULE_CHANNEL_ID
            
            admin_text = (
                f"<b>📝 Новая запись!</b>\n\n"
                f"👤 Клиент: {data['client_name']}\n"
                f"📞 Телефон: {data['phone']}\n"
                f"📅 Дата: {formatted_date}\n"
                f"⏰ Время: {data['selected_time']}\n"
                f"🆔 ID: {callback.from_user.id}"
            )
            await callback.bot.send_message(ADMIN_ID, admin_text, parse_mode='HTML')
            
            if SCHEDULE_CHANNEL_ID and SCHEDULE_CHANNEL_ID != '@schedule_channel_username':
                try:
                    channel_text = (
                        f"<b>📅 Расписание на {formatted_date}</b>\n\n"
                        f"⏰ {data['selected_time']} - {data['client_name']}"
                    )
                    await callback.bot.send_message(SCHEDULE_CHANNEL_ID, channel_text, parse_mode='HTML')
                except Exception as e:
                    logging.error(f"Ошибка отправки в канал: {e}")
            
            # Планируем напоминание
            if new_appointment:
                from bot import scheduler
                await scheduler.schedule_reminder(
                    new_appointment['id'],
                    callback.from_user.id,
                    data['selected_date'],
                    data['selected_time']
                )
        else:
            await callback.message.edit_text(
                "❌ Не удалось создать запись. Возможно, это время уже занято.",
                reply_markup=await calendar.get_calendar()
            )
        
    except Exception as e:
        logging.error(f"Ошибка при подтверждении записи: {e}", exc_info=True)
        await callback.message.edit_text(
            "❌ Произошла ошибка при создании записи. Попробуйте позже."
        )
    finally:
        await state.clear()
        await callback.answer()

@router.callback_query(F.data == "cancel")
async def cancel_appointment_creation(callback: CallbackQuery, state: FSMContext):
    """Отмена создания записи"""
    await callback.message.edit_text("❌ Запись отменена.")
    await state.clear()
    await callback.answer()