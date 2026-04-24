import os
import json
import config

def main():
    print("Генерация локального сайта (Про-версия с исправленными альбомами)...")
    
    json_file = os.path.join(config.SAVE_DIR, 'messages.jsonl')
    html_file = os.path.join(config.SAVE_DIR, 'index.html')
    
    if not os.path.exists(json_file):
        print("Ошибка: Файл messages.jsonl не найден.")
        return

    clean_channel_id = str(config.CHANNEL_TARGET).replace('-100', '').replace('@', '')

    # 1. Просто читаем базу (ОНА УЖЕ В ХРОНОЛОГИЧЕСКОМ ПОРЯДКЕ: от старых к новым)
    raw_messages = []
    with open(json_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                raw_messages.append(json.loads(line))
                
    # УБРАЛИ raw_messages.reverse() ОТСЮДА!

    # 2. Собираем альбомы в правильном порядке
    grouped_messages = []
    months_index = set()
    albums = {} 
    
    for msg in raw_messages:
        month_key = msg['date'][:7] 
        months_index.add(month_key)
        
        msg['media_paths'] = [msg['media_path']] if msg.get('media_path') else []
        if 'media_path' in msg:
            del msg['media_path']

        group_id = msg.get('grouped_id')

        if group_id:
            if group_id in albums:
                # Так как идем по хронологии, просто добавляем новые фото в конец массива
                parent_msg = albums[group_id]
                if msg['media_paths']:
                    parent_msg['media_paths'].extend(msg['media_paths'])
                
                # Текст тоже склеиваем в правильном порядке
                if msg.get('text'):
                    parent_msg['text'] = (parent_msg.get('text', '') + "\n\n" + msg['text']).strip()
            else:
                grouped_messages.append(msg)
                albums[group_id] = msg
        else:
            grouped_messages.append(msg)

    # 3. А ВОТ ТЕПЕРЬ переворачиваем ГОТОВЫЙ список, чтобы новые посты были сверху
    grouped_messages.reverse()

    sorted_months = sorted(list(months_index))
    js_data = json.dumps(grouped_messages, ensure_ascii=False)
    js_months = json.dumps(sorted_months, ensure_ascii=False)

    # --- HTML Шаблон остается без изменений ---
    html_template = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Архив Канала</title>
    <style>
        body {{
            background-color: #e4ecef; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            margin: 0; padding: 0; color: #000; display: flex; height: 100vh; overflow: hidden;
        }}
        .sidebar {{ width: 300px; background: #fff; border-right: 1px solid #d1d9dd; display: flex; flex-direction: column; z-index: 10; }}
        .search-box {{ padding: 15px; border-bottom: 1px solid #eee; }}
        .search-box input {{ width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 20px; outline: none; box-sizing: border-box; transition: border 0.3s; }}
        .search-box input:focus {{ border-color: #2a82b9; }}
        .nav-list {{ flex: 1; overflow-y: auto; padding: 10px 0; }}
        .nav-item {{ padding: 10px 20px; cursor: pointer; color: #333; font-weight: 500; }}
        .nav-item:hover {{ background: #f4f6f9; color: #2a82b9; }}
        
        .chat-area {{ flex: 1; overflow-y: auto; padding: 20px; position: relative; scroll-behavior: smooth; }}
        .chat-container {{ max-width: 680px; margin: 0 auto; display: flex; flex-direction: column; gap: 10px; padding-bottom: 40px; }}
        
        .message {{ 
            background: #ffffff; border-radius: 12px; padding: 12px 16px; 
            box-shadow: 0 1px 2px rgba(0,0,0,0.1); word-wrap: break-word; 
            transition: background-color 0.5s ease;
        }}
        .msg-date {{ color: #8c9fa8; font-size: 12px; margin-bottom: 8px; font-weight: 500; }}
        .msg-text {{ font-size: 15px; line-height: 1.4; white-space: pre-wrap; }}
        
        .msg-text b {{ font-weight: bold; }}
        .msg-text i {{ font-style: italic; }}
        .msg-text s {{ text-decoration: line-through; }}
        .msg-text code {{ background: #f0f0f0; padding: 2px 4px; border-radius: 4px; font-family: monospace; }}
        .msg-text a {{ color: #2a82b9; text-decoration: none; }}
        .msg-text a:hover {{ text-decoration: underline; }}
        .internal-link {{ background: #eef2f5; padding: 2px 6px; border-radius: 6px; font-weight: 500; cursor: pointer; display: inline-block; }}
        
        .media-gallery {{ margin-top: 10px; display: grid; gap: 5px; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); }}
        .media-item img, .media-item video {{ width: 100%; height: auto; border-radius: 8px; max-height: 400px; object-fit: cover; cursor: pointer; }}
        .media-item audio {{ width: 100%; margin-top: 5px; outline: none; }}
        .file-link {{ display: block; padding: 10px; background: #f4f6f9; border-radius: 8px; text-decoration: none; color: #2a82b9; font-weight: 500; }}
        .file-link:hover {{ background: #eef2f5; }}
        
        .poll-box {{ margin-top: 10px; background: #f4f6f9; padding: 12px; border-radius: 8px; border: 1px solid #e1e8ed; }}
        .poll-question {{ font-weight: bold; margin-bottom: 12px; font-size: 15px; }}
        .poll-option {{ margin-bottom: 8px; font-size: 14px; display: flex; justify-content: space-between; background: #fff; padding: 8px; border-radius: 6px; }}
        .poll-total {{ font-size: 12px; color: #8c9fa8; margin-top: 12px; text-align: right; }}

        .back-btn {{
            display: none; position: fixed; bottom: 30px; right: 30px;
            background: #2a82b9; color: #fff; border: none; padding: 12px 24px;
            border-radius: 50px; font-size: 15px; font-weight: 600; cursor: pointer;
            box-shadow: 0 4px 15px rgba(42, 130, 185, 0.4); z-index: 1000;
            transition: transform 0.2s, background 0.2s;
        }}
        .back-btn:hover {{ background: #216a96; transform: translateY(-2px); }}
        
        #noResults {{ display: none; text-align: center; color: #8c9fa8; margin-top: 20px; font-size: 15px; }}
    </style>
</head>
<body>

    <div class="sidebar">
        <div class="search-box"><input type="text" id="searchInput" placeholder="Поиск по тексту, дате, ID..." oninput="filterMessages()"></div>
        <div class="nav-list" id="navList"></div>
    </div>
    <div class="chat-area" id="chatArea">
        <div class="chat-container" id="chat">
            <div id="noResults">По вашему запросу ничего не найдено 🤷‍♂️</div>
        </div>
    </div>

    <button class="back-btn" id="backBtn" onclick="goBack()">⬅ Вернуться</button>

    <script>
        const messages = {js_data};
        const months = {js_months};
        const cleanChannelId = '{clean_channel_id}'; 
        
        const chatContainer = document.getElementById('chat');
        const navList = document.getElementById('navList');
        const chatArea = document.getElementById('chatArea');
        const backBtn = document.getElementById('backBtn');
        const noResults = document.getElementById('noResults');
        
        let jumpHistory = [];

        function updateBackButton() {{
            backBtn.style.display = jumpHistory.length > 0 ? 'block' : 'none';
        }}

        function saveCurrentPosition() {{
            jumpHistory.push(chatArea.scrollTop);
            updateBackButton();
        }}

        function goBack() {{
            if (jumpHistory.length > 0) {{
                const previousScroll = jumpHistory.pop();
                chatArea.scrollTo({{ top: previousScroll, behavior: 'smooth' }});
                updateBackButton();
            }}
        }}

        function createLinkElement(text, url) {{
            const regex = new RegExp(`t\\\\.me/(c/)?${{cleanChannelId}}/(\\\\d+)`);
            const match = url.match(regex);
            if (match) {{
                const targetMsgId = match[2];
                return `<a class="internal-link" onclick="scrollToMessage('${{targetMsgId}}')">🔗 ${{text}}</a>`;
            }}
            return `<a href="${{url}}" target="_blank">${{text}}</a>`;
        }}

        function parseMarkdown(text) {{
            if (!text) return '';
            let html = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
            html = html.replace(/\\*\\*(.+?)\\*\\*/g, '<b>$1</b>');
            html = html.replace(/__(.+?)__/g, '<i>$1</i>');
            html = html.replace(/~~(.+?)~~/g, '<s>$1</s>');
            html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
            html = html.replace(/\\[([^\\]]+)\\]\\((https?:\\/\\/[^\\)]+)\\)/g, function(fullMatch, linkText, url) {{
                return createLinkElement(linkText, url);
            }});
            html = html.replace(/(?<!href=")(https?:\\/\\/[^\\s<]+)/g, function(fullMatch, url) {{
                return createLinkElement(url, url);
            }});
            return html;
        }}

        messages.forEach(msg => {{
            const msgDiv = document.createElement('div');
            msgDiv.className = 'message';
            msgDiv.setAttribute('data-month', msg.date.substring(0, 7)); 
            msgDiv.id = 'msg-' + msg.id; 

            let html = `<div class="msg-date">${{msg.date}} (ID: ${{msg.id}})</div>`;
            if (msg.text) {{ html += `<div class="msg-text">${{parseMarkdown(msg.text)}}</div>`; }}

            if (msg.media_paths && msg.media_paths.length > 0) {{
                html += `<div class="media-gallery">`;
                msg.media_paths.forEach(path => {{
                    if (!path) return;
                    const ext = path.split('.').pop().toLowerCase();
                    const filename = path.split('/').pop().split('\\\\').pop();
                    html += `<div class="media-item">`;
                    if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext)) {{
                        html += `<a href="${{path}}" target="_blank"><img src="${{path}}" loading="lazy" alt="Image"></a>`;
                    }} else if (['mp4', 'mov', 'webm'].includes(ext)) {{
                        html += `<video controls src="${{path}}"></video>`;
                    }} else if (['ogg', 'oga', 'mp3', 'wav', 'm4a'].includes(ext)) {{
                        html += `<audio controls src="${{path}}"></audio>`;
                    }} else {{
                        html += `<a href="${{path}}" target="_blank" class="file-link">📎 Скачать: ${{filename}}</a>`;
                    }}
                    html += `</div>`;
                }});
                html += `</div>`;
            }}

            if (msg.poll) {{
                html += `<div class="poll-box"><div class="poll-question">📊 ${{msg.poll.question}}</div>`;
                msg.poll.options.forEach(opt => {{
                    html += `<div class="poll-option"><span>${{opt.text}}</span><strong>${{opt.voters}} чел.</strong></div>`;
                }});
                html += `<div class="poll-total">Всего проголосовало: ${{msg.poll.total_voters}}</div></div>`;
            }}

            msgDiv.innerHTML = html;
            chatContainer.appendChild(msgDiv);
        }});

        months.forEach(month => {{
            const div = document.createElement('div');
            div.className = 'nav-item';
            div.innerText = month; 
            div.onclick = () => scrollToMonth(month);
            navList.appendChild(div);
        }});

        function filterMessages() {{
            const query = document.getElementById('searchInput').value.toLowerCase().trim();
            const msgs = document.getElementsByClassName('message');
            let foundCount = 0;
            
            if (!query) {{
                for (let m of msgs) m.style.display = 'block';
                noResults.style.display = 'none';
                return;
            }}

            for (let m of msgs) {{
                const fullText = m.textContent.toLowerCase();
                if (fullText.includes(query)) {{
                    m.style.display = 'block';
                    foundCount++;
                }} else {{
                    m.style.display = 'none';
                }}
            }}
            
            noResults.style.display = foundCount === 0 ? 'block' : 'none';
        }}

        function scrollToMonth(monthKey) {{
            const target = document.querySelector(`[data-month="${{monthKey}}"]`);
            if (target) {{
                saveCurrentPosition(); 
                chatArea.scrollTo({{ top: target.offsetTop - 20, behavior: 'smooth' }});
            }}
        }}
        
        function scrollToMessage(msgId) {{
            let target = document.getElementById('msg-' + msgId);
            
            if (!target) {{
                let currentId = parseInt(msgId);
                while(currentId > parseInt(msgId) - 15) {{
                    currentId--;
                    target = document.getElementById('msg-' + currentId);
                    if (target) break;
                }}
            }}
            
            if (target) {{
                saveCurrentPosition(); 
                chatArea.scrollTo({{ top: target.offsetTop - 20, behavior: 'smooth' }});
                target.style.backgroundColor = "#fff3cd";
                setTimeout(() => {{ target.style.backgroundColor = "#ffffff"; }}, 2000);
            }} else {{
                alert("Сообщение ID: " + msgId + " не найдено в скачанной базе.");
            }}
        }}
    </script>
</body>
</html>
"""

    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_template)
        
    print(f"Готово! Сайт обновлен. Открой: {os.path.abspath(html_file)}")

if __name__ == "__main__":
    main()