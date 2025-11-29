# クイックスタート

ローカルで最短起動するための 3 ステップだけをまとめました。細かい設定は後で `USER_GUIDE.md` を参照してください。

## 前提
- Python 3.13 以上
- [uv](https://github.com/astral-sh/uv)
- Discord Bot（トークンとギルド ID）
- Google Gemini API キー
- Obsidian Vault を置くディレクトリ（書き込み可能）

## ステップ 1: 依存を入れる
```bash
uv sync --dev
```

## ステップ 2: .env を作る
```bash
./scripts/manage.sh init
```
対話プロンプトでトークンやパスを入力すると、ルートに `.env` が生成されます。主な項目:

| プロンプト | 例 | メモ |
| --- | --- | --- |
| Discord Bot Token | `abc.def.ghi` | Discord Developer Portal で取得 |
| Discord Guild ID | `123456789012345678` | Slash コマンドを同期するサーバ ID |
| Gemini API Key | `AIzaxxx` | Google AI Studio で発行 |
| Obsidian Vault path | `~/Obsidian/MindBridge` | ローカル保存先 |

## ステップ 3: 起動
```bash
./scripts/manage.sh run   # 内部で uv run python -m src.main
```
Discord の監視チャンネルに投稿し、`/status` が返ってくれば成功です。

## 動作確認チェック
- `/help` が表示される
- `/integration_status` で Garmin/Calendar 状態が見える（設定済みなら）
- Vault に新しい Markdown ができ、YAML フロントマターが付く
- `logs/` にランタイムログが追記される

## オプション設定の例
- 音声文字起こし: `GOOGLE_CLOUD_SPEECH_API_KEY` またはサービスアカウント JSON
- Garmin / Calendar: `GARMIN_EMAIL`, `GARMIN_PASSWORD`, `GOOGLE_CALENDAR_*`
- GitHub バックアップ: `GITHUB_TOKEN`, `OBSIDIAN_BACKUP_REPO`

より詳しい操作やトラブル対応は `docs/basic-usage.md` と `docs/USER_GUIDE.md` へ。
