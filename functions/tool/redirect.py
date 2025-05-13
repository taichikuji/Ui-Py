from re import compile
from typing import TYPE_CHECKING, List, Pattern, Tuple
from discord.ext import commands
from discord import Message

if TYPE_CHECKING:
    from main import UiPy


class ReplaceCog(commands.Cog):
    def __init__(self, bot: "UiPy"):
        self.bot = bot
        self.patterns: List[Tuple[Pattern[str], str]] = [
            (compile(r'https?://(?:www\.)?(?:x|twitter)\.com/(?P<user>[^/\s]+)/status/(?P<id>\d+)(?:\?[^ \s]*)?'),
             r'https://fxtwitter.com/\g<user>/status/\g<id>'),
            (compile(r'https?://(?:www\.)?(?:bsky\.social|bsky\.app)/(?P<rest>\S+)'),
             r'https://fxbsky.app/\g<rest>'),
            (compile(r'https?://(?:www\.|vm\.)?tiktok\.com/(?P<rest>\S+)'),
             r'https://vm.tnktok.com/\g<rest>'),
            (compile(r'https?://(?:www\.)?instagram\.com/(?P<rest>\S+)'),
             r'https://instagramez.com/\g<rest>'),
            (compile(r'https?://(?:www\.)?pixiv\.net/(?P<rest>\S+)'),
             r'https://phixiv.net/\g<rest>'),
            (compile(r'https?://(?:www\.)?youtube\.com/shorts/(?P<rest>\S+)'),
             r'https://youtu.be/\g<rest>'),
            (compile(r'https?://(?:www\.)?reddit\.com/(?P<rest>\S+)'),
             r'https://vxreddit.com/\g<rest>'),
        ]


    def replace_text(self, text: str) -> str:
        for pattern, repl in self.patterns:
            text = pattern.sub(repl, text)
        return text


    @commands.Cog.listener()
    async def on_message(self, message: Message) -> None:
        if message.author.bot or not message.content:
            return
        if 'http://' not in message.content and 'https://' not in message.content:
            return
        if (fixed := self.replace_text(message.content)) != message.content:
            await message.channel.send(f"{message.author.mention} sent:\n{fixed}")
            try:
                await message.delete()
            except Exception:
                pass


async def setup(bot: "UiPy"):
    await bot.add_cog(ReplaceCog(bot))
