import aiosqlite
from config import DB_PATH

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                last_updated TEXT
            )
        ''')
        await db.commit()

async def get_task_updated(db: aiosqlite.Connection, task_id: str) -> str:
    """Возвращает дату последнего обновления задачи, если она существует."""
    async with db.execute('SELECT last_updated FROM tasks WHERE task_id = ?', (task_id,)) as cursor:
        row = await cursor.fetchone()
        return row[0] if row else None

async def insert_task(db: aiosqlite.Connection, task_id: str, last_updated: str):
    """Добавляет новую задачу в базу."""
    await db.execute('INSERT INTO tasks (task_id, last_updated) VALUES (?, ?)', 
                   (task_id, last_updated))
    await db.commit()

async def update_task(db: aiosqlite.Connection, task_id: str, last_updated: str):
    """Обновляет дату изменения задачи."""
    await db.execute('UPDATE tasks SET last_updated = ? WHERE task_id = ?', 
                   (last_updated, task_id))
    await db.commit()
