FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DEBUG=false
EXPOSE 8000

# Self-migrating: runs migrations against DATABASE_URL on container start,
# so only the deployed platform's own network path to the DB is ever used.
CMD python manage.py migrate --noinput && \
    gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2
