from playwright.async_api import async_playwright, Page
import json
import asyncio
import time
from datetime import datetime
from db.service.people import PeopleService
from parser.engine import AsyncPersistentBrowserManager
from db.service import BankruptcyInfoService, BankruptcyDocsDataService
from parser import AsyncPersistentBrowserManager, FedResursParser, ElectronicJusiceParser
from log.log import log_print
from env import env

print = log_print 

# Асинхронная главная функция
async def main():
    url_fedresurs = env.URL_FEDRESURS
    cookie_fedresurs = '../cookies_fedresurs.json'

    url_el_jusice = env.URL_KADARBITR
    # Создаем менеджер браузера
    manager = AsyncPersistentBrowserManager(url_fedresurs, cookie_fedresurs, (True if env.HEADLESS_MODE else False))
    
    try:
        # Запускаем браузер fedresurs.ru
        page = await manager.start()
        browser = page.context.browser
        fedresurs_parser = FedResursParser(url_fedresurs, page, browser)

        print('🔄 Выполняем парсинг...')
        # Выполняем парсинг 
        await fedresurs_parser.go_to_entities()
        print('🔄 Поиск ИНН для парсинга...')
        await asyncio.sleep(2)
        start_time = time.time()

        # Получаем данные о людях
        people_data = await fedresurs_parser.parse_individuals()

        start_time = time.time()

        print('🔄 Ищем данные о банкротстве...')
        # await fedresurs_parser.get_data_about_bankruptcy(people_data)

        await fedresurs_parser.get_data_about_bankruptcy_parallel(people_data)

        end_time = time.time()
        execution_time = end_time - start_time
        print(f"⏱️ Время выполнения парсинга fedresurs.ru: {execution_time:.2f} секунд")

        # manager.stop()
        # await manager.close()

        # Переходим в режим поддержания сессии
        # keep_alive_task = asyncio.create_task(manager.keep_alive())
        
        # await keep_alive_task
        print('🔄 Получаем номера дел из таблицы bankruptcy_info...')
        bankruptcy_data = await BankruptcyInfoService().select_data()
        print('✅ Успешно получили номера дел из таблицы bankruptcy_info...')

        print('🔄 Переходим на kad.arbitr.ru...')
        await manager.go_to(url_el_jusice)

        await asyncio.sleep(2)

        el_jusice_parser = ElectronicJusiceParser(page)

        # bankruptcy_docs_data: list[dict] = []

        # print('🔄 Поиск информации о документах банкротсва...')
        # start_time = time.time()
        # for i, el in enumerate(bankruptcy_data):
        #     await el_jusice_parser.get_case_num_field(el['case_num'])
        #     await asyncio.sleep(2)
        #     link = await el_jusice_parser.get_link_case_num()
        #     if link:
        #         await manager.go_to(link)
        #         await asyncio.sleep(2)
        #         data = await el_jusice_parser.go_to_electronic_case()
        #         if data:
        #             data['link'] = link
        #             data['case_num_id'] = el['id']
        #             bankruptcy_docs_data.append(data)
        #     await manager.go_to(url_el_jusice)
        #     await asyncio.sleep(1)
        #     print('✅ Выполнено:', el['case_num'], f'({i+1}/{len(bankruptcy_data)})')
        # end_time = time.time()
        # execution_time = end_time - start_time
        # print(f"⏱️ Время выполнения парсинга kad.arbitr.ru: {execution_time:.2f} секунд")

        # print('🔄 Записываем данные документов о банкротстве...')
        # await BankruptcyDocsDataService().insert_data(bankruptcy_docs_data)
        # print('✅ Данные о документах банкротсвта успешно записаны')

        await el_jusice_parser.process_bankruptcy_docs_parallel(bankruptcy_data)


        keep_alive_task = asyncio.create_task(manager.keep_alive())
        
        await keep_alive_task
        
    except KeyboardInterrupt:
        print("\n👋 Получен сигнал прерывания")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        manager.stop()
        await manager.close()
        print('👋 Программа завершена')

# Точка входа
if __name__ == "__main__":
    asyncio.run(main())