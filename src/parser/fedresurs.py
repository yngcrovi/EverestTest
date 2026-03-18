from playwright.async_api import Page
import asyncio
from datetime import datetime
from db.service import PeopleService, BankruptcyInfoService
from log.log import log_print
from env import env
import re
print = log_print 

class FedResursParser:

    def __init__(self, url: str, page: Page, browser):
        self.url = url
        self.page = page
        self.browser = browser
        self.user_agent = env.USER_AGENT

    async def go_to_entities(self):
        """Асинхронная функция для парсинга данных"""
        try:
            # Переходим для поиска ИНН
            button = self.page.locator('button.el-button')
            await button.click()
        except Exception as e:
            print(f"❌ Ошибка парсинга: {e}")
            return False
        
    async def parse_individuals(self) -> dict:
        """Асинхронная функция для парсинга физических лиц"""
        try:
            # Ищем табы
            li = await self.page.locator('div.tab_mb').locator('ul.tab__nav').locator('li.tab__li').all()

            if not li:
                print('❌ Табы не найдены')
                return False
            
            # Ищем вкладку "Физические лица"
            found = False
            for i, l in enumerate(li):
                text_button = await l.locator('span.tab__name').text_content()
                
                if text_button and text_button.lower().strip() == 'физические лица':
                    await l.click()
                    found = True
                    print('✅ Найдена вкладка "Физические лица"')
                    break

            if not found:
                print('❌ Вкладка "Физические лица" не найдена')
                return False
            
            # Ждем загрузки блока
            await self.page.wait_for_selector('el-tab.selected', timeout=10000)
            
            # Ищем блок с данными о физ лицах
            selected_type_div = self.page.locator('el-tab.selected')
            
            # Внутри блока находим кнопку для подгрузки данных
            load_more = selected_type_div.locator('div.more_btn')

            # Загружаем больше данных
            print("🔄 Загрузка дополнительных данных...")
            for i in range(env.QUANTITY_INN-1):
                await load_more.click()
                await asyncio.sleep(2)
                print(f"✅  Загружена порция {i+1}/{env.QUANTITY_INN-1}")

            # Получаем все карточки людей
            div_individuals = await selected_type_div.locator('div.u-card-result__wrapper').all()
            print(f'✅ Найдено {len(div_individuals)} человек')

            people_data = []

            for div in div_individuals:
                # Извлекаем ФИО и ссылку
                div_fio = div.locator('div.u-card-result__name-wrapper')
                
                # Получаем href
                href_element = div_fio.locator('a').first
                href = await href_element.get_attribute('href')
                
                # Получаем ФИО
                fio_element = div_fio.locator('span').first
                fio = await fio_element.text_content()
                
                # Ищем ИНН
                div_docs = await div.locator('div.u-card-result__item-id').all()

                inn = None
                
                for docs in div_docs:
                    spans = await docs.locator('span').all()
                    if len(spans) >= 2:
                        name = await spans[0].text_content()
                        num_text = await spans[1].text_content()
                        
                        if name and name.lower().strip() == 'инн' and num_text:
                            try:
                                inn = int(num_text)
                            except:
                                inn = num_text
                            break
                if inn and fio:
                    people_data.append({
                        'path': href,
                        'fio': fio.strip() if fio else None,
                        'id': inn
                    })

                
                # Выводим прогресс
                if len(people_data) % 10 == 0:
                    print(f"✅ Обработано {len(people_data)}/{len(div_individuals)}")

            print('🔄 Сохраняем данные в таблицу people...')

            await PeopleService().insert_data(people_data)

            print('✅ Данные успешно сохранены в таблицу people')

            return people_data

        except Exception as e:
            print(f'❌ Ошибка в parse_individuals(): {e}')
            import traceback
            traceback.print_exc()
            return False

    async def get_data_about_bankruptcy_parallel(self, data: list[dict], max_concurrent=4) -> dict:
        """
        Оптимизированный параллельный парсинг с повторными попытками
        """
        
        all_results = []
        semaphore = asyncio.Semaphore(max_concurrent)
        date_pattern = re.compile(r'(\d{2})\.(\d{2})\.(\d{4})')
        
        # Счетчики для статистики
        stats = {
            'success': 0,
            'no_data': 0,
            'timeout': 0,
            'error': 0
        }
        
        async def process_person(person_data, index):
            """Обработка одного человека с повторными попытками"""
            
            # Максимальное количество попыток
            max_attempts = 2
            
            for attempt in range(max_attempts):
                page = None
                try:
                    page = await self.page.context.new_page()
                    
                    # Адаптивный таймаут: 25с -> 35с -> 45с
                    timeout = 25000 + (attempt * 10000)
                    page.set_default_timeout(timeout)
                    
                    # Стратегия ожидания: сначала networkidle, потом domcontentloaded
                    wait_strategy = 'networkidle' if attempt == 0 else 'domcontentloaded'
                    
                    await page.goto(
                        f"{self.url + person_data['path']}", 
                        wait_until=wait_strategy,
                        timeout=timeout
                    )
                    
                    # Небольшая задержка для загрузки динамики
                    await page.wait_for_timeout(2000)
                    
                    # Поиск элементов
                    case_num = None
                    last_dt = None

                    div_bankrupt = page.locator('div[page-item-name="bankrupt"]')
                    
                    # Проверяем наличие блока
                    if await div_bankrupt.count() == 0:
                        if attempt == max_attempts - 1:
                            stats['no_data'] += 1
                        continue
                    
                    # Поиск номера дела
                    case_properties = div_bankrupt.locator('div.info-item-name_properties')
                    if await case_properties.count():
                        case_links = await case_properties.locator('a').all()
                        if case_links:
                            case_num = await case_links[0].text_content()

                    # Поиск даты
                    value_elements = await div_bankrupt.locator('div.info-item-value').all()
                    if value_elements:
                        for value_elem in value_elements:
                            wrapper = value_elem.locator('entity-card-bankruptcy-publication-wrapper')
                            if await wrapper.count():
                                pub_links = wrapper.locator('div.pub-link').locator('a')
                                if await pub_links.count():
                                    info = await pub_links.first.text_content()
                                    match = date_pattern.search(info or '')
                                    if match:
                                        day, month, year = match.groups()
                                        last_dt = f"{year}-{month}-{day}"
                                        break
                    
                    if case_num and last_dt:
                        date_obj = datetime.strptime(last_dt, "%Y-%m-%d").date()
                        stats['success'] += 1
                        print(f'✅ {index + 1}/{len(data)}: {person_data["fio"]}')
                        return {
                            'inn': person_data['id'],
                            'case_num': case_num.strip(),
                            'last_bankruptcy_dt': date_obj
                        }
                    else:
                        # Если данные не найдены на первой попытке, пробуем еще раз
                        if attempt == max_attempts - 1:
                            stats['no_data'] += 1
                            print(f'⚠️ Нет данных: {person_data["fio"]}')
                        
                except Exception as e:
                    error_type = type(e).__name__
                    if 'Timeout' in error_type:
                        if attempt == max_attempts - 1:
                            stats['timeout'] += 1
                            print(f'⏱️ Таймаут: {person_data["fio"]}')
                    else:
                        if attempt == max_attempts - 1:
                            stats['error'] += 1
                            print(f'❌ Ошибка: {person_data["fio"]}')
                    
                    # Пауза перед повторной попыткой
                    await asyncio.sleep(2)
                finally:
                    if page:
                        await page.close()
                
                # Если не удалось, пробуем еще раз
                await asyncio.sleep(1)
            
            return None
        
        async def run_with_semaphore(person, idx):
            async with semaphore:
                return await process_person(person, idx)
        
        print(f"🚀 Запускаем параллельный парсинг с {max_concurrent} вкладками...")
        
        # Создаем задачи
        tasks = [run_with_semaphore(person, i) for i, person in enumerate(data)]
        
        # Собираем результаты
        start_time = datetime.now()
        for completed in asyncio.as_completed(tasks):
            result = await completed
            if result:
                all_results.append(result)
            
            # Показываем прогресс каждые 5 элементов
            if len(all_results) % 5 == 0:
                elapsed = (datetime.now() - start_time).seconds
                print(f'📊 Прогресс: {len(all_results)}/{len(data)} за {elapsed}с')
        
        # Статистика
        elapsed = (datetime.now() - start_time).seconds
        print(f"\n📊 Статистика за {elapsed}с:")
        print(f"  ✅ Успешно: {stats['success']}")
        print(f"  ⚠️ Нет данных: {stats['no_data']}")
        print(f"  ⏱️ Таймаут: {stats['timeout']}")
        print(f"  ❌ Ошибки: {stats['error']}")
        print(f"  📦 Всего обработано: {sum(stats.values())}")
        
        # Сохраняем в БД
        if all_results:
            print(f'🔄 Сохраняем {len(all_results)} записей в таблицу bankruptcy_info...')
            await BankruptcyInfoService().insert_data(all_results)
            print('✅ Данные сохранены в таблицу bankruptcy_info')
        
        return all_results