from playwright.async_api import async_playwright
import json
import asyncio
import time
from datetime import datetime
from log.log import log_print
from env import env
print = log_print 

class AsyncPersistentBrowserManager:
    def __init__(self, url, cookie_file='cookies.json', headless=False):  # По умолчанию с дисплеем
        self.url = url
        self.cookie_file = cookie_file
        self.headless = headless  # False = с дисплеем, True = без дисплея
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.last_refresh = time.time()
        self.refresh_interval = 45 * 60  # 45 минут
        self.running = True
        
    async def start(self):
        """Запускает браузер и держит его открытым (асинхронно)"""
        mode = "БЕЗ ДИСПЛЕЯ (headless)" if self.headless else "С ДИСПЛЕЕМ"
        print(f"🚀 Запуск постоянного браузера ({mode})...")
        
        self.playwright = await async_playwright().start()
        
        # Базовые аргументы для всех режимов
        launch_args = [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-blink-features=AutomationControlled',
        ]
        
        # Добавляем специфичные аргументы в зависимости от режима
        if self.headless:
            # Аргументы для headless-режима (без дисплея)
            launch_args.extend([
                '--disable-gpu',
                '--disable-software-rasterizer',
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-extensions',
                '--disable-setuid-sandbox',
                '--disable-webgl',
                '--disable-features=VizDisplayCompositor',
                '--disable-features=UseOzonePlatform',
            ])
        else:
            # Аргументы для режима с дисплеем
            launch_args.extend([
                '--disable-gpu',  # Для WSL
                '--disable-software-rasterizer',
            ])
        
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=launch_args
        )
        
        # Создаем контекст
        self.context = await self.browser.new_context(
            user_agent=env.USER_AGENT,
            viewport={'width': 1920, 'height': 1080}
        )
        
        # Загружаем сохраненные куки
        await self.load_cookies()
        
        self.page = await self.context.new_page()
        
        # Устанавливаем таймауты
        self.page.set_default_navigation_timeout(60000)
        self.page.set_default_timeout(30000)
        
        # Первоначальная загрузка
        await self.refresh_page()
        
        return self.page
    
    async def load_cookies(self):
        """Загружает куки из файла (асинхронно)"""
        try:
            def read_cookies():
                with open(self.cookie_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            cookies = await asyncio.to_thread(read_cookies)
            
            playwright_cookies = []
            for cookie in cookies:
                pcookie = {
                    'name': cookie['name'],
                    'value': cookie['value'],
                    'domain': cookie['domain'],
                    'path': cookie.get('path', '/'),
                    'secure': cookie.get('secure', False),
                    'httpOnly': cookie.get('httpOnly', False),
                }
                if 'expirationDate' in cookie:
                    pcookie['expires'] = cookie['expirationDate']
                playwright_cookies.append(pcookie)
            
            await self.context.add_cookies(playwright_cookies)
            print(f"✅ Загружено {len(playwright_cookies)} кук")
        except FileNotFoundError:
            print("⚠️ Файл кук не найден")
        except Exception as e:
            print(f"⚠️ Ошибка загрузки кук: {e}")
    
    async def save_cookies(self):
        """Сохраняет текущие куки в файл (асинхронно)"""
        cookies = await self.context.cookies()
        
        edit_cookies = []
        for cookie in cookies:
            ecookie = {
                'name': cookie['name'],
                'value': cookie['value'],
                'domain': cookie['domain'],
                'path': cookie.get('path', '/'),
                'secure': cookie.get('secure', False),
                'httpOnly': cookie.get('httpOnly', False),
                'sameSite': cookie.get('sameSite', 'unspecified'),
            }
            if 'expires' in cookie:
                ecookie['expirationDate'] = cookie['expires']
            edit_cookies.append(ecookie)
        
        def write_cookies():
            with open(self.cookie_file, 'w', encoding='utf-8') as f:
                json.dump(edit_cookies, f, indent=2, ensure_ascii=False)
        
        await asyncio.to_thread(write_cookies)
        print(f"💾 Сохранено {len(edit_cookies)} кук")
    
    async def refresh_page(self):
        """Обновляет страницу, сохраняя сессию (асинхронно)"""
        print(f"\n🔄 [{datetime.now().strftime('%H:%M:%S')}] Обновление страницы...")
        
        try:
            await self.page.goto(self.url, wait_until='networkidle', timeout=60000)
            await asyncio.sleep(3)

            title = await self.page.title()
            content = await self.page.content()
            
            if "403" in title or "forbidden" in content.lower():
                print("❌ Получен 403! Возможно, нужна ручная проверка")
                await asyncio.to_thread(input, "👆 Пройдите проверку в браузере, затем нажмите Enter...")
                await self.save_cookies()
            else:
                print("✅ Страница успешно загружена")
                await self.save_cookies()
                self.last_refresh = time.time()
                
        except Exception as e:
            print(f"❌ Ошибка при обновлении: {e}")
    
    async def keep_alive(self):
        """Держит браузер открытым и периодически обновляет страницу (асинхронно)"""
        print(f"\n🔄 Запущен режим постоянного обновления")
        print(f"⏱️  Интервал обновления: 45 минут")
        print(f"🖥️  Режим: {'Без дисплея' if self.headless else 'С дисплеем'}")
        print("❌ Нажмите Ctrl+C для выхода\n")
        
        try:
            while self.running:
                current_time = time.time()
                
                if current_time - self.last_refresh > self.refresh_interval:
                    await self.refresh_page()
                
                await asyncio.sleep(60)
                
        except asyncio.CancelledError:
            print("\n👋 Завершение работы...")
        finally:
            await self.save_cookies()
            await self.close()
    
    async def close(self):
        """Закрывает браузер (асинхронно)"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    def stop(self):
        """Останавливает цикл keep_alive"""
        self.running = False

    async def go_to(self, url):
        await self.page.goto(url, wait_until='networkidle')