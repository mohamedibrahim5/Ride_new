FROM python:3.10-slim-buster

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

# Install system dependencies including GDAL
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    net-tools \
    curl \
    wget \
    nano \
    libgdal-dev \
    gdal-bin \
    python3-gdal

# Set GDAL env vars to match system installation
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# Setup project directory
RUN mkdir -p /ride_server/logs && chown -R root:root /ride_server/logs
WORKDIR /ride_server
COPY . /ride_server/

# Upgrade pip and install all dependencies (skip GDAL in requirements)
RUN pip install --upgrade pip && pip install -r requirements.txt

# Optional: install GDAL wheel from PyPi matching system version (optional)
# RUN pip install GDAL==$(gdal-config --version)

EXPOSE 8000

CMD ["gunicorn", "project.wsgi:application", "--bind", "0.0.0.0:8000"]
