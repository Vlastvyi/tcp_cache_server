# Используем свежий Python
FROM python:3.13-slim

WORKDIR /app
COPY server.py /app/server.py
COPY client.py /app/client.py

EXPOSE 6379
CMD ["python", "server.py", "--host", "0.0.0.0", "--port", "6379"]
