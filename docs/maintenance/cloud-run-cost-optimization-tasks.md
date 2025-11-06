# Cloud Run コスト最適化タスクリスト

Cloud Run サービス `mindbridge` の費用削減に向けた追跡タスクを整理しています。完了した項目はチェックボックスを更新し、変更履歴を残してください。

## 未完了タスク

- [ ] Cloud Monitoring ダッシュボードで直近 30 日の指標（`container/cpu/utilization`, `container/memory/usage_bytes`, リクエスト数、同時接続数）を可視化し、必要に応じてダッシュボードを共有。
- [ ] 指標を元に `deploy/cloud-run.yaml` の `run.googleapis.com/memory` / `run.googleapis.com/cpu` 値のダウンサイジング可否を検証し、影響をテスト環境で確認。
- [ ] Discord ボットの負荷要因を洗い出し、重い処理を Cloud Run Jobs または Cloud Functions に切り出す案を評価。
- [ ] Cloud Monitoring または BigQuery で日次コストレポートをエクスポートし、Looker Studio 等で推移を可視化。
- [ ] ネットワーク出口（インターネット / リージョン間）の利用状況を確認し、Cloud CDN やリージョン統合の費用対効果を算出。

## 完了済み

- [x] 常時稼働サービス向けに `maxScale=1` を設定し、同時稼働数を抑制（2025-11-06）。
