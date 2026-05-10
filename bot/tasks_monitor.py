import asyncio
from bot.core import bot
from bot.formatters import format_due_date, format_task_message
from database.db_manager import get_task_updated, insert_task, update_task
from config import GROUP_CHAT_ID, POLLING_INTERVAL

def fetch_tasks_sync(service):
    """Синхронный вызов Google Tasks API."""
    results = service.tasks().list(tasklist='@default', showHidden=True).execute()
    return results.get('items', [])

async def sync_tasks(service):
    """Асинхронная задача проверки новых и обновленных задач."""
    try:
        # Выполняем синхронный сетевой запрос в отдельном потоке (executor)
        loop = asyncio.get_running_loop()
        items = await loop.run_in_executor(None, fetch_tasks_sync, service)

        for task in items:
            task_id = task.get('id')
            title = task.get('title', 'Без названия')
            current_update_time = task.get('updated')
            status = task.get('status')
            notes = task.get('notes')
            
            due_date_raw = task.get('due')
            formatted_due = format_due_date(due_date_raw)

            last_updated = get_task_updated(task_id)

            if not last_updated:
                # Новая задача
                msg = format_task_message("🆕 Новая задача", title, formatted_due, notes)
                await bot.send_message(chat_id=GROUP_CHAT_ID, text=msg)
                insert_task(task_id, current_update_time)
            
            elif last_updated != current_update_time:
                # Задача изменена
                status_str = "✅ Завершена" if status == 'completed' else "🔄 Обновлена"
                msg = format_task_message(status_str, title, formatted_due, notes)
                await bot.send_message(chat_id=GROUP_CHAT_ID, text=msg)
                update_task(task_id, current_update_time)

    except Exception as e:
        print(f"Ошибка синхронизации: {e}")

async def monitor_loop(service):
    """Бесконечный цикл проверки задач."""
    print("Мониторинг запущен с отслеживанием дат...")
    while True:
        await sync_tasks(service)
        await asyncio.sleep(POLLING_INTERVAL)
