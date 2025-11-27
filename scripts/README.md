# MindBridge 管理スクリプト

## クイックスタート

### ローカル起動

```bash
# 環境設定
./scripts/manage.sh init

# 起動
./scripts/manage.sh run
```

## 主要コマンド

- `init` - ローカル環境設定
- `run` - ローカル起動
- `clean [--with-uv-cache]` - キャッシュ削除

## 事前準備

1. **Discord Bot**： Bot 作成と Token 取得
2. **Gemini API Key**： Google AI Studio で作成
3. **GitHub リポジトリ**： Obsidian vault バックアップ用（任意）

## トラブルシューティング

- `./scripts/manage.sh clean --with-uv-cache` でキャッシュを掃除
- `docker compose logs -f` または `podman-compose logs -f` でコンテナログ確認
