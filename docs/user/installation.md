# Installation Guide

Complete installation and setup guide for MindBridge.

> 💡 **Quick start needed?** See [Quick Start](quick-start.md) for a 5-minute setup.

## Prerequisites

### System Requirements
- **OS**: macOS 10.15+, Ubuntu 20.04+, Windows 10+ (WSL2 recommended)
- **Python**: 3.13+ (project developed on 3.13)
- **Memory**: Minimum 512MB, recommended 1GB+
- **Storage**: Minimum 1GB, recommended 5GB+ (including Obsidian vault)
- **Network**: Internet connection required

### Required Software

**1. Python 3.13**

macOS (Homebrew):
```bash
brew install python@3.13
python3.13 --version
```

Ubuntu/Debian:
```bash
sudo apt update
sudo apt install software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install python3.13 python3.13-venv python3.13-pip
```

**2. uv package manager**

```bash
# Unix systems (macOS/Linux) - recommended
curl -LsSf https://astral.sh/uv/install.sh | sh

# Manual installation via pip
pip install uv

# Windows (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex

# Verify installation
uv --version
```

## Installation

### 1. Get the Code

```bash
# Clone repository
git clone https://github.com/kenvexar/mindbridge.git
cd mindbridge

# Verify project structure
ls -la
```

### 2. Install Dependencies

```bash
# Install production dependencies
uv sync

# For developers (include dev dependencies)
uv sync --dev

# Verify installation
uv pip list
```

### 3. Configuration Setup

```bash
# Copy example configuration
cp .env.example .env

# Edit configuration file
nano .env  # or your preferred editor
```

## Discord Setup

### 1. Create Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Enter application name (e.g., "MindBridge Bot")
4. Note the Application ID

### 2. Configure Bot

1. Select "Bot" from left menu
2. Click "Add Bot"
3. Configure bot settings:
   - **Public Bot**: Off (for personal use)
   - **Requires OAuth2 Code Grant**: Off
   - **Message Content Intent**: On (required)
   - **Server Members Intent**: On (recommended)
   - **Presence Intent**: Off

### 3. Get Bot Token

1. In "Token" section, click "Copy"
2. Save token securely
3. Add to `.env` file as `DISCORD_BOT_TOKEN`

### 4. Set Bot Permissions

1. Go to "OAuth2" → "URL Generator"
2. Select **Scopes**:
   - `bot`
   - `applications.commands`

3. Select **Bot Permissions**:
   - **Text Permissions**: Send Messages, Send Messages in Threads, Embed Links, Attach Files, Read Message History, Add Reactions
   - **Voice Permissions**: Connect, Speak
   - **General Permissions**: Use Slash Commands

### 5. Invite Bot to Server

1. Copy generated URL
2. Access URL to invite bot
3. Select appropriate server
4. Confirm permissions

## API Configuration

### 1. Google Gemini API

