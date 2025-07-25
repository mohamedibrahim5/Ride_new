FROM ghcr.io/osgeo/gdal:ubuntu-full-latest

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /ride_server
COPY . /ride_server/

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    python3-dev \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

EXPOSE 8000
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "project.asgi:application"]
