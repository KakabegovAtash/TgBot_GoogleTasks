import sqlite3
from config import DB_PATH

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            last_updated TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_task_updated(task_id: str) -> str:
    """Возвращает дату последнего обновления задачи, если она существует."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT last_updated FROM tasks WHERE task_id = ?', (task_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def insert_task(task_id: str, last_updated: str):
    """Добавляет новую задачу в базу."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO tasks (task_id, last_updated) VALUES (?, ?)', 
                   (task_id, last_updated))
    conn.commit()
    conn.close()

def update_task(task_id: str, last_updated: str):
    """Обновляет дату изменения задачи."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE tasks SET last_updated = ? WHERE task_id = ?', 
                   (last_updated, task_id))
    conn.commit()
    conn.close()
