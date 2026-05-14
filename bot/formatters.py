from datetime import datetime, timezone, timedelta

LOCAL_TZ = timezone(timedelta(hours=9)) # Часовой пояс UTC+9

def format_due_date(iso_string: str) -> str:
    """Парсинг даты и добавление дня недели."""
    if not iso_string:
        return None
    try:
        clean_iso = iso_string.split('.')[0]
        dt = datetime.fromisoformat(clean_iso)
        dt = dt.replace(tzinfo=timezone.utc)
        dt_local = dt.astimezone(LOCAL_TZ)
        
        # Список дней недели для перевода на русский
        days = [
            'Понедельник', 'Вторник', 'Среда', 
            'Четверг', 'Пятница', 'Суббота', 'Воскресенье'
        ]
        day_name = days[dt_local.weekday()]
        
        date_str = dt_local.strftime('%Y.%m.%d')
        return f"🗓 Дата: <i>{date_str}</i> ({day_name})"
    except Exception as e:
        print(f"Ошибка парсинга даты: {e}")
        return f"🗓 Дата: {iso_string[:10]}"

def format_task_message(status: str, title: str, formatted_due: str, notes: str, owner: str = None) -> str:
    """Форматирует сообщение о задаче."""
    prefix = f"[{owner}] " if owner else ""
    msg = f"<b>{prefix}{status}:</b>\n    <i>{title}</i>"
    if formatted_due: 
        msg += f"\n{formatted_due}"
    if notes: 
        msg += f"\n📝 <i>Заметка:</i> {notes}"
    return msg

def format_week_tasks(items, start_of_week: datetime, end_of_week: datetime) -> str:
    """Форматирует список задач на неделю с группировкой по дням."""
    tasks_by_day = {i: [] for i in range(7)}
    
    # Распределяем задачи по дням недели
    for task in items:
        title = task.get('title', 'Без названия')
        if task.get('status') == 'completed':
            formatted_title = f"✅ <s>{title}</s>"
        else:
            formatted_title = f"🔸 {title}"
            
        due_date_raw = task.get('due')
        if not due_date_raw:
            continue
            
        clean_iso = due_date_raw.split('.')[0]
        dt = datetime.fromisoformat(clean_iso).replace(tzinfo=timezone.utc)
        dt_local = dt.astimezone(LOCAL_TZ)
        
        # Проверяем, что задача попадает в текущую неделю
        if start_of_week.date() <= dt_local.date() <= end_of_week.date():
            tasks_by_day[dt_local.weekday()].append(formatted_title)

    start_str = start_of_week.strftime('%d.%m')
    end_str = end_of_week.strftime('%d.%m')
    lines = [f"🗓 <b>Задачи на неделю ({start_str} - {end_str}):</b>\n"]
    
    days_names = [
        'Понедельник', 'Вторник', 'Среда', 
        'Четверг', 'Пятница', 'Суббота', 'Воскресенье'
    ]
    
    for i in range(7):
        current_day = start_of_week + timedelta(days=i)
        day_date_str = current_day.strftime('%d.%m')
        lines.append(f"<b>{days_names[i]} ({day_date_str})</b>")
        
        day_tasks = tasks_by_day[i]
        if not day_tasks:
            lines.append("💤 Нет задач\n")
        else:
            for task_text in day_tasks:
                lines.append(task_text)
            lines.append("") # Пустая строка после дня
            
    return "\n".join(lines).strip()
