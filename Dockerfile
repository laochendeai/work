FROM mcr.microsoft.com/playwright/python:v1.44.0

USER root
WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app
RUN chown -R pwuser:pwuser /app

USER pwuser
ENV PYTHONUNBUFFERED=1 \
    QUEUE_MODE=1
EXPOSE 8000

CMD ["python", "main.py"]
