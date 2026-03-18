FROM python:3.12-slim

# Устанавливаем все зависимости для Chromium + Xvfb
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    # Зависимости Chromium (твои)
    libx11-6 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    libglib2.0-0 \
    libgdk-pixbuf-2.0-0 \
    libgtk-3-0 \
    libpango-1.0-0 \
    libcairo2 \
    libdbus-1-3 \
    libatk-bridge2.0-0 \
    libatspi2.0-0 \
    libnss3 \
    libnspr4 \
    libgbm1 \
    libdrm2 \
    libasound2 \
    # Добавляем Xvfb (виртуальный экран)
    xvfb \
    # Для корректной работы dbus
    dbus-x11 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Устанавливаем браузер Playwright
RUN playwright install chromium

COPY . .

# Скрипт для запуска с Xvfb
CMD xvfb-run -a --server-args="-screen 0 1280x1024x24" python main.py