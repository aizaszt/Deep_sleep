import os
import pymysql
from dotenv import load_dotenv
from groq import Groq
from pathlib import Path

env_file = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_file)

print(f"✅ База из .env: {os.getenv('DB_NAME')}")

api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key) if api_key else None


def get_db_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 3306)),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        charset='utf8mb4'
    )


def get_tables():
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tables


def get_db_context():
    conn = get_db_connection()
    tables = get_tables()
    db_context = ""
    with conn.cursor() as cursor:
        for table in tables:
            cursor.execute(f"SELECT * FROM {table} LIMIT 5")
            rows = cursor.fetchall()
            cols = [desc[0] for desc in cursor.description]
            db_context += f"\nТаблица {table}:\nКолонки: {cols}\n{rows}\n"
    conn.close()
    return db_context


def chat():
    print("🤖 Подключаюсь к базе данных...")
    try:
        tables = get_tables()
        print(f"✅ Найдены таблицы: {', '.join(tables)}")
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        return

    print("\n💬 Чат готов! Введи 'выход' для выхода.\n")

    while True:
        user_input = input("Ты: ").strip()
        if user_input.lower() in ["выход", "exit"]:
            print("До свидания!")
            break
        if not user_input:
            continue

        print("⏳ Думаю...")
        try:
            db_data = get_db_context()
        except Exception as e:
            print(f"❌ Ошибка БД: {e}")
            continue

        prompt = f"""
Ты — аналитик данных. Анализируй данные и давай конкретные выводы.
Отвечай кратко и по делу — только цифры и факты.
Отвечай на том же языке, на котором задан вопрос.

=== ДАННЫЕ ИЗ БАЗЫ ===
{db_data}
======================

Вопрос: {user_input}

Дай конкретный аналитический ответ с цифрами и выводами.
"""
        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000
            )
            print(f"\n🤖 Бот: {response.choices[0].message.content}\n")
        except Exception as e:
            print(f"❌ Ошибка Groq: {e}\n")


if __name__ == "__main__":
    chat()