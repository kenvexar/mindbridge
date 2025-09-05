# 🔧 トラブルシューティングガイド

MindBridgeの運用中に発生する可能性のある問題と解決方法を体系的に説明します。

## 📋 目次

1. [問題の分類と優先度](#問題の分類と優先度)
2. [セットアップ関連の問題](#セットアップ関連の問題)
3. [実行時の問題](#実行時の問題)
4. [パフォーマンス問題](#パフォーマンス問題)
5. [API関連の問題](#api関連の問題)
6. [ストレージ関連の問題](#ストレージ関連の問題)
7. [診断ツールとログ分析](#診断ツールとログ分析)
8. [緊急時の対応](#緊急時の対応)

## 🎯 問題の分類と優先度

### 緊急度分類

| レベル | 説明 | 対応時間 | 例 |
|--------|------|----------|-----|
| **P0 - 緊急** | サービス完全停止 | 即座 | Bot起動不可、全機能停止 |
| **P1 - 高** | 主要機能停止 | 1時間以内 | AI処理不可、ファイル保存不可 |
| **P2 - 中** | 一部機能不具合 | 4時間以内 | 音声認識不可、コマンド一部不動作 |
| **P3 - 低** | パフォーマンス劣化 | 24時間以内 | 処理速度低下、メモリ使用量増大 |

## 🚀 セットアップ関連の問題

### ボットが起動しない

**症状:**
```bash
uv run python -m src.main
# エラーメッセージが表示されて終了
```

#### 原因1: Python依存関係の問題

**診断:**
```bash
# Pythonバージョン確認
python --version  # 3.13以上が必要

# 依存関係確認
uv pip list | grep discord
uv pip list | grep pydantic
```

**解決方法:**
```bash
# 依存関係を完全に再インストール
rm uv.lock
uv cache clean
uv sync --reinstall

# 特定パッケージの再インストール
uv pip uninstall discord.py
uv pip install discord.py
```

#### 原因2: 環境変数の設定ミス

**診断:**
```bash
# 必須環境変数の確認
echo $DISCORD_BOT_TOKEN
echo $GEMINI_API_KEY
echo $OBSIDIAN_VAULT_PATH

# .envファイルの確認
cat .env | grep -E "(DISCORD_|GEMINI_|OBSIDIAN_)"
```

**解決方法:**
```bash
# .envファイルの構文チェック
python -c "
import os
from dotenv import load_dotenv
load_dotenv('.env')
print('DISCORD_BOT_TOKEN:', len(os.getenv('DISCORD_BOT_TOKEN', '')) > 0)
print('GEMINI_API_KEY:', len(os.getenv('GEMINI_API_KEY', '')) > 0)
"

# 環境変数を直接設定してテスト
export DISCORD_BOT_TOKEN="your_token"
export GEMINI_API_KEY="your_key"
uv run python -m src.main
```

#### 原因3: ポート競合

**診断:**
```bash
# 8080ポートの使用確認
lsof -i :8080
netstat -tulpn | grep :8080
```

**解決方法:**
```bash
# 競合プロセスの終了
pkill -f "python -m src.main"

# 別ポートの使用
export PORT=8081
uv run python -m src.main
```

### Discord認証エラー

**症状:**
```
discord.errors.LoginFailure: Improper token has been passed.
```

**診断手順:**

1. **トークンの妥当性確認:**
```bash
# トークンの長さチェック（正常: 70文字程度）
echo $DISCORD_BOT_TOKEN | wc -c

# Discord Developer Portalでトークン再確認
curl -H "Authorization: Bot $DISCORD_BOT_TOKEN" \
     https://discord.com/api/v10/users/@me
```

2. **Bot権限の確認:**
- Discord Developer Portalで以下を確認:
  - Bot権限が正しく設定されている
  - OAuth2 URLで適切なスコープが選択されている
  - ボットがサーバーに正しく招待されている

**解決方法:**
```bash
# 新しいトークンの生成
# 1. Discord Developer Portalでトークンを再生成
# 2. .envファイルを更新
# 3. ボットを再起動
```

### Obsidian Vaultアクセスエラー

**症状:**
```
FileNotFoundError: Vault path does not exist
PermissionError: Permission denied
```

**診断:**
```bash
# パスの存在確認
ls -la "$OBSIDIAN_VAULT_PATH"

# 権限確認
stat "$OBSIDIAN_VAULT_PATH"

# 書き込みテスト
touch "$OBSIDIAN_VAULT_PATH/test.md"
rm "$OBSIDIAN_VAULT_PATH/test.md"
```

**解決方法:**
```bash
# ディレクトリ作成
mkdir -p "$OBSIDIAN_VAULT_PATH"

# 権限修正
chmod 755 "$OBSIDIAN_VAULT_PATH"

# 所有者変更（必要に応じて）
sudo chown $USER:$USER "$OBSIDIAN_VAULT_PATH"

# フォルダ構造の初期化
mkdir -p "$OBSIDIAN_VAULT_PATH"/{00_Inbox,01_DailyNotes,02_Tasks,03_Ideas,10_Knowledge,11_Projects,12_Resources,20_Finance,21_Health,30_Archive,80_Attachments,90_Meta}
```

## ⚡ 実行時の問題

### メッセージが処理されない

**症状:** Discordにメッセージを投稿してもObsidianに保存されない

#### レベル1診断

```bash
# ボットの動作状況確認
# Discordで以下のコマンドを実行:
/status
/ping

# ログの確認
tail -f logs/bot.log | grep -E "(ERROR|WARNING)"
```

#### レベル2診断

```bash
# チャンネル設定の確認
echo $CHANNEL_INBOX
echo $CHANNEL_VOICE

# Bot権限の確認
# Discord Developer Portalで確認:
# - Send Messages: ✓
# - Read Message History: ✓
# - Attach Files: ✓
# - Use Slash Commands: ✓
```

#### レベル3診断

```bash
# 詳細ログの有効化
export LOG_LEVEL=DEBUG
uv run python -m src.main

# 特定チャンネルでのテスト
# テストメッセージ: "テスト - $(date)"
```

**解決方法:**

1. **チャンネルID間違い:**
```bash
# 正しいチャンネルIDの取得
# 1. Discord開発者モード有効化
# 2. チャンネル右クリック → "IDをコピー"
# 3. .envファイル更新
```

2. **Bot権限不足:**
```bash
# ボットを再招待
# 1. Discord Developer Portal → OAuth2 → URL Generator
# 2. 必要な権限を全て選択
# 3. 生成されたURLでボットを再招待
```

### AI処理の失敗

**症状:**
```
AIError: Processing failed
API key not valid
429 Too Many Requests
```

#### Gemini API制限エラー

**診断:**
```bash
# API使用量確認
# Discordコマンド: /ai_stats

# 現在のAPI制限設定確認
echo $GEMINI_API_DAILY_LIMIT
echo $GEMINI_API_MINUTE_LIMIT
```

**解決方法:**
```bash
# レート制限の調整
export GEMINI_API_MINUTE_LIMIT=10  # デフォルト15を10に減らす

# キャッシュのクリア（重複処理を避ける）
# Discordコマンド: /clear_cache

# 手動でのAPI接続テスト
python -c "
import google.generativeai as genai
genai.configure(api_key='$GEMINI_API_KEY')
model = genai.GenerativeModel('gemini-pro')
response = model.generate_content('Hello')
print(response.text)
"
```

### 音声処理の失敗

**症状:** 音声ファイルをアップロードしても文字起こしされない

**診断:**
```bash
# Google Cloud Speech API設定確認
echo $GOOGLE_APPLICATION_CREDENTIALS
ls -la "$GOOGLE_APPLICATION_CREDENTIALS"

# サービスアカウントキーの有効性確認
python -c "
from google.cloud import speech
client = speech.SpeechClient()
print('Google Cloud Speech client initialized successfully')
"
```

**解決方法:**
```bash
# 1. 音声機能を無効化（一時的）
export MOCK_SPEECH_ENABLED=true

# 2. サービスアカウントキーの再設定
# Google Cloud Consoleで新しいキーを生成
# 環境変数を更新

# 3. 音声ファイル形式の確認
# 対応形式: MP3, WAV, FLAC, OGG, M4A, WEBM
```

## 📊 パフォーマンス問題

### 処理速度の低下

**症状:** メッセージ処理に通常より時間がかかる

**診断:**
```bash
# システムリソース確認
top -p $(pgrep -f "python -m src.main")
free -h
df -h

# Bot統計確認
# Discordコマンド: /system_metrics
```

**解決方法:**

1. **メモリ不足:**
```bash
# メモリクリア
# Discordコマンド: /clear_cache

# プロセス再起動
pkill -f "python -m src.main"
uv run python -m src.main
```

2. **ディスク容量不足:**
```bash
# 古いログファイルの削除
find logs/ -name "*.log" -mtime +30 -delete

# Obsidianボルトのクリーンアップ
find "$OBSIDIAN_VAULT_PATH" -name "*.tmp" -delete
```

3. **API制限による遅延:**
```bash
# 並行処理数の調整
export MAX_CONCURRENT_AI_REQUESTS=3  # デフォルト5を3に減らす
```

### メモリリーク

**症状:** 時間経過とともにメモリ使用量が増大

**診断:**
```bash
# メモリ使用量の監視
while true; do
    ps aux | grep "python -m src.main" | grep -v grep
    sleep 60
done

# Python メモリプロファイリング
python -m memory_profiler src/main.py
```

**解決方法:**
```bash
# 定期的なプロセス再起動の設定
# crontabで4時間ごとに再起動
0 */4 * * * /path/to/restart_bot.sh

# restart_bot.sh の内容:
#!/bin/bash
pkill -f "python -m src.main"
sleep 5
cd /path/to/mindbridge
uv run python -m src.main &
```

## 🌐 API関連の問題

### Discord API エラー

**症状:**
```
discord.errors.HTTPException: 429 Too Many Requests
discord.errors.Forbidden: 403 Forbidden
```

**解決方法:**

1. **レート制限:**
```bash
# Discord APIレート制限の確認と調整
# Bot内部でのレート制限処理は自動実装済み
# 手動でのメッセージ送信頻度を調整
```

2. **権限不足:**
```bash
# Bot権限の再確認
# Discord サーバー設定 → 役職 → Bot役職の権限確認
```

### Google API エラー

**症状:**
```
google.api_core.exceptions.Unauthenticated
google.api_core.exceptions.ResourceExhausted
```

**解決方法:**
```bash
# 1. 認証情報の確認
gcloud auth list
gcloud config list

# 2. プロジェクト設定の確認
gcloud config set project YOUR_PROJECT_ID

# 3. API有効化の確認
gcloud services list --enabled | grep -E "(speech|generativeai)"
```

## 💾 ストレージ関連の問題

### ファイル保存エラー

**症状:**
```
OSError: [Errno 28] No space left on device
PermissionError: [Errno 13] Permission denied
```

**解決方法:**

1. **ディスク容量不足:**
```bash
# 容量確認
df -h
du -sh "$OBSIDIAN_VAULT_PATH"

# クリーンアップ
find "$OBSIDIAN_VAULT_PATH" -name "*.backup" -mtime +30 -delete
find logs/ -name "*.log" -mtime +7 -delete
```

2. **権限問題:**
```bash
# 権限の修正
sudo chown -R $USER:$USER "$OBSIDIAN_VAULT_PATH"
chmod -R 755 "$OBSIDIAN_VAULT_PATH"
```

### ファイル破損

**症状:** Obsidianノートが開けない、内容が不正

**診断:**
```bash
# ファイル整合性チェック
find "$OBSIDIAN_VAULT_PATH" -name "*.md" -exec file {} \;

# 破損ファイルの特定
find "$OBSIDIAN_VAULT_PATH" -name "*.md" -size 0
```

**解決方法:**
```bash
# バックアップからの復元
# Discordコマンド: /backup_vault
# 最新のバックアップファイルを確認して復元

# 自動バックアップの有効化
export AUTO_BACKUP_ENABLED=true
export BACKUP_INTERVAL_HOURS=6
```

## 🔍 診断ツールとログ分析

### ログレベルの調整

```bash
# デバッグログの有効化
export LOG_LEVEL=DEBUG
export LOG_FORMAT=json  # 構造化ログ

# 特定モジュールのみデバッグ
export DEBUG_MODULES="ai,obsidian"
```

### 診断用スクリプト

```bash
#!/bin/bash
# diagnosis.sh - 総合診断スクリプト

echo "=== MindBridge 診断 ==="

# 1. 環境確認
echo "1. 環境確認"
python --version
uv --version
echo "DISCORD_BOT_TOKEN: $(echo $DISCORD_BOT_TOKEN | head -c 10)..."
echo "GEMINI_API_KEY: $(echo $GEMINI_API_KEY | head -c 10)..."

# 2. ファイルシステム
echo "2. ファイルシステム"
ls -la "$OBSIDIAN_VAULT_PATH" || echo "Vault path not accessible"
df -h | grep -E "(Filesystem|/)"

# 3. ネットワーク接続
echo "3. ネットワーク接続"
curl -s -o /dev/null -w "%{http_code}" https://discord.com/api/v10/gateway
curl -s -o /dev/null -w "%{http_code}" https://generativelanguage.googleapis.com

# 4. プロセス状態
echo "4. プロセス状態"
ps aux | grep "python -m src.main" | grep -v grep

# 5. ログエラー
echo "5. 最近のエラー"
tail -n 50 logs/bot.log | grep -E "(ERROR|CRITICAL)" | tail -n 5

echo "=== 診断完了 ==="
```

### ログ分析コマンド

```bash
# エラーパターンの分析
grep -E "(ERROR|CRITICAL)" logs/bot.log | tail -20

# API使用量の分析
grep "AI_REQUEST" logs/bot.log | grep "$(date +%Y-%m-%d)" | wc -l

# パフォーマンス分析
grep "PROCESSING_TIME" logs/bot.log | awk '{print $NF}' | sort -n | tail -10

# 特定時間範囲のログ
grep "2025-08-17 10:" logs/bot.log
```

## 🚨 緊急時の対応

### サービス完全停止時

**即座に実行:**
```bash
# 1. プロセス確認
ps aux | grep "python -m src.main"

# 2. 強制終了
pkill -9 -f "python -m src.main"

# 3. 設定の最小化
cp .env .env.backup
cp .env.example .env
# 必須項目のみ設定

# 4. セーフモードで起動
export ENABLE_MOCK_MODE=true
export LOG_LEVEL=DEBUG
uv run python -m src.main
```

### データ復旧

**バックアップからの復元:**
```bash
# 1. 利用可能なバックアップの確認
ls -la backups/

# 2. 最新バックアップの復元
cp -r backups/latest/* "$OBSIDIAN_VAULT_PATH/"

# 3. 権限の修正
chmod -R 755 "$OBSIDIAN_VAULT_PATH"
```

### 緊急連絡先

| 問題カテゴリ | 連絡先 | 対応時間 |
|-------------|-------|----------|
| **システム障害** | GitHub Issues | 24時間以内 |
| **データ損失** | メンテナー直接連絡 | 即座 |
| **セキュリティ問題** | security@project.com | 即座 |

## 🔄 予防保守

### 定期チェック項目

**毎日:**
```bash
# ディスク容量チェック
df -h | grep -E "9[0-9]%"

# エラーログチェック
grep "ERROR" logs/bot.log | grep "$(date +%Y-%m-%d)" | wc -l
```

**毎週:**
```bash
# バックアップの実行
# Discordコマンド: /backup_vault

# 統計の確認
# Discordコマンド: /vault_stats
```

**毎月:**
```bash
# 依存関係の更新確認
uv sync --upgrade

# ログローテーション
find logs/ -name "*.log" -mtime +30 -delete
```

## 📚 参考資料

### 関連ドキュメント
- [システム監視ガイド](monitoring.md)
- [デプロイメントガイド](deployment.md)
- [設定オプション](configuration.md)

### 外部リソース
- [Discord API Status](https://discordstatus.com/)
- [Google Cloud Status](https://status.cloud.google.com/)
- [Discord.py Documentation](https://discordpy.readthedocs.io/)

### ログ出力例

**正常なログ:**
```json
{
  "timestamp": "2025-08-17T10:30:15Z",
  "level": "INFO",
  "message": "Message processed successfully",
  "user_id": "123456789",
  "channel_id": "987654321",
  "processing_time": 1.23
}
```

**エラーログ:**
```json
{
  "timestamp": "2025-08-17T10:31:20Z",
  "level": "ERROR",
  "message": "AI processing failed",
  "error": "API rate limit exceeded",
  "retry_after": 60
}
```

---

このトラブルシューティングガイドを使用して、問題を迅速に特定・解決してください。新しい問題パターンが発見された場合は、このドキュメントの更新も検討してください。
