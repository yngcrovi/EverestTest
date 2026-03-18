from datetime import datetime

def log_print(*args, **kwargs):
    """Функция для вывода в консоль и файл"""
    # Получаем текст для вывода
    text = ' '.join(str(arg) for arg in args)
    
    # Выводим в консоль
    print(*args, **kwargs)
    
    # Записываем в файл
    with open('../log/log.txt', 'a', encoding='utf-8') as f:
        # Добавляем timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        f.write(f"[{timestamp}] {text}\n")