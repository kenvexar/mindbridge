# プロジェクト整理サマリ

## 1. ディレクトリ構成の見直し
- トップレベル構造は大きく「ランタイム (src/)」「テスト (tests/)」「ドキュメント (docs/)」「DevOps (deploy/, scripts/, docker*)」の4系統で整理済み。
- `src/` 下のドメイン別パッケージは明確だが、ガーミン連携が `src/garmin` と `src/lifelog/integrations` に分散しているため、将来的に `src/integrations/`（外部サービス集約）へ再配置する余地あり。
- `docs/` 直下にデプロイ関連資料が重複 (`deployment.md` と `DEPLOYMENT_GUIDE.md`) しており、章立て統合とセクション分類 (`docs/guide/`, `docs/ops/` など) を行うと参照性が上がる。
- `tests/manual/` は検証スクリプトが増えているため、カテゴリ整理と README の整備を継続メンテナンス対象としている。
- `logs/` や `vault/` など生成物ディレクトリは `.gitkeep` のみ残し、その他キャッシュは CLI コマンドで削除できるようにした。

| パス | 主な役割 | 現状メモ | 推奨対応 |
| --- | --- | --- | --- |
| `src/ai/`, `src/audio/`, `src/bot/` | AI・音声・Discord Bot | モジュール別に整理済み | 各パッケージに README (概要/依存/テスト) を追加すると新規参入が容易 |
| `src/garmin/` & `src/lifelog/integrations/` | Garmin/外部連携 | ガーミン処理が二箇所に分散 | `src/integrations/garmin/` を新設し依存を一本化する計画を策定 |
| `docs/` | ドキュメント | ガイドと仕様が混在 | サブディレクトリ分類と重複ファイル統合 (`docs/deploy/` など) |
| `tests/manual/` | 手動テスト | カテゴリ別 README を継続的にメンテナンスする運用へ移行 | 将来的にディレクトリもカテゴリ別に分割検討 |
| `scripts/manage.sh` | CLI ユーティリティ | コマンド集中管理 | `clean` サブコマンドを追加済み（キャッシュ削除） |

## 2. 依存関係の棚卸し
| 区分 | パッケージ | 主用途 / 参照箇所 | 推奨アクション |
| --- | --- | --- | --- |
| 基盤 | `discord.py`, `PyNaCl` | Discord Bot / 音声機能 (`src/bot`, `src/audio`) | 必須。PyNaCl は音声送信に必要なため維持 |
| 基盤 | `google-genai`, `google-cloud-speech`, `garminconnect` | Gemini API, Speech-to-Text, Garmin 連携 (`src/ai`, `src/audio`, `src/garmin`) | バージョン追従のためマイナ更新監視を継続 |
| 基盤 | `pydantic`, `pydantic-settings`, `python-dotenv` | 設定管理 (`src/config/settings.py`) | `python-dotenv` は `env_file` 読み込みで必須。バージョン固定検討 |
| 基盤 | `aiofiles`, `aiohttp`, `tenacity`, `rich`, `structlog`, `pydub`, `python-dateutil`, `numpy`, `scikit-learn`, `beautifulsoup4`, `cryptography`, `pyyaml` | 各ドメイン機能で広範に使用 | 現状維持。`numpy`/`scikit-learn` はライフログ解析で利用中 |
| 任意 | `google-cloud-secret-manager` | 直接利用なし (`src/security/secret_manager` は環境変数のみ) | Optional エクストラへ移動し、実際に利用する場合は切替ドキュメントを追加 |
| 任意 | `google-api-python-client` 系 (optional extra) | Google API 連携 | 追加時のみ `uv sync --extra google-api` を案内済み |
| 開発 | `pytest` 系, `ruff`, `mypy`, 型スタブ | 開発/CI で使用 | 維持。新規プラグイン導入時は `tests/` に記載 |
| セキュリティ | `bandit`, `pip-audit`, `pip` (固定リビルド) | 任意利用 | `pip` は CVE 回避のため固定 rev を維持 |

### 依存アップデート方針
- Optional 化するパッケージは `[project.optional-dependencies]` に移し、`docs/development-guide.md` から参照リンクを張る。
- 追加で導入する場合は `docs/maintenance/housekeeping.md` を更新して履歴を残す。

## 3. タスク管理の整備
現在進行中のタスクはありません。

## 4. 参考コマンド
- ディレクトリ／キャッシュの整理: `./scripts/manage.sh clean`
- 依存の棚卸し: `uv pip list --tree`
- 使用状況確認: `rg -g"*.py" "<package or import>" src tests`
