FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# FastEmbed caches models here — mount a volume to persist across runs
ENV FASTEMBED_CACHE_PATH=/root/.cache/fastembed
ENTRYPOINT ["python", "-m", "aim"]
