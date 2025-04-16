from discord.ext import commands
from typing import TYPE_CHECKING
from discord import app_commands, Interaction

if TYPE_CHECKING:
    from main import UiPy


class PingCog(commands.Cog):
    def __init__(self, bot: "UiPy"):
        self.bot = bot

    @app_commands.command(
        name="ping",
        description="Check the bot's latency."
    )
    async def ping(self, interaction: Interaction):
        latency = int(self.bot.latency * 1000)
        await interaction.response.send_message(
            f":ping_pong: Pong! Latency: {latency}ms"
        )


async def setup(bot: "UiPy"):
    await bot.add_cog(PingCog(bot))
