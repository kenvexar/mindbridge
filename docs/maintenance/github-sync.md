# Git リモート Vault 同期ノート

Obsidian Vault を GitHub / GitLab（Self-Managed を含む）にバックアップするための設定と運用の注意点です。Bot は起動時に `git pull`、終了時に `git push` を実行します。

## 必要なシークレット
| 変数 | 用途 | 置き場の例 |
| --- | --- | --- |
| `GIT_PROVIDER` | `github` / `gitlab` を指定。未設定なら `github` | `.env` |
| `GITLAB_TOKEN` | GitLab PAT（self-managed 可、`api` 権限推奨） | `.env` |
| `GITHUB_TOKEN` | GitHub PAT（`repo` 権限） | `.env` |
| `OBSIDIAN_BACKUP_REPO` | Vault 用リモート | `https://gitlab.example.com/group/vault.git` 等 |
| `OBSIDIAN_BACKUP_BRANCH` | 使用するブランチ | 例: `main` |

`.env` に追記します。SSH キー運用なら Deploy Key と `known_hosts` の配置を忘れずに。

## 初回セットアップ
1. Vault ディレクトリ（既定 `./vault`）で `git init` し、リモートを追加。
2. 上記 3 変数を設定。GitLab Self-Managed の場合は `GIT_PROVIDER=gitlab` と `GITLAB_TOKEN` を使用。
3. `./scripts/manage.sh run --once` など短時間起動で pull/push の挙動を確認。

## 運用のベストプラクティス
- **コミット粒度**: Bot は自動コミットしません。`git status` で差分と破損の有無を把握。
- **競合回避**: 複数環境で同期する場合はブランチを分けるか、CI で定期的に `git pull --rebase`。
- **ログ監視**: `logs/github_sync.log`（ローカル）や Cloud Logging (`GitHubObsidianSync`) を確認し、`exit status 128` などを早期に検出。

## ありがちなエラーと対処
- `fatal: could not read Username` — PAT 権限を確認（GitLab はユーザー名 `oauth2` で PAT を使う）。
- `Host key verification failed` — `known_hosts` を更新し、必要なら `ssh-keyscan github.com`。
- 自動 push されない — ログの `GitHub sync disabled` を確認し、`OBSIDIAN_BACKUP_REPO` が設定されているかをチェック。

ユーザー向けの簡易手順は `docs/USER_GUIDE.md` に記載し、運用上の細かいポイントはこのノートで管理します。
