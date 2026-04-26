import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
from pathlib import Path

# Поиск файла .env
current_file = Path(__file__).resolve()
env_file = current_file.parent.parent.parent / ".env"

if env_file.exists():
    load_dotenv(dotenv_path=env_file)
    print(f"--- Файл .env загружен из: {env_file} ---")
else:
    load_dotenv()
    print("--- ПРЕДУПРЕЖДЕНИЕ: .env не найден, используем дефолт ---")


def get_db_connection():
    """Создает подключение к MySQL."""
    try:
        host = os.getenv("DB_HOST", "127.0.0.1")
        port = os.getenv("DB_PORT", 3306)
        user = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")
        database = os.getenv("DB_NAME")

        port = int(port) if port else 3306

        print(f"Попытка подключения к {host}:{port}...")

        connection = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            connect_timeout=10,  # Минимум два пробела перед комментарием
            use_pure=True
        )

        if connection.is_connected():
            print("Успешно: Подключение к MySQL установлено.")
            return connection

    except Error as e:
        print(f"Ошибка MySQL: {e}")
    except Exception as e:
        print(f"Критическая ошибка: {e}")

    return None


if __name__ == "__main__":
    conn = get_db_connection()
    if conn:
        conn.close()
        print("Соединение закрыто.")
