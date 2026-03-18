from playwright.sync_api import sync_playwright
import json
import time

def convert_cookies_for_playwright(editthiscookie_json):
    """
    Конвертирует куки из формата EditThisCookie в формат Playwright
    """
    playwright_cookies = []
    
    for cookie in editthiscookie_json:
        # Создаем базовую структуру
        new_cookie = {
            'name': cookie['name'],
            'value': cookie['value'],
            'domain': cookie['domain'],
            'path': cookie.get('path', '/'),
            'secure': cookie.get('secure', False),
            'httpOnly': cookie.get('httpOnly', False),
        }
        
        # Добавляем sameSite только если есть и значение корректное
        if 'sameSite' in cookie:
            sameSite = cookie['sameSite'].capitalize()  # Преобразуем в правильный регистр
            if sameSite in ['Strict', 'Lax', 'None']:
                new_cookie['sameSite'] = sameSite
        
        # Добавляем expires если есть
        if 'expirationDate' in cookie:
            new_cookie['expires'] = cookie['expirationDate']
        elif 'expires' in cookie:
            new_cookie['expires'] = cookie['expires']
        
        playwright_cookies.append(new_cookie)
    
    return playwright_cookies

def load_cookies_safe(file_path):
    """
    Безопасно загружает куки из файла
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        raw_cookies = json.load(f)
    
    # Конвертируем в формат Playwright
    return convert_cookies_for_playwright(raw_cookies)

# Основной код
url = "https://fedresurs.ru/"

print("🚀 Запуск Playwright...")

with sync_playwright() as p:
    # Запускаем браузер с правильными аргументами для WSL
    browser = p.chromium.launch(
        headless=False,
        args=[
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-software-rasterizer'
        ]
    )
    
    # Создаем контекст
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        viewport={'width': 1920, 'height': 1080}
    )
    
    # Загружаем и добавляем куки
    try:
        cookies = load_cookies_safe('cookies.json')
        context.add_cookies(cookies)
        print(f"✅ Загружено {len(cookies)} кук")
    except FileNotFoundError:
        print("⚠️ Файл cookies.json не найден, продолжаем без кук")
    except Exception as e:
        print(f"⚠️ Ошибка при загрузке кук: {e}")
    
    # Создаем страницу
    page = context.new_page()
    
    # Увеличиваем таймауты
    page.set_default_navigation_timeout(60000)
    page.set_default_timeout(30000)
    
    print("🌐 Загружаю страницу...")
    
    try:
        # Переходим на сайт
        response = page.goto(url, wait_until='domcontentloaded', timeout=60000)
        
        if response:
            print(f"📊 Статус ответа: {response.status}")
        
        # Ждем появления контента
        page.wait_for_selector('body', timeout=10000)
        time.sleep(3)  # Даем время выполниться JavaScript
        
        # Проверяем результат
        title = page.title()
        print(f"📄 Заголовок страницы: {title}")
        
        # Проверяем, не 403 ли это
        if "403" in title or "forbidden" in title.lower():
            print("❌ Похоже, куки не сработали (получили 403)")
            
            # Делаем скриншот для анализа
            page.screenshot(path='error_403.png')
            print("📸 Скриншот сохранен как error_403.png")
        else:
            print("✅ Успех! Страница загружена")
            
            # Ищем имя игрока
            try:
                player_name = page.locator('h1').first
                if player_name:
                    print(f"🏆 Игрок: {player_name.text_content()}")
            except:
                pass
            
            # Сохраняем HTML для анализа
            html = page.content()
            with open('hltv_page.html', 'w', encoding='utf-8') as f:
                f.write(html)
            print("💾 HTML сохранен в hltv_page.html")
        
    except Exception as e:
        print(f"❌ Ошибка при загрузке: {e}")
    
    print("⏸️ Браузер останется открытым 30 секунд...")
    time.sleep(30)
    browser.close()