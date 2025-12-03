# Lightweight Python image suitable for Discord bots
FROM python:3.11-slim

# Avoids Python writing .pyc files and enables unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY sticky_bot.py ./

# Default command
CMD ["python", "sticky_bot.py"]
