FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DEBUG=false
EXPOSE 8000

# Self-migrating: runs migrations against DATABASE_URL on container start,
# so only the deployed platform's own network path to the DB is ever used.
# gthread, not the sync default: sync workers handle one request at a time
# per process with no way to overlap the wait on Postgres I/O, measured
# directly in scripts/load_test.js (see README's "Scale, for real").
CMD python manage.py migrate --noinput && \
    gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 --threads 4 --worker-class gthread
