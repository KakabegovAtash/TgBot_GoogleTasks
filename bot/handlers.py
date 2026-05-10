import asyncio
from datetime import datetime, timedelta, timezone
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from services.google_tasks import get_service
from bot.formatters import format_week_tasks, LOCAL_TZ

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Базовый обработчик команды /start."""
    await message.answer("Бот для мониторинга Google Tasks работает. "
                         "Я буду присылать обновления в настроенный групповой чат.")

def get_week_range():
    now = datetime.now(LOCAL_TZ)
    # 0 = Понедельник, 6 = Воскресенье
    start_of_week = now - timedelta(days=now.weekday())
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_week = start_of_week + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return start_of_week, end_of_week

def fetch_weekly_tasks_sync(service, start_of_week, end_of_week):
    # У Google API dueMax работает как строгое неравенство по дате, 
    # поэтому для включения воскресенья мы передаем dueMax как понедельник следующей недели.
    due_min = start_of_week.date().isoformat() + "T00:00:00.000Z"
    due_max = (end_of_week + timedelta(days=1)).date().isoformat() + "T00:00:00.000Z"
    results = service.tasks().list(
        tasklist='@default', 
        showHidden=True, 
        dueMin=due_min,
        dueMax=due_max
    ).execute()
    return results.get('items', [])

@router.message(Command("week"))
async def cmd_week(message: Message):
    """Обработчик команды /week. Присылает задачи на текущую неделю."""
    try:
        service = get_service()
        start_of_week, end_of_week = get_week_range()
        
        loop = asyncio.get_running_loop()
        items = await loop.run_in_executor(None, fetch_weekly_tasks_sync, service, start_of_week, end_of_week)
        
        response_text = format_week_tasks(items, start_of_week, end_of_week)
        await message.answer(response_text)
    except Exception as e:
        await message.answer(f"Ошибка при получении задач: {e}")

def get_next_week_range():
    start_of_current, _ = get_week_range()
    start_of_next = start_of_current + timedelta(days=7)
    end_of_next = start_of_next + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return start_of_next, end_of_next

@router.message(Command("nextweek"))
async def cmd_nextweek(message: Message):
    """Обработчик команды /nextweek. Присылает задачи на следующую неделю."""
    try:
        service = get_service()
        start_of_week, end_of_week = get_next_week_range()
        
        loop = asyncio.get_running_loop()
        items = await loop.run_in_executor(None, fetch_weekly_tasks_sync, service, start_of_week, end_of_week)
        
        response_text = format_week_tasks(items, start_of_week, end_of_week)
        await message.answer(response_text)
    except Exception as e:
        await message.answer(f"Ошибка при получении задач: {e}")
