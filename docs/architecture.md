# アーキテクチャ

## システム概要

```
Discord → MessageProcessor → AIProcessor → TemplateEngine → Obsidian Vault
                               │                │
                               └─ AdvancedNoteAnalyzer ─┐
                             Garmin / Calendar Integrations → Daily Note / Lifelog
```

`src/main.py` が設定とシークレットを読み込み、必要なコンポーネントを遅延初期化してランタイムコンテキストを構築します。Discord Bot、外部連携スケジューラ、ヘルスチェックサーバが同時に稼働し、Vault への書き込みや統計集計を行います。

---

## ランタイム構成

| レイヤー | 主なモジュール | 役割 |
| --- | --- | --- |
| 設定/セキュリティ | `src/config/settings.py`, `src/config/secure_settings.py`, `src/security/secret_manager.py`, `src/security/access_logger.py` | `.env` / Secret Manager から設定を読み込み、シークレットを検証。セキュリティイベントを構造化ログへ記録。 |
| エントリポイント | `src/main.py` | 設定検証、GitHub 同期セットアップ、Discord Bot とヘルス分析スケジューラを起動。 |
| 遅延ロード | `src/utils/lazy_loader.py` | `AIProcessor` や `GarminClient` をメモリ有効期間付きで共有。 |

---

## Discord Bot (`src/bot/`)

- **`DiscordBot` (`client.py`)**: Slash コマンド・イベントハンドラを登録し、`ChannelConfig` と `NotificationSystem` を管理。起動時にギルド専用コマンドへ同期。
- **`MessageProcessor` (`message_processor.py`)**: Discord メッセージからテキスト・添付・メタデータを抽出。URL、コードブロック、メンション、添付種別を解析。
- **ハンドラー群 (`handlers/`)**: 音声処理、ノート生成、ライフログ判定などを専用クラスに分離。重複処理を防ぎ、メトリクスを記録。
- **Slash コマンド (`commands/`)**: 基本操作、設定、統計、家計、タスク、統合管理をカテゴリ別に実装。`CommandMixin` がレスポンス統一やエラーハンドリングを提供。
- **モニタリング (`metrics.py`)**: API 利用状況やシステムメトリクスを追跡し、コマンド応答に反映。

---

## AI パイプライン (`src/ai/`)

- **`AIProcessor`**: Gemini API 呼び出し、LRU キャッシュ、キュー処理、レート上限監視。`ProcessingSettings` で閾値やトークン上限を制御。
- **`GeminiClient`**: `google-genai` SDK の薄いラッパー。エラーハンドリングと再試行を統一。
- **`AdvancedNoteAnalyzer`**: ノート分類、洞察生成、関連ノート推定を担当。Obsidian マネージャと連携。
- **`url_processor`**: aiohttp + BeautifulSoup でリンク先のタイトル/メタディスクリプション/本文を取得。
- **`vector_store`**: Vault から TF-IDF ベクターストアを構築し、類似ノート探索や検索支援に利用。

---

## Obsidian サブシステム (`src/obsidian/`)

- **`ObsidianFileManager`**: Markdown 読み書き、フロントマターのマージ、添付ファイル管理。
- **`TemplateEngine`**: デフォルトテンプレート生成、カスタムテンプレート読み込み、プレースホルダー置換。
- **`DailyNoteIntegration`**: 日次ノートへの統合、統計値更新、ToC セクションの生成。
- **`analytics/vault_statistics.py`**: Vault 全体のノート数、タグ頻度、平均サイズなどを集計し、Slash コマンドから参照。
- **`github_sync.py`**: GitHub リポジトリとの同期。起動時の pull、終了時の push、`.gitignore` セットアップを自動化。

---

## 外部連携とライフログ (`src/lifelog/`, `src/integrations/`, `src/health_analysis/`)

- **`IntegrationManager`**: 連携ごとの設定 (`IntegrationSettings`) と認証情報 (`IntegrationCredentials`) を暗号化ファイルで管理。Garmin/Calendar/Financial パイプラインをプラグインとして登録。
- **`IntegrationSyncScheduler`**: APScheduler ベースの簡易スケジューラで各連携の同期ジョブを管理。Slash コマンドからステータスを確認。
- **`LifelogManager`**: ライフログデータを JSON で永続化し、`LifelogAnalyzer` が習慣・目標・気分の統計を提供。
- **健康分析 (`health_analysis/`)**: `HealthDataAnalyzer` が Garmin データを解析し、`HealthActivityIntegrator` が Obsidian ノートにまとめる。`HealthAnalysisScheduler` がバックグラウンドで実行。

---

## 生産性ツール

- **タスク管理 (`src/tasks/`)**: `TaskManager`, `ScheduleManager` が Obsidian ノートを元にタスク作成・更新・統計を行う。Slash コマンドで CRUD 操作・統計照会が可能。
- **家計管理 (`src/finance/`)**: 支出、収入、定期購入、予算を `ExpenseManager`, `SubscriptionManager`, `BudgetManager` が扱う。Slash コマンドで記録とサマリー表示。

---

## モニタリングとセキュリティ

- **`monitoring/health_server.py`**: Bot の稼働状態を HTTP で公開する軽量ヘルスチェックサーバ（デフォルト 8080）。
- **`security/access_logger.py`**: 起動や認証失敗などの重要イベントを JSON 形式で記録。Secret Manager 操作もロギング対象。
- **`security/simple_admin.py`**: CLI からのシークレット確認・更新のための補助ユーティリティ。

---

## データフローとストレージ

| データ種別 | 保存先 | 備考 |
| --- | --- | --- |
| Obsidian ノート | `obsidian_vault_path` 配下 (`.md`) | YAML フロントマター + Markdown。本体は Git 同期可能。 |
| 添付ファイル | `80_Attachments/` 以下 | 画像/音声/その他でディレクトリ分割。 |
| ライフログデータ | `vault/90_Meta/lifelog_data/*.json` | `LifelogManager` が JSON として永続化。 |
| 連携設定/認証情報 | `~/.mindbridge/integrations/` | 設定は平文 JSON、資格情報は Fernet で暗号化。 |
| ログ | `logs/` | アプリケーションログ、音声処理ログ、calendar 認証ログなど。 |

---

## 設計上の特徴

- **非同期 I/O**: Discord、AI、ファイル操作、HTTP 呼び出しはすべて `asyncio` で統一。
- **遅延初期化**: `get_component_manager()` が高コストなクライアントを必要時に生成し、TTL ごとに再利用。
- **耐障害性**: 主要処理は例外を吸収し、UI 側にエラーを返す際もログとメトリクスを記録。外部サービスの失敗はフォールバック（例: 音声ファイル保存）のみで継続。
- **構成のカスタマイズ性**: テンプレート、チャンネル構成、AI モデル、Vault 階層は設定ファイルで調整可能。
- **監査ログ**: セキュリティ関連イベントは `log_security_event` を通じて追跡し、モニタリング容易性を確保。

この構造により、Discord の入力から Obsidian ノート生成までを一貫して自動化しつつ、外部サービスのデータ同期や統計表示も単一ランタイムで提供します。
