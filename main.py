try:
    from config import *
except:
    print("Unable to find config.py")
    exit()

from config import token
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import json
import os
import aiohttp
import io
import asyncio
import sys
from pystyle import Colors, Colorate

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

BACKUPS_FILE = "backups.json"
MAX_MESSAGES = 500

try:
    if os.path.exists(BACKUPS_FILE):
        with open(BACKUPS_FILE, "r") as f:
            backups = json.load(f)
    else:
        backups = {}
except (json.JSONDecodeError, FileNotFoundError):
    backups = {}

def save_backups():
    with open(BACKUPS_FILE, "w") as f:
        json.dump(backups, f, indent=2)

if not backups:
    save_backups()

class BackupView(discord.ui.View):
    def __init__(self, backup_data):
        super().__init__(timeout=60)
        self.backup_data = backup_data

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        temp_channel = None
        try:

            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.guild.me: discord.PermissionOverwrite(
                    read_messages=True,
                    manage_channels=True,
                    send_messages=True
                )
            }
            temp_channel = await interaction.guild.create_text_channel("backup-restore-log", overwrites=overwrites)

            temp_channel_id = temp_channel.id

            # Perform restoration
            await self.clean_existing_structure(interaction.guild)
            await self.restore_guild_details(interaction.guild)
            await self.restore_server_structure(interaction.guild)

            temp_channel = interaction.guild.get_channel(temp_channel_id)
            if temp_channel:
                await temp_channel.send(
                    "✅ Restoration complete! This channel will self-destruct in 30 seconds...",
                    delete_after=30
                )
                await asyncio.sleep(35)  
                await temp_channel.delete()
            else:
                await interaction.user.send("✅ Restoration complete! (Temporary channel was removed prematurely)")

        except Exception as e:
            error_msg = f"❌ Critical error: {str(e)}"
            try:
                
                if temp_channel and interaction.guild.get_channel(temp_channel.id):
                    await temp_channel.send(error_msg, delete_after=10)
                    await temp_channel.delete(delay=10)
                await interaction.user.send(error_msg)
            except:
                await interaction.user.send(error_msg)

    async def clean_existing_structure(self, guild):
        temp_channel = await guild.create_text_channel("temp-backup-channel", overwrites={
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, manage_channels=True)
        })
        for channel in guild.channels:
            if channel.id != temp_channel.id and not isinstance(channel, discord.CategoryChannel):
                try:
                    await channel.delete()
                except:
                    pass
        for category in guild.categories:
            try:
                await category.delete()
            except:
                pass
        return temp_channel

    async def restore_guild_details(self, guild):
        async with aiohttp.ClientSession() as session:
            await guild.edit(name=self.backup_data['guild_name'])
            if self.backup_data['guild_icon']:
                async with session.get(self.backup_data['guild_icon']) as resp:
                    if resp.status == 200:
                        await guild.edit(icon=await resp.read())

    async def restore_server_structure(self, guild):
        category_mapping = {}
        channel_mapping = {}
        for channel_data in self.backup_data["channels"]:
            if channel_data["type"] == "category":
                new_category = await guild.create_category(channel_data["name"], position=channel_data["position"])
                category_mapping[channel_data["id"]] = new_category.id
        for channel_data in self.backup_data["channels"]:
            if channel_data["type"] != "category":
                parent_id = category_mapping.get(channel_data.get("category"))
                parent = guild.get_channel(parent_id) if parent_id else None
                if channel_data["type"] == "text":
                    new_channel = await guild.create_text_channel(
                        name=channel_data["name"],
                        category=parent,
                        position=channel_data["position"],
                        topic=channel_data.get("topic", "")
                    )
                    channel_mapping[channel_data["id"]] = new_channel.id
                    await self.restore_channel_content(new_channel, channel_data["id"])
                elif channel_data["type"] == "voice":
                    await guild.create_voice_channel(
                        name=channel_data["name"],
                        category=parent,
                        position=channel_data["position"]
                    )
        await self.restore_roles(guild)
        await self.restore_emojis_and_stickers(guild)

    async def restore_channel_content(self, channel, original_id):
        if str(original_id) in self.backup_data["messages"]:
            for msg in self.backup_data["messages"][str(original_id)]:
                try:
                    files = []
                    async with aiohttp.ClientSession() as session:
                        for att in msg.get("attachments", []):
                            async with session.get(att["url"]) as resp:
                                if resp.status == 200:
                                    files.append(discord.File(io.BytesIO(await resp.read()), filename=att["filename"]))
                    await channel.send(
                        content=f"**{msg['author']}** ({msg['timestamp']}):\n{msg['content']}",
                        embeds=[discord.Embed.from_dict(e) for e in msg["embeds"]],
                        files=files
                    )
                except:
                    pass

    async def restore_roles(self, guild):
        for role_data in self.backup_data["roles"]:
            try:
                await guild.create_role(
                    name=role_data["name"],
                    permissions=discord.Permissions(role_data["permissions"]),
                    color=discord.Color.from_str(role_data["color"]),
                    hoist=role_data["hoist"]
                )
            except:
                pass

    async def restore_emojis_and_stickers(self, guild):
        async with aiohttp.ClientSession() as session:
            for emoji_data in self.backup_data["emojis"]:
                try:
                    await guild.create_custom_emoji(
                        name=emoji_data["name"],
                        image=bytes(emoji_data["data"])
                    )
                except Exception as e:
                    print(f"Emoji Error: {str(e)}")
            
            for sticker_data in self.backup_data["stickers"]:
                try:
                    file = discord.File(
                        io.BytesIO(bytes(sticker_data["data"])),
                        filename=f"{sticker_data['name']}.png"
                    )
                    await guild.create_sticker(
                        name=sticker_data["name"],
                        description=sticker_data["description"],
                        emoji=sticker_data["emoji"],
                        file=file
                    )
                except Exception as e:
                    print(f"Sticker Error: {str(e)}")

