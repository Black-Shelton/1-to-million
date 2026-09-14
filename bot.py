import asyncio
import random
import sqlite3

from telethon import TelegramClient, events, errors


# ==================================================
# НАСТРОЙКИ
# ==================================================

API_ID = 30686053
API_HASH = "e564c17caee89b1b70f89ad5a43eebcf"

# ID НОВОЙ ГРУППЫ
CHAT_ID = -1004350659392

# ID владельца
OWNER_ID = 5679778859

# Счётчик
END_NUMBER = 1_000_000

# Задержка между сообщениями
MIN_DELAY = 2.0
MAX_DELAY = 3.0

# SQLite
DATABASE = "counter.db"

# Файл сессии Telethon
SESSION_NAME = "counter_session"


# ==================================================
# DATABASE
# ==================================================

db = sqlite3.connect(
    DATABASE,
    check_same_thread=False
)

db.execute("""
CREATE TABLE IF NOT EXISTS counter (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    last_sent INTEGER NOT NULL
)
""")

db.execute("""
INSERT OR IGNORE INTO counter (id, last_sent)
VALUES (1, 0)
""")

db.commit()


def get_last_number():
    cursor = db.execute(
        "SELECT last_sent FROM counter WHERE id = 1"
    )

    row = cursor.fetchone()

    if row:
        return row[0]

    return 0


def save_last_number(number):
    db.execute(
        "UPDATE counter SET last_sent = ? WHERE id = 1",
        (number,)
    )

    db.commit()


# ==================================================
# TELETHON
# ==================================================

client = TelegramClient(
    SESSION_NAME,
    API_ID,
    API_HASH
)

counting = False
counter_task = None


# ==================================================
# ПРОВЕРКА ГРУППЫ
# ==================================================

async def get_target_chat():

    print("🔎 Ищу группу...")

    try:

        chat = await client.get_entity(CHAT_ID)

        print()
        print("✅ Группа найдена!")
        print(f"📌 Название: {getattr(chat, 'title', 'Без названия')}")
        print(f"🆔 ID: {chat.id}")
        print()

        return chat

    except Exception as e:

        print()
        print("❌ Не удалось найти группу.")
        print()
        print("Ошибка:")
        print(type(e).__name__, e)
        print()

        print(
            "Проверь, что аккаунт Telethon "
            "вступил в эту группу."
        )

        return None


# ==================================================
# СЧЁТЧИК
# ==================================================

async def counter_loop(chat):

    global counting

    number = get_last_number() + 1

    if number > END_NUMBER:

        print()
        print("🎉 Счётчик уже достиг 1 000 000!")

        counting = False
        return

    print()
    print("========================================")
    print("🚀 СЧЁТЧИК ЗАПУЩЕН")
    print("========================================")
    print(f"📊 Последнее сохранённое: {get_last_number()}")
    print(f"➡️ Начинаем с: {number}")
    print(f"🏁 Цель: {END_NUMBER}")
    print("⏱ Задержка: 2–3 секунды")
    print("========================================")
    print()

    counting = True

    while counting and number <= END_NUMBER:

        try:

            # ------------------------------------------
            # ОТПРАВКА
            # ------------------------------------------

            await client.send_message(
                chat,
                str(number)
            )

            # ------------------------------------------
            # СОХРАНЕНИЕ В SQLITE
            # ------------------------------------------

            save_last_number(number)

            print(
                f"✅ Отправлено: {number}"
            )

            number += 1

            # ------------------------------------------
            # ПРОВЕРКА ОКОНЧАНИЯ
            # ------------------------------------------

            if number > END_NUMBER:

                print()
                print("========================================")
                print("🎉 ГОТОВО!")
                print("🎉 ДОСТИГНУТО 1 000 000")
                print("========================================")

                counting = False
                break

            # ------------------------------------------
            # КД 2–3 СЕКУНДЫ
            # ------------------------------------------

            delay = random.uniform(
                MIN_DELAY,
                MAX_DELAY
            )

            print(
                f"⏳ Следующее сообщение "
                f"через {delay:.2f} сек."
            )

            await asyncio.sleep(delay)

        # ------------------------------------------
        # FLOOD WAIT
        # ------------------------------------------

        except errors.FloodWaitError as e:

            print()
            print("⚠️ TELEGRAM FLOOD WAIT")
            print(
                f"⏳ Telegram попросил "
                f"подождать {e.seconds} сек."
            )
            print("⏸ Счётчик временно остановлен.")
            print()

            await asyncio.sleep(e.seconds)

            print("▶ Продолжаем...")

        # ------------------------------------------
        # НЕТ ПРАВА ПИСАТЬ
        # ------------------------------------------

        except errors.ChatWriteForbiddenError:

            print()
            print("❌ В этой группе нельзя отправлять сообщения.")
            print("🛑 Счётчик остановлен.")

            counting = False

        # ------------------------------------------
        # БАН
        # ------------------------------------------

        except errors.UserBannedInChannelError:

            print()
            print("❌ Этот аккаунт заблокирован в группе.")
            print("🛑 Счётчик остановлен.")

            counting = False

        # ------------------------------------------
        # НУЖНЫ ПРАВА
        # ------------------------------------------

        except errors.ChatAdminRequiredError:

            print()
            print("❌ Для этого действия нужны права администратора.")
            print("🛑 Счётчик остановлен.")

            counting = False

        # ------------------------------------------
        # ДРУГАЯ ОШИБКА
        # ------------------------------------------

        except Exception as e:

            print()
            print("❌ Неожиданная ошибка:")
            print(
                f"{type(e).__name__}: {e}"
            )
            print()

            print("⏳ Повтор через 5 секунд...")

            await asyncio.sleep(5)


