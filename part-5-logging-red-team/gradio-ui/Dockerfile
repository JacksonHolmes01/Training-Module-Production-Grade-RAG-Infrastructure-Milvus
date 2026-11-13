# Overridden in hardening/06-pinned.yml to pin the exact image you scanned
ARG BASE_IMAGE=python:3.12-slim
FROM ${BASE_IMAGE}

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

ENV GRADIO_ANALYTICS_ENABLED=False
EXPOSE 7860
CMD ["python", "app.py"]
