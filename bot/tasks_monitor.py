import asyncio
from datetime import datetime, timedelta, timezone
import aiosqlite
from bot.core import bot
from bot.formatters import format_due_date, format_task_message
from database.db_manager import (
    get_task, 
    insert_task, 
    update_task, 
    delete_task, 
    cleanup_old_completed_tasks
)
from config import GROUP_CHAT_ID, MESSAGE_THREAD_ID, POLLING_INTERVAL, DB_PATH

def fetch_tasks_sync(service, is_first_run: bool = False):
    """
    Синхронный вызов Google Tasks API с пагинацией:
    - При первом старте (is_first_run=True): запрашивает все активные (незавершенные) задачи без ограничения по времени,
      а также недавние задачи за 14 дней, чтобы полностью инициализировать актуальное состояние базы данных.
    - В регулярном мониторинге: запрашивает задачи за последние 7 дней с флагами showHidden=True и showDeleted=True.
    """
    items = []
    seen_ids = set()

    def _fetch(query_params: dict):
        page_token = None
        while True:
            params = dict(query_params)
            params['tasklist'] = '@default'
            params['maxResults'] = 100
            params['pageToken'] = page_token
            results = service.tasks().list(**params).execute()
            
            for task in results.get('items', []):
                t_id = task.get('id')
                if t_id and t_id not in seen_ids:
                    seen_ids.add(t_id)
                    items.append(task)
                    
            page_token = results.get('nextPageToken')
            if not page_token:
                break

    if is_first_run:
        # 1. Загружаем все открытые задачи (независимо от того, когда они были созданы)
        _fetch({'showCompleted': False, 'showHidden': True, 'showDeleted': False})
        
        # 2. Добавляем задачи, измененные за последние 14 дней (включая недавно закрытые)
        fourteen_days_ago = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat().replace("+00:00", "Z")
        _fetch({'showHidden': True, 'showDeleted': False, 'updatedMin': fourteen_days_ago})
    else:
        # Регулярный опрос: изменения за последние 7 дней + удаленные задачи (корзина)
        seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat().replace("+00:00", "Z")
        _fetch({'showHidden': True, 'showDeleted': True, 'updatedMin': seven_days_ago})

    return items

async def fetch_tasks_with_retry(service, is_first_run: bool = False, max_retries: int = 3, retry_delay: float = 3.0):
    """Выполняет вызов Google Tasks API в executor'е с retry при сетевых сбоях и таймаутах."""
    loop = asyncio.get_running_loop()
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            return await loop.run_in_executor(None, fetch_tasks_sync, service, is_first_run)
        except Exception as e:
            last_err = e
            if attempt < max_retries:
                await asyncio.sleep(retry_delay * attempt)
            else:
                raise last_err

async def sync_tasks(db: aiosqlite.Connection, service, owner: str, is_first_run: bool, consecutive_errors: dict):
    """Асинхронная задача проверки новых, обновленных и удаленных задач."""
    try:
        items = await fetch_tasks_with_retry(service, is_first_run=is_first_run)
        consecutive_errors[owner] = 0  # Сбрасываем счетчик ошибок при успешном ответе

        for task in items:
            raw_task_id = task.get('id')
            db_task_id = f"{owner}_{raw_task_id}"
            title = task.get('title', 'Без названия')
            current_update_time = task.get('updated')
            status = task.get('status')
            is_deleted = task.get('deleted', False)
            notes = task.get('notes')

            existing_record = await get_task(db, db_task_id)

            # 1. Задача удалена (помещена в корзину Google Tasks)
            if is_deleted:
                if existing_record:
                    if not is_first_run:
                        msg = format_task_message("🗑️ Задача удалена", title, None, None, owner)
                        await bot.send_message(chat_id=GROUP_CHAT_ID, message_thread_id=MESSAGE_THREAD_ID, text=msg)
                    await delete_task(db, db_task_id)
                continue

            due_date_raw = task.get('due')
            formatted_due = format_due_date(due_date_raw)

            if not existing_record:
                # Задачи нет в локальной БД
                if status == 'completed':
                    # Защита от бага: если задача уже завершена в Google, но не была в нашей БД,
                    # это точно не "Новая задача". Просто молча сохраняем её.
                    await insert_task(db, db_task_id, current_update_time, status)
                else:
                    # Действительно новая открытая задача
                    if not is_first_run:
                        msg = format_task_message("🆕 Новая задача", title, formatted_due, notes, owner)
                        await bot.send_message(chat_id=GROUP_CHAT_ID, message_thread_id=MESSAGE_THREAD_ID, text=msg)
                    await insert_task(db, db_task_id, current_update_time, status)

            else:
                last_updated, old_status = existing_record
                if last_updated != current_update_time or old_status != status:
                    # Задача изменена или сменился статус
                    if not is_first_run:
                        status_str = "✅ Завершена" if status == 'completed' else "🔄 Обновлена"
                        msg = format_task_message(status_str, title, formatted_due, notes, owner)
                        await bot.send_message(chat_id=GROUP_CHAT_ID, message_thread_id=MESSAGE_THREAD_ID, text=msg)
                    await update_task(db, db_task_id, current_update_time, status)

        return True
    except Exception as e:
        consecutive_errors[owner] = consecutive_errors.get(owner, 0) + 1
        print(f"⚠️ Ошибка синхронизации для {owner} (попытка {consecutive_errors[owner]}): {e}")
        
        # Отправляем алерт в чат только при 3+ последовательных сбоях (сеть действительно лежит)
        if consecutive_errors[owner] >= 3:
            error_msg = f"⚠️ Ошибка синхронизации для {owner}: {e}"
            try:
                await bot.send_message(chat_id=GROUP_CHAT_ID, message_thread_id=MESSAGE_THREAD_ID, text=error_msg)
            except Exception:
                pass
        return False

async def monitor_loop(services: dict):
    """Бесконечный цикл проверки задач с автоочисткой БД раз в сутки."""
    print("Мониторинг запущен с отслеживанием дат и тихим стартом...")
    first_run_done = set()
    sync_notified = False
    consecutive_errors = {owner: 0 for owner in services.keys()}
    last_cleanup_date = None

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
            today = datetime.now(timezone.utc).date()
            async with aiosqlite.connect(DB_PATH) as db:
                # Раз в сутки: безопасная автоочистка завершенных задач старше 30 дней
                if last_cleanup_date != today:
                    deleted = await cleanup_old_completed_tasks(db, days=30)
                    if deleted > 0:
                        print(f"🧹 Автоочистка БД: удалено {deleted} устаревших выполненных задач.")
                    last_cleanup_date = today

                for owner, service in services.items():
                    is_first = owner not in first_run_done
                    success = await sync_tasks(db, service, owner, is_first, consecutive_errors)
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

