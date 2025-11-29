# GitHub Vault 同期ノート

Obsidian Vault を GitHub にバックアップするための設定と運用の注意点です。Bot は起動時に `git pull`、終了時に `git push` を実行します。

## 必要なシークレット
| 変数 | 用途 | 置き場の例 |
| --- | --- | --- |
| `GITHUB_TOKEN` | `repo` 権限の PAT | `.env` / Secret Manager (`github-token`) |
| `OBSIDIAN_BACKUP_REPO` | Vault 用リモート | `git@github.com:owner/vault.git` など |
| `OBSIDIAN_BACKUP_BRANCH` | 使用するブランチ | 例: `main` |

Secret Manager を使わない場合は `.env` に追記します。SSH キー運用なら Deploy Key と `known_hosts` の配置を忘れずに。

## 初回セットアップ
1. Vault ディレクトリ（既定 `./vault`）で `git init` し、リモートを追加。
2. 上記 3 変数を設定。
3. `./scripts/manage.sh run --once` など短時間起動で pull/push の挙動を確認。

## 運用のベストプラクティス
- **コミット粒度**: Bot は自動コミットしません。`git status` で差分と破損の有無を把握。
- **競合回避**: 複数環境で同期する場合はブランチを分けるか、CI で定期的に `git pull --rebase`。
- **ログ監視**: `logs/github_sync.log`（ローカル）や Cloud Logging (`GitHubObsidianSync`) を確認し、`exit status 128` などを早期に検出。

## ありがちなエラーと対処
- `fatal: could not read Username` — PAT 権限または Secret Manager のバージョンを確認。
- `Host key verification failed` — `known_hosts` を更新し、必要なら `ssh-keyscan github.com`。
- 自動 push されない — ログの `GitHub sync disabled` を確認し、`OBSIDIAN_BACKUP_REPO` が設定されているかをチェック。

ユーザー向けの簡易手順は `docs/USER_GUIDE.md` に記載し、運用上の細かいポイントはこのノートで管理します。
