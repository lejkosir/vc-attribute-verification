FROM node:20-bookworm

RUN apt-get update && apt-get install -y curl && \
    curl -L https://github.com/iden3/circom/releases/download/v2.1.9/circom-linux-amd64 \
         -o /usr/local/bin/circom && \
    chmod +x /usr/local/bin/circom

RUN npm install -g snarkjs

WORKDIR /app

RUN npm install circomlib

COPY circuits/age_checkV2/age_check_v2.circom /app/age_check_v2.circom
COPY circom/run_setup.sh /app/run_setup.sh
RUN chmod +x /app/run_setup.sh

CMD ["/bin/sh", "/app/run_setup.sh"]
