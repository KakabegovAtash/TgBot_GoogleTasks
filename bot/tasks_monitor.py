import asyncio
from datetime import datetime, timedelta, timezone
import aiosqlite
from bot.core import bot
from bot.formatters import format_due_date, format_task_message
from database.db_manager import get_task_updated, insert_task, update_task
from config import GROUP_CHAT_ID, MESSAGE_THREAD_ID, POLLING_INTERVAL, DB_PATH

def fetch_tasks_sync(service):
    """Синхронный вызов Google Tasks API с фильтрацией старых задач и пагинацией."""
    fourteen_days_ago = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat().replace("+00:00", "Z")
    
    items = []
    page_token = None
    
    while True:
        results = service.tasks().list(
            tasklist='@default', 
            showHidden=True, 
            updatedMin=fourteen_days_ago,
            maxResults=100,
            pageToken=page_token
        ).execute()
        
        items.extend(results.get('items', []))
        page_token = results.get('nextPageToken')
        if not page_token:
            break
            
    return items

async def sync_tasks(db: aiosqlite.Connection, service, owner: str, is_first_run: bool):
    """Асинхронная задача проверки новых и обновленных задач."""
    try:
        loop = asyncio.get_running_loop()
        items = await loop.run_in_executor(None, fetch_tasks_sync, service)

        for task in items:
            raw_task_id = task.get('id')
            db_task_id = f"{owner}_{raw_task_id}"
            title = task.get('title', 'Без названия')
            current_update_time = task.get('updated')
            status = task.get('status')
            notes = task.get('notes')
            
            due_date_raw = task.get('due')
            formatted_due = format_due_date(due_date_raw)

            last_updated = await get_task_updated(db, db_task_id)

            if not last_updated:
                # Новая задача
                if not is_first_run:
                    msg = format_task_message("🆕 Новая задача", title, formatted_due, notes, owner)
                    await bot.send_message(chat_id=GROUP_CHAT_ID, message_thread_id=MESSAGE_THREAD_ID, text=msg)
                await insert_task(db, db_task_id, current_update_time)
            
            elif last_updated != current_update_time:
                # Задача изменена
                if not is_first_run:
                    status_str = "✅ Завершена" if status == 'completed' else "🔄 Обновлена"
                    msg = format_task_message(status_str, title, formatted_due, notes, owner)
                    await bot.send_message(chat_id=GROUP_CHAT_ID, message_thread_id=MESSAGE_THREAD_ID, text=msg)
                await update_task(db, db_task_id, current_update_time)
        return True
    except Exception as e:
        error_msg = f"⚠️ Ошибка синхронизации для {owner}: {e}"
        print(error_msg)
        try:
            await bot.send_message(chat_id=GROUP_CHAT_ID, message_thread_id=MESSAGE_THREAD_ID, text=error_msg)
        except Exception:
            pass
        return False

async def monitor_loop(services: dict):
    """Бесконечный цикл проверки задач."""
    print("Мониторинг запущен с отслеживанием дат и тихим стартом...")
    first_run_done = set()
    sync_notified = False
    
    try:
        await bot.send_message(
            chat_id=GROUP_CHAT_ID, 
            message_thread_id=MESSAGE_THREAD_ID, 
            text="🤖 Бот запущен. Выполняю начальную синхронизацию задач..."
        )
    except Exception as e:
        print(f"Ошибка отправки стартового сообщения: {e}")
    
    while True:
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                for owner, service in services.items():
                    is_first = owner not in first_run_done
                    success = await sync_tasks(db, service, owner, is_first)
                    if success and is_first:
                        first_run_done.add(owner)
                        
            if not sync_notified and len(first_run_done) == len(services):
                sync_notified = True
                try:
                    await bot.send_message(
                        chat_id=GROUP_CHAT_ID, 
                        message_thread_id=MESSAGE_THREAD_ID, 
                        text="✅ Бот успешно синхронизировал все задачи! Приятного использования."
                    )
                except Exception as e:
                    print(f"Ошибка отправки сообщения об успехе: {e}")
                    
        except Exception as e:
            print(f"Критическая ошибка мониторинга: {e}")
            
        await asyncio.sleep(POLLING_INTERVAL)
