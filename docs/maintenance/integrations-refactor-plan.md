# 外部連携パッケージ再編計画

> Status: `lifelog/integrations` のブリッジ層とパイプライン実装を導入済み

## 背景
- 現在 Garmin 関連コードが `src/garmin/` と `src/lifelog/integrations/garmin.py` に分散し、API クライアント層と統合ロジックの責務が曖昧になっている。
- `src/lifelog/integrations/` ディレクトリは Google Calendar など他サービスも抱えており、共通の抽象化 (`BaseIntegration`) と個別実装が混在している。
- 今後 Notion や他クラウドとの連携が増える想定のため、統一的な `src/integrations/` 階層を設けて責務境界を明確にしたい。

## 現状の責務分解
| モジュール | 主な責務 | 課題 |
| --- | --- | --- |
| `src/garmin/client.py` | Garmin Connect API の低レベルクライアント、認証、キャッシュ管理 | Fitbit など他サービスとの共通化が難しいレイアウト |
| `src/garmin/models.py` | Garmin 固有 DTO | `lifelog` 側の `GarminActivityData` 等と重複項目が多い |
| `src/lifelog/integrations/base.py` | 統合用抽象クラス、エラー処理、レート制御 | 外部サービス固有の例外を十分に吸収できていない |
| `src/lifelog/integrations/garmin.py` | Lifelog ストリームへのマッピング、Discord 通知など | API 呼び出しを `GarminClient` と直接連携しており境界が不明瞭 |
| `src/lifelog/integrations/google_calendar.py` | Google Calendar インポート | 将来 `src/integrations/google` へ再配置予定 |

## 提案する新構成
```
src/
  integrations/
    base/
      __init__.py
      registry.py         # IntegrationManager 代替
      schemas.py          # 共通 DTO (IntegrationResult など)
    garmin/
      __init__.py
      client.py           # 既存 src/garmin/client.py を移動
      models.py           # Garmin 固有モデル
      service.py          # fetch/normalize を担当
    google_calendar/
      __init__.py
      client.py
      service.py
  lifelog/
    integrations/
      __init__.py
      bridge.py           # BaseIntegration を薄いブリッジとして残す
      pipelines/
        garmin_pipeline.py
        calendar_pipeline.py
```

- `src/integrations/` は外部 API ごとのサブパッケージを格納し、API クライアント/サービス層を担当する。
- `src/lifelog/integrations/` は Lifelog ドメインへのマッピング（DTO→ノート、通知、スケジューラ連携）に専念する。
- `IntegrationManager` は `registry.py` として外部連携の登録/DI を担い、Lifelog 側はそれを呼び出す構造に変更。

## 移行ステップ
- ✅ `src/lifelog/integrations/bridge.py` を追加し、統合パイプラインを管理する `IntegrationBridge` を新設。
- ✅ `src/lifelog/integrations/pipelines/` 配下に Garmin / Google Calendar 用パイプラインと汎用パイプラインを配置。
- ✅ `src/lifelog/manager.py` から外部連携データ変換ロジックを移設し、ブリッジ経由での変換に統一。

## リスクと対応
| リスク | 影響 | 対応策 |
| --- | --- | --- |
| import ループ | Lifelog→Integrations→Lifelog の循環 | API 層では Lifelog 型に依存しないよう DTO を共通化 |
| 大規模変更でレビューが負担増 | 複数 PR に分割 | ステップ毎に PR 作成、ドメインテストを段階的に実行 |
| キャッシュディレクトリのパス変更 | 既存のキャッシュが失われる | `GarminClient` に旧パス fallback を一時期残す |

## 依存するタスク
- `scripts/manage.sh` の `clean` コマンドに将来的なキャッシュ削除対象として `src/integrations/*/.cache` を追加する。
- ドキュメント (`docs/architecture.md`) に新しいレイヤー構成を追記。

## 次アクション
- ブリッジ／パイプラインの単体テストを追加し、LifelogManager からの変換結果を検証する。
- `IntegrationScheduler` など旧構造に依存する箇所の命名整理（`pipelines/` への再配置含む）。
