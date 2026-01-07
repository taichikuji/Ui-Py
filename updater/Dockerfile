FROM alpine:3

# Install dependencies
RUN apk add --no-cache \
    bash \
    git \
    docker-cli \
    docker-cli-compose

# Create a shim for docker-compose (v1) using docker compose (v2)
RUN echo -e '#!/bin/sh\ndocker compose "$@"' > /usr/local/bin/docker-compose && \
    chmod +x /usr/local/bin/docker-compose

# Copy scripts
COPY updater.sh /usr/local/bin/updater.sh
COPY entrypoint.sh /usr/local/bin/entrypoint.sh

RUN chmod +x /usr/local/bin/updater.sh /usr/local/bin/entrypoint.sh

WORKDIR /workspace

CMD ["/usr/local/bin/entrypoint.sh"]
