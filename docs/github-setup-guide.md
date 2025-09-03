# 🚀 GitHub 無料永続化設定ガイド

MindBridge で **完全無料** での Obsidian データ永続化を設定する方法です。

## 📋 概要

このシステムは GitHub リポジトリを使って Obsidian vault の内容を永続化します。

### ✅ メリット
- **完全無料** (プライベートリポジトリも無料)
- **容量**: 1GB まで無料 (通常の Obsidian vault には十分)
- **自動同期**: アプリの起動・終了時に自動でバックアップ・復元
- **バージョン管理**: Git 履歴で変更追跡可能
- **高い信頼性**: GitHub の高い可用性

### ❌ デメリット
- 大きなファイル (画像・動画) には不向き
- 初回設定が必要

---

## 🔧 設定手順

### ステップ 1: GitHub Personal Access Token の作成

1. [GitHub Settings](https://github.com/settings/tokens) にアクセス
2. 「 Generate new token (classic) 」をクリック
3. 設定:
   - **Note**: `obsidian-bot-token`
   - **Expiration**: `No expiration` (または適切な期間)
   - **Scopes**: `repo` (Full control of private repositories) にチェック
4. 「 Generate token 」をクリック
5. **トークンをコピーして保存** (再表示されません！)

### ステップ 2: バックアップ用リポジトリの作成

1. [GitHub](https://github.com) で新しいリポジトリを作成
2. 設定:
   - **Repository name**: `obsidian-vault-backup` (または任意の名前)
   - **Visibility**: `Private` (推奨)
   - **Initialize**: チェックなし (空のリポジトリ)
3. リポジトリ URL をコピー (例: `https://github.com/username/obsidian-vault-backup.git`)

### ステップ 3: 環境変数の設定

`.env` ファイルに以下を追加:

```bash
# GitHub Integration (FREE Data Persistence)
GITHUB_TOKEN=ghp_your_personal_access_token_here
OBSIDIAN_BACKUP_REPO=https://github.com/yourusername/obsidian-vault-backup.git
OBSIDIAN_BACKUP_BRANCH=main
GIT_USER_NAME=ObsidianBot
GIT_USER_EMAIL=bot@example.com
```

### ステップ 4: 動作確認

1. Bot を起動: `uv run python -m src.main`
2. ログで以下を確認:
   ```
   INFO Successfully restored vault from GitHub
   ```
3. Bot を停止: `Ctrl+C`
4. ログで以下を確認:
   ```
   INFO Successfully backed up vault to GitHub during shutdown
   ```

---

## 🔍 トラブルシューティング

### よくあるエラー

#### 1. `GitHub sync not configured`
```bash
# .env ファイルで GITHUB_TOKEN が設定されていることを確認
echo $GITHUB_TOKEN
```

#### 2. `Permission denied`
- Personal Access Token の `repo` スコープが有効か確認
- トークンが期限切れでないか確認

#### 3. `Repository not found`
- リポジトリ URL が正しいか確認
- リポジトリがプライベートの場合、アクセス権限があるか確認

#### 4. `Git command failed`
```bash
# Git がインストールされているか確認
git --version

# Git の初期設定
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

---

## ⚡ 高度な設定

### 定期自動バックアップ

10 分間隔での自動バックアップを有効にする場合:

```python
# src/bot/backup_system.py の初期化部分で
self.backup_destinations = [BackupDestination.GITHUB]
self.auto_backup_enabled = True
self.backup_interval_hours = 0.16  # 10 分間隔
```

### 手動同期コマンド

Discord コマンドで手動同期:

```bash
/backup_vault  # GitHub に手動バックアップ
```

### Cloud Run での設定

Cloud Run 環境での環境変数設定:

```bash
# Secret Manager に保存 (推奨)
gcloud secrets create github-token --data-file=<(echo -n "$GITHUB_TOKEN")

# または環境変数として直接設定
gcloud run deploy mindbridge \
  --set-env-vars="GITHUB_TOKEN=$GITHUB_TOKEN,OBSIDIAN_BACKUP_REPO=$REPO_URL"
```

---

## 📊 使用量とコスト

### GitHub 無料枠 (個人アカウント)
- **ストレージ**: 1GB (十分)
- **帯域幅**: 月 100GB (十分)
- **プライベートリポジトリ**: 無制限
- **API 制限**: 5000 リクエスト/時間 (十分)

### 実際の使用量 (推定)
- **一般的な Obsidian vault**: 10-50MB
- **1 日のバックアップ**: ~10 回 (起動・終了・定期)
- **月間 API 呼び出し**: ~300 回
- **月間帯域幅使用量**: ~100MB

**結論**: 通常使用では無料枠内で十分運用可能です。

---

## 🚨 セキュリティ注意事項

1. **Personal Access Token の管理**
   - `.env` ファイルを git に commit しない
   - トークンが漏洩した場合は即座に削除・再生成

2. **リポジトリの可視性**
   - バックアップリポジトリは **Private** に設定
   - 機密情報が含まれる可能性があるため

3. **定期的なメンテナンス**
   - トークンの期限確認
   - 不要な古いコミットの削除 (`git gc`)

---

## 🎯 まとめ

GitHub を使った無料永続化により:
- ✅ **0 円** でデータ永続化
- ✅ Cloud Run でもローカルでも同じ設定で動作
- ✅ 自動バックアップ・復元
- ✅ バージョン管理で変更履歴追跡

この設定により、完全無料で信頼性の高いデータ永続化システムが構築できます。
