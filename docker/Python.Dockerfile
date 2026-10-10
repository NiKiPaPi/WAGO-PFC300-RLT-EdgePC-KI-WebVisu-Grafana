FROM python:3.12.10-slim-bookworm
WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock && useradd -u 10001 -m app && mkdir /data && chown app /data
COPY contracts contracts
COPY backend backend
COPY simulation simulation
USER app