1. Visit [Google AI Studio](https://aistudio.google.com/)
2. Login with Google account
3. Click "Get API key"
4. Select "Create API key in new project"
5. Copy API key to `.env` as `GEMINI_API_KEY`

**Usage Limits:**
- Free tier: 1,500 requests/day, 15 requests/minute
- For higher limits, configure billing in [Google Cloud Console](https://console.cloud.google.com/)

### 2. Google Cloud Speech-to-Text (Optional)

**Create Service Account:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select project
3. Navigate to "APIs & Services" → "Credentials"
4. Click "Create Credentials" → "Service Account"
5. Enter service account name
6. Assign role: "Cloud Speech Client"
7. Download JSON key

**Configure:**
```bash
# Place service account key
mkdir -p ~/.config/gcloud/
cp ~/Downloads/service-account-key.json ~/.config/gcloud/speech-key.json

# Set environment variable
echo "GOOGLE_APPLICATION_CREDENTIALS=$HOME/.config/gcloud/speech-key.json" >> .env
```

## Discord Channels Setup

Create these 3 channels in your Discord server:

```
📝 memo           ← Main input channel (text, voice, files)
🔔 notifications  ← System notifications
🤖 commands       ← Bot commands
```

**Important**: Channel names must be exact (`memo`, `notifications`, `commands`) for auto-detection.

### Get Server ID

1. Enable Developer Mode in Discord: Settings → Advanced → Developer Mode
2. Right-click server name → "Copy ID"
3. Add to `.env` as `DISCORD_GUILD_ID`

## Obsidian Setup

### 1. Prepare Obsidian Vault

**Create new vault:**
```bash
# Create vault directory
mkdir -p ~/Documents/ObsidianVault
cd ~/Documents/ObsidianVault

# Create folder structure optimized for AI classification
mkdir -p {00_Inbox,01_DailyNotes,02_Tasks,03_Ideas}
mkdir -p {10_Knowledge,11_Projects,12_Resources}
mkdir -p {20_Finance,21_Health}
mkdir -p {30_Archive,80_Attachments,90_Meta/Templates}

# Set vault path in .env
echo "OBSIDIAN_VAULT_PATH=$HOME/Documents/ObsidianVault" >> .env
```

**Use existing vault:**
```bash
# Verify existing vault path
ls -la /path/to/your/existing/vault

# Set in .env
echo "OBSIDIAN_VAULT_PATH=/path/to/your/existing/vault" >> .env
```

### 2. Configure Obsidian

**Recommended plugins:**
1. Open vault in Obsidian
2. Settings → Community Plugins → Turn off Safe Mode
3. Install recommended plugins:
   - **Calendar** - Daily note navigation
   - **Templater** - Advanced templating
   - **Dataview** - Data visualization
   - **Tag Wrangler** - Tag organization

## Environment Variables

Complete `.env` configuration:

```env
# Required
DISCORD_BOT_TOKEN=your_discord_bot_token
DISCORD_GUILD_ID=your_guild_id
GEMINI_API_KEY=your_gemini_api_key
OBSIDIAN_VAULT_PATH=/path/to/your/obsidian/vault

# Optional: Speech-to-Text
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# Optional: Garmin Connect
GARMIN_EMAIL=your_email@example.com
GARMIN_USERNAME=your_username
GARMIN_PASSWORD=your_password

# Optional: Security
USE_SECRET_MANAGER=false  # Usually false for local setup
ENABLE_ACCESS_LOGGING=true
```

## Testing Installation

### 1. Verify Configuration

```bash
# Check environment variables
cat .env | grep -E "(DISCORD_|GEMINI_|OBSIDIAN_)"

# Verify Python environment
uv run python --version
uv run python -c "import discord; print('discord.py version:', discord.__version__)"
uv run python -c "import google.generativeai as genai; print('Gemini API available')"
```

### 2. Run Tests

```bash
# Run all tests
uv run pytest

# Run basic configuration tests
uv run pytest tests/unit/test_config.py -v

# Run integration tests
uv run pytest tests/integration/ -v
```

### 3. Start Bot

```bash
# Start bot
uv run python -m src.main

# Verify startup logs show channel detection:
# "Found memo channel: 123456789"
# "Found notifications channel: 987654321"
# "Found commands channel: 456789123"
```

### 4. Test Functionality

**Basic functionality:**
1. Post text message to `#memo` → Check AI categorization
2. Upload audio file to `#memo` → Verify transcription
3. Test commands in `#commands`:
   - `/ping`
   - `/status`
   - `/help`

**AI Classification test:**
- "Lunch $15" → 20_Finance folder
- "TODO: finish report" → 02_Tasks folder
- "Workout 3km" → 21_Health folder
- "Python learning notes" → 10_Knowledge folder

## Troubleshooting

### Common Issues

**Bot won't start:**
```bash
# Check Python version
python --version  # Must be 3.13+

# Reinstall dependencies
uv sync --reinstall

# Check logs
tail -f logs/bot.log

# Debug mode
LOG_LEVEL=DEBUG uv run python -m src.main
```

**Discord authentication errors:**
```bash
# Verify token
echo $DISCORD_BOT_TOKEN

# Check bot permissions in Discord Developer Portal:
# - Message Content Intent: ON (required)
# - Send Messages, Read Message History permissions
```

**Obsidian file creation errors:**
```bash
# Check path and permissions
ls -la $OBSIDIAN_VAULT_PATH
chmod 755 $OBSIDIAN_VAULT_PATH

# Verify folder structure
tree $OBSIDIAN_VAULT_PATH
```

**API rate limits:**
```bash
# Check Gemini API usage
# Discord: /ai_stats command
# Free tier limits: 1,500/day, 15/minute

# Check Speech API usage in Google Cloud Console
# Free tier: 60 minutes/month
```

### Channel Detection Issues

**Problem**: Bot can't find channels

**Solutions:**
1. Verify exact channel names (`memo`, `notifications`, `commands`)
2. Check bot has channel view permissions
3. Verify `DISCORD_GUILD_ID` is correct
4. Check startup logs for "Found memo channel" messages

### No Response to Messages

**Problem**: Bot doesn't respond to `#memo` posts

**Solutions:**
1. Verify bot is online
2. Check Message Content Intent is enabled
3. Check `#notifications` for error messages
4. Allow few seconds for AI processing

## Next Steps

After installation:
1. **[Quick Start Guide](quick-start.md)** - Get started quickly
2. **[Basic Usage](basic-usage.md)** - Day-to-day usage
3. **[Commands Reference](commands-reference.md)** - Available commands

## Support

For issues:
1. **[GitHub Issues](https://github.com/kenvexar/mindbridge/issues)** - Bug reports and feature requests
2. **[Troubleshooting Guide](../operations/troubleshooting.md)** - Common solutions
3. Include log files and error messages in reports
