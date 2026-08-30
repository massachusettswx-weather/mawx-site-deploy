FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV MPLCONFIGDIR=/tmp/matplotlib

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libeccodes0 \
        libeccodes-dev \
        gcc \
        g++ \
    && rm -rf /var/lib/apt/lists/*

COPY jobs/requirements.txt /app/jobs/requirements.txt

RUN pip install --no-cache-dir \
    -r /app/jobs/requirements.txt

COPY shared /app/shared
COPY jobs /app/jobs

ENTRYPOINT ["python", "jobs/update_polar_vortex.py"]
CMD ["--daily"]
