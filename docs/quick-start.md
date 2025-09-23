# クイックスタート

最短 3 ステップでローカル実行。

## 前提条件

- Python 3.13+ と uv パッケージマネージャー
- Discord アカウント と Google Gemini API キー

## 1. 依存関係インストール

```bash
uv sync --dev
```

## 2. 環境設定

```bash
./scripts/manage.sh init
```

## 3. 起動

```bash
uv run python -m src.main
```

## 使用開始

Discord チャンネル `#memo` にメッセージを投稿すると、 AI が自動で Obsidian ノートを生成します。
