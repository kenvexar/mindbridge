# AI

## 概要
- Gemini/Gemini Flash を中心とした大規模言語モデル呼び出しと後処理を担当します。
- ベクターストアや URL 解析を通じて、Discord メッセージや Obsidian ノート向けエンリッチメントを行います。

## 主要モジュール
| モジュール | 説明 |
| --- | --- |
| `processor.py` | AIProcessor 本体。キュー処理、優先度制御、Gemini クライアント委譲を担う |
| `gemini_client.py` | `google-genai` SDK を利用した Gemini API ラッパー |
| `vector_store.py` | Obsidian ノートから生成した TF-IDF ベクターストアの管理 |
| `note_analyzer.py` | ノート分類や洞察抽出などの高レベル分析ロジック |
| `url_processor.py` | URL からのメタデータ取得と HTML パース (`aiohttp`, `BeautifulSoup`) |
| `mock_processor.py` | テスト用モック実装 |

## 外部依存
- `google-genai`, `aiohttp`, `beautifulsoup4`, `scikit-learn`, `numpy`。
- API キーは `SecureSettingsManager.get_gemini_api_key()` から供給 (`GEMINI_API_KEY`)。

## テスト
- 単体テスト: `tests/unit/test_ai_processor.py`。
- 手動テスト: `tests/manual/simple_test.py`, `tests/manual/quick_voice_test.py`（AI モック動作確認）。

## 連携・利用箇所
- `src/main.py` で `AIProcessor` が DI され、Discord Bot や Health Analyzer から再利用。
- Obsidian 連携 (`src/obsidian/file_manager.py`) やタスク管理 (`src/tasks/task_manager.py`) からの洞察生成に参照される。

## メモ
- ベクターストアはローカルファイルで管理。将来的に外部ストレージ対応を検討。
- Gemini API レート制限は `AIProcessor` のメトリクス (`self.stats`) で監視。
