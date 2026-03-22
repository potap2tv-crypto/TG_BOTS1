import os
from dotenv import load_dotenv

load_dotenv()

# Токен бота
BOT_TOKEN = os.getenv('BOT_TOKEN')

# ID администратора
ADMIN_ID = int(os.getenv('ADMIN_ID', '123456789'))

# ID канала для расписания (опционально)
SCHEDULE_CHANNEL_ID = os.getenv('SCHEDULE_CHANNEL_ID', '@schedule_channel_username')

# Настройки базы данных
DATABASE_PATH = 'manicure_bot.db'

# Временные слоты по умолчанию (можно менять через админку)
DEFAULT_TIME_SLOTS = [
    '10:00', '11:00', '12:00', '13:00', '14:00',
    '15:00', '16:00', '17:00', '18:00', '19:00'
]

# Рабочие дни по умолчанию (пн-пт)
DEFAULT_WORKDAYS = [0, 1, 2, 3, 4]  # 0 - понедельник, 4 - пятница