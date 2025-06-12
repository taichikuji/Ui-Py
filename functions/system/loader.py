from time import localtime, strftime
from typing import TYPE_CHECKING
from discord.ext import commands
from discord import app_commands, Interaction

if TYPE_CHECKING:
    from main import UiPy


class LoaderCog(commands.Cog):
    """Cog for loading, unloading, and reloading extensions."""
    def __init__(self, bot: "UiPy"):
        self.bot = bot

    @app_commands.command(
        name="load",
        description="Load an extension."
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def load(self, interaction: Interaction, extension: str) -> None:
        """Load a bot extension."""
        try:
            await self.bot.load_extension(f"functions.{extension}")
            print(
                f"[INFO] LoaderCog: {extension} loaded at {strftime('%A, %d %b %Y, %I:%M:%S %p', localtime())}."
            )
            description = (
                f":white_check_mark: Loaded extension '{extension}' successfully."
            )
        except commands.ExtensionAlreadyLoaded:
            description = (
                f":information_source: Extension '{extension}' is already loaded."
            )
        except commands.ExtensionNotFound:
            description = f":x: Extension '{extension}' not found."
        except commands.ExtensionFailed:
            description = f":x: Extension '{extension}' failed to load due to an error."
        except commands.NoEntryPointError:
            description = f":x: Extension '{extension}' does not have a setup function."
        except Exception as e:
            description = f":x: An unexpected error occurred: {e}"
            print(f"[ERROR] LoaderCog: {description}")
        await interaction.response.send_message(description, ephemeral=True)

    @app_commands.command(
        name="unload",
        description="Unload an extension."
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def unload(self, interaction: Interaction, extension: str) -> None:
        """Unload a bot extension."""
        try:
            await self.bot.unload_extension(f"functions.{extension}")
            description = (
                f":white_check_mark: Unloaded extension '{extension}' successfully."
            )
        except commands.ExtensionNotLoaded:
            description = f":information_source: Extension '{extension}' is not loaded."
        except Exception as e:
            description = f":x: An unexpected error occurred: {e}"
            print(f"[ERROR] LoaderCog: {description}")
        await interaction.response.send_message(description, ephemeral=True)

    @app_commands.command(
        name="reload",
        description="Reload an extension."
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def reload(self, interaction: Interaction, extension: str) -> None:
        """Reload a bot extension."""
        try:
            await self.bot.reload_extension(f"functions.{extension}")
            print(
                f"[INFO] LoaderCog: {extension} reloaded at {strftime('%A, %d %b %Y, %I:%M:%S %p', localtime())}."
            )
            description = (
                f":white_check_mark: Reloaded extension '{extension}' successfully."
            )
        except commands.ExtensionNotLoaded:
            description = f":x: Extension '{extension}' is not loaded."
        except commands.ExtensionNotFound:
            description = f":x: Extension '{extension}' not found."
        except commands.ExtensionFailed:
            description = (
                f":x: Extension '{extension}' failed to reload due to an error."
            )
        except commands.NoEntryPointError:
            description = f":x: Extension '{extension}' does not have a setup function."
        except Exception as e:
            description = f":x: An unexpected error occurred: {e}"
            print(f"[ERROR] LoaderCog: {description}")
        await interaction.response.send_message(description, ephemeral=True)


async def setup(bot: "UiPy"):
    """Add the LoaderCog to the bot."""
    await bot.add_cog(LoaderCog(bot))
