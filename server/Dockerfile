FROM python:3.10-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends poppler-utils libgl1 libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# oemer downloads its recognition models on first use. Trigger that during the
# build so the first real scan doesn't have to wait for the download.
RUN python -c "from PIL import Image; Image.new('RGB', (800, 300), 'white').save('/tmp/blank.png')" \
 && (oemer /tmp/blank.png -o /tmp/warmup || true) \
 && rm -rf /tmp/warmup /tmp/blank.png

COPY app.py .
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
