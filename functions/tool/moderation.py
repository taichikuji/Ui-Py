from asyncio import sleep
from math import ceil
from typing import TYPE_CHECKING, Optional

from discord import (ButtonStyle, Embed, Interaction, Member, Message,
                     PermissionOverwrite, app_commands)
from discord.ext import commands
from discord.ui import Button, View, button

if TYPE_CHECKING:
    from main import UiPy


class VotekickView(View):
    def __init__(self, required_votes: int, author: Member, target: Member):
        super().__init__(timeout=60.0)
        self.required_votes = required_votes
        self.author = author
        self.target = target
        self.yes_votes = set()
        self.no_votes = set()
        self.message: Optional[Message] = None

    async def on_timeout(self):
        if self.message:
            for item in self.children:
                if isinstance(item, Button):
                    item.disabled = True
            
            embed = self.message.embeds[0]
            embed.title = "Votekick Timed Out"
            embed.description = f"The votekick against {self.target.mention} timed out."
            embed.color = 0xff0000  # Red
            await self.message.edit(embed=embed, view=self)

    async def update_embed(self, interaction: Interaction):
        if self.message:
            embed = self.message.embeds[0]
            embed.set_field_at(1, name="Votes", value=f"Yes: {len(self.yes_votes)}\nNo: {len(self.no_votes)}", inline=True)
            await interaction.response.edit_message(embed=embed, view=self)

    @button(label="Yes", style=ButtonStyle.green)
    async def yes_button(self, interaction: Interaction, button: Button):
        if interaction.user.id in self.yes_votes or interaction.user.id in self.no_votes:
            await interaction.response.send_message("You have already voted.", ephemeral=True)
            return

        self.yes_votes.add(interaction.user.id)
        await self.update_embed(interaction)

        if len(self.yes_votes) >= self.required_votes:
            self.stop()
            if self.message:
                for item in self.children:
                    if isinstance(item, Button):
                        item.disabled = True
                
                embed = self.message.embeds[0]
                embed.title = "Votekick Successful"
                embed.description = f":information_source: {self.target.mention} has been kicked from the voice channel."
                embed.color = 0x00ff00 # Green
                await self.message.edit(embed=embed, view=self)

            if self.target.voice and self.target.voice.channel:
                original_channel = self.target.voice.channel
                await self.target.move_to(None, reason="Votekick successful.")
                
                overwrite = PermissionOverwrite()
                overwrite.connect = False
                await original_channel.set_permissions(self.target, overwrite=overwrite)
                
                await sleep(60)
                
                await original_channel.set_permissions(self.target, overwrite=None)


    @button(label="No", style=ButtonStyle.red)
    async def no_button(self, interaction: Interaction, button: Button):
        if interaction.user.id in self.yes_votes or interaction.user.id in self.no_votes:
            await interaction.response.send_message("You have already voted.", ephemeral=True)
            return

        self.no_votes.add(interaction.user.id)
        await self.update_embed(interaction)


class ModerationCog(commands.Cog):
    """Cog for moderation commands."""
    def __init__(self, bot: "UiPy"):
        self.bot = bot
        self.votekicks = {}

    @app_commands.command(name="votekick", description="Start a vote to kick a user from the current voice channel.")
    async def votekick(self, interaction: Interaction, member: Member):
        if not interaction.guild:
            await interaction.response.send_message(":x: This command can only be used in a server.", ephemeral=True)
            return

        author = interaction.user
        if not isinstance(author, Member):
            await interaction.response.send_message(":x: You must be a member of this server to use this command.", ephemeral=True)
            return

        if not author.voice or not author.voice.channel:
            await interaction.response.send_message(":x: You must be in a voice channel to start a votekick.", ephemeral=True)
            return

        if not member.voice or member.voice.channel != author.voice.channel:
            await interaction.response.send_message(f":x: {member.mention} is not in your voice channel.", ephemeral=True)
            return

        if member.id == author.id:
            await interaction.response.send_message(":x: You cannot votekick yourself.", ephemeral=True)
            return

        if member.bot:
            await interaction.response.send_message(":x: You cannot votekick a bot.", ephemeral=True)
            return

        if member.id in self.votekicks:
            await interaction.response.send_message(f":x: A votekick for {member.mention} is already in progress.", ephemeral=True)
            return

        voice_channel = author.voice.channel
        members_in_vc = [m for m in voice_channel.members if not m.bot]
        required_votes = ceil(len(members_in_vc) * 2 / 3)

        embed = Embed(
            title=f"Votekick for {member.display_name}",
            description=f":information_source: {author.mention} has started a votekick against {member.mention}.",
            color=self.bot.color
        )
        embed.add_field(name="Required Votes", value=str(required_votes), inline=True)
        embed.add_field(name="Votes", value="Yes: 0\nNo: 0", inline=True)
        embed.set_footer(text="The vote will end in 60 seconds.")

        view = VotekickView(required_votes, author, member)
        
        await interaction.response.send_message(embed=embed, view=view)
        message = await interaction.original_response()
        view.message = message
        self.votekicks[member.id] = message

        await view.wait()
        self.votekicks.pop(member.id, None)


async def setup(bot: "UiPy"):
    await bot.add_cog(ModerationCog(bot))
