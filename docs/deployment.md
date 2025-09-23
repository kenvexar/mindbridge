# デプロイメント

## Google Cloud Run （推奨）

月額約 8 円で 24/7 運用。

### 自動デプロイ

```bash
# 基本機能のみ
./scripts/manage.sh full-deploy YOUR_PROJECT_ID

# 音声認識・健康データ統合含む
./scripts/manage.sh full-deploy YOUR_PROJECT_ID --with-optional
```

### 手動デプロイ

```bash
# 1. 環境設定
make env PROJECT_ID=your-project

# 2. シークレット設定
make secrets PROJECT_ID=your-project

# 3. デプロイ
make deploy PROJECT_ID=your-project
```

## ローカル運用

### Docker

```bash
# .env.docker を設定
cp .env.docker.example .env.docker

# 起動
docker compose up -d
```

### 直接実行

```bash
uv sync --dev
./scripts/manage.sh init
uv run python -m src.main
```
