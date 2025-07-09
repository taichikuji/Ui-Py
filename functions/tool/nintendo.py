from typing import TYPE_CHECKING, Optional
from re import fullmatch
from os import makedirs, path
from aiosqlite import connect
from discord import Interaction, app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from main import UiPy


class NintendoCog(commands.Cog):
    """Cog for Nintendo Switch Friend Code linking and sharing."""
    def __init__(self, bot: "UiPy"):
        self.bot = bot
        self.db_path = "data/ui.sqlite"

    async def cog_load(self):
        await self._init_db()

    async def _init_db(self):
        makedirs(path.dirname(self.db_path), exist_ok=True)
        async with connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS nintendo_links (
                    discord_id INTEGER PRIMARY KEY,
                    nintendo_id TEXT NOT NULL
                )
            """)
            await db.commit()

    async def _save_nintendo_link(self, discord_id: int, nintendo_id: str):
        async with connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO nintendo_links (discord_id, nintendo_id) VALUES (?, ?)",
                (discord_id, nintendo_id)
            )
            await db.commit()

    async def _get_nintendo_link(self, discord_id: int) -> Optional[str]:
        async with connect(self.db_path) as db:
            async with db.execute("SELECT nintendo_id FROM nintendo_links WHERE discord_id = ?", (discord_id,)) as cursor:
                if row := await cursor.fetchone():
                    return row[0]
                return None

    def _validate_nintendo_id(self, nintendo_id: str) -> bool:
        """Validate Nintendo Switch Friend Code format: SW-####-####-####"""
        return bool(fullmatch(r"SW-\d{4}-\d{4}-\d{4}", nintendo_id.upper()))

    @app_commands.command(name="link-nintendo", description="Link your Discord account to a Nintendo Switch Friend Code.")
    async def link_nintendo(self, interaction: Interaction, nintendo_id: str):
        await interaction.response.defer(ephemeral=True)

        # Clean friend code input
        nintendo_id = nintendo_id.strip().upper()
        
        if not self._validate_nintendo_id(nintendo_id):
            await interaction.followup.send(
                ":x: Invalid Friend Code format. Please use the format: `SW-####-####-####`\n"
                "Example: `SW-1234-5678-9012`"
            )
            return
        
        await self._save_nintendo_link(interaction.user.id, nintendo_id)
        await interaction.followup.send(
            f":white_check_mark: Your Discord account has been successfully linked to Nintendo Friend Code: `{nintendo_id}`."
        )

    @app_commands.command(name="share", description="Share your linked Nintendo Switch Friend Code.")
    async def share_nintendo(self, interaction: Interaction):
        await interaction.response.defer()
        
        if not (linked_nintendo_id := await self._get_nintendo_link(interaction.user.id)):
            await interaction.followup.send(
                ":information_source: You haven't linked a Nintendo Switch Friend Code yet. "
                "Please use `/link <your_nintendo_id>` command first."
            )
            return
        
        await interaction.followup.send(
            f"Here's my Nintendo Switch Friend ID! `{linked_nintendo_id}`"
        )


async def setup(bot: "UiPy"):
    await bot.add_cog(NintendoCog(bot))