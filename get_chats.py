import asyncio
from telethon import TelegramClient
import config

async def main():
    # Используем уже созданную сессию 'user_session'
    async with TelegramClient('user_session', config.API_ID, config.API_HASH) as client:
        print("Получаю список твоих чатов и каналов...")
        
        # get_dialogs() заставляет Telethon загрузить кэш чатов
        dialogs = await client.get_dialogs()
        
        print("\n--- ТВОИ КАНАЛЫ И ГРУППЫ ---")
        for dialog in dialogs:
            # Выводим только каналы и группы, чтобы не спамить личными переписками
            if dialog.is_channel or dialog.is_group:
                print(f"ID: {dialog.id} | Название: {dialog.title}")
        print("----------------------------\n")

if __name__ == "__main__":
    asyncio.run(main())