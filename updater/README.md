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

This is meant to be as simple as possible. Only thing that you have to keep in mind is that `docker-compose.yml` has this value;

```docker
- CRON_SCHEDULE=${CRON_SCHEDULE:-0 0 * * *}
```

This value is meant to be modified with the actual value you want to use. For example, if you wanted to have it every 30 minutes, modify it from default to this;

```docker
- CRON_SCHEDULE=${CRON_SCHEDULE:-*/30 * * * *}
```

Quite easy!

Afterwards, run the ./init-docker.sh to deploy both ui-py and the updater. Afterwards, it should just work! It does the following:

1. Using git, it will detect if there are any further changes to the git project. In other words, the project should be git pull'd to allow the connection to work. If it was downloaded directly, it will not work since the git connection is non-existant.

2. Once it goes through, it will do a git pull, if changes are detected, it will run `./init-docker.sh --soft` and that will automatically do the required steps to kill the container, pull the new version and publish it accordingly.

