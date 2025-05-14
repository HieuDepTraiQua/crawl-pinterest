# Sử dụng Python 3.9 làm base image
FROM python:3.9-slim

# Cài đặt các dependencies hệ thống cần thiết
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Tạo và chuyển đến thư mục làm việc
WORKDIR /app

# Copy requirements.txt và cài đặt các dependencies Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Cài đặt Playwright và các dependencies
RUN playwright install chromium
RUN playwright install-deps

# Copy toàn bộ source code vào container
COPY . .

# Tạo các thư mục cần thiết
# RUN mkdir -p logs avatars

# Thiết lập biến môi trường
ENV PYTHONUNBUFFERED=1
ENV MONGO_URL=mongodb://192.168.161.230:27011,192.168.161.230:27012,192.168.161.230:27013/?replicaSet=rs0
ENV DATABASE_NAME=pinterest_data
ENV CRAWL_CONTROLLER_ENDPOINT=http://localhost:8080/api/upload/multiple
ENV SFTP_USERNAME=htsc
ENV SFTP_PASSWORD=Htsc@123

# Command mặc định khi chạy container
ENTRYPOINT ["python", "app.py"]
