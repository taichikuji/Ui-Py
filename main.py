from glob import iglob
from os import sep
from discord import Intents, Client, app_commands, Interaction,errors
from discord.ext import commands
from config import TOKEN

intents = Intents.default()
intents.message_content = True

client = Client(intents=intents)
tree = app_commands.CommandTree(client)

@client.event
async def on_ready():
    print(f'[INFO] on_ready process [{client.user}]')
    await tree.sync()
    print('[INFO] Slash commands synced')

@tree.command(name="hello", description="Hello world command")
async def hello_command(interaction: Interaction):
    await interaction.response.send_message("Reply send! Hello world!")

try:
    client.run(TOKEN)
except errors.LoginFailure:
    print("[ERROR] An error occured related to Login. {E26}")
except Exception as e:
    print("[ERROR] An error occured. {str(e)} {E28}")

