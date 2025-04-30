# Ui-Py
## Who is Ui?

Ui is a bot written in Python, inspired by the character Ui Hirasawa from the K-On! show.

<p align="center"><img src="media/ui.webp" width="150px" /><br/>
<img src="https://img.shields.io/github/license/taichikuji/Ui-Py?color=FF3351&logo=github" />
<img src="https://img.shields.io/github/commit-activity/w/taichikuji/Ui-Py?label=commits&logo=github" />
<img src="https://img.shields.io/librariesio/github/taichikuji/Ui-Py?logo=github" />
</p>

## Why Python?

Because this is a rewrite and retry at writing best practices code in Python, keeping modularity as it was with my previous projects.

## How do I make it work?

<a href="https://github.com/taichikuji/Ui-Py/wiki/How-to-get-the-bot-working/">// We are building it!</a>

To deploy, you have the following options:

1. **Using Docker-Compose**  
    Pass the variable into your `docker-compose.yml` file or export it:
    ```bash
    export TOKEN='TOKEN'
    ```  
    Afterwards, deploy easily with:
    ```bash
    ./deploy-dc.sh
    ```

2. **Using Docker Build and Run**  
    Build the image:
    ```bash
    docker build -t ui:latest .
    ```  
    Run the container with the TOKEN environment variable:
    ```bash
    docker run -e TOKEN="TOKEN" ui:latest
    ```
### 3. **Using ghcr.io**

You can now deploy using GitHub Packages without building the Dockerfile yourself!

Simply pull the image with the following command:

```bash
docker pull ghcr.io/taichikuji/ui-py:latest
```

This image can even be used in your Kubernetes cluster!

We don't have a Kubernetes deployment YAML at the moment, but one may be provided in the future.

## Uses:

- <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/github/pipenv/locked/python-version/taichikuji/Ui-Py"/></a>
- <a href="https://pypi.org/project/pipenv/"><img src="https://img.shields.io/pypi/v/pipenv"/></a>

### Dependencies

- <a href="https://pypi.org/project/discord.py/"><img src="https://img.shields.io/github/pipenv/locked/dependency-version/taichikuji/Ui-Py/discord.py/master"/></a>
- <a href="https://pypi.org/project/aiohttp/"><img src="https://img.shields.io/github/pipenv/locked/dependency-version/taichikuji/Ui-Py/aiohttp/master"/></a>

