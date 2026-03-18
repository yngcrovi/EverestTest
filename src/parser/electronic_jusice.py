from playwright.async_api import Page
import asyncio
import time
from datetime import datetime
from db.service import BankruptcyDocsDataService

class ElectronicJusiceParser:
    def __init__(self, page: Page):
        self.page = page

    async def process_bankruptcy_docs_parallel(self, bankruptcy_data: list[dict], max_concurrent=4) -> list[dict]:
        """
        Параллельная обработка документов банкротства в нескольких вкладках
        
        Args:
            bankruptcy_data: список данных о банкротстве
            max_concurrent: максимальное количество одновременных вкладок
        """
        
        all_results = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_one_case(case_item, index):
            """Обработка одного дела в отдельной вкладке"""
            
            # Создаем новую вкладку
            page = await self.page.context.new_page()
            
            try:
                # Устанавливаем таймаут
                page.set_default_timeout(30000)
                
                # 1. Переходим на главную страницу kad.arbitr.ru
                await page.goto('https://kad.arbitr.ru', wait_until='domcontentloaded')
                
                # 2. Вводим номер дела
                input_field = page.locator('div#sug-cases').locator('input[type="text"]')
                if await input_field.count():
                    await input_field.fill(case_item['case_num'])
                
                # 3. Нажимаем кнопку поиска
                button = page.locator('div#b-form-submit').locator('button[type="submit"]')
                if await button.count():
                    await button.click()
                
                # Ждем результатов поиска
                await asyncio.sleep(2)
                
                # 4. Получаем ссылку на дело
                a = page.locator('table#b-cases').locator('tbody').locator('td.num').locator('a')
                link = None
                if await a.count():
                    link = await a.get_attribute('href')
                
                if not link:
                    print(f'⚠️ Пропущено: {case_item["case_num"]} - ссылка не найдена')
                    return None
                
                # 5. Переходим по ссылке
                await page.goto(link, wait_until='domcontentloaded')
                await page.wait_for_timeout(2000)
                
                # 6. Парсим данные
                button = page.locator('div.js-case-chrono-button--ed')
                if not await button.count():
                    print(f'⚠️ Пропущено: {case_item["case_num"]} - кнопка не найдена')
                    return None
                    
                await button.click()
                await asyncio.sleep(2)
                
                li = await page.locator('div#chrono_ed_content').locator('ul').locator('li').all()
                if len(li) == 0:
                    print(f'⚠️ Пропущено: {case_item["case_num"]} - элементы не найдены')
                    return None
                
                # Получаем дату
                dt = await li[0].locator('p.b-case-chrono-ed-item-date').text_content()
                
                # Получаем название документа (только прямой текст без span)
                link_element = li[0].locator('a').first
                docs_name = await link_element.evaluate('''(element) => {
                    let text = '';
                    for (let node of element.childNodes) {
                        if (node.nodeType === 3 && node.textContent.trim()) {
                            text += node.textContent;
                        }
                    }
                    return text.trim();
                }''')
                
                result = {
                    'case_num_id': case_item['id'],
                    'link': link,
                    'docs_name': docs_name.strip() if docs_name else '',
                    'last_dt': datetime.strptime(dt, '%d.%m.%Y').date()
                }
                
                print(f'✅ Выполнено: {case_item["case_num"]} ({index + 1}/{len(bankruptcy_data)})')
                return result
                
            except Exception as e:
                print(f'❌ Ошибка при обработке {case_item["case_num"]}: {str(e)[:50]}')
                return None
            finally:
                await page.close()
        
        async def run_with_semaphore(case, idx):
            async with semaphore:
                return await process_one_case(case, idx)
        
        print(f"🚀 Запускаем параллельную обработку {len(bankruptcy_data)} дел с {max_concurrent} вкладками...")
        
        start_time = time.time()
        
        # Создаем все задачи
        tasks = [run_with_semaphore(case, i) for i, case in enumerate(bankruptcy_data)]
        
        # Собираем результаты по мере выполнения
        for completed in asyncio.as_completed(tasks):
            result = await completed
            if result:
                all_results.append(result)
            
            # Показываем прогресс каждые 5 элементов
            if len(all_results) % 5 == 0:
                elapsed = time.time() - start_time
                print(f'📊 Прогресс: {len(all_results)}/{len(bankruptcy_data)} за {elapsed:.1f}с')
        
        elapsed = time.time() - start_time
        print(f"\n📊 Итог за {elapsed:.1f}с:")
        print(f"  ✅ Успешно: {len(all_results)}/{len(bankruptcy_data)}")
        print(f"  ⚠️ Пропущено: {len(bankruptcy_data) - len(all_results)}")
        
        # Сохраняем в БД
        if all_results:
            print(f'🔄 Записываем {len(all_results)} записей...')
            await BankruptcyDocsDataService().insert_data(all_results)
            print('✅ Данные успешно сохранены')
        
        return all_results