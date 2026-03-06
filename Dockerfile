FROM python:3.11-slim

WORKDIR /usr/src/app

COPY fetch_magister.py .
COPY main.py .

CMD ["python", "./main.py"]