from os import makedirs, path
from typing import TYPE_CHECKING

from aiosqlite import connect
from discord import (ButtonStyle, Embed, Interaction, Member,
                     PermissionOverwrite, VoiceChannel, VoiceState,
                     app_commands)
from discord.ext import commands
from discord.ui import Button, Modal, TextInput, View, button

if TYPE_CHECKING:
    from main import UiPy


class VoiceControlView(View):
    def __init__(self, channel: VoiceChannel, owner: Member):
        super().__init__(timeout=None)
        self.channel = channel
        self.owner = owner

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user != self.owner:
            await interaction.response.send_message(
                ":x: You don't own this channel!", ephemeral=True
            )
            return False
        return True

    @button(label="Lock", style=ButtonStyle.red)
    async def lock_channel(self, interaction: Interaction, button: Button) -> None:
        overwrite = self.channel.overwrites_for(interaction.guild.default_role)
        overwrite.connect = False
        await self.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)

        button.disabled = True
        self.children[1].disabled = False
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(":lock: Channel locked.", ephemeral=True)

    @button(label="Unlock", style=ButtonStyle.green, disabled=True)
    async def unlock_channel(self, interaction: Interaction, button: Button) -> None:
        overwrite = self.channel.overwrites_for(interaction.guild.default_role)
        overwrite.connect = None
        await self.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)

        button.disabled = True
        self.children[0].disabled = False
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(":unlock: Channel unlocked.", ephemeral=True)

    @button(label="Rename", style=ButtonStyle.primary)
    async def rename_channel(self, interaction: Interaction, button: Button) -> None:
        await interaction.response.send_modal(RenameModal(self.channel))


class RenameModal(Modal, title="Rename Channel"):
    name = TextInput(label="New Name", placeholder="My Cool Channel", min_length=1, max_length=100)

    def __init__(self, channel: VoiceChannel):
        super().__init__()
        self.channel = channel

    async def on_submit(self, interaction: Interaction) -> None:
        await self.channel.edit(name=self.name.value)
        await interaction.response.send_message(
            f":white_check_mark: Renamed to **{self.name.value}**", ephemeral=True
        )


class LobbyCog(commands.Cog):
    """Cog for dynamic voice channel creation and cleanup."""
    def __init__(self, bot: "UiPy"):
        self.bot = bot
        self.db_path = "data/ui.sqlite"
        self.active_channels: set[int] = set()
        self.generators: dict[int, int] = {}  # guild_id -> channel_id

    async def cog_load(self):
        await self._init_db()
        await self._load_generators()
        await self._load_lobby_active()

    async def _init_db(self):
        makedirs(path.dirname(self.db_path), exist_ok=True)
        async with connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS lobby_generator (
                    guild_id INTEGER PRIMARY KEY,
                    channel_id INTEGER NOT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS lobby_active (
                    channel_id INTEGER PRIMARY KEY
                )
            """)
            await db.commit()

    async def _load_generators(self):
        async with connect(self.db_path) as db:
            async with db.execute("SELECT guild_id, channel_id FROM lobby_generator") as cursor:
                self.generators = {row[0]: row[1] async for row in cursor}

    async def _load_lobby_active(self):
        async with connect(self.db_path) as db:
            async with db.execute("SELECT channel_id FROM lobby_active") as cursor:
                self.active_channels = {row[0] async for row in cursor}

    async def _save_generator(self, guild_id: int, channel_id: int):
        async with connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO lobby_generator (guild_id, channel_id) VALUES (?, ?)",
                (guild_id, channel_id),
            )
            await db.commit()
        self.generators[guild_id] = channel_id

    async def _remove_generator(self, guild_id: int):
        async with connect(self.db_path) as db:
            await db.execute("DELETE FROM lobby_generator WHERE guild_id = ?", (guild_id,))
            await db.commit()
        self.generators.pop(guild_id, None)

    @app_commands.command(
        name="set",
        description="Set or clear the voice channel that creates dynamic lobbies.",
    )
    @app_commands.describe(channel="The voice channel to use as a lobby generator. Leave empty to clear.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_channels=True)
    async def set_generator(self, interaction: Interaction, channel: VoiceChannel | None = None) -> None:
        if channel is None:
            if interaction.guild_id not in self.generators:
                await interaction.response.send_message(
                    ":x: No lobby generator is set for this server.", ephemeral=True
                )
                return
            await self._remove_generator(interaction.guild_id)
            await interaction.response.send_message(
                ":white_check_mark: Lobby generator cleared.", ephemeral=True
            )
        else:
            await self._save_generator(interaction.guild_id, channel.id)
            await interaction.response.send_message(
                f":white_check_mark: **{channel.name}** is now the lobby generator.", ephemeral=True
            )

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState) -> None:
        if before.channel == after.channel:
            return

        if before.channel and before.channel.id in self.active_channels:
            if len(before.channel.members) == 0:
                await self._delete_lobby(before.channel)

        if after.channel and after.channel.id == self.generators.get(after.channel.guild.id):
            await self._create_lobby(member, after.channel)

    async def _create_lobby(self, member: Member, generator: VoiceChannel) -> None:
        guild = member.guild
        overwrites = {
            guild.default_role: PermissionOverwrite(connect=True),
            member: PermissionOverwrite(connect=True, move_members=True, manage_channels=True),
        }

        new_channel = await guild.create_voice_channel(
            name=f"{member.display_name}'s Lobby",
            category=generator.category,
            overwrites=overwrites,
            reason=f"Dynamic channel for {member.display_name}",
        )

        try:
            await member.move_to(new_channel)
            self.active_channels.add(new_channel.id)
            async with connect(self.db_path) as db:
                await db.execute("INSERT INTO lobby_active (channel_id) VALUES (?)", (new_channel.id,))
                await db.commit()

            embed = Embed(
                title=":control_knobs: Voice Control",
                description=f"Welcome to your temporary channel, {member.mention}.\nUse the buttons below to manage it.",
                color=self.bot.color,
            )
            await new_channel.send(embed=embed, view=VoiceControlView(new_channel, member))
        except Exception as e:
            print(f"[ERROR] LobbyCog: Failed to set up lobby for {member.display_name}: {e}")
            self.active_channels.discard(new_channel.id)
            await new_channel.delete()

    async def _delete_lobby(self, channel: VoiceChannel) -> None:
        try:
            await channel.delete(reason="Dynamic channel empty")
        except Exception:
            pass
        self.active_channels.discard(channel.id)
        async with connect(self.db_path) as db:
            await db.execute("DELETE FROM lobby_active WHERE channel_id = ?", (channel.id,))
            await db.commit()


async def setup(bot: "UiPy"):
    """Add the LobbyCog to the bot."""
    await bot.add_cog(LobbyCog(bot))
