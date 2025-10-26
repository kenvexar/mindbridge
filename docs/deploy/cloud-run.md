# Cloud Run デプロイガイド

Google Cloud Run へ MindBridge を安全にデプロイするための手順をまとめています。基本的には `./scripts/manage.sh` を利用することで、プロジェクト準備からデプロイ、後処理までを自動化できます。

---

## 0. デプロイ前チェックリスト

本番／ステージング問わず、以下を完了してから Cloud Run へデプロイしてください。

1. コード状態を確認する: `git status --short` が空であること（未コミットの変更は別ブランチへ退避）。
2. テストと静的解析を実行する:

    ```bash
    uv run pytest -q
    uv run ruff check .
    uv run mypy src       # 型チェックを実施する場合
    ```
3. `.env` や `mise.local.toml` 等のローカル設定が最新であることを確認し、`scripts/manage.sh` に実行権限がある (`chmod +x scripts/manage.sh`）。
4. Google Cloud CLI のログイン状態を確認する: `gcloud auth list` でアクティブアカウントに問題がないこと。
5. 音声機能を利用する場合は `google-cloud-speech-credentials` を含む必須シークレットが Secret Manager に存在するか確認する:

    ```bash
    gcloud secrets describe google-cloud-speech-credentials --project="$PROJECT_ID"
    ```
6. 課金アラートや予算が設定済みか確認し、想定外の費用発生に備える。
7. 上記をまとめて検証したい場合は次のコマンドで自動チェックできます。

    ```bash
    ./scripts/manage.sh deploy-precheck "$PROJECT_ID" --region us-central1
    ```

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
| `health-endpoint-token` | `/metrics` など敏感なヘルスエンドポイント保護用の共有トークン |
| `health-callback-state` | OAuth リダイレクト `/callback` で検証する CSRF 対策トークン |

Secret Manager へ登録すると、Cloud Run では `SECRET_MANAGER_STRATEGY=google` と `SECRET_MANAGER_PROJECT_ID` を通じて自動的に読み込みます。`health-endpoint-token` と `health-callback-state` はそれぞれ環境変数 `HEALTH_ENDPOINT_TOKEN`、`HEALTH_CALLBACK_STATE` にマッピングされ、 `/metrics`・`/callback` で必須となります。

---

### 3.1 ヘルスチェック公開ポリシー

Cloud Run 上で MindBridge を運用する際は、ヘルスサーバーを完全にクローズドに保護してください。

- `/health`・`/ready`・`/metrics` へのアクセスには必ず `X-Health-Token: <health-endpoint-token>` または `Authorization: Bearer <token>` を付与します。トークンが無いリクエストは 503/401 で拒否されます。
- アプリ起動時に `HEALTH_ENDPOINT_TOKEN`・`HEALTH_CALLBACK_STATE`・`ENCRYPTION_KEY` がいずれか欠けている場合、`HealthServer` は起動に失敗します。Secret Manager もしくは `.env` で必ず定義してください。
- Cloud Run デプロイでは `--no-allow-unauthenticated` と `--ingress internal-and-cloud-load-balancing` を指定し、Serverless VPC Access や Cloud Load Balancing を併用して内部ネットワークのみから到達できるようにします。
- 外部公開が必要な場合は、GCLB/IAP のバックエンド構成でカスタムヘッダーに `X-Health-Token` を注入し、Cloud Armor で許可 IP をホワイトリスト化します。
- ローカル確認時は `.env` に上記 3 つの値を設定し、次のようにヘッダー付きで確認します。

    ```bash
    curl -H "X-Health-Token: ${HEALTH_ENDPOINT_TOKEN}" http://localhost:8080/ready
    ```

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

### 5.0 デプロイ自動化 CLI

- チェックリストのみ実行:

  ```bash
  ./scripts/manage.sh deploy-precheck "$PROJECT_ID" --region us-central1
  ```

- チェックリスト完了後に Cloud Run まで自動デプロイ:

  ```bash
  ./scripts/manage.sh deploy-auto "$PROJECT_ID" us-central1 --skip-mypy
  ```

  `--skip-mypy` などのフラグで個別チェックを省略できます。`deploy-auto` は内部で `deploy-precheck` を実行してから `deploy` を呼び出します。

### 5.1 ワンコマンドで実行

```bash
./scripts/manage.sh full-deploy "$PROJECT_ID" --with-optional
```

`env` → `secrets` → `optional` → `deploy` の流れを一括で実行します。`--with-optional` を付けると音声処理用の Speech 認証情報や Garmin 連携のテンプレートも自動生成します。音声機能を利用しない場合だけフラグを外してください。

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
  --ingress internal-and-cloud-load-balancing \
  --no-allow-unauthenticated \
  --memory=512Mi \
  --cpu=1 \
  --set-env-vars="ENVIRONMENT=production,SECRET_MANAGER_STRATEGY=google,SECRET_MANAGER_PROJECT_ID=$PROJECT_ID"
```

その他の推奨設定:

- 最小インスタンス数は 0、最大インスタンス数は 3〜5 程度
- `--ingress internal-and-cloud-load-balancing` や Cloud Armor を利用してアクセス制御する場合は追加設定が必要

### 5.3 デプロイ直前チェック

ワンコマンド実行・手動手順に関わらず、以下を満たしているか確認します。

- Artifact Registry に最新のイメージが存在する:

    ```bash
    gcloud artifacts docker images list "us-central1-docker.pkg.dev/$PROJECT_ID/mindbridge/mindbridge" --sort-by=~CREATE_TIME --limit=5
    ```
- サービスアカウント `mindbridge-service@$PROJECT_ID.iam.gserviceaccount.com` が `roles/secretmanager.secretAccessor` と `roles/speech.client` を保持している。
- Secret Manager に `discord-bot-token`、`discord-guild-id`、`gemini-api-key`、`google-cloud-speech-credentials`、`health-endpoint-token`、`health-callback-state` など必須シークレットが存在し、最新版のステータスが `ENABLED` になっている。
- Cloud Run 用の環境変数が変わった場合は `deploy/cloud-run.yaml` を更新済みである。

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
   - Cloud Run サービス URL `/health` にアクセスすると `HealthServer` がレスポンスを返します。
   - `/metrics` を確認する場合は `X-Health-Token: <health-endpoint-token>` または `Authorization: Bearer <token>` を必ず付与してください。
5. **音声処理の動作確認**
   - Discord へ短い音声メッセージを送信し、チャンネルの転記ノートが生成されるかを確認。
   - もしくは Cloud Run のログで `SpeechProcessor` のジョブ完了ログと使用分数を確認し、無料枠内に収まっているかをチェックします。

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
