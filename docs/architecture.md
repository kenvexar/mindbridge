# アーキテクチャ概要

「投稿を受け取ってノートにするまで」の流れを中心に、主要コンポーネントの役割を整理します。

## 全体フロー
1. **Discord** — Slash コマンドとメッセージを受信。
2. **MessageProcessor** — テキスト整形・メタデータ抽出・添付処理。
3. **AIProcessor / AdvancedNoteAnalyzer** — Gemini で要約・タグ・カテゴリ、類似ノート推定。
4. **TemplateEngine** — YAML フロントマターと本文を組み立てた Markdown を生成。
5. **ObsidianFileManager** — Vault へ保存し、必要に応じて Daily Note に統合。
6. **Schedulers & Integrations** — Garmin / Calendar などの同期やヘルス分析をバックグラウンドで実行。
7. **Monitoring** — `/status` と HTTP ヘルスサーバが稼働状況を返し、セキュリティログを記録。

`src/main.py` が設定とシークレットを読み込み、Discord Bot・スケジューラ・ヘルスサーバをまとめて起動します。高コストなクライアントは遅延初期化され、TTL 付きで共有されます。

## レイヤー別の主役
| レイヤー | モジュール | 役割 |
| --- | --- | --- |
| 設定/セキュリティ | `src/config/settings.py`, `src/config/secure_settings.py`, `src/security/access_logger.py` | `.env` による設定・シークレット読み込みと監査ログ出力 |
| エントリポイント | `src/main.py` | 設定検証、GitHub 同期セットアップ、Bot/スケジューラ起動 |
| Discord Bot | `src/bot/client.py`, `src/bot/message_processor.py`, `src/bot/commands/*`, `src/bot/handlers/*` | Slash コマンドとメッセージ処理、通知、統計、音声・ノート生成ハンドラ |
| AI パイプライン | `src/ai/ai_processor.py`, `src/ai/gemini_client.py`, `src/ai/advanced_note_analyzer.py`, `src/ai/url_processor.py` | Gemini 呼び出し、レート制御、キャッシュ、URL 解析、類似ノート推定 |
| Obsidian | `src/obsidian/obsidian_file_manager.py`, `src/obsidian/template_system/`, `src/obsidian/daily_note_integration.py`, `src/obsidian/analytics/vault_statistics.py`, `src/obsidian/github_sync.py` | Markdown 生成・保存、テンプレート、日次統合、統計、GitHub 同期 |
| 連携/ライフログ | `src/integrations/`, `src/lifelog/`, `src/health_analysis/` | Integration Manager と Scheduler、Garmin/Calendar、健康データ解析、ライフログ管理 |
| 生産性ツール | `src/tasks/`, `src/finance/` | タスク・家計の CRUD と集計を Slash コマンドで提供 |
| モニタリング | `src/monitoring/health_server.py`, `src/bot/metrics.py` | HTTP ヘルスチェック、コマンド応答でのメトリクス表示 |

## データの置き場
| 種別 | 保存先 | 補足 |
| --- | --- | --- |
| ノート | `OBSIDIAN_VAULT_PATH` 配下（`.md`） | YAML フロントマター + Markdown |
| 添付 | `80_Attachments/` 以下 | 画像/音声/その他でサブフォルダ分け |
| ライフログ | `vault/90_Meta/lifelog_data/*.json` | JSON 永続化 |
| 連携設定・資格情報 | `~/.mindbridge/integrations/` | 設定は平文、資格情報は暗号化 JSON |
| ログ | `logs/` | アプリ/セキュリティ/音声/認証ログなど |

## 設計のポイント
- **非同期 I/O**: Discord・AI・ファイル・HTTP を asyncio で統一。
- **遅延初期化**: 使うまで重いクライアントを作らない。TTL で再利用。
- **フォールバック重視**: 外部サービスが落ちても、最低限のノート保存は続行。
- **カスタマイズ性**: テンプレート、チャンネル構成、AI モデル、Vault 階層を設定で切り替え可能。
- **監査性**: セキュリティイベントを構造化ログに記録し、運用時の追跡性を確保。

より細かなモジュール説明は各 `src/<package>/README.md` やソースコメントを参照してください。
