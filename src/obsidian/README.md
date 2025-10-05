# Obsidian

## 概要
- Obsidian Vault とのファイル同期、テンプレート適用、ノート生成を担当します。
- Daily note の自動生成やバックアップ、GitHub 連携を含む幅広いファイル操作ユーティリティを提供します。

## 主要モジュール
| モジュール | 説明 |
| --- | --- |
| `file_manager.py` | Vault 内のファイル作成・更新・削除を担う中心クラス |
| `daily_integration.py` | 日次ノートへのタスク/ログ統合ロジック |
| `template_system/` | YAML フロントマター生成とテンプレート処理 |
| `backup/backup_manager.py` | GitHub やローカルバックアップ処理 |
| `analytics/vault_statistics.py` | Vault 統計情報の収集 |
| `github_sync.py` | GitHub リポジトリとの同期制御 |
| `search/note_search.py` | ノート全文検索とメタ情報取得 |

## 外部依存
- `aiofiles`, `pyyaml`, `structlog`, `aiohttp` (GitHub API) 。
- GitHub 連携では `SecureSettingsManager` 経由で `GITHUB_TOKEN` を取得。

## テスト
- 単体テスト: `tests/unit/test_obsidian.py`, `tests/unit/test_yaml_generator.py`, `tests/unit/test_daily_integration.py`。
- 手動テスト: `tests/manual/test_manage.sh`, `tests/manual/test_voice_memo.py`（ノート生成確認）。

## 連携・利用箇所
- AI からの生成結果をノートに書き込む (`src/ai/note_analyzer.py`)。
- Health/Lifelog/Tasks の各統合で Vault を経由したデータ保存を実施。

## メモ
- デプロイ資料統合後に `docs/deploy/` への参照リンク更新が必要。
- Vault パスが存在しない場合は `Settings.obsidian_vault_path` に基づき自動作成。
