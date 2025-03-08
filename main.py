import datetime
import asyncio
import json
import os

from telethon.errors.rpcerrorlist import PhoneNumberBannedError, PasswordHashInvalidError, UsernameInvalidError
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest
from telethon import TelegramClient, events

from config import MIN_MONTHS_PREMIUM, DEVICE_MODEL, SYSTEM_VERSION, CHANNELS, COUNTRY, AUTO_LEAVE_CHANNELS

with open('accounts.json', 'r') as file:
    data = json.load(file)
    accounts = data['accounts']

async def job_wait(client, date, channels):
    delta = date - datetime.datetime.now()
    await asyncio.sleep(delta.total_seconds())
    await asyncio.sleep(3600)
    try:
        for channel in channels:
            await client(LeaveChannelRequest(channel))
            print(f"Розыгрыш в канале {channel} завершён, вышел из него")
    except Exception as e:
        print(f"Ошибка: {e}")

async def check_last_messages(client, phone):
    for channel in CHANNELS:
        try:
            async for message in client.iter_messages(channel, limit=20):
                if message.media and hasattr(message.media, 'months') and message.media.months >= MIN_MONTHS_PREMIUM:
                    if message.media.countries_iso2 is None or COUNTRY in message.media.countries_iso2:
                        date_str = str(message.media.until_date)[:-9]
                        date = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M")
                        print(f"[с 20 последних соо] Нашёл розыгрыш на {message.media.months} месяца для {phone}")
                        target_channels = message.media.channels
                        for ch in target_channels:
                            await client(JoinChannelRequest(ch))
                            print(f"[с 20 последних соо] Вступил в канал {ch} для {phone}")
                        if AUTO_LEAVE_CHANNELS:
                            await job_wait(client, date, target_channels)
        except Exception as e:
            print(f"Ошибка проверки сообщений в {channel}: {e}")

async def client_worker(account):
    phone = account['phone']
    print(f"Начинаю вход в {phone}")
    client = TelegramClient(
        session=f"tg_{phone}",
        api_id=account['api_id'],
        api_hash=account['api_hash'],
        device_model=DEVICE_MODEL,
        system_version=SYSTEM_VERSION
    )

    @client.on(events.NewMessage(CHANNELS))
    async def general_handler(event):
        try:
            if event.message.media and hasattr(event.message.media, 'months') and event.message.media.months >= MIN_MONTHS_PREMIUM:
                if event.message.media.countries_iso2 is None or COUNTRY in event.message.media.countries_iso2:
                    date_str = str(event.message.media.until_date)[:-9]
                    date = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M")
                    print(f"Нашёл розыгрыш на {event.message.media.months} месяца для {phone}")
                    target_channels = event.message.media.channels
                    for ch in target_channels:
                        await client(JoinChannelRequest(ch))
                        print(f"Вступил в канал {ch} для {phone}")
                    if AUTO_LEAVE_CHANNELS:
                        await job_wait(client, date, target_channels)
        except Exception as e:
            print(f"Ошибка для {phone}: {e}")

    try:
        await client.start(phone=phone)
        print(f"Успешный вход для {phone}")
        await check_last_messages(client, phone)
        await client.run_until_disconnected()
    except PhoneNumberBannedError:
        print(f"Аккаунт {phone} заблокирован")
    except PasswordHashInvalidError:
        print(f"Неверный пароль для {phone}")
    except UsernameInvalidError:
        pass
    except Exception as e:
        print(f"Ошибка для {phone}: {e}")

async def main():
    tasks = [asyncio.create_task(client_worker(account)) for account in accounts]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
