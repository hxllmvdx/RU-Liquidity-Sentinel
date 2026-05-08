FROM python:3.11-slim
WORKDIR /app
COPY ml-services ./ml-services
WORKDIR /app/ml-services
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "grpc_server/server.py"]
