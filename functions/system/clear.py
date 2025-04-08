from discord.ext import commands
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import UiPyBot

class ClearCog(commands.Cog):
    def __init__(self, bot: 'UiPyBot'):
        self.bot = bot

    @commands.hybrid_command(
        name="clear",
        description="Remove one or more messages. Defaults to 2 messages."
    )
    @commands.has_guild_permissions(manage_messages=True)
    async def clear(self, ctx: commands.Context, amount: int = 2):
        interaction = getattr(ctx, 'interaction', None)
        if interaction:
            await interaction.response.defer(ephemeral=True)
        deleted = await ctx.channel.purge(limit=amount)
        msg = f":wastebasket: Deleted {len(deleted)} messages."
        if interaction:
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await ctx.send(msg)

    @clear.error
    async def clear_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingPermissions):
            msg = f":x: You don't have permission to use this command, {ctx.author.mention}."
            if ctx.interaction:
                await ctx.interaction.response.send_message(msg, ephemeral=True)
            else:
                await ctx.send(msg)
        else:
            print(f"[ERROR] An unexpected error occurred: {error}")
            raise error

async def setup(bot: 'UiPyBot'):
    await bot.add_cog(ClearCog(bot))
