FROM python:3.14-alpine

WORKDIR /app

COPY requirements.txt .

RUN apk add --no-cache build-base

RUN apk update && apk add docker

RUN pip install -r requirements.txt


COPY .. .

EXPOSE 8000

CMD ["fastapi", "run", "main.py", "--port", "8080"]