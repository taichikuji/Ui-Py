from discord.ext import commands
from discord import app_commands
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import UiPyBot

class CloseCog(commands.Cog):
    def __init__(self, bot: 'UiPyBot'):
        self.bot = bot

    @commands.hybrid_command(
        name="shutdown",
        description="Shuts down the bot gracefully."
    )
    @commands.is_owner()
    async def shutdown_bot(self, ctx: commands.Context):
        bot_user = ctx.bot.user
        print(f"[INFO] Shutdown command initiated by owner ({ctx.author.id}).")
        if ctx.interaction:
            await ctx.interaction.response.send_message(f":wave: Shutting down {bot_user.name}...", ephemeral=True)
        else:
            await ctx.send(f":wave: Shutting down {bot_user.name}...")
        await ctx.bot.close()
        print(f"[INFO] Bot close() method invoked.")

async def setup(bot: 'UiPyBot'):
    await bot.add_cog(CloseCog(bot))