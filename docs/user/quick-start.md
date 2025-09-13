# クイックスタート

最短 3 ステップでローカル実行できます。

## 1. 依存関係

```
uv sync --dev
```

## 2. 環境設定

対話式セットアップ:

```
./scripts/local-setup.sh
```

または `.env.example` をコピーして必須項目を記入:

```
cp .env.example .env
# 必須: DISCORD_BOT_TOKEN / GEMINI_API_KEY / OBSIDIAN_VAULT_PATH
```

## 3. 起動

```
./scripts/local-run.sh
# もしくは
make run
```

## 追加機能（任意）

- 音声認識（Google Cloud Speech-to-Text）: `.env.example` のキーを追記
- Garmin/Google Calendar 連携: 必要なキーを `.env` に追記

## よくある質問

- Discord チャンネルは最低 `#memo`, `#notifications`, `#commands` を作成してください。
- Vault パスは存在しない場合、自動作成されます。
- ログレベルを上げる場合は `.env` の `LOG_LEVEL=DEBUG` に変更してください。

## 参考: API キー取得手順（アンカー）

<a id="discord-bot-setup"></a>
### Discord Bot セットアップ

1. Discord Developer Portal で新規アプリ作成 → Bot 追加
2. Bot Token をコピー（`.env` の `DISCORD_BOT_TOKEN`）
3. OAuth2 → URL Generator で `bot` と `applications.commands` を選択し招待
4. 権限: Send Messages / Read Message History / Attach Files / Use Slash Commands / Message Content Intent

<a id="gemini-api-setup"></a>
### Gemini API セットアップ

1. Google AI Studio で API Key を作成
2. 取得したキーを `.env` の `GEMINI_API_KEY` に設定
