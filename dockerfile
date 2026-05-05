FROM python:3.11-slim

ENV PYTHONUNBUFFERED=True
ENV APP_HOME=/app
WORKDIR $APP_HOME

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gunicorn

COPY . .

EXPOSE 8080
CMD exec gunicorn --bind :8080 --workers 2 --threads 4 --timeout 0 app:app