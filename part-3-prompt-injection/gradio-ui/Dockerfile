FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

ENV GRADIO_ANALYTICS_ENABLED=False
EXPOSE 7860
CMD ["python", "app.py"]
