from discord.ext import commands
from discord import app_commands, Interaction, Message

class PingCog(commands.Cog):
    def __init__(self, bot: commands.AutoShardedBot):
        self.bot = bot

    @app_commands.command(name="ping", description="Check the bot's latency.")
    async def ping(self, interaction: Interaction):
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f":ping_pong: Pong! Latency: {latency}ms")

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if message.author.bot:
            return

async def setup(bot: commands.AutoShardedBot):
    await bot.add_cog(PingCog(bot))