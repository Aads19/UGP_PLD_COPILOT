FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend/requirements.txt /app/backend-requirements.txt
RUN pip install --no-cache-dir -r /app/backend-requirements.txt

COPY pld_copilot /app/pld_copilot
COPY backend /app/backend
COPY ["PLD CATEGORY FINAL DATASET.csv", "/app/PLD CATEGORY FINAL DATASET.csv"]

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
