# Garmin Connect 連携ガイド

## 概要

MindBridge は `python-garminconnect` ライブラリを使用して Garmin Connect から健康データを取得し、 Obsidian ノートとして自動保存する機能を提供します。 OAuth 不要で、シンプルなユーザー名/パスワード認証により、睡眠、歩数、心拍数、アクティビティデータを統合的に管理できます。

## 機能特徴

### データ取得
- **睡眠データ**: 睡眠時間、深い睡眠、レム睡眠、睡眠スコア
- **歩数データ**: 日別歩数、目標達成率
- **心拍数データ**: 安静時心拍数、最大心拍数、心拍ゾーン
- **アクティビティデータ**: 運動記録、カロリー消費、距離

### 分析機能
- AI による健康データ傾向分析
- 日別・週別・月別統計
- 異常値検出とアラート

### Obsidian 統合
- `21_Health` フォルダへの自動保存
- 日次健康レポート生成
- メタデータ付きマークダウン形式

## アーキテクチャ

### コアコンポーネント

#### GarminClient (`src/garmin/client.py`)
```python
class GarminClient:
    # 主要メソッド
    authenticate()              # Garmin Connect 認証
    get_health_data()          # 統合ヘルスデータ取得
    get_cache_stats()          # キャッシュ統計
    test_connection()          # 接続テスト
```

**主要機能:**
- 自動認証・再認証
- レート制限対応
- キャッシュ機能（デフォルト 24 時間）
- エラーハンドリング・リトライ
- ネットワーク接続チェック

#### データモデル (`src/garmin/models.py`)
```python
# データ構造
HealthData          # 統合健康データ
├── SleepData      # 睡眠データ
├── StepsData      # 歩数データ
├── HeartRateData  # 心拍数データ
└── ActivityData   # アクティビティデータ

# エラー型
GarminConnectionError      # 接続エラー
GarminAuthenticationError  # 認証エラー
GarminDataRetrievalError  # データ取得エラー
GarminRateLimitError      # レート制限エラー
GarminTimeoutError        # タイムアウト
GarminOfflineError        # オフライン状態
```

#### ヘルスデータ分析 (`src/health_analysis/analyzer.py`)
```python
class HealthDataAnalyzer:
    # AI を使用した健康データ分析
    # トレンド分析、異常値検出、洞察生成
```

### キャッシュシステム (`src/garmin/cache.py`)
- データ取得の最適化
- API レート制限の回避
- オフライン時の過去データ利用

### データフォーマッタ (`src/garmin/formatter.py`)
- Obsidian マークダウン形式への変換
- メタデータ生成
- グラフ・チャート対応

## セットアップ

### 環境変数設定
```env
# Garmin Connect 認証情報
GARMIN_EMAIL=your-garmin-email@example.com
GARMIN_PASSWORD=your-secure-password

# キャッシュ設定
GARMIN_CACHE_DIR=~/.cache/mindbridge/garmin
GARMIN_CACHE_HOURS=24

# テスト・開発用
MOCK_GARMIN_ENABLED=false  # 本番: false, 開発: true
```

### 依存関係
依存関係はリポジトリの `pyproject.toml` に定義されています。バージョンはそちらを参照してください。

## 使用方法

### 基本的な健康データ取得
```python
from src.garmin.client import GarminClient
from src.config.settings import Settings

settings = Settings()
garmin_client = GarminClient(
    email=settings.garmin_email,
    password=settings.garmin_password
)

# 今日のヘルスデータ取得
health_data = await garmin_client.get_health_data(date.today())
print(f"歩数: {health_data.steps.total_steps}")
print(f"睡眠時間: {health_data.sleep.total_sleep_hours}時間")
```

### Discord 経由での健康データ確認
```
/health_stats today      # 今日の健康統計
/health_trends week      # 週間トレンド
/garmin_sync            # 手動データ同期
/health_report monthly  # 月次レポート生成
```

## データ保存形式

### Obsidian ノート例
```markdown
---
date: 2024-01-15
type: health_daily
source: garmin_connect
tags: [health, fitness, sleep, steps]
sleep_score: 85
steps_goal_achieved: true
---

# 健康データ - 2024-01-15

## 睡眠
- **合計睡眠時間**: 7 時間 45 分
- **深い睡眠**: 1 時間 20 分
- **レム睡眠**: 1 時間 30 分
- **睡眠スコア**: 85/100

## 活動量
- **歩数**: 12,450 歩 (目標達成!)
- **距離**: 8.2km
- **消費カロリー**: 2,340kcal

## 心拍数
- **安静時心拍数**: 58bpm
- **最大心拍数**: 165bpm

## アクティビティ
- ランニング: 30 分, 5km
- 筋トレ: 45 分

## AI 分析
今日は睡眠の質が良好で、運動目標も達成されています。継続的な運動習慣が心拍数の改善につながっています。
```

## トラブルシューティング

### よくある問題

#### 1. 認証エラー
```
GarminAuthenticationError: Invalid credentials
```
**解決策:**
- Garmin Connect のパスワードを確認
- 2 段階認証が有効な場合はアプリパスワードを使用

#### 2. レート制限
```
GarminRateLimitError: API rate limit exceeded
```
**解決策:**
- キャッシュ時間を延長 (`GARMIN_CACHE_HOURS=48`)
- 取得頻度を調整

#### 3. データ取得失敗
```
GarminDataRetrievalError: Failed to retrieve sleep data
```
**解決策:**
- ネットワーク接続を確認
- Garmin Connect サーバー状況を確認
- リトライ後もエラーが続く場合は一時的にモックデータを使用

### デバッグ情報
```python
# 接続テスト
result = await garmin_client.test_connection()
print(f"接続状態: {result['status']}")

# キャッシュ統計
stats = garmin_client.get_cache_stats()
print(f"キャッシュヒット率: {stats.hit_rate}%")
```

## 開発・テスト

### モックデータ使用
```env
MOCK_GARMIN_ENABLED=true  # 開発時のみ
```

### テスト実行
```bash
# Garmin 統合テスト
uv run python test_garmin_integration.py

# ヘルスデータ分析テスト
uv run python test_health_analysis.py
```

## セキュリティ考慮事項

- Garmin 認証情報は環境変数で管理
- Google Secret Manager 連携対応
- ローカルキャッシュの暗号化
- API キーローテーション対応

## 今後の拡張予定

- [ ] Apple HealthKit 連携
- [ ] Fitbit API 対応
- [ ] ヘルスデータの機械学習分析
- [ ] 健康目標の自動設定・追跡
- [ ] 医療データエクスポート機能
