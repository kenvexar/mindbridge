# Audio

## 概要
- Discord から受信した音声やローカル録音をテキスト化し、ノート生成や AI 処理へ渡す音声パイプラインを提供します。
- Google Cloud Speech API を利用した認識、`pydub` によるフォーマット変換、音声使用量トラッキングを担います。

## 主要モジュール
| モジュール | 説明 |
| --- | --- |
| `speech_processor.py` | 音声ファイルの検証、分割、認識、メタデータ化を行うメインロジック |
| `models.py` | 音声処理結果・統計の Pydantic モデル群 |

## 外部依存
- `google-cloud-speech`, `aiohttp`, `aiofiles`, `pydub`, `tenacity`。
- 必須環境変数: `GOOGLE_CLOUD_SPEECH_API_KEY` または `GOOGLE_APPLICATION_CREDENTIALS`。

## テスト
- 手動テスト: `tests/manual/test_voice_memo.py`, `tests/manual/test_real_voice.py`, `tests/manual/quick_voice_test.py`。
- 統合テスト: `tests/integration/test_complete_integration.py` で音声→AI→Obsidian フローを確認。

## 連携・利用箇所
- `src/bot/handlers/audio_handler.py` から呼び出され、Discord ボイスメッセージを処理。
- Obsidian のテンプレート生成 (`src/obsidian/template_system`) と連動。

## メモ
- `pydub` はローカルで `ffmpeg` の存在が前提。CI ではモックモードを利用する。
- API 呼び出し数は `AudioUsageStats` で追跡されるため、アラート設定は `Settings` の閾値に依存。
