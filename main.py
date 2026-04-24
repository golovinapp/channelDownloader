import os
import json
import asyncio
from telethon import TelegramClient
import config

async def main():
    print("=== Инициализация ===")
    os.makedirs(config.MEDIA_DIR, exist_ok=True)
    
    JSON_FILE = os.path.join(config.SAVE_DIR, 'messages.jsonl')
    TEMP_FILE = os.path.join(config.SAVE_DIR, 'messages_temp.jsonl')
    
    # 1. Уборка мусора: удаляем файлы 0 байт, оставшиеся от неудачных скачиваний
    deleted_count = 0
    for filename in os.listdir(config.MEDIA_DIR):
        filepath = os.path.join(config.MEDIA_DIR, filename)
        if os.path.isfile(filepath) and os.path.getsize(filepath) == 0:
            os.remove(filepath)
            deleted_count += 1
    if deleted_count > 0:
        print(f"Удалено битых файлов (0 байт) из папки media: {deleted_count}")

    # 2. Чтение истории: загружаем в память то, что уже было скачано
    saved_messages = {}
    if os.path.exists(JSON_FILE):
        print(f"Найдена существующая база {JSON_FILE}. Загрузка...")
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    saved_messages[data['id']] = data
        print(f"Постов в локальной базе: {len(saved_messages)}")
    else:
        print("База не найдена. Будет выполнена полная загрузка с нуля.")

    print("\n=== Авторизация Telegram ===")
    async with TelegramClient('user_session', config.API_ID, config.API_HASH) as client:
        try:
            channel = await client.get_entity(config.CHANNEL_TARGET)
            print(f"Канал подключен: {channel.title}")
        except Exception as e:
            print(f"Критическая ошибка доступа к каналу: {e}")
            return

        print("\n=== Старт синхронизации ===")
        # Открываем временный файл для безопасной записи
        with open(TEMP_FILE, 'w', encoding='utf-8') as f:
            
            # reverse=True означает чтение от старых к новым
            async for message in client.iter_messages(channel, reverse=True):
                
                is_new_message = message.id not in saved_messages
                
                # Формируем или достаем базовые данные поста
                msg_data = saved_messages.get(message.id, {
                    "id": message.id,
                    "date": message.date.strftime('%Y-%m-%d %H:%M:%S'),
                    "text": message.text if message.text else "",
                    "media_path": None,
                    "poll": None
                })
                
                needs_download = False
                custom_path = None

                # --- ОБРАБОТКА ОПРОСОВ ---
                if message.poll and not msg_data.get("poll"):
                    try:
                        poll_obj = message.poll.poll
                        results_obj = message.poll.results
                        
                        poll_data = {
                            "question": poll_obj.question,
                            "total_voters": getattr(results_obj, 'total_voters', 0),
                            "options": []
                        }
                        
                        # Сопоставляем голоса с вариантами ответов (они хранятся хитро, через байтовые ключи)
                        votes_map = {}
                        if getattr(results_obj, 'results', None):
                            for res in results_obj.results:
                                votes_map[res.option] = getattr(res, 'voters', 0)
                                
                        for answer in poll_obj.answers:
                            poll_data["options"].append({
                                "text": answer.text,
                                "voters": votes_map.get(answer.option, 0)
                            })
                            
                        msg_data["poll"] = poll_data
                        print(f"[{message.id}] -> Сохранен опрос: '{poll_data['question']}'")
                    except Exception as e:
                        print(f"[{message.id}] Ошибка извлечения опроса: {e}")
                # -------------------------

                # 3. Обработка медиа
                if message.media:
                    # Безопасная генерация имени
                    safe_name = "media.unknown"
                    if getattr(message, 'file', None):
                        if message.file.name:
                            safe_name = message.file.name
                        else:
                            safe_name = f"media{message.file.ext or '.jpg'}"
                    
                    custom_file_name = f"{message.id}_{safe_name}"
                    custom_path = os.path.join(config.MEDIA_DIR, custom_file_name)
                    
                    # Проверка целостности файла
                    if os.path.exists(custom_path) and os.path.getsize(custom_path) > 0:
                        msg_data["media_path"] = os.path.relpath(custom_path, config.SAVE_DIR)
                    else:
                        needs_download = True
                
                # 4. Скачивание (если файла нет или он битый)
                if needs_download:
                    print(f"[{message.id}] Скачивание медиа...")
                    try:
                        fresh_msg = await client.get_messages(channel, ids=message.id)
                        path = await client.download_media(fresh_msg, file=custom_path)
                        
                        if path:
                            if os.path.exists(path) and os.path.getsize(path) == 0:
                                os.remove(path)
                                print(f" -> Ошибка сервера: получен пустой файл.")
                                msg_data["media_path"] = None
                            else:
                                print(f" -> Сохранено: {path}")
                                msg_data["media_path"] = os.path.relpath(path, config.SAVE_DIR)
                        else:
                            # ВОТ ТУТ МЫ ЛОВИМ ПУСТОТУ
                            print(f" -> Пропущено: нет физического файла (вероятно превью ссылки или опрос).")
                            msg_data["media_path"] = None
                            
                    except Exception as e:
                        print(f"[{message.id}] Ошибка скачивания: {e}")
                        msg_data["media_path"] = None
                
                # 5. Запись строки в JSONL
                f.write(json.dumps(msg_data, ensure_ascii=False) + '\n')
                f.flush()
                
                # 6. Умная задержка
                # Ждем только если мы делали запрос к API (качали медиа или это новый текстовый пост)
                if needs_download or is_new_message:
                    await asyncio.sleep(config.DELAY)

    # 7. Финализация: заменяем старую базу на новую, только если всё прошло без фатальных сбоев
    os.replace(TEMP_FILE, JSON_FILE)
    print(f"\n=== Готово! ===")
    print(f"Актуальная база сохранена в: {JSON_FILE}")

if __name__ == "__main__":
    asyncio.run(main())