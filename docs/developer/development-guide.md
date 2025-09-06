# Development Guide

Comprehensive guide for MindBridge development, from environment setup to implementation.

## Table of Contents

1. [Development Environment Setup](#development-environment-setup)
2. [Project Structure](#project-structure)
3. [Development Workflow](#development-workflow)
4. [Code Style and Guidelines](#code-style-and-guidelines)
5. [Testing Strategy](#testing-strategy)
6. [Debugging Techniques](#debugging-techniques)
7. [New Feature Development](#new-feature-development)
8. [Performance Optimization](#performance-optimization)

## 🚀 Development Environment Setup

### Required Tools

```bash
# Essential tools
python --version          # 3.13+
uv --version              # Latest
git --version             # 2.20+
docker --version          # 20.10+ (optional)

# Recommended tools
code --version            # VS Code
curl --version            # HTTP testing
jq --version              # JSON processing
```

### Environment Setup

```bash
# 1. Clone repository
git clone https://github.com/kenvexar/mindbridge.git
cd mindbridge

# 2. Install development dependencies
uv sync --dev

# 3. Setup pre-commit hooks
uv run pre-commit install

# 4. Configure environment
cp .env.example .env.development
```

### VS Code Configuration

`.vscode/settings.json`:
```json
{
    "python.pythonPath": "./.venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "python.formatting.provider": "ruff",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests/"],
    "python.testing.autoTestDiscoverOnSaveEnabled": true,
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        ".mypy_cache": true,
        ".pytest_cache": true,
        ".ruff_cache": true
    },
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": "explicit",
        "source.fixAll.ruff": "explicit"
    }
}
```

`.vscode/extensions.json`:
```json
{
    "recommendations": [
        "ms-python.python",
        "charliermarsh.ruff",
        "ms-python.mypy-type-checker",
        "ms-vscode.vscode-json",
        "redhat.vscode-yaml",
        "ms-python.debugpy"
    ]
}
```

### Development Configuration

`.env.development`:
```env
# Development environment
ENVIRONMENT=development
LOG_LEVEL=DEBUG
LOG_FORMAT=pretty

# Mock mode (test without API keys)
ENABLE_MOCK_MODE=true
MOCK_DISCORD_ENABLED=true
MOCK_GEMINI_ENABLED=true
MOCK_GARMIN_ENABLED=true
MOCK_SPEECH_ENABLED=true

# Test Obsidian vault
OBSIDIAN_VAULT_PATH=./test_vault

# Discord settings (if testing with real bot)
# DISCORD_BOT_TOKEN=your_dev_token
# DISCORD_GUILD_ID=your_test_server_id
# GEMINI_API_KEY=your_dev_key

# Development features
ENABLE_AUTO_RELOAD=true
ENABLE_DEBUG_ENDPOINTS=true
ENABLE_PROFILING=false
```

## 🏗️ Project Structure

### Architecture Overview

```
src/
├── config/              # Configuration management
│   ├── settings.py         # Main settings with Pydantic
│   └── secure_settings.py  # Secure settings with encryption
├── utils/               # Shared utilities and logging
│   ├── logger.py           # Structured logging setup
│   └── mixins.py           # Utility mixins
├── security/            # Security and authentication
│   ├── secret_manager.py   # Secret management
│   └── access_logger.py    # Access logging
├── bot/                 # Discord bot implementation
│   ├── client.py           # Main Discord client
│   ├── handlers.py         # Message event handlers
│   ├── commands/           # Command modules
│   ├── mixins/             # Reusable bot mixins
│   └── models.py           # Bot data models
├── ai/                  # AI processing and analysis
│   ├── processor.py        # Main AI processor
│   ├── gemini_client.py    # Google Gemini API client
│   ├── note_analyzer.py    # Note analysis and categorization
│   └── models.py           # AI data models
├── obsidian/            # Obsidian vault integration
│   ├── core/               # Core vault operations
│   ├── search/             # Search functionality
│   ├── backup/             # Backup management
│   ├── analytics/          # Vault analytics
│   ├── models.py           # Obsidian data models
│   └── template_system.py  # Advanced templating
├── tasks/               # Task management system
│   └── models.py           # Task data models
├── finance/             # Financial management
│   └── models.py           # Finance data models
├── audio/               # Voice processing
│   └── models.py           # Audio data models
├── garmin/              # Garmin Connect integration
│   └── models.py           # Garmin data models
├── health_analysis/     # Health data processing
│   └── models.py           # Health data models
├── monitoring/          # Application monitoring
│   └── health_server.py    # Health check server
└── main.py              # Application entry point
```

### Key Design Patterns

1. **Dependency Injection**: Constructor-based dependency management
2. **Factory Pattern**: Client creation and configuration  
3. **Strategy Pattern**: Pluggable processing methods
4. **Template Method Pattern**: Common processing workflows
5. **Repository Pattern**: Data access abstraction
6. **Observer Pattern**: Event-driven notifications

### Module Dependencies

```mermaid
graph TD
    A[main.py] --> B[bot/client.py]
    B --> C[bot/handlers.py]
    C --> D[ai/processor.py] 
    D --> E[obsidian/core/vault_manager.py]
    B --> F[bot/commands/]
    F --> G[tasks/task_manager.py]
    F --> H[finance/expense_manager.py]
    D --> I[ai/gemini_client.py]
    E --> J[obsidian/template_system.py]
```

## 🔄 Development Workflow

### Day-to-day Development

```bash
# 1. Start development session
uv run python -m src.main --dev

# 2. Run tests continuously
uv run pytest --watch

# 3. Check code quality
uv run ruff check src/ --fix
uv run mypy src/

# 4. Format code
uv run ruff format src/
```

### Feature Development Cycle

1. **Planning Phase**
   ```bash
   # Create feature branch
   git checkout -b feature/new-ai-classification
   
   # Document requirements
   echo "## Feature: Enhanced AI Classification" > docs/features/ai-classification.md
   ```

2. **Implementation Phase**
   ```bash
   # Write tests first (TDD)
   touch tests/unit/test_new_classification.py
   
   # Implement feature
   # Edit src/ai/enhanced_classifier.py
   
   # Validate implementation
   uv run pytest tests/unit/test_new_classification.py -v
   ```

3. **Integration Phase**
   ```bash
   # Integration testing
   uv run pytest tests/integration/ -v
   
   # Manual testing
   uv run python -m src.main --dev
   ```

4. **Quality Assurance**
   ```bash
   # Full test suite
   uv run pytest --cov=src
   
   # Code quality checks
   uv run ruff check src/ --fix && uv run ruff format src/
   uv run mypy src/
   
   # Pre-commit validation
   uv run pre-commit run --all-files
   ```

### Git Workflow

```bash
# Daily workflow
git checkout main
git pull origin main
git checkout -b feature/new-feature

# Development commits
git add src/new_module.py tests/test_new_module.py
git commit -m "feat: implement new AI classification module"

# Before push
uv run pytest
uv run ruff check src/ --fix && uv run ruff format src/
git push origin feature/new-feature

# Create PR when ready
gh pr create --title "Add enhanced AI classification" --body "Implementation details..."
```

## 📝 Code Style and Guidelines

### Ruff Configuration

`pyproject.toml`:
```toml
[tool.ruff]
target-version = "py313"
line-length = 88
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings  
    "F",    # pyflakes
    "I",    # isort
    "B",    # flake8-bugbear
    "C4",   # flake8-comprehensions
    "UP",   # pyupgrade
    "SIM",  # flake8-simplify
]
ignore = [
    "E501",  # line too long, handled by formatter
    "B008",  # do not perform function calls in argument defaults
    "C901",  # too complex
]

[tool.ruff.per-file-ignores]
"tests/**/*" = ["D", "S101", "PLR2004"]

[tool.ruff.mccabe]
max-complexity = 10

[tool.ruff.isort]
known-first-party = ["src"]
```

### Code Conventions

**1. Type Hints**
```python
# Good
async def process_message(
    content: str, 
    metadata: dict[str, Any]
) -> ProcessingResult:
    """Process message with AI analysis."""
    pass

# Bad
async def process_message(content, metadata):
    pass
```

**2. Error Handling**
```python
# Good
try:
    result = await ai_processor.analyze(content)
except APIError as e:
    logger.error("AI processing failed", extra={"error": str(e), "content_length": len(content)})
    raise ProcessingError(f"Analysis failed: {e}") from e
except Exception as e:
    logger.exception("Unexpected error in AI processing")
    raise

# Bad
try:
    result = await ai_processor.analyze(content)
except:
    print("Error occurred")
    return None
```

**3. Logging**
```python
# Good
logger.info(
    "Message processed successfully",
    extra={
        "message_id": message.id,
        "channel": message.channel.name,
        "processing_time": processing_time,
        "ai_confidence": result.confidence
    }
)

# Bad
print(f"Processed message {message.id}")
```

**4. Async/Await**
```python
# Good
async def save_to_obsidian(note: Note) -> Path:
    """Save note to Obsidian vault."""
    async with aiofiles.open(note.path, "w") as f:
        await f.write(note.content)
    return note.path

# Bad
def save_to_obsidian(note: Note) -> Path:
    with open(note.path, "w") as f:
        f.write(note.content)
    return note.path
```

## 🧪 Testing Strategy

### Test Structure

```
tests/
├── unit/                # Unit tests
│   ├── test_ai/
│   ├── test_bot/
│   ├── test_obsidian/
│   └── test_config/
├── integration/         # Integration tests
│   ├── test_ai_obsidian.py
│   ├── test_discord_flow.py
│   └── test_end_to_end.py
├── fixtures/            # Test fixtures
│   ├── discord_messages.json
│   ├── ai_responses.json
│   └── obsidian_notes.md
└── conftest.py          # Pytest configuration
```

### Writing Tests

**Unit Test Example:**
```python
# tests/unit/test_ai/test_processor.py
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.ai.processor import AIProcessor
from src.ai.models import ProcessingResult

@pytest.fixture
def ai_processor():
    """Create AI processor with mocked dependencies."""
    gemini_client = AsyncMock()
    return AIProcessor(gemini_client=gemini_client)

@pytest.mark.asyncio
async def test_process_message_success(ai_processor):
    """Test successful message processing."""
    # Arrange
    content = "Test message about Python programming"
    expected_result = ProcessingResult(
        summary="Programming discussion",
        tags=["python", "programming"],
        category="knowledge",
        confidence=0.85
    )
    ai_processor.gemini_client.analyze.return_value = expected_result
    
    # Act
    result = await ai_processor.process_message(content)
    
    # Assert
    assert result.summary == "Programming discussion"
    assert "python" in result.tags
    assert result.category == "knowledge"
    ai_processor.gemini_client.analyze.assert_called_once_with(content)
```

**Integration Test Example:**
```python
# tests/integration/test_discord_to_obsidian.py
import pytest
import tempfile
from pathlib import Path

from src.bot.client import DiscordBot
from src.obsidian.core.vault_manager import VaultManager

@pytest.mark.asyncio
async def test_full_message_processing_flow():
    """Test complete flow from Discord message to Obsidian note."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Arrange
        vault_path = Path(temp_dir) / "test_vault"
        vault_manager = VaultManager(vault_path)
        
        # Create mock Discord message
        mock_message = create_mock_discord_message(
            content="Today I learned about async/await in Python",
            author="test_user",
            channel_name="memo"
        )
        
        # Act
        bot = DiscordBot(vault_manager=vault_manager)
        await bot.process_message(mock_message)
        
        # Assert
        created_files = list(vault_path.rglob("*.md"))
        assert len(created_files) == 1
        
        note_content = created_files[0].read_text()
        assert "async/await" in note_content
        assert "Python" in note_content
        assert "tags: [\"python\", \"programming\", \"learning\"]" in note_content
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/unit/test_ai/test_processor.py -v

# Run tests matching pattern
uv run pytest -k "test_message_processing" -v

# Run tests with live logging
uv run pytest --log-cli-level=INFO

# Run in parallel
uv run pytest -n auto
```

### Test Configuration

`pytest.ini`:
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow tests
    external: Tests requiring external services
addopts = 
    --strict-markers
    --tb=short
    --capture=no
    -ra
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
```

## 🐛 Debugging Techniques

### Debug Configuration

```python
# src/utils/debug.py
import logging
import sys
from typing import Any

def setup_debug_logging() -> None:
    """Setup debug logging configuration."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime) s - %(name) s - %(levelname) s - %(message) s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('debug.log')
        ]
    )

def debug_print(obj: Any, name: str = "DEBUG") -> None:
    """Enhanced debug printing."""
    print(f"\n=== {name} ===")
    print(f"Type: {type(obj)}")
    print(f"Value: {obj}")
    if hasattr(obj, '__dict__'):
        print(f"Attributes: {obj.__dict__}")
    print("=" * (len(name) + 8))
```

### Debugging Discord Bot

```python
# Debug Discord events
@bot.event
async def on_message(message: discord.Message) -> None:
    """Debug message processing."""
    logger.debug(
        "Received message",
        extra={
            "message_id": message.id,
            "content": message.content[:100],
            "author": str(message.author),
            "channel": message.channel.name,
            "guild": message.guild.name if message.guild else None
        }
    )
    
    # Process message with error handling
    try:
        await process_message_handler(message)
    except Exception as e:
        logger.exception(
            "Message processing failed",
            extra={
                "message_id": message.id,
                "error": str(e)
            }
        )
```

### AI Processing Debug

```python
# Debug AI processing
async def debug_ai_analysis(content: str) -> ProcessingResult:
    """Debug AI analysis with detailed logging."""
    logger.debug("Starting AI analysis", extra={"content_length": len(content)})
    
    start_time = time.time()
    try:
        result = await gemini_client.analyze(content)
        processing_time = time.time() - start_time
        
        logger.debug(
            "AI analysis completed",
            extra={
                "processing_time": processing_time,
                "confidence": result.confidence,
                "tags_count": len(result.tags),
                "category": result.category
            }
        )
        return result
    except Exception as e:
        logger.exception("AI analysis failed", extra={"content": content[:200]})
        raise
```

### Docker Debugging

```bash
# Debug in Docker container
./scripts/docker-local-test.sh

# Access container for debugging
docker compose exec mindbridge-bot /bin/bash

# View container logs
docker compose logs -f mindbridge-bot

# Debug with volume mounts for live code changes
docker compose -f docker-compose.debug.yml up
```

## 🚀 New Feature Development

### Feature Development Process

1. **Requirements Analysis**
   ```markdown
   # Feature: Enhanced AI Classification
   
   ## Problem
   Current AI classification has limited accuracy for technical content.
   
   ## Solution
   Implement specialized classifiers for different content types.
   
   ## Acceptance Criteria
   - [ ] 95%+ accuracy for programming content
   - [ ] Support for 10+ programming languages
   - [ ] Performance under 2 seconds
   ```

2. **Design Phase**
   ```python
   # Design interfaces first
   from abc import ABC, abstractmethod
   
   class ContentClassifier(ABC):
       @abstractmethod
       async def classify(self, content: str) -> ClassificationResult:
           pass
   
   class ProgrammingClassifier(ContentClassifier):
       async def classify(self, content: str) -> ClassificationResult:
           # Implementation here
           pass
   ```

3. **Test-Driven Development**
   ```python
   # Write tests first
   @pytest.mark.asyncio
   async def test_programming_classifier_python_code():
       """Test classification of Python code snippets."""
       classifier = ProgrammingClassifier()
       content = "def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)"
       
       result = await classifier.classify(content)
       
       assert result.category == "programming"
       assert "python" in result.tags
       assert result.confidence > 0.9
   ```

### Adding New Commands

```python
# src/bot/commands/new_commands.py
from discord import app_commands
from discord.ext import commands

class NewCommands(commands.Cog):
    """New feature commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="new_feature")
    @app_commands.describe(
        parameter="Description of parameter"
    )
    async def new_feature_command(
        self, 
        interaction: discord.Interaction,
        parameter: str
    ) -> None:
        """Implement new feature."""
        await interaction.response.defer()
        
        try:
            result = await self.process_new_feature(parameter)
            await interaction.followup.send(f"✅ Feature result: {result}")
        except Exception as e:
            logger.exception("New feature command failed")
            await interaction.followup.send(f"❌ Error: {e}")
    
    async def process_new_feature(self, parameter: str) -> str:
        """Process new feature logic."""
        # Implementation here
        return f"Processed: {parameter}"

async def setup(bot: commands.Bot) -> None:
    """Setup function for the cog."""
    await bot.add_cog(NewCommands(bot))
```

### Configuration Updates

```python
# src/config/settings.py - Add new settings
class Settings(BaseSettings):
    # ... existing settings ...
    
    # New feature settings
    new_feature_enabled: bool = Field(False, description="Enable new feature")
    new_feature_threshold: float = Field(0.8, description="Confidence threshold")
    new_feature_cache_ttl: int = Field(3600, description="Cache TTL in seconds")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
```

## ⚡ Performance Optimization

### Profiling and Monitoring

```python
# src/utils/profiler.py
import asyncio
import time
import functools
from typing import Callable, Any

def async_timer(func: Callable) -> Callable:
    """Decorator to time async function execution."""
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(
                f"Function {func.__name__} completed",
                extra={
                    "execution_time": execution_time,
                    "function": func.__name__
                }
            )
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"Function {func.__name__} failed",
                extra={
                    "execution_time": execution_time,
                    "function": func.__name__,
                    "error": str(e)
                }
            )
            raise
    return wrapper

# Usage
@async_timer
async def process_message(content: str) -> ProcessingResult:
    """Process message with timing."""
    pass
```

### Caching Strategy

```python
# src/utils/cache.py
from typing import Any, Optional
import asyncio
from functools import wraps

class AsyncLRUCache:
    """Async LRU cache implementation."""
    
    def __init__(self, max_size: int = 128, ttl: int = 3600):
        self.max_size = max_size
        self.ttl = ttl
        self._cache: dict[str, tuple[Any, float]] = {}
    
    async def get(self, key: str) -> Optional[Any]:
        """Get item from cache."""
        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.time() - timestamp < self.ttl:
                return value
            else:
                del self._cache[key]
        return None
    
    async def set(self, key: str, value: Any) -> None:
        """Set item in cache."""
        if len(self._cache) >= self.max_size:
            # Remove oldest item
            oldest_key = min(self._cache.keys(), 
                           key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]
        
        self._cache[key] = (value, time.time())

# Global cache instance
ai_cache = AsyncLRUCache(max_size=500, ttl=3600)

@async_timer
async def cached_ai_analysis(content: str) -> ProcessingResult:
    """AI analysis with caching."""
    cache_key = f"ai_analysis:{hash(content)}"
    
    # Try cache first
    cached_result = await ai_cache.get(cache_key)
    if cached_result:
        logger.debug("Cache hit for AI analysis")
        return cached_result
    
    # Compute result
    result = await ai_processor.analyze(content)
    
    # Cache result
    await ai_cache.set(cache_key, result)
    logger.debug("Cache miss for AI analysis - result cached")
    
    return result
```

### Database Optimization

```python
# Optimize file operations
import aiofiles
from pathlib import Path

async def batch_file_operations(operations: list[tuple[Path, str]]) -> None:
    """Perform file operations in batch."""
    async def write_file(path: Path, content: str) -> None:
        async with aiofiles.open(path, "w") as f:
            await f.write(content)
    
    # Execute operations concurrently
    tasks = [write_file(path, content) for path, content in operations]
    await asyncio.gather(*tasks, return_exceptions=True)
```

### Memory Optimization

```python
# src/utils/memory.py
import psutil
import gc
from typing import Generator, Any

def monitor_memory() -> None:
    """Monitor memory usage."""
    process = psutil.Process()
    memory_info = process.memory_info()
    logger.info(
        "Memory usage",
        extra={
            "rss_mb": memory_info.rss / 1024 / 1024,
            "vms_mb": memory_info.vms / 1024 / 1024,
            "percent": process.memory_percent()
        }
    )

def batch_processor(items: list[Any], batch_size: int = 100) -> Generator[list[Any], None, None]:
    """Process items in batches to manage memory."""
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        yield batch
        # Force garbage collection between batches
        gc.collect()
```

---

This development guide provides the foundation for effective MindBridge development. Follow these practices to maintain code quality, performance, and maintainability.