# Proxmox LXC Deployment

Deploy Ui-Py as a Proxmox LXC container with a single command.

## Quick Start

Run from the **Proxmox host** shell:

```bash
bash -c "$(wget -qO- https://raw.githubusercontent.com/taichikuji/Ui-Py/main/proxmox/uipy.sh)"
```

## What It Does

| Step | Description |
|------|-------------|
| **1. LXC Creation** | Creates a Debian 13 unprivileged container via the [community-scripts](https://github.com/community-scripts/ProxmoxVE) `build.func` framework (MIT licensed). Interactive menus let you pick storage, networking, and advanced settings. |
| **2. Resource Defaults** | 2 CPU cores, 1 GB RAM, 4 GB disk — sized for Python + ffmpeg/voice dependencies. |
| **3. Application Install** | Installs Python 3, pipenv, ffmpeg, libopus, libnacl, clones the repo to `/opt/uipy`, and runs `pipenv install --deploy`. |
| **4. Systemd Service** | Configures `uipy.service` (enabled, but **not started** until you set your token). |

## Post-Install Setup

After the script finishes, enter the container and configure your bot token:

```bash
# 1. Enter the LXC container (replace <CTID> with the ID shown at the end of the script)
pct enter <CTID>

# 2. Edit the environment file
nano /opt/uipy/.env

# 3. Replace "your_discord_bot_token_here" with your actual Discord token
#    Optionally uncomment and set STEAM_TOKEN for Steam commands

# 4. Start the bot
systemctl start uipy

# 5. Verify it's running
systemctl status uipy
```

## Updating

Re-running the script on an existing container triggers the built-in `update_script()`, which:

1. Updates the base system (`apt upgrade`)
2. Pulls the latest code (`git pull`)
3. Reinstalls dependencies (`pipenv install --deploy`)
4. Restarts the service

The container is also a standard Debian LXC, so it is compatible with the [community-scripts LXC updater](https://github.com/community-scripts/ProxmoxVE) for system-level updates.