FROM python:3.10-slim-buster

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

RUN apt-get update && apt-get -y install libpq-dev gcc net-tools curl wget nano

RUN mkdir -p /ride_server/logs && chown -R root:root /ride_server/logs

WORKDIR /ride_server

COPY . /ride_server/

RUN pip install --upgrade pip && pip install -r requirements.txt

EXPOSE 8000

CMD ["gunicorn", "project.wsgi:application", "--bind", "0.0.0.0:8000"]
