FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV WEATHER_LOCAL_ROOT=/tmp/massachusettswx
ENV WEATHER_STORAGE_BUCKET=massachusettswx-nwp-project

RUN apt-get update && apt-get install -y \
    libeccodes0 \
    libgeos-dev \
    proj-bin \
    libproj-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# ============================================================
# PRE-CACHE CARTOPY / NATURAL EARTH
#
# Legacy-Docker-compatible form: avoid Dockerfile heredocs.
# ============================================================

RUN python -c "from cartopy.io import shapereader; datasets=[('50m','physical','land'),('50m','physical','ocean'),('50m','physical','coastline'),('50m','cultural','admin_0_boundary_lines_land'),('50m','cultural','admin_1_states_provinces_lakes'),('110m','physical','land'),('110m','physical','ocean'),('110m','physical','coastline'),('110m','cultural','admin_0_boundary_lines_land')]; [print('Cached:', r, c, n, '->', shapereader.natural_earth(resolution=r, category=c, name=n)) for r,c,n in datasets]"


COPY . .

CMD ["python", "cloud_job.py"]
