# Manual Tests

このディレクトリには手動実行用のテストファイルが含まれています。

## テストファイル一覧

### `quick_voice_test.py`
- **目的**: 音声メモ機能のクイックテスト（モック機能使用）
- **実行**: `uv run python tests/manual/quick_voice_test.py`
- **概要**: SpeechProcessor の基本機能とモックデータでの動作確認

### `simple_test.py`
- **目的**: シンプルなコンポーネントテスト
- **実行**: `uv run python tests/manual/simple_test.py`
- **概要**: MockAIProcessor を使用したメッセージ処理テスト

### `test_real_voice.py`
- **目的**: 実際の音声ファイルを使用したテスト
- **実行**: `uv run python tests/manual/test_real_voice.py`
- **概要**: pydub で生成した実際の音声データでのテスト

### `test_voice_memo.py`
- **目的**: 音声メモ機能の総合テストスクリプト
- **実行**: `uv run python tests/manual/test_voice_memo.py`
- **概要**: 音声処理、 Bot 統合、 Obsidian 統合の包括的テスト

### `test_garmin_integration.py`
- **目的**: Garmin Connect 統合テストスクリプト
- **実行**: `uv run python tests/manual/test_garmin_integration.py`
- **概要**: Garmin 認証、健康データ取得、キャッシュ機能のテスト

## 実行方法

プロジェクトルートディレクトリから以下のコマンドでテストを実行してください：

```bash
# 個別のテスト実行
uv run python tests/manual/<test_file_name>.py

# 例：音声メモ機能のクイックテスト
uv run python tests/manual/quick_voice_test.py
```

## 注意事項

- すべてのテストファイルは適切にプロジェクトルートパスを設定しています
- 一部のテストは外部 API を使用するため、適切な認証情報が必要です
- テスト実行前に `uv sync` でプロジェクトの依存関係をインストールしてください
