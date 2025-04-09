FROM python:3.12-slim AS builder

WORKDIR /usr/src/app

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends build-essential git libffi-dev ffmpeg libnacl-dev python3-dev && \
    pip install pipenv

RUN mkdir -p /ffmpeg-deps/usr/bin && \
    cp $(which ffmpeg) $(which ffprobe) /ffmpeg-deps/usr/bin/ && \
    mkdir -p /ffmpeg-deps/usr/lib && \
    ldd $(which ffmpeg) | grep "=> /" | awk '{print $3}' | xargs -I '{}' cp -v '{}' /ffmpeg-deps/usr/lib/

COPY Pipfile Pipfile.lock ./
RUN pipenv requirements > requirements.txt

FROM python:3.12-slim

WORKDIR /usr/src/app

COPY --from=builder /usr/src/app/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY --from=builder /ffmpeg-deps/usr/bin/* /usr/bin/
COPY --from=builder /ffmpeg-deps/usr/lib/* /usr/lib/

COPY main.py functions ./

CMD ["python", "./main.py"]