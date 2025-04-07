from time import localtime, strftime
from typing import TYPE_CHECKING
from discord.ext import commands

if TYPE_CHECKING:
    from main import UiPyBot

class LoaderCog(commands.Cog):
    def __init__(self, bot: 'UiPyBot'):
        self.bot = bot

    @commands.hybrid_command(
        name="load",
        description="Load an extension."
    )
    @commands.is_owner()
    async def load(self, ctx: commands.Context, extension: str):
        try:
            await self.bot.load_extension(f"functions.{extension}")
            print(f"[INFO] {extension} loaded at {strftime('%A, %d %b %Y, %I:%M:%S %p', localtime())}.")
            description = f":white_check_mark: Loaded extension '{extension}' successfully."
        except commands.ExtensionAlreadyLoaded:
            description = f":information_source: Extension '{extension}' is already loaded."
        except commands.ExtensionNotFound:
            description = f":x: Extension '{extension}' not found."
        except commands.ExtensionFailed:
            description = f":x: Extension '{extension}' failed to load due to an error."
        except commands.NoEntryPointError:
            description = f":x: Extension '{extension}' does not have a setup function."

        if ctx.interaction:
            await ctx.interaction.response.send_message(description, ephemeral=True)
        else:
            await ctx.send(description)

    @commands.hybrid_command(
        name="unload",
        description="Unload an extension."
    )
    @commands.is_owner()
    async def unload(self, ctx: commands.Context, extension: str):
        try:
            await self.bot.unload_extension(f"functions.{extension}")
            description = f":white_check_mark: Unloaded extension '{extension}' successfully."
        except commands.ExtensionNotLoaded:
            description = f":information_source: Extension '{extension}' is not loaded."

        if ctx.interaction:
            await ctx.interaction.response.send_message(description, ephemeral=True)
        else:
            await ctx.send(description)

    @commands.hybrid_command(
        name="reload",
        description="Reload an extension."
    )
    @commands.is_owner()
    async def reload(self, ctx: commands.Context, extension: str):
        try:
            await self.bot.reload_extension(f"functions.{extension}")
            print(f"[INFO] {extension} reloaded at {strftime('%A, %d %b %Y, %I:%M:%S %p', localtime())}.")
            description = f":white_check_mark: Reloaded extension '{extension}' successfully."
        except commands.ExtensionNotLoaded:
            description = f":x: Extension '{extension}' is not loaded."
        except commands.ExtensionNotFound:
            description = f":x: Extension '{extension}' not found."
        except commands.ExtensionFailed:
            description = f":x: Extension '{extension}' failed to reload due to an error."
        except commands.NoEntryPointError:
            description = f":x: Extension '{extension}' does not have a setup function."

        if ctx.interaction:
            await ctx.interaction.response.send_message(description, ephemeral=True)
        else:
            await ctx.send(description)
    
    @load.error
    @unload.error
    @reload.error
    async def command_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            description = ":x: You need to specify the module to load/unload/reload. Usage: `load <folder.file>`, `unload <folder.file>`, `reload <folder.file>`."
        else:
            description = str(error)

        if ctx.interaction:
            await ctx.interaction.response.send_message(description, ephemeral=True)
        else:
            await ctx.send(description)


async def setup(bot: 'UiPyBot'):
    await bot.add_cog(LoaderCog(bot))
