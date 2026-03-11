FROM python:3.11-slim

WORKDIR /usr/src/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install --with-deps chromium

COPY fetch_magister.py .
COPY main.py .
COPY ics_manager.py .

CMD ["python", "./main.py"]