FROM python:3.11-alpine

RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    nodejs \
    npm

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN npm install circomlibjs

COPY main.py .
COPY ../poseidon_hasher.js .

EXPOSE 5000

CMD ["python", "main.py"]