from discord.ext import commands
from discord import Interaction, Message
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import UiPyBot

class PingCog(commands.Cog):
    def __init__(self, bot: 'UiPyBot'):
        self.bot = bot

    @commands.hybrid_command(name="ping", description="Check the bot's latency.")
    async def ping(self, ctx: commands.Context) -> None:
        latency = int(self.bot.latency * 1000)
        print(f"[INFO] Ping command invoked. Latency: {latency}ms")
        if ctx.interaction:
            await ctx.interaction.response.send_message(f":ping_pong: Pong! Latency: {latency}ms", ephemeral=True)
        else:
            await ctx.send(f":ping_pong: Pong! Latency: {latency}ms")

async def setup(bot: 'UiPyBot') -> None:
    await bot.add_cog(PingCog(bot))