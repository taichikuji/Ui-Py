from discord.ext import commands
from discord import app_commands, Interaction
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import UiPyBot

class CloseCog(commands.Cog):
    def __init__(self, bot: 'UiPyBot'):
        self.bot = bot
    
    @app_commands.command(
        name="shutdown",
        description="Shuts down the bot gracefully."
    )
    @commands.is_owner()
    async def shutdown_bot(self, interaction: Interaction):
        bot_user = interaction.client.user
        print(f"[INFO] Shutdown command initiated by owner ({interaction.user.id}).")
        await interaction.response.send_message(f":wave: Shutting down {bot_user.name}...", ephemeral=True)
        await interaction.client.close()
        print(f"[INFO] Bot close() method invoked.")

async def setup(bot: 'UiPyBot'):
    await bot.add_cog(CloseCog(bot))