import asyncio
import random
import sqlite3

from telethon import TelegramClient, events, errors


# ==============================
# НАСТРОЙКИ
# ==============================

API_ID = 30686053
API_HASH = "e564c17caee89b1b70f89ad5a43eebcf"

CHAT_ID = -1004350659392
OWNER_ID = 5679778859

END_NUMBER = 1_000_000

MIN_DELAY = 2
MAX_DELAY = 3

DATABASE = "counter.db"
SESSION_NAME = "counter_session"


# ==============================
# SQLITE
# ==============================

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
    row = db.execute(
        "SELECT last_sent FROM counter WHERE id = 1"
    ).fetchone()

    return row[0] if row else 0


def save_last_number(number):
    db.execute(
        "UPDATE counter SET last_sent = ? WHERE id = 1",
        (number,)
    )
    db.commit()


# ==============================
# TELEGRAM
# ==============================

client = TelegramClient(
    SESSION_NAME,
    API_ID,
    API_HASH
)

counting = False
counter_task = None
target_chat = None


# ==============================
# ПОИСК ГРУППЫ
# ==============================

async def prepare_chat():
    global target_chat

    try:
        target_chat = await client.get_entity(CHAT_ID)

        print("✅ Группа найдена!")
        print("Название:", getattr(target_chat, "title", "Без названия"))
        print("ID:", target_chat.id)

        return True

    except Exception as e:
        print("❌ Не удалось найти группу:")
        print(type(e).__name__, e)
        print()
        print("Убедись, что аккаунт состоит в этой группе.")

        return False


# ==============================
# СЧЁТЧИК
# ==============================

async def counter_loop():

    global counting

    number = get_last_number() + 1

    print()
    print("🚀 СЧЁТЧИК ЗАПУЩЕН")
    print("Начало:", number)
    print("Конец:", END_NUMBER)
    print("КД: 2–3 секунды")
    print()

    while counting and number <= END_NUMBER:

        try:

            await client.send_message(
                target_chat,
                str(number)
            )

            save_last_number(number)

            print("✅ Отправлено:", number)

            number += 1

            if number > END_NUMBER:

                print()
                print("🎉 ДОСТИГНУТО 1 000 000!")

                counting = False
                break

            delay = random.uniform(
                MIN_DELAY,
                MAX_DELAY
            )

            await asyncio.sleep(delay)

        except errors.FloodWaitError as e:

            print(
                f"⚠️ Telegram попросил подождать "
                f"{e.seconds} секунд."
            )

            await asyncio.sleep(e.seconds)

        except errors.ChatWriteForbiddenError:

            print("❌ Нельзя писать в эту группу.")
            counting = False

        except errors.UserBannedInChannelError:

            print("❌ Аккаунт заблокирован в группе.")
            counting = False

        except Exception as e:

            print("❌ Ошибка:", type(e).__name__, e)

            await asyncio.sleep(5)


# ==============================
# /startcount
# ==============================

@client.on(events.NewMessage(pattern=r"^/startcount$"))
async def start_count(event):

    global counting
    global counter_task

    if event.sender_id != OWNER_ID:
        return

    if counting:
        await event.reply("⚠️ Счётчик уже работает.")
        return

    if target_chat is None:
        await event.reply("❌ Группа не найдена.")
        return

    counting = True

    counter_task = asyncio.create_task(
        counter_loop()
    )

    await event.reply(
        "🚀 Счётчик запущен!\n\n"
        f"Последнее: {get_last_number()}\n"
        f"Следующее: {get_last_number() + 1}\n"
        f"Цель: {END_NUMBER}\n"
        "КД: 2–3 сек."
    )


# ==============================
# /stopcount
# ==============================

@client.on(events.NewMessage(pattern=r"^/stopcount$"))
async def stop_count(event):

    global counting

    if event.sender_id != OWNER_ID:
        return

    if not counting:
        await event.reply("ℹ️ Счётчик уже остановлен.")
        return

    counting = False

    await event.reply(
        "🛑 Счётчик остановлен.\n\n"
        f"Последнее число: {get_last_number()}"
    )


# ==============================
# /status
# ==============================

@client.on(events.NewMessage(pattern=r"^/status$"))
async def status(event):

    if event.sender_id != OWNER_ID:
        return

    state = "🟢 Работает" if counting else "🔴 Остановлен"

    last = get_last_number()

    await event.reply(
        "📊 СТАТУС\n\n"
        f"Состояние: {state}\n"
        f"Последнее: {last}\n"
        f"Следующее: {last + 1}\n"
        f"Цель: {END_NUMBER}"
    )


# ==============================
# /resetcount
# ==============================

@client.on(events.NewMessage(pattern=r"^/resetcount$"))
async def reset_count(event):

    if event.sender_id != OWNER_ID:
        return

    if counting:
        await event.reply(
            "❌ Сначала используй /stopcount"
        )
        return

    save_last_number(0)

    await event.reply(
        "♻️ Счётчик сброшен.\n"
        "Следующее число: 1"
    )


# ==============================
# ЗАПУСК
# ==============================

async def main():

    print("================================")
    print("🤖 TELEGRAM COUNTER")
    print("================================")

    await client.start()

    me = await client.get_me()

    print("👤 Аккаунт:", me.first_name)
    print("🆔 ID:", me.id)

    if me.id != OWNER_ID:

        print()
        print("❌ Неправильный аккаунт!")
        print("Текущий ID:", me.id)
        print("Нужный ID:", OWNER_ID)

        await client.disconnect()
        return

    print("✅ Аккаунт подтверждён.")

    if not await prepare_chat():

        await client.disconnect()
        return

    print()
    print("💾 Последнее число:", get_last_number())
    print("➡️ Следующее:", get_last_number() + 1)
    print()
    print("Команды:")
    print("/startcount")
    print("/stopcount")
    print("/status")
    print("/resetcount")
    print()
    print("✅ Готово.")

    await client.run_until_disconnected()


# ==============================
# START
# ==============================

try:
    asyncio.run(main())

except KeyboardInterrupt:
    print("🛑 Остановлено.")

finally:
    db.close()
