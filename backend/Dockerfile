FROM python:3.11-slim

RUN useradd --create-home sandboxuser

USER sandboxuser

WORKDIR /app

ENV PYTHONUNBUFFERED=1

CMD ["python", "sample.py"]