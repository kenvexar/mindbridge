#!/bin/bash
set -e

# 個人用 MindBridge ローカル Docker テスト用スクリプト

echo "🚀 Personal MindBridge - ローカル Docker テスト"
echo "================================================"

# 環境変数ファイルの確認
if [ ! -f ".env.docker" ]; then
    echo "❌ .env.docker ファイルが見つかりません。"
    echo "   サンプル: cp .env.docker.example .env.docker"
    exit 1
fi

# 個人用ディレクトリの作成
echo "📁 個人用ディレクトリを作成中..."
mkdir -p vault logs backups .cache .config

# Docker イメージのビルド
echo "🔨 Docker イメージをビルド中..."
docker compose build

# コンテナの起動
echo "🚀 コンテナを起動中..."
docker compose up -d

# 起動確認
echo "⏳ サービスの起動を待機中..."
sleep 10

# ヘルスチェック
echo "🔍 ヘルスチェック実行中..."
for i in {1..30}; do
    if curl -s http://localhost:8080/health > /dev/null 2>&1; then
        echo "✅ サービスが正常に起動しました！"
        echo "🌐 ヘルスチェック URL: http://localhost:8080/health"
        break
    fi
    echo "   起動中... ($i/30)"
    sleep 2
done

# ログの表示
echo "📋 最新のログ:"
docker compose logs --tail=20 mindbridge-bot

echo ""
echo "📝 役立つコマンド:"
echo "   ログ監視: docker compose logs -f"
echo "   コンテナ停止: docker compose down"
echo "   イメージ再ビルド: docker compose build --no-cache"
echo "   コンテナ内シェル: docker compose exec mindbridge-bot /bin/bash"
