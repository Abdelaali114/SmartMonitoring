FROM python:3.11-slim
WORKDIR /app


# system deps for kubernetes client & exec streaming
RUN apt-get update && apt-get install -y gcc git netcat-openbsd curl && rm -rf /var/lib/apt/lists/*



COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt


COPY app ./app


ENV PYTHONUNBUFFERED=1
EXPOSE 7777
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7777"]