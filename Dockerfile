FROM python:3.12-slim AS builder

WORKDIR /usr/src/app

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends build-essential git libffi-dev ffmpeg libnacl-dev python3-dev && \
    pip install pipenv

COPY Pipfile Pipfile.lock ./
RUN pipenv requirements > requirements.txt

FROM python:3.12-slim

WORKDIR /usr/src/app

COPY --from=builder /usr/src/app/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "./main.py"]