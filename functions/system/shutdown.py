from discord.ext import commands
from typing import TYPE_CHECKING
from discord import app_commands, Interaction

if TYPE_CHECKING:
    from main import UiPy


class CloseCog(commands.Cog):
    def __init__(self, bot: "UiPy"):
        self.bot = bot

    @app_commands.command(
        name="shutdown",
        description="Shuts down the bot gracefully."
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def shutdown_bot(self, interaction: Interaction):
        await interaction.response.send_message(
            f":wave: Shutting down {interaction.client.user.name}...",
            ephemeral=True
        )
        try:
            await interaction.client.close()
        except Exception as e:
            print(f"[ERROR] Failed to shut down the bot: {e}")
            raise


async def setup(bot: "UiPy"):
    await bot.add_cog(CloseCog(bot))
