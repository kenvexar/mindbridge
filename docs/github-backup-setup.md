# GitHub バックアップ設定ガイド

## 概要

MindBridge Bot は Obsidian vault を GitHub リポジトリに自動バックアップする機能を提供します。 Discord で作成されたメモやタスクが自動的に GitHub に保存され、データの永続化と履歴管理が可能になります。

## 前提条件

1. GitHub アカウント
2. Google Cloud プロジェクトでの MindBridge 環境

## セットアップ手順

### 1. GitHub Personal Access Token の作成

1. GitHub にログインし、[Personal Access Tokens](https://github.com/settings/tokens) にアクセス
2. **"Generate new token (classic)"** をクリック
3. トークン設定:
   - **Token name**: `MindBridge Obsidian Sync`
   - **Expiration**: `No expiration` (推奨) または適切な期限
   - **Select scopes**:
     - ✅ `repo` - Full control of private repositories
     - ✅ `workflow` - Update GitHub Action workflows
4. **"Generate token"** をクリック
5. 生成されたトークンをコピー（**一度しか表示されません**）

### 2. GitHub リポジトリの作成

1. GitHub で新しいリポジトリを作成
2. リポジトリ設定:
   - **Repository name**: `obsidian-vault` (推奨)
   - **Visibility**: `Private` (推奨)
   - **Initialize**: README やライセンスは不要
3. リポジトリ URL をコピー（例: `https://github.com/username/obsidian-vault.git`）

### 3. シークレットの設定

専用スクリプトを使用してシークレットを設定します：

```bash
./scripts/setup-github-secrets.sh
```

または手動で設定：

```bash
# GitHub Personal Access Token
echo -n "YOUR_ACTUAL_GITHUB_TOKEN" | gcloud secrets create github-token --data-file=- --project=mindbridge-469901

# GitHub リポジトリ URL
echo -n "https://github.com/YOUR_USERNAME/obsidian-vault.git" | gcloud secrets create obsidian-backup-repo --data-file=- --project=mindbridge-469901
```

### 4. Cloud Run サービスの再デプロイ

```bash
./scripts/deploy.sh
```

## 機能概要

### 自動バックアップ

- **トリガー**: Discord でメモ、タスク、ファイルが作成された時
- **頻度**: リアルタイム（メッセージ処理後即座に）
- **対象ファイル**: 
  - Markdown ノート（`.md`）
  - 画像ファイル
  - 音声ファイル（音声メモの文字起こし含む）
  - その他のアップロードファイル

### Git 履歴管理

- **コミット形式**: `Add: [ファイル名] - [日付時刻]`
- **ブランチ**: `main`（デフォルト）
- **作者**: `MindBridge Bot <mindbridge-bot@example.com>`

### ディレクトリ構造

```
obsidian-vault/
├── Memos/              # 一般的なメモ
├── Tasks/              # タスク管理
├── Finance/            # 家計管理
├── Health/             # ヘルスデータ
├── Learning/           # 学習記録
├── Quick Notes/        # 短いメモ
├── Voice Memos/        # 音声メモ（文字起こし）
└── Files/              # アップロードファイル
```

## トラブルシューティング

### よくある問題

1. **認証エラー**
   - GitHub token の権限を確認
   - トークンの有効期限を確認
   - Secret Manager での設定を確認

2. **リポジトリアクセスエラー**
   - リポジトリ URL の形式を確認
   - プライベートリポジトリへのアクセス権限を確認

3. **同期失敗**
   - Cloud Run のログを確認: 
     ```bash
     gcloud run services logs read mindbridge --region=asia-northeast1 --project=mindbridge-469901 --limit=50
     ```

### デバッグ方法

```bash
# シークレットの確認
gcloud secrets list --project=mindbridge-469901 --filter="name:github-token OR name:obsidian-backup-repo"

# サービスの健康状態確認
curl https://mindbridge-379366010578.asia-northeast1.run.app/metrics

# ログの確認
gcloud run services logs read mindbridge --region=asia-northeast1 --project=mindbridge-469901 --limit=50
```

## セキュリティ注意事項

1. **GitHub Token の管理**
   - 適切な権限のみ付与
   - 定期的な更新を推奨
   - 漏洩時は即座に削除・再作成

2. **リポジトリの可視性**
   - プライベートリポジトリの使用を推奨
   - 機密情報を含む場合は追加の暗号化を検討

3. **アクセス制御**
   - Google Cloud IAM での適切な権限設定
   - Secret Manager での秘匿情報管理

## 高度な設定

### カスタムブランチの使用

環境変数 `OBSIDIAN_BACKUP_BRANCH` で別のブランチを指定可能：

```bash
# cloud-run.yaml で設定
- name: OBSIDIAN_BACKUP_BRANCH
  value: "develop"
```

### Git 設定のカスタマイズ

```bash
# cloud-run.yaml で設定
- name: GIT_USER_NAME
  value: "Your Bot Name"
- name: GIT_USER_EMAIL
  value: "your-bot@domain.com"
```

## 関連ドキュメント

- [Cloud Run デプロイメントガイド](../CLAUDE.md#cloud-run-デプロイメント)
- [Secret Manager 設定](../scripts/setup-secrets.sh)
- [GitHub API ドキュメント](https://docs.github.com/en/rest)