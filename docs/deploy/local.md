# ローカルデプロイガイド

開発や小規模運用で使うローカル実行と Docker Compose の手順をまとめました。

## 1. 共通準備
```bash
uv sync --dev              # 依存インストール
./scripts/manage.sh init   # .env を対話生成
```
`.env` に必須シークレットが入ります。音声/Garmin/Calendar など追加で使うものがあれば追記してください。

### ひとり運用のポイント
-.env だけで完結するため追加設定は不要。
- `.env` は権限を絞る (`chmod 600 .env`)。Git にはコミットしない。
- 最低限の例:
  ```env
  DISCORD_BOT_TOKEN=...
  DISCORD_GUILD_ID=...
  GEMINI_API_KEY=...
  OBSIDIAN_VAULT_PATH=/Users/you/Obsidian/MindBridge
  ```

## 2. `uv run` で直接動かす
```bash
./scripts/manage.sh run    # 内部で uv run python -m src.main
```
`Ctrl+C` で終了。GitHub バックアップが有効なら終了時に自動 push します。

特徴: 最軽量でコード変更が即反映。個人利用やデバッグに向きます。

## 3. Docker Compose で動かす
```bash
cp .env .env.docker                # 必要なら編集
docker compose up -d mindbridge
docker compose logs -f mindbridge
```
停止は `docker compose down`。ボリュームごと消すときは `docker compose down -v`。

ヒント:
- `.env.docker` ではパスをコンテナ内に合わせる（例: `OBSIDIAN_VAULT_PATH=/data/vault`）。
- SELinux Enforcing 環境ではボリュームの `:Z` オプションで権限エラーを防止（compose で設定済み）。
- 反映されない環境変数がある場合は `docker compose up -d --build` で再ビルド。

## 4. よくあるトラブル
| 症状 | 解決策 |
| --- | --- |
| Vault が作成されない | `OBSIDIAN_VAULT_PATH` の存在と権限を確認 |
| Slash コマンドが出ない | `DISCORD_GUILD_ID` を設定し、同期完了まで数十秒待つ |
| 音声文字起こしが落ちる | Speech API キー/サービスアカウントと `GOOGLE_APPLICATION_CREDENTIALS` のパスを確認 |
| 再起動で設定が消える | Docker の場合は `.env.docker` とボリュームマウントを再確認 (`docker compose config` が有効) |

## 5. モックモード（外部 API を呼ばない）
```env
ENABLE_MOCK_MODE=true
MOCK_DISCORD_ENABLED=true
MOCK_GEMINI_ENABLED=true
MOCK_GARMIN_ENABLED=true
MOCK_SPEECH_ENABLED=true
```
CI やオフライン検証で利用できます。

## 6. メンテとテスト
```bash
uv run pytest -q
uv run pytest --cov=src --cov-report=term-missing
uv run ruff check . --fix
uv run mypy src
./scripts/manage.sh clean --with-uv-cache   # キャッシュ掃除
```
手動テストが必要なシナリオは `docs/testing.md` を参照してください。
