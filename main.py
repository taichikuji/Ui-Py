from glob import iglob
from os import sep, environ
from discord import Intents, Activity, ActivityType
from discord.ext import commands
from aiohttp import ClientSession

TOKEN = environ.get("TOKEN")
if TOKEN is None:
    raise EnvironmentError("[ERROR] TOKEN environment variable not set")


class UiPy(commands.AutoShardedBot):
    def __init__(self):
        intents = Intents.default()
        intents.message_content = True
        super().__init__(
            description="Do you want coffee, or tea?",
            command_prefix=commands.when_mentioned,
            case_insensitive=True,
            intents=intents,
        )
        self._bot_token = TOKEN
        self.session: ClientSession | None = None
        self.color = 0xFF3351

    async def setup_hook(self):
        self.session = ClientSession()
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
        assert self.user is not None, "self.user is None in on_ready!"
        display = Activity(
            name="Ping me, or use Slash Commands!", type=ActivityType.listening
        )
        await self.change_presence(activity=display)
        print(f"[INFO] Ui Online! - {self.user.name} {self.user.id}")

    async def close(self):
        try:
            if self.session is not None:
                await self.session.close()
            await super().close()
            print("[INFO] Session closed!")
        except Exception as e:
            print(f"[ERROR] Failed to close aiohttp session - {e}")
            raise

    def run(self, *args, **kwargs):
        try:
            super().run(str(self._bot_token), reconnect=True, *args, **kwargs)
        except TypeError:
            print("[ERROR] An unexpected keyword argument was passed!")
        except Exception as e:
            print(f"[ERROR] An exception occurred: {e}")


if __name__ == "__main__":
    print("[INFO] Starting Ui-Py...")
    UiPy().run()
