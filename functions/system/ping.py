from typing import TYPE_CHECKING
from discord.ext import commands
from discord import app_commands, Interaction

if TYPE_CHECKING:
    from main import UiPy


class PingCog(commands.Cog):
    """Cog for checking bot latency."""
    def __init__(self, bot: "UiPy"):
        self.bot = bot

    @app_commands.command(
        name="ping",
        description="Check the bot's latency."
    )
    async def ping(self, interaction: Interaction) -> None:
        """Respond with the bot's latency in milliseconds."""
        latency = int(self.bot.latency * 1000)
        await interaction.response.send_message(
            f":ping_pong: Pong! Latency: {latency}ms"
        )


async def setup(bot: "UiPy"):
    """Add the PingCog to the bot."""
    await bot.add_cog(PingCog(bot))
