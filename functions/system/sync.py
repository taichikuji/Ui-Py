from discord import app_commands, Object, HTTPException, Forbidden
from discord.ext import commands
import traceback
from typing import Literal, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from main import UiPyBot

class SyncCog(commands.Cog):
    def __init__(self, bot: "UiPyBot"):
        self.bot = bot
    
    @commands.hybrid_group(
        name="sync",
        description="Sync application commands (Owner Only)",
    )
    @commands.is_owner()
    async def sync(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
             await ctx.send(
                 "Please specify a subcommand: `global` or `guild [id]`.\n"
                 "(e.g., `/sync guild` or `@BotName sync global`)",
                 ephemeral=True
            )
    
    @sync.command(name="global", description="Sync commands globally (can take up to an hour).")
    @commands.is_owner()
    async def sync_global(self, ctx: commands.Context):
        is_slash = ctx.interaction is not None
        invoked_by = ctx.author
        print(f"[INFO] Global sync initiated by owner ({invoked_by.id}) via {'slash command' if is_slash else 'text command'}.")
        if is_slash: await ctx.defer(ephemeral=True)
        try:
            synced_commands = await self.bot.tree.sync()
            msg = f"Synced {len(synced_commands)} commands globally."
            print(f"[INFO] {msg}")
            if is_slash and ctx.interaction: await ctx.interaction.followup.send(msg, ephemeral=True)
            else: await ctx.send(msg)
        except HTTPException as e:
            msg = f"Failed to sync globally: {e.status} {getattr(e, 'text', 'No additional information')}"
            print(f"[ERROR] {msg}")
            traceback.print_exc()
            if is_slash: await ctx.interaction.followup.send(msg, ephemeral=True)
            else: await ctx.send(msg)
        except Exception as e:
            msg = f"[ERROR] An unexpected error occurred during global sync."
            print(f"[ERROR] {msg}")
            traceback.print_exc()
            if is_slash: await ctx.interaction.followup.send(msg, ephemeral=True)
            else: await ctx.send(msg)

    @sync.command(name="guild", description="Sync commands to a specific guild (usually instant).")
    @app_commands.describe(
        guild_id="Optional: Guild ID to sync to (defaults to current guild, or dev guild if configured)"
    )
    @commands.is_owner()
    async def sync_guild(self, ctx: commands.Context, guild_id: Optional[str] = None):
        is_slash = ctx.interaction is not None
        invoked_by = ctx.author
        print(f"[INFO] Guild sync initiated by owner ({invoked_by.id}) via {'slash command' if is_slash else 'text command'}.")

        if is_slash: await ctx.defer(ephemeral=True)

        target_guild_object: Optional[Object] = None
        guild_identifier = "Unknown"

        if guild_id:
            try:
                target_guild_object = Object(id=int(guild_id))
                guild_identifier = f"specified guild ({guild_id})"
            except ValueError:
                err_msg = "Invalid Guild ID format. Please provide a numerical ID."
                if is_slash: await ctx.interaction.followup.send(err_msg, ephemeral=True)
                else: await ctx.send(err_msg)
                return
        elif ctx.guild:
            target_guild_object = ctx.guild
            guild_identifier = f"current guild ({ctx.guild.id})"
        elif self.bot.dev_guild:
             target_guild_object = self.bot.dev_guild
             guild_identifier = f"configured development guild ({self.bot.dev_guild.id})"
        else:
            err_msg = "Cannot determine target guild. Please specify a Guild ID or run this command in a server."
            if is_slash: await ctx.interaction.followup.send(err_msg, ephemeral=True)
            else: await ctx.send(err_msg)
            return

        print(f"[INFO] Attempting guild sync for {guild_identifier}.")
        try:
            print(f"[INFO] Clearing commands for guild {target_guild_object.id}...")
            self.bot.tree.clear_commands(guild=target_guild_object)
            await self.bot.tree.sync(guild=target_guild_object)

            synced_commands = await self.bot.tree.sync(guild=target_guild_object)
            msg = f"Synced {len(synced_commands)} commands to {guild_identifier}."
            print(f"[INFO] {msg}")
            if is_slash: await ctx.interaction.followup.send(msg, ephemeral=True)
            else: await ctx.send(msg)
        except Forbidden as e:
            msg = f"Failed to sync to {guild_identifier}: {e.status if hasattr(e, 'status') else 'N/A'} {e.text if hasattr(e, 'text') else 'Missing Permissions. Ensure the bot is in the guild with \'application.commands\' scope.'}"
            print(f"[ERROR] {msg}")
            traceback.print_exception(type(e), e, e.__traceback__)
            if is_slash: await ctx.interaction.followup.send(msg, ephemeral=True)
            else: await ctx.send(msg)
        except HTTPException as e:
            msg = f"Failed to sync to {guild_identifier}: {e.status} {e.text}"
            print(f"[ERROR] {msg}")
            traceback.print_exc()
            if is_slash: await ctx.interaction.followup.send(msg, ephemeral=True)
            else: await ctx.send(msg)
        except Exception as e:
            msg = f"An unexpected error occurred during guild sync for {guild_identifier}."
            print(f"[ERROR] {msg}")
            traceback.print_exc()
            if is_slash: await ctx.interaction.followup.send(msg, ephemeral=True)
            else: await ctx.send(msg)


async def setup(bot: "UiPyBot"):
    await bot.add_cog(SyncCog(bot))