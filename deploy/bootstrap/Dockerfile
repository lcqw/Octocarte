FROM python:3.12-slim
WORKDIR /app
COPY deploy/bootstrap/initialize.py /app/initialize.py
USER 0:0
ENTRYPOINT ["python", "/app/initialize.py"]
