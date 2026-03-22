import sqlite3
import datetime
from typing import List, Dict, Optional, Tuple
from config import DATABASE_PATH, DEFAULT_TIME_SLOTS, DEFAULT_WORKDAYS

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DATABASE_PATH)
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        """Создание всех необходимых таблиц"""
        
        # Таблица пользователей
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                phone TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица записей
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                client_name TEXT,
                phone TEXT,
                date TEXT,
                time TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reminder_sent BOOLEAN DEFAULT 0,
                UNIQUE(date, time)
            )
        ''')
        
        # Таблица временных слотов
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS time_slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time TEXT UNIQUE,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # Таблица рабочих дней
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS workdays (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE,
                is_working BOOLEAN DEFAULT 1,
                note TEXT
            )
        ''')
        
        # Заполняем временные слоты по умолчанию
        self.cursor.execute("SELECT COUNT(*) FROM time_slots")
        if self.cursor.fetchone()[0] == 0:
            for time in DEFAULT_TIME_SLOTS:
                self.cursor.execute(
                    "INSERT OR IGNORE INTO time_slots (time) VALUES (?)",
                    (time,)
                )
        
        self.conn.commit()
    
    # ========== Методы для работы с пользователями ==========
    
    def add_user(self, user_id: int, username: str = None, 
                 first_name: str = None, last_name: str = None):
        """Добавление или обновление пользователя"""
        self.cursor.execute('''
            INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name))
        self.conn.commit()
    
    def update_user_phone(self, user_id: int, phone: str):
        """Обновление телефона пользователя"""
        self.cursor.execute(
            "UPDATE users SET phone = ? WHERE user_id = ?",
            (phone, user_id)
        )
        self.conn.commit()
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Получение информации о пользователе"""
        self.cursor.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = self.cursor.fetchone()
        if row:
            return {
                'user_id': row[0],
                'username': row[1],
                'first_name': row[2],
                'last_name': row[3],
                'phone': row[4],
                'created_at': row[5]
            }
        return None
    
    # ========== Методы для работы с записями ==========
    
    def create_appointment(self, user_id: int, client_name: str, 
                          phone: str, date: str, time: str) -> bool:
        """Создание новой записи"""
        try:
            # Проверяем, нет ли уже записи у пользователя на эту дату
            self.cursor.execute('''
                SELECT id FROM appointments 
                WHERE user_id = ? AND date = ? AND status = 'active'
            ''', (user_id, date))
            
            if self.cursor.fetchone():
                return False
            
            # Проверяем, свободен ли слот
            self.cursor.execute('''
                SELECT id FROM appointments 
                WHERE date = ? AND time = ? AND status = 'active'
            ''', (date, time))
            
            if self.cursor.fetchone():
                return False
            
            # Создаем запись
            self.cursor.execute('''
                INSERT INTO appointments (user_id, client_name, phone, date, time)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, client_name, phone, date, time))
            
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def cancel_appointment(self, appointment_id: int) -> bool:
        """Отмена записи"""
        self.cursor.execute('''
            UPDATE appointments 
            SET status = 'cancelled' 
            WHERE id = ? AND status = 'active'
        ''', (appointment_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def get_user_appointments(self, user_id: int) -> List[Dict]:
        """Получение всех активных записей пользователя"""
        self.cursor.execute('''
            SELECT * FROM appointments 
            WHERE user_id = ? AND status = 'active' AND date >= date('now')
            ORDER BY date, time
        ''', (user_id,))
        
        rows = self.cursor.fetchall()
        appointments = []
        for row in rows:
            appointments.append({
                'id': row[0],
                'user_id': row[1],
                'client_name': row[2],
                'phone': row[3],
                'date': row[4],
                'time': row[5],
                'status': row[6],
                'created_at': row[7],
                'reminder_sent': row[8]
            })
        return appointments
    
    def get_appointments_by_date(self, date: str) -> List[Dict]:
        """Получение всех записей на конкретную дату"""
        self.cursor.execute('''
            SELECT a.*, u.username, u.first_name, u.last_name
            FROM appointments a
            LEFT JOIN users u ON a.user_id = u.user_id
            WHERE a.date = ? AND a.status = 'active'
            ORDER BY a.time
        ''', (date,))
        
        rows = self.cursor.fetchall()
        appointments = []
        for row in rows:
            appointments.append({
                'id': row[0],
                'user_id': row[1],
                'client_name': row[2],
                'phone': row[3],
                'date': row[4],
                'time': row[5],
                'status': row[6],
                'created_at': row[7],
                'reminder_sent': row[8],
                'username': row[9],
                'first_name': row[10],
                'last_name': row[11]
            })
        return appointments
    
    def get_appointment_by_id(self, appointment_id: int) -> Optional[Dict]:
        """Получение записи по ID"""
        self.cursor.execute(
            "SELECT * FROM appointments WHERE id = ?",
            (appointment_id,)
        )
        row = self.cursor.fetchone()
        if row:
            return {
                'id': row[0],
                'user_id': row[1],
                'client_name': row[2],
                'phone': row[3],
                'date': row[4],
                'time': row[5],
                'status': row[6],
                'created_at': row[7],
                'reminder_sent': row[8]
            }
        return None
    
    def get_upcoming_appointments(self) -> List[Dict]:
        """Получение всех будущих записей"""
        self.cursor.execute('''
            SELECT * FROM appointments 
            WHERE status = 'active' AND date >= date('now')
            ORDER BY date, time
        ''')
        
        rows = self.cursor.fetchall()
        appointments = []
        for row in rows:
            appointments.append({
                'id': row[0],
                'user_id': row[1],
                'client_name': row[2],
                'phone': row[3],
                'date': row[4],
                'time': row[5],
                'status': row[6],
                'created_at': row[7],
                'reminder_sent': row[8]
            })
        return appointments
    
    def mark_reminder_sent(self, appointment_id: int):
        """Отметить, что напоминание отправлено"""
        self.cursor.execute(
            "UPDATE appointments SET reminder_sent = 1 WHERE id = ?",
            (appointment_id,)
        )
        self.conn.commit()
    
    # ========== Методы для работы со слотами ==========
    
    def get_available_slots(self, date: str) -> List[str]:
        """Получение доступных временных слотов на дату"""
        # Получаем все активные временные слоты
        self.cursor.execute(
            "SELECT time FROM time_slots WHERE is_active = 1 ORDER BY time"
        )
        all_slots = [row[0] for row in self.cursor.fetchall()]
        
        # Получаем занятые слоты
        self.cursor.execute('''
            SELECT time FROM appointments 
            WHERE date = ? AND status = 'active'
        ''', (date,))
        busy_slots = [row[0] for row in self.cursor.fetchall()]
        
        # Проверяем, рабочий ли день
        self.cursor.execute(
            "SELECT is_working FROM workdays WHERE date = ?",
            (date,)
        )
        workday = self.cursor.fetchone()
        
        if workday and not workday[0]:
            return []  # День полностью закрыт
        
        # Возвращаем свободные слоты
        return [slot for slot in all_slots if slot not in busy_slots]
    
    def add_time_slot(self, time: str) -> bool:
        """Добавление временного слота"""
        try:
            self.cursor.execute(
                "INSERT INTO time_slots (time, is_active) VALUES (?, 1)",
                (time,)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def remove_time_slot(self, time: str) -> bool:
        """Удаление временного слота (деактивация)"""
        self.cursor.execute(
            "UPDATE time_slots SET is_active = 0 WHERE time = ?",
            (time,)
        )
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def restore_time_slot(self, time: str) -> bool:
        """Восстановление временного слота"""
        self.cursor.execute(
            "UPDATE time_slots SET is_active = 1 WHERE time = ?",
            (time,)
        )
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def get_all_time_slots(self) -> List[Dict]:
        """Получение всех временных слотов"""
        self.cursor.execute(
            "SELECT * FROM time_slots ORDER BY time"
        )
        rows = self.cursor.fetchall()
        slots = []
        for row in rows:
            slots.append({
                'id': row[0],
                'time': row[1],
                'is_active': bool(row[2])
            })
        return slots
    
    # ========== Методы для работы с рабочими днями ==========
    
    def set_workday(self, date: str, is_working: bool, note: str = None):
        """Установка рабочего дня"""
        self.cursor.execute('''
            INSERT OR REPLACE INTO workdays (date, is_working, note)
            VALUES (?, ?, ?)
        ''', (date, is_working, note))
        self.conn.commit()
    
    def is_workday(self, date: str) -> bool:
        """Проверка, является ли день рабочим"""
        self.cursor.execute(
            "SELECT is_working FROM workdays WHERE date = ?",
            (date,)
        )
        result = self.cursor.fetchone()
        if result:
            return bool(result[0])
        
        # Если день не указан в таблице, проверяем по умолчанию (пн-пт)
        dt = datetime.datetime.strptime(date, '%Y-%m-%d').date()
        return dt.weekday() in DEFAULT_WORKDAYS
    
    def get_workday_info(self, date: str) -> Optional[Dict]:
        """Получение информации о рабочем дне"""
        self.cursor.execute(
            "SELECT * FROM workdays WHERE date = ?",
            (date,)
        )
        row = self.cursor.fetchone()
        if row:
            return {
                'id': row[0],
                'date': row[1],
                'is_working': bool(row[2]),
                'note': row[3]
            }
        return None
    
    def close(self):
        """Закрытие соединения с БД"""
        if self.conn:
            self.conn.close()
            