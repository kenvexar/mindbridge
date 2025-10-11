# ローカルデプロイガイド

MindBridge をローカル環境で実行する方法をまとめます。開発・検証・短期運用に最適です。

## 1. 共通準備

```bash
uv sync --dev              # 依存関係のインストール
./scripts/manage.sh init   # .env を生成し必須シークレットを登録
```

`./scripts/manage.sh init` はローカル用の `.env` を作成します。必要に応じて `GOOGLE_CLOUD_SPEECH_API_KEY` や `GARMIN_EMAIL` などを追記してください。

### 個人運用（Secret Manager なし）のポイント

- 既定の `SECRET_MANAGER_STRATEGY=env` を維持すれば、すべての資格情報を `.env` で完結できます。
- `.env` は `chmod 600 .env` などで権限を絞り、Git にはコミットしないでください。
- 推奨サンプル:
  ```env
  DISCORD_BOT_TOKEN=xxxxxxxxxxxxxxxx
  DISCORD_GUILD_ID=123456789012345678
  GEMINI_API_KEY=xxxxx-yyyyy-zzzzz
  OBSIDIAN_VAULT_PATH=/Users/you/Obsidian/Vault
  SECRET_MANAGER_STRATEGY=env
  ```
- Garmin や Google Calendar など追加連携を使う場合は `.env` に追記し、`./scripts/manage.sh run` で再起動すると値が再読込されます。

---

## 2. `uv run` で直接実行

### 起動

```bash
./scripts/manage.sh run    # 内部的には uv run python -m src.main
```

### 停止

キーボード割り込み（`Ctrl+C`）で安全に終了できます。終了時に GitHub バックアップが有効なら自動で push されます。

### 特徴

- 最も軽量でコード変更が即反映。
- 依存関係はすべてローカルの Python 仮想環境上に配置。
- `.env` のみで Secret を管理するため、個人使用や開発検証に最適。

---

## 3. Docker Compose で実行

### 設定と起動

```bash
cp .env .env.docker                # もしくは .env.docker.example をベースに編集
docker compose up -d mindbridge

# ログを確認
docker compose logs -f mindbridge
```

### 停止・クリーンアップ

```bash
docker compose down          # コンテナ停止
docker compose down -v       # ボリュームも削除
```

### ヒント

- `.env.docker` では `OBSIDIAN_VAULT_PATH=/data/vault` などコンテナ内パスを指定し、`docker-compose.yml` のボリュームマウントでローカルディレクトリに接続します。
- 環境変数が反映されない場合は `docker compose up -d --build` でイメージを再ビルドしてください。

---

## 4. よくあるトラブル

| 症状 | 解決策 |
| --- | --- |
| Vault が作成されない | `.env` / `.env.docker` の `OBSIDIAN_VAULT_PATH` が存在するか、権限があるかを確認。 |
| Slash コマンドが表示されない | `DISCORD_GUILD_ID` を設定し、Bot を再起動。同期には数十秒かかる場合があります。 |
| 音声文字起こしに失敗 | Speech API キーやサービスアカウント JSON を設定し、`GOOGLE_APPLICATION_CREDENTIALS` のパスが正しいか確認。 |
| 再起動で設定が消える | Docker の場合は `.env.docker` とボリュームのマウントを確認。`docker compose config` で最終設定を確認可能。 |

---

## 5. モックモード

外部 API への接続を避けたい場合は `.env` に以下を追加します。

```env
ENABLE_MOCK_MODE=true
MOCK_DISCORD_ENABLED=true
MOCK_GEMINI_ENABLED=true
MOCK_GARMIN_ENABLED=true
MOCK_SPEECH_ENABLED=true
```

モックモードでは Discord 実接続を行わず、AI/Garmin/音声処理がスタブレスポンスを返します。統合テストや CI での使用を想定しています。

---

## 6. テストとメンテナンス

```bash
uv run pytest -q
uv run pytest --cov=src --cov-report=term-missing
uv run ruff check . --fix
uv run mypy src
```

不要になったキャッシュや生成物は `./scripts/manage.sh clean --with-uv-cache` で削除できます。手動テストが必要なシナリオは `docs/testing.md` の「手動テスト」セクションを参照してください。
