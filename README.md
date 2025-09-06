# MindBridge

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

AI-powered personal knowledge bridge that uses Discord as an interface for intelligent memo processing and automatic Obsidian note saving.

## Overview

MindBridge captures messages, processes them with Google Gemini AI, and organizes them into structured Obsidian notes with automatic categorization and metadata extraction.

### Core Features

**🤖 AI-Powered Message Processing**
- Automatic Discord message capture with AI analysis and metadata extraction  
- URL content fetching and summarization
- Intelligent categorization and folder assignment

**🎤 Voice Memo Processing**
- Google Cloud Speech-to-Text integration for automatic transcription
- Multiple audio format support (MP3, WAV, FLAC, OGG, M4A, WEBM)

**📝 Obsidian Integration**
- Structured Markdown note generation with automatic folder classification
- Daily Note integration with Activity Log and Daily Tasks
- Template system with placeholder replacement

**💰 Finance Management**
- Expense tracking and subscription management
- Automatic financial reports and budgeting

**✅ Task Management**  
- Task creation, tracking, and productivity reviews
- Project management with progress tracking

**🏃 Health Data Integration** (Optional)
- Garmin Connect integration for activity data sync
- Health analytics and pattern analysis

## Quick Start

### Prerequisites
- Python 3.13+
- [uv](https://github.com/astral-sh/uv) (fast Python package manager)
- Discord Bot token  
- Google Gemini API key
- Obsidian vault

### Installation
```bash
# Clone repository
git clone https://github.com/kenvexar/mindbridge.git
cd mindbridge

# Install dependencies  
uv sync

# Environment setup
cp .env.example .env
# Edit .env file with your API keys
```

### Configuration

Required environment variables:
```env
DISCORD_BOT_TOKEN=your_discord_bot_token
DISCORD_GUILD_ID=your_guild_id  
GEMINI_API_KEY=your_gemini_api_key
OBSIDIAN_VAULT_PATH=/path/to/your/obsidian/vault
```

### Discord Setup

Create these 3 channels in your Discord server:
```
📝 memo           ← Main input channel (text, voice, files)
🔔 notifications  ← System notifications  
🤖 commands       ← Bot commands
```

Channel IDs are auto-detected by name - no manual configuration needed!

### Running the Application

```bash
# Start the bot
uv run python -m src.main

# With debug mode
uv run python -m src.main --debug
```

### Usage

**Simply post to #memo channel!** AI automatically processes and saves to appropriate Obsidian folders:

**AI Auto-Classification & Obsidian Folder Structure:**

**High-frequency folders (00-09):**
- `"Quick note"` → 📥 **00_Inbox** (uncategorized)
- `"Today's reflection"` → 📅 **01_DailyNotes** (daily logs)  
- `"TODO: finish report"` → ✅ **02_Tasks** (task management)
- `"New idea for project"` → 💡 **03_Ideas** (ideas and insights)

**Knowledge & learning (10-19):**
- `"Python learning notes"` → 📚 **10_Knowledge** (learning content)
- `"Project update"` → 🚀 **11_Projects** (project work)
- `"Reference materials"` → 📖 **12_Resources** (resources)

**Records & management (20-29):**
- `"$15 lunch"` → 💰 **20_Finance** (expenses)
- `"Workout completed"` → 🏃 **21_Health** (health tracking)

**Archive & system (30+):**
- Completed items → 📦 **30_Archive**
- Attachments → 📎 **80_Attachments**
- Templates → ⚙️ **90_Meta**

Voice files are automatically transcribed and categorized by content.

## Development

### Commands
```bash
# Package management
uv sync                    # Install dependencies
uv add <package>           # Add new package
uv add --dev <package>     # Add dev package

# Testing
uv run pytest             # Run all tests
uv run pytest --cov=src   # Run with coverage
uv run pytest tests/unit/test_obsidian.py  # Specific test

# Code quality
uv run ruff check src/ --fix && uv run ruff format src/
uv run mypy src/          # Type checking

# Docker testing
./scripts/docker-local-test.sh  # Automated Docker testing
```

### Architecture

The application follows a layered architecture:

1. **Bot Layer** (`src/bot/`): Discord interface and command handling
2. **Processing Layer** (`src/ai/`): AI analysis and content processing  
3. **Business Logic** (`src/tasks/`, `src/finance/`): Domain functionality
4. **Integration Layer** (`src/obsidian/`, `src/garmin/`, `src/audio/`): External services
5. **Security Layer** (`src/security/`): Authentication and access control
6. **Monitoring Layer** (`src/monitoring/`): Health checks and observability

### Key Technologies
- **Discord.py**: Discord API integration
- **Google Generative AI**: Gemini API for AI processing
- **Google Cloud Speech**: Speech-to-text processing
- **Pydantic**: Data validation and settings
- **aiofiles/aiohttp**: Async I/O operations
- **structlog + rich**: Structured logging
- **scikit-learn**: Machine learning for content analysis

## Documentation

### 📚 User Documentation
- **[Installation Guide](docs/user/installation.md)** - Detailed setup instructions
- **[Quick Start](docs/user/quick-start.md)** - Get started quickly
- **[Basic Usage](docs/user/basic-usage.md)** - Day-to-day usage
- **[Commands Reference](docs/user/commands-reference.md)** - Available commands
- **[Examples](docs/user/examples.md)** - Usage examples

### 🛠️ Developer Documentation
- **[Development Guide](docs/developer/development-guide.md)** - Development setup
- **[Architecture](docs/developer/architecture.md)** - System design

### 🚀 Operations Documentation
- **[Deployment](docs/operations/deployment.md)** - Production deployment
- **[Monitoring](docs/operations/monitoring.md)** - Monitoring and logging
- **[Troubleshooting](docs/operations/troubleshooting.md)** - Issue resolution

## Supported Environments

- **Development**: Local development with mock mode support
- **Production**: Google Cloud Run (24/7 operation)
- **Container**: Docker support
- **OS**: macOS, Linux, Windows (WSL2)

## Contributing

Contributions welcome! Please see the development guide for contribution guidelines.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/kenvexar/mindbridge/issues) for bug reports and feature requests
- **Documentation**: Comprehensive documentation available
- **Discussions**: Project discussions and community support

---

**Project Information**
- Version: 0.1.0
- Python: 3.13+
- Maintainer: Kent
- Last Updated: 2025