from typing import TYPE_CHECKING, Optional
from discord.ext import commands
from discord import Member, app_commands, Interaction, TextChannel, Thread

if TYPE_CHECKING:
    from main import UiPy


class ClearCog(commands.Cog):
    def __init__(self, bot: "UiPy"):
        self.bot = bot

    @app_commands.command(
            name="clear",
            description="Remove messages in bulk. Defaults to 1 message."
            )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear(self, interaction: Interaction, amount: int = 1, user: Optional[Member] = None):
        await interaction.response.defer(ephemeral=True)
        
        def check_message(message):
            return user is None or message.author == user
        
        channel = interaction.channel
        if isinstance(channel, (TextChannel, Thread)):
            deleted = await channel.purge(limit=amount, check=check_message)
            if user:
                msg = f":wastebasket: Deleted {len(deleted)} messages from {user.display_name}."
            else:
                msg = f":wastebasket: Deleted {len(deleted)} messages."
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.followup.send(
                ":x: This command can only be used in text channels.", ephemeral=True
            )
            return

    @clear.error
    async def clear_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                f":x: You don't have permission to use this command, {interaction.user.mention}.",
                ephemeral=True
            )
        else:
            print(f"[ERROR] An unexpected error occurred: {error}")


async def setup(bot: "UiPy"):
    await bot.add_cog(ClearCog(bot))
