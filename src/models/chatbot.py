import os
from dotenv import load_dotenv
from groq import Groq
from pathlib import Path
from deep_sleep.src.db_queries import get_data

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent / ".env")
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def chat():
    print("🤖 Загружаю данные из базы...")
    try:
        data = get_data()
        print("✅ Данные загружены!\n")
    except Exception as e:
        print(f"❌ Ошибка БД: {e}")
        return

    messages = [{
        "role": "system",
        "content": (
            "Ты — аналитик данных по исследованию сна (100 000 записей).\n"
            "Отвечай ТОЛЬКО по данным ниже. Не выдумывай.\n"
            "Отвечай кратко с цифрами. Отвечай на языке вопроса.\n\n"
            "Данные покрывают:\n"
            "1. Базовая статистика (сон, возраст, BMI, пол, хронотип)\n"
            "2. Образ жизни (кофеин, алкоголь, экран, снотворное)\n"
            "3. Окружающая среда (сезон, температура, день/выходной)\n"
            "4. Сменная работа vs стресс (физиология, REM, пульс)\n"
            "5. Риск выгорания (burnout_index, профессии, страны)\n\n"
            f"=== ДАННЫЕ ===\n{data}\n=============="
        )
    }]

    print("💬 Чат готов! Введи 'выход' для выхода.\n")
    while True:
        user_input = input("Ты: ").strip()
        if user_input.lower() in ["выход", "exit"]:
            break
        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})
        print("⏳ Думаю...")
        try:
            r = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
                max_tokens=500
            )
            ans = r.choices[0].message.content
            messages.append({"role": "assistant", "content": ans})
            print(f"\n🤖 {ans}\n")
        except Exception as e:
            print(f"❌ {e}\n")
            if "413" in str(e):
                messages = messages[:1] + messages[-2:]
                print("⚠️ История сокращена, попробуй снова.\n")


if __name__ == "__main__":
    chat()



