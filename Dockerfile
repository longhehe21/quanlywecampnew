FROM python:3.11-slim

WORKDIR /app

# Copy requirements và install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

# Port
EXPOSE 8000

# Run gunicorn
CMD gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 2