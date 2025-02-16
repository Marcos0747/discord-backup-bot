# Discord Server Backup Bot

A bot to create/restore complete server backups including roles, channels, messages, emojis, and stickers.

## ✨ Features

- Full server structure backup
- Message history preservation (up to 500 messages/channel)
- Emoji and sticker restoration
- Role permissions cloning
- Interactive confirmation system

## 💦 Requirements

- Python 3.8+
- Discord bot token with proper permissions
- [Required Permissions](#required-permissions)

## 🛠️ Installation
1. Clone repository:

git clone https://github.com/Marcos0747/discord-backup-bot.git
cd discord-backup-bot

2. Install dependencies:

`setup.bat`

3. Add your bot token in `config.py` file

4. Run the bot:

`python main.py`

## 📋 Commands

- `/backup` - Create server backup
- `/restore [backup_id]` - Restore from backup
- `/help` - Shows help message
- `/restart` - Restarts the bot

## 💤 Required Permissions

- Administrator
- Manage Roles
- Manage Channels
- Manage Emojis and Stickers
- Read Message History
- Manage Webhooks

## 💯 Troubleshooting

- Missing Permissions: Ensure bot has admin privileges
- Channel Errors: Delete existing backups.json and restart
- Sticker Issues: Verify server has available sticker slots

**⚠️ Warning: Backup files contain sensitive server data. Store securely!**

## 🤝 Contributions

Contributions are welcome! Please open an issue or a pull request if you wish to contribute.


