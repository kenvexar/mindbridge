# Google Cloud Platform デプロイガイド (無料枠最適化)

MindBridge を Google Cloud Platform で**月額約 8 円**で運用するための完全ガイドです。

## 費用概算 (無料枠適用後)

| サービス | 無料枠 | 月額費用 |
|---------|-------|----------|
| Cloud Run | 200 万リクエスト/月 | **$0** |
| Artifact Registry | 0.5GB | **$0** |
| Cloud Build | 120 分/日 | **$0** |
| Secret Manager | 6 シークレット | **$0.06** |
| Gemini API | 1,500 回/日 | **$0** |
| Speech-to-Text | 60 分/月 | **$0** |
| **合計** | | **約$0.06/月 (8 円)** |

## セットアップ手順

### 1. 前提条件

```bash
# Google Cloud CLI のインストール
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# 認証
gcloud auth login
gcloud auth application-default login
```

### 2. プロジェクト作成

```bash
# 新しいプロジェクト作成
export PROJECT_ID="mindbridge-$(date +%s)"
gcloud projects create $PROJECT_ID

# プロジェクト設定
gcloud config set project $PROJECT_ID

# 請求アカウントの関連付け (必須)
BILLING_ACCOUNT=$(gcloud billing accounts list --filter="open=true" --format="value(name)" --limit=1)
gcloud billing projects link $PROJECT_ID --billing-account=$BILLING_ACCOUNT
```

### 3. シークレットと環境設定

推奨: 付属スクリプトで Secret Manager に安全に登録します。

```bash
# 必須シークレットの設定（対話式）
./scripts/manage.sh secrets <PROJECT_ID> --with-optional
```

### 4. デプロイ実行

```bash
# リポジトリをクローン
git clone https://github.com/kenvexar/mindbridge.git
cd mindbridge

# 完全自動デプロイ（推奨）
./scripts/manage.sh full-deploy <PROJECT_ID> --with-optional

# もしくは分割実行
./scripts/manage.sh env <PROJECT_ID>
./scripts/manage.sh secrets <PROJECT_ID>
./scripts/manage.sh deploy <PROJECT_ID>
```

### 5. 費用監視設定

Cloud Console の「請求」→「予算とアラート」から予算を作成し、50%/80%/100% のしきい値通知を設定してください。

## 詳細設定

### Cloud Run 設定 (無料枠最適化)

```yaml
# deploy/cloudbuild.yaml の主要設定
memory: '512Mi'          # 無料枠内のメモリ
cpu: '1'                 # 無料枠内の CPU
concurrency: '10'        # 同時リクエスト数制限
max-instances: '3'       # 最大インスタンス数
min-instances: '0'       # スケールゼロで費用節約
timeout: '300'           # 5 分タイムアウト
```

### Secret Manager 設定

`scripts/manage.sh secrets` により以下が作成・更新されます：

- `discord-bot-token`
- `discord-guild-id`
- `gemini-api-key`
- `github-token`
- `obsidian-backup-repo`
- （オプション）`google-cloud-speech-credentials`

### 予算アラート設定

- **50% 使用時**: 注意喚起
- **80% 使用時**: 警告
- **100% 使用時**: 緊急アラート

## 監視・ダッシュボード

### Cloud Console でのモニタリング

1. **Cloud Run**: https://console.cloud.google.com/run
2. **予算**: https://console.cloud.google.com/billing/budgets
3. **ダッシュボード**: https://console.cloud.google.com/monitoring

### 主要メトリクス

- リクエスト数/分
- CPU/メモリ使用率
- API 呼び出し回数
- エラー率

## トラブルシューティング

### よくある問題

**1. デプロイが失敗する**
```bash
# API の有効化確認
gcloud services list --enabled

# 権限確認
gcloud auth list
```

**2. Secret Manager エラー**
```bash
# シークレット一覧確認
gcloud secrets list

# シークレット再作成
echo -n "your-token" | gcloud secrets create discord-bot-token --data-file=-
```

**3. 予算アラートが届かない**
```bash
# 通知チャンネル確認
gcloud alpha monitoring channels list

# Pub/Sub トピック確認
gcloud pubsub topics list
```

### ログの確認

```bash
# Cloud Run ログ
gcloud run services logs read mindbridge --region=us-central1

# Cloud Build ログ
gcloud builds list --limit=10
```

## 費用最適化のコツ

### 1. 無料枠の効率活用

- **Cloud Run**: リクエスト処理時のみ課金
- **API 制限**: 無料枠内での自動制御
- **ストレージ**: 最小限のデータ保存

### 2. 使用量監視

- リアルタイム監視ダッシュボード
- 予算アラートによる早期警告
- 月末の使用量レビュー

### 3. コスト削減施策

- スケールゼロでアイドル時費用ゼロ
- 軽量 Docker イメージ使用
- 効率的な API 呼び出し

## 更新・メンテナンス

### アプリケーションの更新

```bash
# コード変更後
git add . && git commit -m "feat: new feature"
./scripts/manage.sh deploy <PROJECT_ID>
```

### 定期メンテナンス

- 月次: 費用レビュー
- 週次: ログ確認
- 日次: ヘルスチェック

## 関連リンク

- [Google Cloud 無料枠](https://cloud.google.com/free)
- [Cloud Run 料金](https://cloud.google.com/run/pricing)
- [Gemini API 料金](https://ai.google.dev/pricing)
- [Speech-to-Text 料金](https://cloud.google.com/speech-to-text/pricing)

## サポート

問題が発生した場合：

1. [トラブルシューティング](#トラブルシューティング) を確認
2. ログを確認
3. GitHub Issues で報告

---

ヒント: 無料枠を活用すれば、低コストで本格的な AI 知識管理システムを運用できます。
