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
COPY poseidon_hasher.js .
COPY eddsa_signer.js .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]