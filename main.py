from discord import Intents, Activity, ActivityType
from discord.ext import commands
from glob import iglob
from os import sep
from aiohttp import ClientSession

try:
    from config import TOKEN
except ImportError:
    print("[ERROR] Failed to import TOKEN from config.py")

class UiPy(commands.AutoShardedBot):
    def __init__(self):
        super().__init__(
            description="Do you want, coffee, or tea?",
            command_prefix=commands.when_mentioned,
            case_insensitive=True,
            intents=Intents.default(),
        )
        self._bot_token = TOKEN
        self.session: ClientSession | None = None
        self.color = 0xFF3351
        self.owner_id = 199632174603829249 # https://discordid.taichikuji.org?id=199632174603829249
        print("[INFO] super().__init__() finished")

    async def setup_hook(self):
        self.session = ClientSession()
        print("[INFO] ClientSession created")
        for functions in iglob("functions/**/*.py", recursive=True):
            module = functions.replace(".py", "").replace(sep, ".")
            try:
                await self.load_extension(module)
                print(f"[INFO] Loaded {module}")
            except ImportError:
                print(f"[ERROR] Extension import failure! [{module}]")
            except commands.errors.ExtensionFailed:
                print(f"[ERROR] Extension failed! [{module}]")
            except Exception:
                print(f"[ERROR] Unexpected exception! [{module}]")

    async def on_ready(self):
        display = Activity(name="Ping me, or use Slash Commands!", type=ActivityType.listening)
        await self.change_presence(activity=display)
        print(f"[INFO] Ui Online! - {self.user.name} {self.user.id}")

    async def close(self):
        try:
            await self.session.close()
            await super().close()
            print("[INFO] Session closed!")
        except Exception as e:
            print(f"[ERROR] Failed to close aiohttp session! {E52} - {e}")
            raise

    def run(self, **kwargs):
        try:
            super().run(self._bot_token, reconnect=True, **kwargs)
        except TypeError:
            print("[ERROR] An unexpected keyword argument was passed! {E59}")
            return TypeError
        except Exception:
            print("[ERROR] An exception occurred! {E62}")

if __name__ == "__main__":
    print("[INFO] Starting Ui-Py...")
    UiPy().run()