import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/tasks.readonly']

def get_service(token_path: str):
    """Авторизуется и возвращает сервис для работы с Google Tasks API."""
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
        else:
            raise Exception(f"Токен недействителен. Файл {token_path} не найден или устарел. "
                            f"Необходимо запустить процесс OAuth авторизации.")
    return build('tasks', 'v1', credentials=creds)
