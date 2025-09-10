from typing import TYPE_CHECKING

from discord import Interaction, Member, TextChannel, Thread, app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from main import UiPy


class ClearCog(commands.Cog):
    """Cog for bulk message removal in text channels."""
    def __init__(self, bot: "UiPy"):
        self.bot = bot

    @app_commands.command(
            name="clear",
            description="Remove messages in bulk. Defaults to 1 message."
            )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear(self, interaction: Interaction, amount: int = 1, user: Member | None = None) -> None:
        """Bulk delete messages, optionally filtering by user."""
        await interaction.response.defer(ephemeral=True)
        
        def check_message(message):
            return user is None or message.author == user
        
        if isinstance(channel := interaction.channel, (TextChannel, Thread)):
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
    async def clear_error(self, interaction: Interaction, error: app_commands.AppCommandError) -> None:
        """Handle errors for the clear command."""
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                f":x: You don't have permission to use this command, {interaction.user.mention}.",
                ephemeral=True
            )
        else:
            print(f"[ERROR] ClearCog: An unexpected error occurred: {error}")


async def setup(bot: "UiPy"):
    """Add the ClearCog to the bot."""
    await bot.add_cog(ClearCog(bot))
