# Local Deployment

## 事前準備
```bash
uv sync --dev
./scripts/manage.sh init
```

## Docker Compose
```bash
cp .env.docker.example .env.docker
Docker compose up -d
docker compose logs -f mindbridge
```

### よくあるトラブル
- 環境変数が同期されない: `.env.docker` を再生成し `docker compose up -d --build` を実行。
- Vault が作成されない: `.env.docker` の `OBSIDIAN_VAULT_PATH` をローカルパスに変更。

## 直接実行 (uv run)
```bash
uv sync --dev
./scripts/manage.sh init
uv run python -m src.main
```

### ヒント
- 開発中は `ENVIRONMENT=development` と `ENABLE_MOCK_MODE=1` を `.env` に設定すると API コストを抑えられる。
- 音声処理を行わない場合は `Settings.mock_speech_enabled` を使って `SpeechProcessor` をスキップ。

## ローカルテスト
```bash
uv run pytest -q
uv run pytest --cov=src --cov-report=term-missing
uv run ruff check . --fix
uv run mypy src
```

追加で実運用に近い確認が必要な場合は `tests/manual/README.md` を参照し、音声・Garmin・カレンダーの手動テストを実行してください。
