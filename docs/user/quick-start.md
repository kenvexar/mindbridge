# Quick Start Guide

**Get MindBridge running in 10 minutes**

This guide will have you up and running with automatic memo processing in under 10 minutes.

## ⏱️ Time Breakdown
- Setup: 2 minutes
- Installation: 3 minutes
- Configuration: 3 minutes
- Launch & Test: 2 minutes

## 📋 Prerequisites

Have these ready before starting:

- [ ] Python 3.13+ installed
- [ ] Discord Bot token ([how to get](#discord-bot-setup))
- [ ] Google Gemini API key ([how to get](#gemini-api-setup))
- [ ] Obsidian vault (or empty folder)
- [ ] Discord server (where you can add bots)

## 🏃‍♂️ Quick Setup

### 1. Get the Project (1 min)

```bash
# Clone repository
git clone https://github.com/kenvexar/mindbridge.git
cd mindbridge

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Install Dependencies (2 min)

```bash
# Install required packages
uv sync

# Verify installation
uv run python --version  # Should show Python 3.13+
```

### 3. Minimal Configuration (3 min)

```bash
# Copy configuration template
cp .env.example .env
```

Edit `.env` file with **4 required settings only**:

```env
# Required settings (that's all you need!)
DISCORD_BOT_TOKEN=your_discord_bot_token_here
DISCORD_GUILD_ID=your_discord_server_id_here
GEMINI_API_KEY=your_gemini_api_key_here
OBSIDIAN_VAULT_PATH=/path/to/your/obsidian/vault
```

### 4. Create Test Vault (30 sec)

```bash
# Create test vault folder
mkdir -p ./test-vault
mkdir -p ./test-vault/{00_Inbox,01_DailyNotes,02_Tasks,03_Ideas}
mkdir -p ./test-vault/{10_Knowledge,11_Projects,12_Resources}
mkdir -p ./test-vault/{20_Finance,21_Health}
mkdir -p ./test-vault/{30_Archive,80_Attachments,90_Meta}

# Update .env with test vault path
echo "OBSIDIAN_VAULT_PATH=$(pwd)/test-vault" >> .env
```

### 5. Create Discord Channels (1 min)

Create these **3 channels exactly** in your Discord server:
```
📝 memo           ← Main input channel
🔔 notifications  ← System notifications
🤖 commands       ← Bot commands
```

**Important**: Use exact channel names (`memo`, `notifications`, `commands`) - bot auto-detects them!

### 6. Launch Bot (1 min)

```bash
# Start the bot
uv run python -m src.main
```

✅ **Success indicators:**
```
INFO: Discord bot starting...
INFO: Found memo channel: 123456789
INFO: Found notifications channel: 987654321
INFO: Found commands channel: 456789123
INFO: Bot is ready! Logged in as YourBot#1234
```

### 7. Test Functionality (2 min)

1. Go to your `#memo` channel
2. Post this message:

```
Test post: Beautiful weather today. Going to study some programming.
```

3. Wait 10-30 seconds, check `test-vault` folder for new Markdown file
4. In `#commands` channel, run `/status` to check bot status

## 🎉 Success!

Congratulations! MindBridge is now running and will automatically:
- Analyze Discord messages with AI
- Generate structured Markdown notes
- Save to Obsidian vault with AI categorization
- Organize content into appropriate folders

## 📚 Next Steps

### Immediate Features to Try
- **Voice memos**: Upload audio files to `#memo` for auto-transcription
- **URL analysis**: Post URLs for automatic content summarization
- **Commands**: Try `/help` in `#commands` channel

### Learn More
- **[Basic Usage](basic-usage.md)** - Day-to-day usage guide
- **[Installation Guide](installation.md)** - Complete setup for all features
- **[Commands Reference](commands-reference.md)** - Full command list

## 🆘 Getting API Keys

### Discord Bot Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Enter application name (e.g., "MindBridge Bot")
4. Go to "Bot" section
5. Click "Add Bot"
6. Copy the "Token" (this is your `DISCORD_BOT_TOKEN`)

**Add bot to server:**
1. Go to "OAuth2" → "URL Generator"
2. Select scopes: "bot" and "applications.commands"
3. Select bot permissions:
   - Send Messages
   - Read Message History
   - Attach Files
   - Use Slash Commands
   - Message Content Intent (in Bot settings)
4. Use generated URL to invite bot

### Gemini API Setup

1. Visit [Google AI Studio](https://aistudio.google.com/)
2. Click "Get API key"
3. Select "Create API key in new project"
4. Copy the API key (this is your `GEMINI_API_KEY`)

### Get Server ID

1. Enable Developer Mode in Discord:
   - Settings → Advanced → Developer Mode
2. Right-click your server name → "Copy ID"
3. This is your `DISCORD_GUILD_ID`

## ❗ Common Issues

**Bot doesn't respond:**
```bash
# Check bot logs
tail -f logs/bot.log

# Verify configuration
cat .env | grep -E "(DISCORD_|GEMINI_|OBSIDIAN_)"
```

**Permission errors:**
```bash
# Check vault permissions
ls -la ./test-vault
chmod 755 ./test-vault
```

**Dependency errors:**
```bash
# Reinstall dependencies
uv sync --reinstall
```

**Bot can't find channels:**
- Verify exact channel names: `memo`, `notifications`, `commands`
- Check bot has permission to see channels
- Verify `DISCORD_GUILD_ID` is correct

## 🧪 Mock Mode Testing

If you don't have API keys yet, test with mock mode:

```bash
# Run in mock mode (no API keys needed)
ENVIRONMENT=development ENABLE_MOCK_MODE=true uv run python -m src.main
```

## 📞 Support

If you run into issues:
- Check [Troubleshooting Guide](../operations/troubleshooting.md)
- Report problems on [GitHub Issues](https://github.com/kenvexar/mindbridge/issues)

---

Once you've confirmed basic functionality with this quick start, explore the [Basic Usage Guide](basic-usage.md) to learn about all features.
