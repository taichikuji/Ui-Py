from typing import TYPE_CHECKING, Optional, Dict
from re import match, fullmatch, IGNORECASE
from os import environ, makedirs, path
from aiosqlite import connect
from discord import Interaction, app_commands, Embed
from discord.ext import commands

if TYPE_CHECKING:
    from main import UiPy

try:
    STEAM_TOKEN = environ.get("STEAM_TOKEN")
except Exception as e:
    print(f"[ERROR] SteamCog: Failed to load STEAM_TOKEN from environment. {e}")
    STEAM_TOKEN = None

class SteamCog(commands.Cog):
    """Cog for Steam integration, linking accounts and fetching lobby information."""
    def __init__(self, bot: "UiPy"):
        self.bot = bot
        self.steam_api_base = "https://api.steampowered.com"
        self.db_path = "data/ui.sqlite"

    async def cog_load(self):
        await self._init_db()

    async def _init_db(self):
        makedirs(path.dirname(self.db_path), exist_ok=True)
        async with connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS steam_links (
                    discord_id INTEGER PRIMARY KEY,
                    steam_id TEXT NOT NULL
                )
            """)
            await db.commit()

    async def _save_steam_link(self, discord_id: int, steam_id: str):
        async with connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO steam_links (discord_id, steam_id) VALUES (?, ?)",
                (discord_id, steam_id)
            )
            await db.commit()

    async def _get_steam_link(self, discord_id: int) -> Optional[str]:
        async with connect(self.db_path) as db:
            async with db.execute("SELECT steam_id FROM steam_links WHERE discord_id = ?", (discord_id,)) as cursor:
                if row := await cursor.fetchone():
                    return row[0]
                return None

    async def _resolve_steam_id(self, vanity_url_or_id: str) -> Optional[str]:
        if not self.bot.session:
            print("[ERROR] SteamCog: Bot aiohttp session is not initialized.")
            return None
        if not STEAM_TOKEN:
            print("[ERROR] SteamCog: STEAM_TOKEN is not set. Cannot resolve Steam ID.")
            return None
        
        vanity_name = vanity_url_or_id
        # regex to extract vanity name from Steam URL
        if profile_match := match(r"(?:https?://)?steamcommunity\\.com/(?:id/([^/]+)|profiles/(\\d{17}))/?", vanity_url_or_id, IGNORECASE):
            # matches id url
            if id_part := profile_match.group(1):
                vanity_name = id_part
            # matches profiles url
            elif profiles_part := profile_match.group(2):
                return profiles_part
            
        # confirm if input is indeed SteamID64 after extraction
        if fullmatch(r"\\d{17}", vanity_name):
            return vanity_name
        
        try:
            # API call to resolve vanity URL to SteamID64
            async with self.bot.session.get(
                f"{self.steam_api_base}/ISteamUser/ResolveVanityURL/v1/",
                params={"key": STEAM_TOKEN, "vanityurl": vanity_name, "url_type": "1"} # url_type 1 for individual profile
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if (response := data.get("response", {})) and response.get("success") == 1:
                        return response.get("steamid")
                    else:
                        print(f"[INFO] SteamCog: Could not resolve vanity '{vanity_name}'. Message: {response.get('message', 'No message')}")
                        return None 
                else:
                    print(f"[ERROR] SteamCog: Steam API error (ResolveVanityURL) - Status {resp.status}")
                    return None
        except Exception as e:
            print(f"[ERROR] SteamCog: Exception during Steam ID resolution for '{vanity_name}': {e}")
            return None
        
        # Default return if no resolution
        return None

    @app_commands.command( name="link-steam", description="Link your Discord account to a Steam ID or vanity URL." )
    async def link_steam(self, interaction: Interaction, steam_identifier: str):
        await interaction.response.defer(ephemeral=True)
        
        if not STEAM_TOKEN:
            await interaction.followup.send(
                ":x: The bot's Steam API key is not configured. Linking is currently unavailable. Please contact the bot owner."
            )
            return
        if not self.bot.session:
            await interaction.followup.send(
                ":x: The bot's HTTP session is not ready. Please try again later."
            )
            return
        
        steam_id = await self._resolve_steam_id(steam_identifier.strip())

        if not steam_id:
            await interaction.followup.send(
                f":x: Could not resolve '{steam_identifier}' to a valid SteamID64. \\\\n"
                "You can use https://www.steamidfinder.com/ to find your SteamID64 or vanity URL."
                "or you can search on Google 'find steamID64 from Vanity URL' for more information"
            )
            return
        
        await self._save_steam_link(interaction.user.id, steam_id)
        await interaction.followup.send(
            f":white_check_mark: Your Discord account has been successfully linked to SteamID: `{steam_id}`."
        )

    @app_commands.command(
            name="lobby",
            description="Get a Steam lobby invite link if you're in a joinable game."
        )
    async def get_lobby(self, interaction: Interaction):
        await interaction.response.defer()

        if not STEAM_TOKEN:
                await interaction.followup.send(
                    ":x: The bot's Steam API key is not configured. Lobby fetching is unavailable. Please contact the bot owner."
                )
                return
        if not self.bot.session:
                await interaction.followup.send(
                    ":x: The bot's HTTP session is not ready. Please try again later."
                )
                return
        
        if not (linked_steam_id := await self._get_steam_link(interaction.user.id)):
            await interaction.followup.send(
                ":information_source: Your Steam account is not linked. "
                "Please use the `/link <your_steam_id_or_vanity_name>` command first."
            )
            return
        
        try:
            async with self.bot.session.get(
                f"{self.steam_api_base}/ISteamUser/GetPlayerSummaries/v2/",
                params={"key": STEAM_TOKEN, "steamids": linked_steam_id}
            ) as resp:
                if resp.status != 200:
                    print(f"[ERROR] SteamCog: Steam API error (GetPlayerSummaries) - Status {resp.status}, Response: {await resp.text()}")
                    await interaction.followup.send(
                        f":x: Error fetching your player summary from Steam (HTTP {resp.status}). "
                        "Your profile might be private or an API error occurred."
                    )
                    return
                data = await resp.json()
            
            if not (players := data.get("response", {}).get("players", [])):
                await interaction.followup.send(
                    ":x: Could not retrieve your player summary from Steam. "
                    "Ensure your Steam profile is public and you've linked the correct ID."
                )
                return
            
            player_info = players[0]
            game_name = player_info.get("gameextrainfo", "Unknown Game")

            if not (app_id := player_info.get("gameid")):
                await interaction.followup.send(
                    ":x: You are not currently in a joinable game. "
                    "Please start a game and try again."
                )
                return
            
            lobby_id = player_info.get("lobbysteamid")
            if not lobby_id or lobby_id == "0":
                await interaction.followup.send(
                    f":information_source: You are currently playing **{game_name}** (AppID: `{app_id}`), "
                    "but you don't seem to be in a joinable lobby, or your lobby details are private."
                )
                return
            
            lobby_url = f"https://taichikuji.github.io/redirector/?url=steam://joinlobby/{app_id}/{lobby_id}/{linked_steam_id}"

            embed = Embed(
                title=f"Steam Lobby Invite for {interaction.user.display_name}",
                description=f"Join {interaction.user.mention}'s lobby for **{game_name}**!",
                color=self.bot.color
            )
            embed.add_field(name="Lobby Link", value=f"`{lobby_url}`", inline=False)
            embed.set_footer(text="Clicking this link requires Steam to be installed and running.")
            if interaction.user.display_avatar:
                embed.set_thumbnail(url=interaction.user.display_avatar.url)
            
            await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"[ERROR] SteamCog - get_lobby command failed for user {interaction.user.id} (SteamID: {linked_steam_id}): {e}")
            await interaction.followup.send(
                ":x: An unexpected error occurred while trying to fetch your lobby information."
            )

async def setup(bot: "UiPy"):
    if not STEAM_TOKEN:
        raise commands.ExtensionFailed(name="functions.tool.steam", original=RuntimeError("STEAM_TOKEN environment variable is not set."))
    await bot.add_cog(SteamCog(bot))