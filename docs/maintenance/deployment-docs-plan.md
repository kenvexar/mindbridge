# デプロイ文書メンテナンスログ

Cloud Run / ローカル運用に関するドキュメント再編の履歴と今後の TODO をまとめます。

## 2025 Q1 アップデート（完了）

- `docs/deploy/overview.md` を作成し、デプロイ戦略の比較と共通ワークフローを整理。
- `docs/deploy/cloud-run.md` を全面改稿。`scripts/manage.sh` ベースの手順、確認項目、トラブルシュートを追加。
- `docs/deploy/local.md` を更新し、`uv run` / Docker Compose 両方の運用手順を整備。
- 旧 `deployment.md` / `DEPLOYMENT_GUIDE.md` は互換性のためのリダイレクト文言のみ残す。
- ルート `README.md`・`docs/README.md`・`docs/quick-start.md` に新しいドキュメントへのリンクを追加。

## 残課題 / 次回アクション

- [ ] Docker イメージのビルド方法を `README.md` に簡易追記し、Cloud Run 以外のホスティング手段（例: 自前 VPS）に触れる。
- [ ] `docs/deploy/cloud-run.md` に監視/アラート設定（Ops Agent, Uptime Check 等）の推奨構成を加筆。
- [ ] Secret Manager を使用しない個人運用向けの簡易ガイドを `docs/deploy/local.md` に追加検討。

## 参照

- 運用全体のサマリ: `docs/maintenance/housekeeping.md`
- テスト/検証の手順: `docs/testing.md`
- 管理スクリプト実装: `scripts/manage.sh`
