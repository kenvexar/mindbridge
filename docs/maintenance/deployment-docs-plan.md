# デプロイ文書メンテナンスログ

Cloud Run / ローカル運用に関するドキュメント再編の履歴と今後の TODO をまとめます。

## 2025 Q1 アップデート（完了）

- `docs/deploy/overview.md` を作成し、デプロイ戦略の比較と共通ワークフローを整理。
- `docs/deploy/cloud-run.md` を全面改稿。`scripts/manage.sh` ベースの手順、確認項目、トラブルシュートを追加。
- `docs/deploy/local.md` を更新し、`uv run` / Docker Compose 両方の運用手順を整備。
- 旧 `deployment.md` / `DEPLOYMENT_GUIDE.md` は廃止し、リンクは `docs/deploy/*.md` へ統合済み。
- ルート `README.md`・`docs/README.md`・`docs/quick-start.md` に新しいドキュメントへのリンクを追加。

## 残課題 / 次回アクション

- 現在、追加の残課題はありません。新しいタスクが発生したらここに追記してください。

## 参照

- 運用全体のサマリ: `docs/maintenance/housekeeping.md`
- テスト/検証の手順: `docs/testing.md`
- 管理スクリプト実装: `scripts/manage.sh`
