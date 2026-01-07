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

[Check our setup guide in the wiki](https://github.com/taichikuji/Ui-Py/wiki/How-to-get-the-bot-working/)

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

> **Note**: If you plan on also using a Cog / Module that requires an additional API Token, check the wiki's specific entry for additional token requirements here: [Setting environment variables](https://github.com/taichikuji/Ui-Py/wiki/Configuration-Guide#setting-environment-variables)

### 3. **Using ghcr.io**

You can now deploy using GitHub Packages without building the Dockerfile yourself!

Simply pull the image with the following command:

```bash
docker pull ghcr.io/taichikuji/ui-py:latest
```

This image can even be used in your Kubernetes cluster!

We don't have a Kubernetes deployment YAML at the moment, but one may be provided in the future.

### Auto-Updater

To enable automatic updates, uncomment the `updater` service and the `labels` section in `docker-compose.yml`.
You can change the update frequency by modifying the `CRON_SCHEDULE` environment variable (default: `0 0 * * *` for daily checks).

## Contributing

The project follows a modular architecture, making it easy to add new features. New functionality can be added by creating new Python files in the appropriate directories under `functions/`.

We welcome contributions from the community! When contributing, GitHub will automatically provide:
- Bug report template when reporting bugs
- Feature request template when suggesting features
- Pull request template when submitting code changes

For detailed contribution guidelines, see our [contribution guide](.github/CONTRIBUTING.md).
For detailed project documentation, visit our [wiki](https://github.com/taichikuji/Ui-Py/wiki).

## Uses:

- <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/github/pipenv/locked/python-version/taichikuji/Ui-Py"/></a>
- <a href="https://pypi.org/project/pipenv/"><img src="https://img.shields.io/pypi/v/pipenv"/></a>

### Dependencies

- <a href="https://pypi.org/project/discord.py/"><img src="https://img.shields.io/github/pipenv/locked/dependency-version/taichikuji/Ui-Py/discord.py/master"/></a>
- <a href="https://pypi.org/project/aiohttp/"><img src="https://img.shields.io/github/pipenv/locked/dependency-version/taichikuji/Ui-Py/aiohttp/master"/></a>
- <a href="https://pypi.org/project/psutil/"><img src="https://img.shields.io/github/pipenv/locked/dependency-version/taichikuji/Ui-Py/psutil/master"/></a>
- <a href="https://pypi.org/project/yt-dlp/"><img src="https://img.shields.io/github/pipenv/locked/dependency-version/taichikuji/Ui-Py/yt-dlp/master"/></a>
- <a href="https://pypi.org/project/pynacl/"><img src="https://img.shields.io/github/pipenv/locked/dependency-version/taichikuji/Ui-Py/pynacl/master"/></a>
- <a href="https://pypi.org/project/aiosqlite/"><img src="https://img.shields.io/github/pipenv/locked/dependency-version/taichikuji/Ui-Py/aiosqlite/master"/></a>