# ==================================================
# /startcount
# ==================================================

@client.on(
    events.NewMessage(
        pattern=r"^/startcount$"
    )
)
async def start_count(event):

    global counting
    global counter_task

    if event.sender_id != OWNER_ID:
        return

    if counting:

        await event.reply(
            "⚠️ Счётчик уже работает."
        )

        return

    chat = await get_target_chat()

    if chat is None:

        await event.reply(
            "❌ Не удалось найти группу.\n"
            "Проверь, что аккаунт состоит в ней."
        )

        return

    counting = True

    counter_task = asyncio.create_task(
        counter_loop(chat)
    )

    await event.reply(
        "🚀 Счётчик запущен!\n\n"
        f"📊 Последнее: {get_last_number()}\n"
        f"➡️ Следующее: {get_last_number() + 1}\n"
        f"🏁 Цель: {END_NUMBER}\n"
        "⏱ КД: 2–3 сек."
    )


# ==================================================
# /stopcount
# ==================================================

@client.on(
    events.NewMessage(
        pattern=r"^/stopcount$"
    )
)
async def stop_count(event):

    global counting

    if event.sender_id != OWNER_ID:
        return

    if not counting:

        await event.reply(
            "ℹ️ Счётчик сейчас остановлен."
        )

        return

    counting = False

    await event.reply(
        "🛑 Счётчик остановлен.\n\n"
        f"📊 Последнее сохранённое число: "
        f"{get_last_number()}"
    )


# ==================================================
# /status
# ==================================================

@client.on(
    events.NewMessage(
        pattern=r"^/status$"
    )
)
async def status(event):

    if event.sender_id != OWNER_ID:
        return

    last_number = get_last_number()

    if counting:
        state = "🟢 Работает"
    else:
        state = "🔴 Остановлен"

    await event.reply(
        "📊 СТАТУС СЧЁТЧИКА\n\n"
        f"Состояние: {state}\n"
        f"Последнее: {last_number}\n"
        f"Следующее: {last_number + 1}\n"
        f"Цель: {END_NUMBER}\n"
        "⏱ КД: 2–3 секунды"
    )


# ==================================================
# /resetcount
# ==================================================

@client.on(
    events.NewMessage(
        pattern=r"^/resetcount$"
    )
)
async def reset_count(event):

    if event.sender_id != OWNER_ID:
        return

    if counting:

        await event.reply(
            "❌ Сначала останови счётчик:\n"
            "/stopcount"
        )

        return

    save_last_number(0)

    await event.reply(
        "♻️ Счётчик сброшен.\n\n"
        "➡️ Следующее число: 1"
    )


# ==================================================
# MAIN
# ==================================================

async def main():

    print()
    print("========================================")
    print("🤖 TELEGRAM COUNTER")
    print("========================================")
    print("🔌 Подключение к Telegram...")
    print()

    await client.start()

    # ------------------------------------------
    # ДАННЫЕ АККАУНТА
    # ------------------------------------------

    me = await client.get_me()

    print(
        f"👤 Имя: {me.first_name or 'Без имени'}"
    )

    print(
        f"🆔 ID аккаунта: {me.id}"
    )

    print()

    # ------------------------------------------
    # ПРОВЕРКА OWNER ID
    # ------------------------------------------

    if me.id != OWNER_ID:

        print("❌ ОШИБКА АККАУНТА!")
        print()
        print(
            f"Текущий ID: {me.id}"
        )

        print(
            f"Нужный ID: {OWNER_ID}"
        )

        print()
        print(
            "Авторизуй Telethon под нужным "
            "Telegram-аккаунтом."
        )

        await client.disconnect()

        return

    print("✅ Аккаунт подтверждён.")
    print()

    # ------------------------------------------
    # ПОЛУЧЕНИЕ ГРУППЫ
    # ------------------------------------------

    chat = await get_target_chat()

    if chat is None:

        print()
        print("❌ Запуск невозможен.")
        print(
            "Вступи аккаунтом в группу "
            "и попробуй снова."
        )

        await client.disconnect()

        return

    # ------------------------------------------
    # ИНФОРМАЦИЯ
    # ------------------------------------------

    last_number = get_last_number()

    print()
    print("========================================")
    print("📊 СЧЁТЧИК")
    print("========================================")
    print(f"Последнее число: {last_number}")
    print(f"Следующее число: {last_number + 1}")
    print(f"Цель: {END_NUMBER}")
    print("КД: 2–3 секунды")
    print("========================================")
    print()

    print("Команды:")
    print("/startcount")
    print("/stopcount")
    print("/status")
    print("/resetcount")
    print()

    print("✅ Бот готов.")
    print()

    await client.run_until_disconnected()


# ==================================================
# ЗАПУСК
# ==================================================

try:

    asyncio.run(main())

except KeyboardInterrupt:

    print()
    print("🛑 Программа остановлена.")

finally:

    db.close()