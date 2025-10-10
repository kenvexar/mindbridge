# デプロイ文書統合案

## 目的
`docs/deployment.md` と `docs/DEPLOYMENT_GUIDE.md` の重複を解消し、利用シーンに応じたガイドへ再編する。

## 現状の課題
- **内容の重複**: Cloud Run デプロイ手順が両ドキュメントで重複し、更新コストが高い。
- **粒度の差**: `deployment.md` は概要中心、`DEPLOYMENT_GUIDE.md` は詳細な運用手順で構成されているが、参照導線がない。
- **構造の混在**: ローカル運用や Docker 手順が散在し、初学者がどちらを読めばよいか判断しづらい。

## 統合方針
1. `docs/deploy/` ディレクトリを新設し、以下3レイヤーで情報を整理する。
   - `overview.md`: デプロイ戦略と選択肢（Cloud Run / ローカル / Docker）の比較表。
   - `cloud-run.md`: Cloud Run 導入の決定版。`DEPLOYMENT_GUIDE.md` の Step 形式を移植し、チェックリスト化。
   - `local.md`: ローカルと Docker 手順を `deployment.md` から移行し、トラブルシューティングを追記。
2. 既存ファイルは以下の通り扱う。
   - `docs/deployment.md` → `docs/deploy/overview.md` にリネーム＋内容再編（重複部分は `cloud-run.md` へ移動）。
   - `docs/DEPLOYMENT_GUIDE.md` → `docs/deploy/cloud-run.md` として再構成。クリティカルパスを冒頭のチェックリストに集約。
   - 旧ファイルには短期的にリダイレクト文言を残し、次回リリースで削除。
3. `README.md` および `docs/quick-start.md` から新ディレクトリへのリンクを張る。

現時点で未着手のタスクはありません。

## レビュー依頼先
- デプロイ作業担当（Cloud Run 運用経験者）
- ドキュメント整備担当（Obsidian 連携チーム）

## 期限の目安
- 初稿作成: 今スプリント（1 週間以内）
- レビュー & Fix: 次スプリント開始時

---
このプランは `docs/maintenance/housekeeping.md` のタスク完了報告として登録済み。
