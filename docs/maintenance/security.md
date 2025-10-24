# Security Maintenance

## Access Log Rotation

MindBridge はセキュリティ監査イベントを `logs/security_access.jsonl` に JSONL 形式で書き出し、既定では **5 MB × 5 世代**（合計 約 25 MB）でローテーションします。長期運用やディスク制限に合わせて、以下の設定値を `.env` もしくは Secret Manager に追加してください。

| 環境変数 | 役割 | 既定値 | 例 |
| --- | --- | --- | --- |
| `ACCESS_LOG_ROTATION_SIZE_MB` | 1 ファイルの最大サイズ (MB) | `5.0` | `10` にすると 10 MB ごとにローテーション |
| `ACCESS_LOG_ROTATION_BACKUPS` | 保存するバックアップ世代数 | `5` | `14` にすると 2 週間分を保持 |

`uv run pytest tests/unit/test_security.py -q` でロガー周りの回帰テストを実行し、設定変更後に Bot を再起動してください。値を小さくするとディスク使用量は抑えられますが、監査証跡の保持期間も短くなります。

## 推奨運用

- Cloud Run などコンテナ環境では、必要に応じて Cloud Logging への転送も併用し、ローカルログは短期間でローテーションされるように調整します。
- ログファイルは機密情報を含む可能性があるため、バックアップ対象から除外し、権限を絞ったロールのみが閲覧できるようにしてください。
