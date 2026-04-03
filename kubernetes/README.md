# Kubernetes Deployment

Deploy Ui-Py on any Kubernetes cluster. Both containers (Discord bot + Lavalink) run as sidecars in a single pod.

## Quick Start

1. **Create your `.env` file** from the example:

   ```bash
   cp .env.example .env
   nano .env
   ```

2. **Create the namespace and secret**:

   ```bash
   kubectl apply -f kubernetes/deployment.yml
   kubectl -n uipy create secret generic uipy-secret --from-env-file=.env
   ```

3. **Restart the deployment** so it picks up the secret:

   ```bash
   kubectl -n uipy rollout restart deployment/uipy
   ```

4. **Verify**:

   ```bash
   kubectl -n uipy get pods
   ```

5. **Check logs**:

   ```bash
   kubectl -n uipy logs deployment/uipy -c discord -f
   kubectl -n uipy logs deployment/uipy -c lavalink -f
   ```

## Architecture

A single Deployment with two containers sharing `localhost`:

| Container  | Image                                  | Role              |
|------------|----------------------------------------|-------------------|
| `discord`  | `ghcr.io/taichikuji/ui-py:latest`     | Discord bot       |
| `lavalink` | `ghcr.io/lavalink-devs/lavalink:4`    | Audio server      |

## Updating

```bash
kubectl -n uipy rollout restart deployment/uipy
```

## Cleanup

```bash
kubectl delete namespace uipy
```
