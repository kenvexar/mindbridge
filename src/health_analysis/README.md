# Health Analysis

## 概要
- Garmin や Lifelog データを分析し、健康レポートやスケジュール化された統合処理を実行します。
- AI による要約と Obsidian ノート更新を自動化します。

## 主要モジュール
| モジュール | 説明 |
| --- | --- |
| `analyzer.py` | `HealthDataAnalyzer`。Garmin データを AI Processor へ渡し洞察を生成 |
| `integrator.py` | HealthActivityIntegrator。アクティビティを Obsidian ノートへ反映 |
| `scheduler.py` | 定期同期タスクを管理するスケジューラ |
| `models.py` | 健康データ/レポートの Pydantic モデル |

## 外部依存
- `numpy`, `scikit-learn`, `structlog`。
- Garmin データ取得には `component_manager` を経由して `GarminClient` を利用します。

## テスト
- 単体テスト: `tests/unit/test_health_analysis.py`。
- 統合テスト: `tests/integration/test_complete_integration.py` でスケジューラ初期化を確認。

## 連携・利用箇所
- `src/main.py` で `HealthAnalysisScheduler` が起動され、AI と Obsidian サービスを注入。
- Lifelog マネージャ (`src/lifelog/manager.py`) と協調して日次ノートに書き込み。

## メモ
- 現在の ML モデルは線形回帰ベース（`sklearn.linear_model.LinearRegression`）。今後のアルゴリズム強化に備え、モデル保存/再学習フローを検討。
