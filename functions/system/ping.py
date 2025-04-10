from discord.ext import commands
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import UiPy


class PingCog(commands.Cog):
    def __init__(self, bot: "UiPy"):
        self.bot = bot

    @commands.hybrid_command(name="ping", description="Check the bot's latency.")
    async def ping(self, ctx: commands.Context):
        latency = int(self.bot.latency * 1000)
        if ctx.interaction:
            await ctx.interaction.response.send_message(
                f":ping_pong: Pong! Latency: {latency}ms", ephemeral=True
            )
        else:
            await ctx.send(f":ping_pong: Pong! Latency: {latency}ms")


async def setup(bot: "UiPy"):
    await bot.add_cog(PingCog(bot))
