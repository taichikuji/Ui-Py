from os import getpid
from platform import machine, python_version, system
from typing import TYPE_CHECKING

from discord import Embed, app_commands, Interaction
from discord.ext import commands
from psutil import Process

if TYPE_CHECKING:
    from main import UiPyBot

class InfoCog(commands.Cog):
    def __init__(self, bot: 'UiPyBot'):
        self.bot = bot

    @app_commands.command(
        name="info",
        description="Show information about the bot, including versions, uptime, and memory usage."
    )
    async def info(self, interaction: Interaction):
        embed = await self.create_embed()
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def create_embed(self):
        em = {
            "title": "Bot's Info",
            "description": "Here's some information about me and my dependencies!",
            "color": self.bot.color,
            "fields": [
                {
                    "name": "Bot version",
                    "value": f"**Python**: {python_version()}\n**Ui-Py**: 0.2.0",
                    "inline": True,
                },
                {"name": "OS", "value": f"**{system()}**: {machine()}", "inline": True},
                {"name": "Uptime", "value": await self.uptime(), "inline": True},
                {"name": "Memory", "value": await self._get_mem_usage(), "inline": True},
            ],
        }
        return Embed.from_dict(em)

    @staticmethod
    async def _get_mem_usage():
        mem_usage = float(Process(getpid()).memory_info().rss) / 1000000
        return f"{round(mem_usage, 2)} MB"

    async def uptime(self):
        with open("/proc/uptime", "r") as f:
            uptime = f.read().split(" ")[0].strip()
        uptime = int(float(uptime))
        uptime_hours = uptime // 3600
        uptime_minutes = (uptime % 3600) // 60
        return f"{uptime_hours} hours, {uptime_minutes} minutes"

async def setup(bot: 'UiPyBot'):
    await bot.add_cog(InfoCog(bot))
