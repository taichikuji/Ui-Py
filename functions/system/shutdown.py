from discord.ext import commands
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import UiPy


class CloseCog(commands.Cog):
    def __init__(self, bot: "UiPy"):
        self.bot = bot

    @commands.hybrid_command(
        name="shutdown", description="Shuts down the bot gracefully."
    )
    @commands.is_owner()
    async def shutdown_bot(self, ctx: commands.Context):
        bot_user = ctx.bot.user
        if ctx.interaction:
            await ctx.interaction.response.send_message(
                f":wave: Shutting down {bot_user.name}...", ephemeral=True
            )
        else:
            await ctx.send(f":wave: Shutting down {bot_user.name}...")
        try:
            await ctx.bot.close()
        except Exception as e:
            print(f"[ERROR] Failed to shut down the bot: {e}")
            raise


async def setup(bot: "UiPy"):
    await bot.add_cog(CloseCog(bot))
