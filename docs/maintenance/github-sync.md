# GitHub Vault Sync Operations

Obsidian Vault を GitHub リポジトリへ同期するためのセットアップと
運用ベストプラクティスをまとめます。
Bot の終了時に `git push` を自動実行する仕組みのため、
資格情報と差分管理を正しく構成することが重要です。

## 1. 必要なシークレット

| 変数 | 用途 | 保存先の例 |
| --- | --- | --- |
| `GITHUB_TOKEN` | repo 権限の PAT | `.env`（個人） / Secret Manager (`github-token`) |
| `OBSIDIAN_BACKUP_REPO` | Vault 用の Git リポジトリ | `git@github.com:owner/vault.git` |
| `OBSIDIAN_BACKUP_BRANCH` | デプロイごとのバックアップブランチ | 例: `main` |

Cloud Run 運用では `scripts/manage.sh secrets <PROJECT_ID> --with-optional` を実行し、
上記シークレットを Google Secret Manager へ登録してください。
Secret Manager を使わない場合は `.env` へ同名の環境変数を追記します。

## 2. 初期同期フロー

1. Vault ディレクトリ（既定 `./vault`）で `git init` を実行し、
   リモートを追加します。
2. `OBSIDIAN_BACKUP_REPO` と `OBSIDIAN_BACKUP_BRANCH` を設定します。
3. Bot を起動すると `git pull` が走り、終了時に `git push` します。
   初回は `./scripts/manage.sh run --once` などで短時間起動し、
   挙動を確認してください。

### SSH 鍵を利用する場合

- `GITHUB_TOKEN` の代わりにデプロイ先へ専用の Deploy Key を登録し、
  `~/.ssh` をボリュームマウントするか
  Secret Manager に暗号化して保存します。
- Cloud Run の場合は Secret Manager から鍵を取得し、
  `/app/.ssh/id_ed25519` に展開する
  カスタムエントリポイントを検討してください。

## 3. 運用ベストプラクティス

- **コミット粒度**: Bot が生成するノートは自動コミットされません。
  Vault での `git status` を確認し、
  破損ファイルがないことを把握してください。
- **競合回避**: 複数環境で同期する場合は `OBSIDIAN_BACKUP_BRANCH` を分けるか、
  定期的に `git pull --rebase` を CI で実行します。
- **ログ監視**: `logs/github_sync.log`（ローカル）または Cloud Logging
  (`GitHubObsidianSync`) を確認し、`exit status 128` 等のエラーを検出したら
  Token/SSH を再設定します。

## 4. トラブルシューティング

- `fatal: could not read Username` が出る場合は、
  PAT の権限と Secret Manager のバージョンを再確認してください。
- `Host key verification failed` の場合は `known_hosts` を更新し、
  Cloud Run では `ssh-keyscan github.com` を併用します。
- 自動 push が行われないときはログの `GitHub sync disabled` を確認し、
  `OBSIDIAN_BACKUP_REPO` が設定されているかを見直してください。

`docs/USER_GUIDE.md` のバックアップ章にはユーザー向け手順のみを載せ、
運用詳細は本ノートで管理してください。
