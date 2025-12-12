FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE $PORT  # tùy chọn, không bắt buộc

CMD gunicorn core.wsgi:application --bind 0.0.0.0:$PORT --workers 2