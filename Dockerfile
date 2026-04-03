FROM python:3.12-slim AS builder

WORKDIR /usr/src/app

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends build-essential git libffi-dev libnacl-dev python3-dev libopus-dev && \
    pip install pipenv

COPY Pipfile Pipfile.lock ./
RUN pipenv requirements > requirements.txt

FROM python:3.12-slim

WORKDIR /usr/src/app

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends libopus0 libsodium23 && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/src/app/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py ./
COPY functions ./functions/

CMD ["python", "./main.py"]
