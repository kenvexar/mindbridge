# クイックスタート

最短 3 ステップで MindBridge をローカル起動します。詳細なセットアップは `docs/USER_GUIDE.md` を参照してください。

## 前提条件

- Python 3.13 以上
- [uv](https://github.com/astral-sh/uv) パッケージマネージャー
- Discord Bot（トークンとギルド ID）
- Google Gemini API キー
- Obsidian Vault 用の書き込み可能なディレクトリ

## 1. 依存関係インストール

```bash
uv sync --dev
```

## 2. 環境設定（.env 自動生成）

```bash
./scripts/manage.sh init
```

対話式に最低限のシークレット（Discord/Gemini など）を登録します。生成された `.env` はルートに保存されます。

## 3. ローカル起動

```bash
./scripts/manage.sh run    # 内部的に uv run python -m src.main を実行
```

起動後は Discord の `#memo` チャンネルにメッセージを投稿すると AI が自動でノート化します。`/status` Slash コマンドで稼働状況を確認してください。

## 動作確認のチェックリスト

- `/help` が利用可能で、コマンド一覧が表示される。
- `/integration_status` で Garmin/Calendar などの状態が取得できる（設定済みの場合）。
- Vault に新しい Markdown ファイルが作成され、YAML フロントマターが付与される。
- `logs/` にランタイムログが追記される。

## オプション機能

- 音声文字起こしを有効化する場合は `.env` に `GOOGLE_CLOUD_SPEECH_API_KEY` またはサービスアカウント JSON を設定。
- Garmin / Google Calendar を使う場合は `./scripts/manage.sh init` でスキップした項目を `.env` に追加し、必要に応じて `./scripts/manage.sh secrets` で Secret Manager に登録。
- GitHub バックアップを利用する場合は `GITHUB_TOKEN` と `OBSIDIAN_BACKUP_REPO` を設定。

## 次のステップ

- Slash コマンドや追加機能は `docs/basic-usage.md` を参照。
- 外部連携、テンプレート、Troubleshooting は `docs/USER_GUIDE.md` に詳しく記載しています。
