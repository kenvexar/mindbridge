# アーキテクチャ

## システム概要

Discord → AI 処理 → Obsidian の自動化システム。

## コンポーネント

### Bot System (`src/bot/`)
- `DiscordBot` - Discord クライアント
- `MessageHandler` - メッセージ処理
- コマンドハンドラー

### AI Processing (`src/ai/`)
- `AIProcessor` - Google Gemini 統合
- `AdvancedNoteAnalyzer` - ノート分析・分類

### Obsidian Integration (`src/obsidian/`)
- `ObsidianFileManager` - ファイル操作
- `TemplateEngine` - YAML フロントマター
- `DailyNoteIntegration` - デイリーノート

### External Integrations
- Garmin Connect
- Google Calendar
- タスク・家計管理

## 設計パターン

- **Lazy Loading**: `ComponentManager` でリソース管理
- **Async Architecture**: 全 I/O 操作で async/await
- **Template System**: YAML + プレースホルダー置換
- **Structured Logging**: `structlog` でログ管理
