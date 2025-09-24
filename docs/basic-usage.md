# 基本的な使用方法

Discord の `#memo` チャンネルに投稿すると、 AI が Obsidian ノートを自動生成します。

## 入力方法

- **テキスト**: 通常の文章を送信すると AI が要約と分類を実施
- **音声ファイル**: MP3 / WAV / FLAC / OGG / M4A / WEBM を添付すると自動で文字起こし
- **URL 含むメッセージ**: コンテンツを取得して要約をノートへ追記

## 自動処理で生成される情報

- YAML フロントマター（タイトル、作成日時、タグなど）
- Daily Note との連携とプレースホルダー置換
- URL 要約や添付ファイルの整理

## 利用可能な Slash コマンド

**基本操作**
- `/help` 基本コマンド一覧
- `/status` Bot の稼働状況
- `/search query:<キーワード> [limit]` ノート検索
- `/random` ランダムなノート表示

**設定関連**
- `/show [setting]` 既知の設定情報の参照（現在は検出したチャンネル数のみ表示）
- `/set setting:<キー> value:<値>` 設定変更リクエスト（永続化は今後対応予定）
- `/history` 設定変更履歴の表示（履歴が無い場合は案内のみ）

**統計情報**
- `/bot` Bot の稼働統計
- `/obsidian` Obsidian Vault の統計
- `/finance` 家計関連の概要統計
- `/tasks` タスク関連統計

**外部連携・ヘルスケア**
- `/integration_status` 登録済み連携の状態一覧
- `/system_status` スケジューラやキャッシュなどの健全性確認
- `/manual_sync name:<連携名>` 指定連携の即時同期
- `/integration_config` 連携設定のプレビュー
- `/scheduler_status` スケジューラジョブの稼働状況
- `/lifelog_stats` ライフログの統計ハイライト
- `/garmin_today` Garmin 今日の活動サマリー
- `/garmin_sleep` Garmin 睡眠データのサマリー
- `/calendar_auth` Google Calendar OAuth 開始
- `/calendar_token code:<認証コード>` Google Calendar トークン登録
- `/calendar_test` Google Calendar 接続テスト

Slash コマンドはギルド専用同期のため、反映に数秒かかることがあります。
