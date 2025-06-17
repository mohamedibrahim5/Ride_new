# Use official OSGeo GDAL image (Ubuntu, full GDAL + Python bindings)
FROM ghcr.io/osgeo/gdal:ubuntu-full-latest

# Set Python environment
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /ride_server
COPY . /ride_server/

# Install extra system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y python3-pip
# Upgrade pip and install Python dependencies
RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install -r requirements.txt

# Expose port and run
EXPOSE 8000
CMD ["gunicorn", "project.wsgi:application", "--bind", "0.0.0.0:8000"]