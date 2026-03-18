FROM python:3.12-slim

# Все необходимые зависимости для Chromium
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
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
    **libasound2** \ 
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install chromium

COPY . .

# RUN mkdir -p /log

CMD ["python", "main.py"]