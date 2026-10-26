import aiosqlite
from config import DB_PATH

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                last_updated TEXT,
                status TEXT
            )
        ''')
        # Миграция: если таблица уже существовала без колонки status
        async with db.execute("PRAGMA table_info(tasks)") as cursor:
            columns = [row[1] for row in await cursor.fetchall()]
            if 'status' not in columns:
                await db.execute("ALTER TABLE tasks ADD COLUMN status TEXT")

        await db.commit()

async def get_task(db: aiosqlite.Connection, task_id: str):
    """Возвращает кортеж (last_updated, status) или None."""
    async with db.execute('SELECT last_updated, status FROM tasks WHERE task_id = ?', (task_id,)) as cursor:
        row = await cursor.fetchone()
        return (row[0], row[1]) if row else None

async def get_task_updated(db: aiosqlite.Connection, task_id: str) -> str:
    """Для обратной совместимости: возвращает дату последнего обновления задачи."""
    task = await get_task(db, task_id)
    return task[0] if task else None

async def insert_task(db: aiosqlite.Connection, task_id: str, last_updated: str, status: str = None):
    """Добавляет новую задачу в базу с сохранением статуса."""
    await db.execute(
        'INSERT INTO tasks (task_id, last_updated, status) VALUES (?, ?, ?)', 
        (task_id, last_updated, status)
    )
    await db.commit()

async def update_task(db: aiosqlite.Connection, task_id: str, last_updated: str, status: str = None):
    """Обновляет дату изменения и статус задачи."""
    await db.execute(
        'UPDATE tasks SET last_updated = ?, status = ? WHERE task_id = ?', 
        (last_updated, status, task_id)
    )
    await db.commit()

async def delete_task(db: aiosqlite.Connection, task_id: str):
    """Удаляет задачу из базы (например, при удалении из Google Tasks)."""
    await db.execute('DELETE FROM tasks WHERE task_id = ?', (task_id,))
    await db.commit()

async def cleanup_old_completed_tasks(db: aiosqlite.Connection, days: int = 30) -> int:
    """
    Безопасная очистка: удаляет только задачи со статусом 'completed',
    завершенные более чем `days` дней назад.
    Возвращает количество удаленных записей.
    """
    async with db.execute(
        "DELETE FROM tasks WHERE status = 'completed' AND datetime(last_updated) < datetime('now', '-' || ? || ' days')",
        (days,)
    ) as cursor:
        deleted_count = cursor.rowcount
    await db.commit()
    return deleted_count

