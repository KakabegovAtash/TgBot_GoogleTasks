import asyncio
from database.db_manager import init_db
from services.google_tasks import get_service
from bot.core import dp, bot
from bot.handlers import router
from bot.tasks_monitor import monitor_loop
from config import ATASH_TOKEN_PATH, MOLDIR_TOKEN_PATH

async def main():
    # Инициализируем БД
    init_db()
    
    # Получаем сервисы Google
    atash_service = get_service(ATASH_TOKEN_PATH)
    moldir_service = get_service(MOLDIR_TOKEN_PATH)
    services = {
        "Аташ": atash_service,
        "Молдир": moldir_service
    }

    # Подключаем роутеры (обработчики команд)
    dp.include_router(router)
    
    # Запускаем фоновую задачу (мониторинг)
    monitor_task = asyncio.create_task(monitor_loop(services))

    # Запускаем поллинг Telegram-бота
    print("Запуск бота...")
    try:
        await dp.start_polling(bot)
    finally:
        # Отменяем фоновую задачу, если бот остановлен
        monitor_task.cancel()

if __name__ == '__main__':
    asyncio.run(main())