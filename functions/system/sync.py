from typing import TYPE_CHECKING
from discord import HTTPException, Forbidden, Guild
from discord.ext import commands

if TYPE_CHECKING:
    from main import UiPy


class SyncCog(commands.Cog):
    """Cog for syncing application commands globally or per guild (admin only)."""
    def __init__(self, bot: "UiPy"):
        self.bot = bot

    @commands.hybrid_group(
        name="sync",
        description="Sync application commands (Admin Only)",
    )
    @commands.has_permissions(administrator=True)
    async def sync(self, ctx: commands.Context) -> None:
        """Base sync command group."""
        if ctx.invoked_subcommand is None:
            await ctx.send(
                "Please specify a subcommand: `global` or `guild`.\n"
                "(e.g., `/sync guild` or `@BotName sync global`)"
            )

    @sync.command(
        name="global", 
        description="Sync commands globally (can take up to an hour)."
    )
    @commands.has_permissions(administrator=True)
    async def sync_global(self, ctx: commands.Context) -> None:
        """Sync commands globally."""
        is_slash = ctx.interaction is not None
        if is_slash:
            await ctx.defer(ephemeral=True)
        try:
            if synced_commands := await self.bot.tree.sync():
                msg = f"Synced {len(synced_commands)} commands globally."
            else:
                msg = "No commands were synced globally."
            if is_slash and ctx.interaction:
                await ctx.interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx.send(msg)
        except HTTPException as e:
            msg = f"Failed to sync globally: {e.status} {getattr(e, 'text', 'No additional information')}"
            if is_slash and ctx.interaction:
                await ctx.interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx.send(msg)
        except Exception as e:
            msg = f"An unexpected error occurred during global sync: {e}"
            if is_slash and ctx.interaction:
                await ctx.interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx.send(msg)

    @sync.command(
        name="guild", 
        description="Sync commands to the current guild (usually instant)."
    )
    @commands.has_permissions(administrator=True)
    async def sync_guild(self, ctx: commands.Context) -> None:
        """Sync commands to the current guild."""
        is_slash = ctx.interaction is not None
        if is_slash:
            await ctx.defer(ephemeral=True)
        if not ctx.guild:
            err_msg = "This command can only be used in a server."
            if is_slash and ctx.interaction:
                await ctx.interaction.followup.send(err_msg, ephemeral=True)
            else:
                await ctx.send(err_msg)
            return
        target_guild_object: Guild = ctx.guild
        try:
            if synced_commands_list := await self.bot.tree.sync(guild=target_guild_object):
                msg = f"Synced {len(synced_commands_list)} commands to guild {target_guild_object.id}"
            else:
                msg = f"No application commands were synced to guild {target_guild_object.id}"
            if is_slash and ctx.interaction:
                await ctx.interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx.send(msg)
        except Forbidden as e:
            msg = f"Failed to sync to guild {target_guild_object.id}: Missing Permissions. {e}"
            if is_slash and ctx.interaction:
                await ctx.interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx.send(msg)
        except HTTPException as e:
            msg = (
                f"Failed to sync to guild {target_guild_object.id}: {e.status} {e.text}"
            )
            if is_slash and ctx.interaction:
                await ctx.interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx.send(msg)
        except Exception as e:
            msg = f"An unexpected error occurred during guild sync for guild {target_guild_object.id}: {e}"
            if is_slash and ctx.interaction:
                await ctx.interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx.send(msg)

    @sync.error
    async def on_sync_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        """Handle errors for the sync command."""
        is_slash = ctx.interaction is not None
        if isinstance(error, commands.MissingPermissions):
            msg = ":x: You need Administrator permissions to use this command."
            if is_slash and ctx.interaction:
                await ctx.interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx.send(msg)
        else:
            print(f"[ERROR] SyncCog: Unexpected error in sync command: {error}")

async def setup(bot: "UiPy"):
    """Add the SyncCog to the bot."""
    await bot.add_cog(SyncCog(bot))
