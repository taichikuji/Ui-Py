from typing import Optional, TYPE_CHECKING
from discord import Embed, Interaction, app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from main import UiPy


class HelpCog(commands.Cog):
    def __init__(self, bot: "UiPy"):
        self.bot = bot

    @app_commands.command(
        name="help",
        description="Shows a list of available commands or details about a specific command.",
    )
    async def show_help(self, interaction: Interaction, command_name: Optional[str] = None):
        if command_name is None:
            embed = Embed(
                title="Help",
                description="Here are the available commands:",
                color=self.bot.color,
            )
            for cmd in self.bot.tree.get_commands():
                embed.add_field(
                    name=cmd.name,
                    value=cmd.description or "No description",
                    inline=False,
                )
            await interaction.response.send_message(embed=embed)
        else:
            command = self.bot.tree.get_command(command_name)
            if command:
                embed = Embed(
                    title=f"Help: {command.name}",
                    description=command.description or "No description",
                    color=self.bot.color,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(
                    f":x: Command `{command_name}` not found.", ephemeral=True
                )


async def setup(bot: "UiPy"):
    await bot.add_cog(HelpCog(bot))
