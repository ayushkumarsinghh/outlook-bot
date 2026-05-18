FROM python:3.10-slim

# Install system dependencies and Google Chrome stable
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    libxss1 \
    libappindicator1 \
    libgconf-2-4 \
    libxi6 \
    librandr2 \
    libasound2 \
    libpangocairo-1.0-0 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    --no-install-recommends && \
    wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list' && \
    apt-get update && \
    apt-get install -y google-chrome-stable --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Set environment variable to flag Docker environment
ENV DOCKER_ENV=true

# Set working directory
WORKDIR /app

# Install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY . .

# Run the bot
CMD ["python", "python.py"]
