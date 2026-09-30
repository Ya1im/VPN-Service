FROM ghcr.io/xtls/xray-core:26.3.27 AS xray

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=xray /usr/local/bin/xray /usr/local/bin/xray
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY vpn ./vpn
COPY app ./app
CMD ["python", "-m", "app.main"]
