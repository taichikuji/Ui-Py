from discord.ext import commands
from typing import TYPE_CHECKING
from discord import Member

if TYPE_CHECKING:
    from main import UiPy


class ClearCog(commands.Cog):
    def __init__(self, bot: "UiPy"):
        self.bot = bot

    @commands.hybrid_command(
        name="clear", description="Remove messages in bulk. Defaults to 2 messages."
    )
    @commands.has_guild_permissions(manage_messages=True)
    async def clear(self, ctx: commands.Context, amount: int = 2, user: Member = None):
        interaction = getattr(ctx, "interaction", None)
        if interaction:
            await interaction.response.defer(ephemeral=True)
        
        def check_message(message):
            return user is None or message.author == user
        
        deleted = await ctx.channel.purge(limit=amount, check=check_message)

        if user:
            msg = f":wastebasket: Deleted {len(deleted)} messages from {user.display_name}."
        else:
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


async def setup(bot: "UiPy"):
    await bot.add_cog(ClearCog(bot))
