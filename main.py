import asyncio
from database.db_manager import init_db
from services.google_tasks import get_service
from bot.core import dp, bot
from bot.handlers import router
from bot.tasks_monitor import monitor_loop
from config import PERSON1_TOKEN_PATH, PERSON2_TOKEN_PATH

async def main():
    # Инициализируем БД
    await init_db()
    
    # Получаем сервисы Google
    person1_service = get_service(PERSON1_TOKEN_PATH)
    person2_service = get_service(PERSON2_TOKEN_PATH)
    services = {
        "Person1": person1_service,
        "Person2": person2_service
    }

    # Подключаем роутеры (обработчики команд)
    dp.include_router(router)
    
    # Запускаем фоновую задачу (мониторинг)
    monitor_task = asyncio.create_task(monitor_loop(services))

    # Запускаем поллинг Telegram-бота
    print("Запуск бота...")
    try:
        await dp.start_polling(bot, services=services)
    finally:
        # Отменяем фоновую задачу, если бот остановлен
        monitor_task.cancel()

if __name__ == '__main__':
    asyncio.run(main())