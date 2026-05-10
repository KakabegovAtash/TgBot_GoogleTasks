import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from config import TOKEN_PATH

SCOPES = ['https://www.googleapis.com/auth/tasks.readonly']

def get_service():
    """Авторизуется и возвращает сервис для работы с Google Tasks API."""
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_PATH, 'w') as token:
                token.write(creds.to_json())
        else:
            raise Exception(f"Токен недействителен. Файл {TOKEN_PATH} не найден или устарел. "
                            f"Необходимо запустить процесс OAuth авторизации.")
    return build('tasks', 'v1', credentials=creds)
