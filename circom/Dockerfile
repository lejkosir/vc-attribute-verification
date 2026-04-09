FROM node:20-bullseye

RUN apt-get update && apt-get install -y \
    curl build-essential git \
    python3 python3-pip

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

WORKDIR /tmp
RUN git clone https://github.com/iden3/circom.git \
    && cd circom \
    && cargo build --release \
    # The fix: Install from the /circom directory inside the repo
    && cargo install --path circom \
    && cp /root/.cargo/bin/circom /usr/local/bin/

RUN npm install -g snarkjs

WORKDIR /app
COPY . .

CMD ["tail", "-f", "/dev/null"]