async def backup_guild(guild: discord.Guild):
    backup = {
        "guild_name": guild.name,
        "guild_icon": str(guild.icon.url) if guild.icon else None,
        "timestamp": str(datetime.now()),
        "roles": [],
        "channels": [],
        "emojis": [],
        "stickers": [],
        "messages": {}
    }
    backup["roles"] = [{
        "name": role.name,
        "permissions": role.permissions.value,
        "color": str(role.color),
        "hoist": role.hoist,
        "position": role.position
    } for role in guild.roles[1:]]
    for channel in guild.channels:
        channel_data = {
            "id": str(channel.id),
            "name": channel.name,
            "type": str(channel.type),
            "position": channel.position,
            "category": str(channel.category.id) if channel.category else None,
            "topic": channel.topic if isinstance(channel, discord.TextChannel) else None
        }
        backup["channels"].append(channel_data)
    for channel in guild.text_channels:
        try:
            messages = []
            async for message in channel.history(limit=MAX_MESSAGES):
                messages.append({
                    "content": message.content,
                    "author": str(message.author),
                    "embeds": [embed.to_dict() for embed in message.embeds],
                    "timestamp": str(message.created_at),
                    "attachments": [{"url": att.url, "filename": att.filename} for att in message.attachments]
                })
            backup["messages"][str(channel.id)] = messages
        except:
            pass
    async with aiohttp.ClientSession() as session:
        for emoji in guild.emojis:
            async with session.get(str(emoji.url)) as resp:
                if resp.status == 200:
                    backup["emojis"].append({"name": emoji.name, "data": list(await resp.read()), "animated": emoji.animated})
        for sticker in await guild.fetch_stickers():
            async with session.get(sticker.url) as resp:
                if resp.status == 200:
                    backup["stickers"].append({
                        "name": sticker.name,
                        "data": list(await resp.read()),
                        "description": sticker.description,
                        "emoji": sticker.emoji
                    })
    return backup

@bot.tree.command(name="backup", description="Create server backup")
@app_commands.checks.has_permissions(administrator=True)
async def backup_command(interaction: discord.Interaction):
    await interaction.response.defer()
    backup_data = await backup_guild(interaction.guild)
    backup_id = f"{interaction.guild.id}-{datetime.now().timestamp()}"
    backups[backup_id] = backup_data
    save_backups()
    embed = discord.Embed(
        title="✅ Backup Complete",
        description=f"ID: `{backup_id}`\nChannels: {len(backup_data['channels'])}\nMessages: {sum(len(v) for v in backup_data['messages'].values())}",
        color=0x00ff00
    )
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="restore", description="Restore server backup")
@app_commands.describe(backup_id="Backup ID to restore")
@app_commands.checks.has_permissions(administrator=True)
async def restore_command(interaction: discord.Interaction,
                           backup_id: str):
    backup_data = backups.get(backup_id)
    if not backup_data:
        return await interaction.response.send_message("❌ Invalid backup ID",
                                                        ephemeral=True)
    embed = discord.Embed(
        title="⚠️ Confirm Restoration",
        description=f"Restore **{backup_data['guild_name']}**?\nThis action is irreversible!",
        color=0xff9900
    )
    view = BackupView(backup_data)
    await interaction.response.send_message(embed=embed,
                                             view=view)

@bot.tree.command(name="restart",
                   description="Restarts The Bot")
async def restart(interaction: discord.Interaction):
    await interaction.response.send_message("Bot is restarting...",
                                             ephemeral=True)
    await bot.close()
    os.execv(sys.executable,
              ['python'] + sys.argv)

@bot.tree.command(name="help",
                   description="Show all available commands with autocomplete syntax")
async def help_command(interaction: discord.Interaction):
    try:
        registered_commands = await bot.tree.fetch_commands()
        command_ids = {cmd.name: cmd.id for cmd in registered_commands}

        embed = discord.Embed(
            title="💥 Backup Bot Help",
            description="> **Available commands with autocomplete syntax:**",
            color=discord.Color.blue()
        )

        commands_info = {
            "backup": "Create a complete server backup",
            "restore": "Restore server from backup",
            "restart": "Restarts The Bot",
            "help": "Show this help message"
        }

        for cmd_name, desc in commands_info.items():
            cmd_id = command_ids.get(cmd_name)
            syntax = f"</{cmd_name}:{cmd_id}>" if cmd_id else f"/{cmd_name}"
            embed.add_field(
                name=syntax,
                value=f"```{desc}```",
                inline=False
            )

        await interaction.response.send_message(embed=embed)
        
    except Exception as error:
        await interaction.response.send_message(
            "❌ Error fetching command syntax",
            ephemeral=True
        )


logo = rf"""
    ____             __             
   / __ )____ ______/ /____  ______ 
  / __  / __ `/ ___/ //_/ / / / __ \
 / /_/ / /_/ / /__/ ,< / /_/ / /_/ /
/_____/\__,_/\___/_/|_|\__,_/ .___/ 
                           /_/      
"""

def banner():
    print(Colorate.Horizontal(Colors.cyan_to_blue, logo, 1))

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="/backup"))
    banner()
    try:
        synced = await bot.tree.sync()
        print(Colorate.Horizontal(Colors.cyan_to_blue, f"Synced {len(synced)} commands"))
    except Exception as e:
        print(Colorate.Horizontal(Colors.cyan_to_blue, f"Command sync error: {e}"))
    print(Colorate.Horizontal(Colors.cyan_to_blue, f"Bot ready as {bot.user}"))

if __name__ == "__main__":
    bot.run(token)