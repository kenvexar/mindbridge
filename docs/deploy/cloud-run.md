# Cloud Run デプロイガイド

Google Cloud Run へ MindBridge を安全にデプロイするための手順をまとめています。基本的には `./scripts/manage.sh` を利用することで、プロジェクト準備からデプロイ、後処理までを自動化できます。

---

## 1. 前提条件

- Google Cloud アカウントと課金が有効なプロジェクト
- [gcloud CLI](https://cloud.google.com/sdk/docs/install) がインストール済み
- `docker`, `bash`, `uv` がローカル環境にインストールされていること
- リポジトリ内の `scripts/manage.sh` に実行権限 (`chmod +x`) が付与されていること

初回のみ以下を実行してください。

```bash
gcloud auth login
gcloud auth configure-docker    # Artifact Registry への push を許可
```

---

## 2. プロジェクト初期化

`<PROJECT_ID>` は Cloud Run 用に作成する GCP プロジェクト ID です。

```bash
export PROJECT_ID="your-mindbridge-project"
./scripts/manage.sh env "$PROJECT_ID"
```

このコマンドで以下が自動化されます。

- 指定したプロジェクトが存在しない場合は作成（オプションで課金アカウントとリンク）
- Cloud Run / Cloud Build / Secret Manager / Speech API など必要な API の有効化
- `mindbridge-service` サービスアカウント作成と IAM ロール付与
- Artifact Registry (`mindbridge` リポジトリ) のセットアップ

---

## 3. シークレット登録

必要なシークレットを Secret Manager に保存します。`--with-optional` を付与すると Garmin/Speech などのオプションも登録できます。

```bash
./scripts/manage.sh secrets "$PROJECT_ID" --with-optional --skip-existing
```

登録する主なシークレット:

| シークレット名 | 用途 |
| --- | --- |
| `discord-bot-token` / `discord-guild-id` | Discord Bot 認証 |
| `gemini-api-key` | Gemini API キー |
| `github-token`, `obsidian-backup-repo` | GitHub バックアップ（任意） |
| `garmin-username`, `garmin-password` | Garmin 連携（オプション） |
| `google-cloud-speech-credentials` | Speech-to-Text サービスアカウント（自動生成可能） |

Secret Manager へ登録すると、Cloud Run では `SECRET_MANAGER_STRATEGY=google` と `SECRET_MANAGER_PROJECT_ID` を通じて自動的に読み込みます。

---

## 4. 追加設定（任意）

```bash
./scripts/manage.sh optional "$PROJECT_ID"
```

このステップでは以下をガイドします。

- Google Calendar OAuth 用のリダイレクト URI 登録
- Webhook／外部サービス連携用の追加シークレット
- Artifact Registry のクリーンアップジョブ作成

---

## 5. ビルドとデプロイ

### 5.1 ワンコマンドで実行

```bash
./scripts/manage.sh full-deploy "$PROJECT_ID" --with-optional
```

`env` → `secrets` → `optional` → `deploy` の流れを一括で実行します。`--with-optional` を外せば必須構成のみデプロイ可能です。

### 5.2 手動実行（参考）

```bash
# コンテナイメージをビルドして Artifact Registry に push
gcloud builds submit --tag "us-central1-docker.pkg.dev/$PROJECT_ID/mindbridge/mindbridge:latest"

# Cloud Run へデプロイ
gcloud run deploy mindbridge \
  --project="$PROJECT_ID" \
  --image="us-central1-docker.pkg.dev/$PROJECT_ID/mindbridge/mindbridge:latest" \
  --region="us-central1" \
  --platform="managed" \
  --allow-unauthenticated \
  --memory=1Gi \
  --cpu=1 \
  --set-env-vars="ENVIRONMENT=production,SECRET_MANAGER_STRATEGY=google,SECRET_MANAGER_PROJECT_ID=$PROJECT_ID"
```

その他の推奨設定:

- 最小インスタンス数は 0、最大インスタンス数は 3〜5 程度
- `--ingress internal-and-cloud-load-balancing` や Cloud Armor を利用してアクセス制御する場合は追加設定が必要

---

## 6. デプロイ後の確認

1. **サービス状態**

   ```bash
   gcloud run services list --project="$PROJECT_ID"
   gcloud run services describe mindbridge --region=us-central1 --project="$PROJECT_ID"
   ```

2. **ログチェック**

   ```bash
   gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=mindbridge" \
     --project="$PROJECT_ID" --limit=50
   ```

3. **Discord 側の動作確認**
   - `/status` で Bot がオンラインか確認。
   - `/integration_status` で Garmin / Calendar などの連携状況を確認。
4. **ヘルスチェック**
   - Cloud Run サービス URL `/healthz` にアクセスすると `HealthServer` がレスポンスを返します。

問題が発生した場合は `logs/` 代替として Cloud Logging を参照し、必要に応じて `./scripts/manage.sh run` でローカル再現を試みてください。

---

## 7. 運用とメンテナンス

- **定期クリーンアップ**: Artifact Registry の古いイメージを削除。

  ```bash
  ./scripts/manage.sh ar-clean "$PROJECT_ID" us-central1 mindbridge mindbridge 5 7 --no-dry-run
  ```

- **シークレット更新**: `./scripts/manage.sh secrets "$PROJECT_ID" --skip-existing` で更新。管理者に通知後、Cloud Run を再デプロイ。
- **ログ監視**: Cloud Logging のフィルタ（`severity>=ERROR`）で異常検知。必要に応じてアラートポリシーを設定。
- **コスト管理**: `gcloud beta billing accounts budgets list` で予算を設定し、推定コストを監視。

### 7.1 監視 / アラート構成の推奨

1. **Cloud Monitoring ワークスペース** – プロジェクトを既存ワークスペースへリンクし、`run.googleapis.com/request_count` や `error_count` をダッシュボード化。
2. **Uptime Check** – `/healthz` へ HTTPS チェックを追加し、タイムアウトや 5xx を検知したら通知する。CLI 例:
   ```bash
   gcloud monitoring uptime-checks create http mindbridge-health \
     --project="$PROJECT_ID" \
     --resource-labels=project_id="$PROJECT_ID" \
     --path="/healthz" \
     --host="<RUN_SERVICE_URL>" \
     --port=443
   ```
3. **アラートポリシー** – `run.googleapis.com/error_count` や `logging.googleapis.com/user/mindbridge_error_ratio`（ログベース指標）にしきい値を設定し、Slack/Webhook に通知。
4. **Ops Agent 連携（任意）** – Cloud Run 単体では不要だが、連携する GCE / GKE ノードがある場合は Ops Agent を導入し、外部依存（PostgreSQL など）のメトリクスを同一チャンネルへ集約する。

---

## 8. トラブルシューティング

| 症状 | 対応策 |
| --- | --- |
| デプロイに失敗する | `gcloud builds submit` / `gcloud run deploy` のログを確認。IAM 権限とサービス有効化状況を再チェック。 |
| Discord Bot が応答しない | Secret Manager に格納した `discord-bot-token` / `discord-guild-id` が最新か確認し、Cloud Run コンソールから再起動。 |
| Slash コマンドが同期されない | `DISCORD_GUILD_ID` が正しいか、Bot を再招待して権限を付与したか確認。 |
| Garmin/Calendar 連携がエラーになる | `/integration_status` で詳細を確認し、必要なら `/manual_sync`。Secret Manager の資格情報を再発行。 |
| GitHub 同期に失敗 | サービスアカウントが Git を実行できるか、`github-token` の権限 (`repo`) が有効か確認。 |

---

## 9. 参考資料

- ローカル/コンテナでの実行: `docs/deploy/local.md`
- リポジトリ構造とメンテナンス: `docs/maintenance/housekeeping.md`
- テスト手順: `docs/testing.md`

Cloud Run デプロイ後もリポジトリの更新があれば `./scripts/manage.sh full-deploy` を再実行し、最新バージョンを反映してください。
