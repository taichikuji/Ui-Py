# Ui-Py updater

## What is this?

This is a response to the fact that watchtower project is being archived.

## Anything I should know?

Obviously! But it is made to be as simple as possible.

This depends on the following:

- `docker`
- `docker-compose`

All included in the project. Meaning the expectation is to have these components to make this image work.

If you use podman, you should ignore this, since it will not work. You have podman auto updater, so please use that instead.

If you use Kubernetes, that's another topic for another day, but suffice to say you have plenty of options.

## How does it work?

This is meant to be as simple as possible. The updater runs on a scheduled cron job inside a Docker container and automatically pulls the latest images and restarts services as needed.

### Configuration

The only configuration you need to set is in your `docker-compose.yml`:

```docker
- CRON_SCHEDULE=${CRON_SCHEDULE:-0 0 * * *}
```

This value follows standard cron syntax and defaults to daily at 00:00. For example, if you wanted updates every 30 minutes:

```docker
- CRON_SCHEDULE=${CRON_SCHEDULE:-*/30 * * * *}
```

### Deployment

Simply run `./init-docker.sh` to deploy both ui-py and the updater. Once deployed, it will handle everything automatically.

### What happens on each run

1. Scans for containers labeled with `com.taichikuji.ui-py.enable=true` that belong to the current Docker Compose project.

2. For each enabled service, pulls the latest image from the registry and recreates the container automatically if the image has changed.

3. Removes old, unused Docker images to keep disk space clean.

The updater runs silently on schedule and only takes action when needed — containers are only recreated if their images have actually changed.

