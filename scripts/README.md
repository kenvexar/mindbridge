# MindBridge 管理スクリプト

## クイックスタート

### 自動デプロイ

```bash
# 基本機能のみ
./scripts/manage.sh full-deploy your-project-id

# オプション機能も含める
./scripts/manage.sh full-deploy your-project-id --with-optional
```

### ローカル起動

```bash
# 環境設定
./scripts/manage.sh init

# 起動
./scripts/manage.sh run
```

## 主要コマンド

- `env <PROJECT_ID>` - Google Cloud 環境セットアップ
- `secrets <PROJECT_ID>` - シークレット設定
- `deploy <PROJECT_ID>` - Cloud Run デプロイ
- `full-deploy <PROJECT_ID>` - 一括実行
- `init` - ローカル環境設定
- `run` - ローカル起動

## 事前準備

1. **Google Cloud SDK**：`gcloud auth login`
2. **Discord Bot**： Bot 作成と Token 取得
3. **Gemini API Key**： Google AI Studio で作成
4. **GitHub リポジトリ**： Obsidian vault バックアップ用

## トラブルシューティング

```bash
# API 有効化
gcloud services enable run.googleapis.com

# ログ確認
gcloud logs tail --service=mindbridge

# サービス確認
gcloud run services list
```
