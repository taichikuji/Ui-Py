from os import environ
from typing import TYPE_CHECKING

from discord import (ButtonStyle, Embed, Interaction, Member,
                     PermissionOverwrite, VoiceChannel, VoiceState)
from discord.ext import commands
from discord.ui import Button, Modal, TextInput, View, button

if TYPE_CHECKING:
    from main import UiPy

try:
    VOICE_CHANNEL_ID = environ.get("VOICE_CHANNEL_ID")
except Exception as e:
    print(f"[ERROR] LobbyCog: Failed to load VOICE_CHANNEL_ID from environment. {e}")
    VOICE_CHANNEL_ID = None

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
        self.active_channels: set[int] = set()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState) -> None:
        if after.channel and after.channel.id == int(VOICE_CHANNEL_ID):
            await self._create_lobby(member, after.channel)

        if before.channel and before.channel.id in self.active_channels:
            if len(before.channel.members) == 0:
                await self._delete_lobby(before.channel)

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

            embed = Embed(
                title=":control_knobs: Voice Control",
                description=f"Welcome to your temporary channel, {member.mention}.\nUse the buttons below to manage it.",
                color=self.bot.color,
            )
            await new_channel.send(embed=embed, view=VoiceControlView(new_channel, member))
        except Exception as e:
            print(f"[ERROR] LobbyCog: Failed to set up lobby for {member.display_name}: {e}")
            await new_channel.delete()

    async def _delete_lobby(self, channel: VoiceChannel) -> None:
        try:
            await channel.delete(reason="Dynamic channel empty")
        except Exception:
            pass
        self.active_channels.discard(channel.id)


async def setup(bot: "UiPy"):
    """Add the LobbyCog to the bot."""
    if not VOICE_CHANNEL_ID:
        raise commands.ExtensionFailed(
            name="functions.tool.lobby",
            original=RuntimeError("VOICE_CHANNEL_ID environment variable is not set."),
        )
    await bot.add_cog(LobbyCog(bot))