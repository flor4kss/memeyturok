FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Prevent Python from writing .pyc files & buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies (fontconfig / freetype)
RUN apt-get update && apt-get install -y --no-install-recommends \
    fontconfig \
    libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose port (Render web service default / custom PORT)
EXPOSE 8080

# Command to run bot
CMD ["python", "-m", "bot.main"]
