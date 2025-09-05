# Obsidian Vault フォルダ構成ガイド

## 概要

MindBridge の新しい使用頻度ベースのフォルダ構成について説明します。

## 📁 フォルダ構成

### 🎯 設計原則

1. **使用頻度順の番号付け** - よく使うものほど小さい番号（上位表示）
2. **機能別グループ化** - 類似機能を10番台単位でまとめ
3. **直感的な順序** - Obsidianで実用的な表示順序
4. **階層構造** - サブフォルダで詳細分類

### 📂 完全フォルダ構成

```
=== 日常使用フォルダ（高頻度・00-09番台）===
00_Inbox/               # 受信箱・未分類
├── unprocessed/        # 未処理
├── pending/           # 保留中
└── staged/            # 準備完了

01_DailyNotes/          # 日次ノート
├── current/           # 今月
└── archive/           # 過去分

02_Tasks/               # タスク管理
├── backlog/           # バックログ
├── active/            # 作業中
├── waiting/           # 待機中
├── completed/         # 完了済み
└── templates/         # テンプレート

03_Ideas/               # アイデア・着想
├── brainstorm/        # ブレインストーム
├── concepts/          # コンセプト
└── innovation/        # 革新的アイデア

=== 知識・学習系（中頻度・10-19番台）===
10_Knowledge/           # 学習・技術知識
├── technical/         # 技術知識
├── processes/         # プロセス・手順
├── tools/             # ツール・方法論
└── learnings/         # 学習記録

11_Projects/            # プロジェクト・仕事
├── active/            # 進行中
├── planning/          # 計画中
├── on-hold/           # 保留中
└── completed/         # 完了

12_Resources/           # 資料・参考文献
├── references/        # 参考文献
├── bookmarks/         # ブックマーク
└── documents/         # 重要文書

=== 記録・管理系（中頻度・20-29番台）===
20_Finance/             # 家計・財務管理
├── expenses/          # 支出記録
├── income/            # 収入記録
├── subscriptions/     # サブスクリプション
├── budgets/           # 予算管理
└── reports/           # 財務レポート

21_Health/              # 健康・運動記録
├── activities/        # 運動・活動
├── sleep/             # 睡眠記録
├── wellness/          # 健康管理
├── medical/           # 医療記録
└── analytics/         # 健康分析

=== アーカイブ（低頻度・30番台）===
30_Archive/             # 完了・過去のもの

=== システム関連（80-90番台）===
80_Attachments/         # 添付ファイル
├── Images/            # 画像ファイル
├── Audio/             # 音声ファイル
├── Documents/         # 文書ファイル
└── Other/             # その他ファイル

90_Meta/                # メタデータ・テンプレート
└── Templates/         # テンプレート
```

## 🤖 AI 自動分類システム

MindBridge の AI が #memo チャンネルの投稿を自動分析し、適切なフォルダに分類します。

### 分類例

| コンテンツ例 | 分類先フォルダ |
|-------------|---------------|
| "1500 ランチ" | 20_Finance/expenses |
| "TODO: 資料作成" | 02_Tasks/active |
| "体重 70kg" | 21_Health/wellness |
| "Python 学習" | 10_Knowledge/learnings |
| "新アイデア" | 03_Ideas/brainstorm |
| "プロジェクト進捗" | 11_Projects/active |
| "参考記事ブックマーク" | 12_Resources/bookmarks |
| "完了した案件" | 30_Archive |

### 特徴的なカテゴリ

- **12_Resources** - 資料・参考文献用の新カテゴリ
- **30_Archive** - 完了・過去のもの用アーカイブ
- **80_Attachments** - 添付ファイル専用領域（自動振り分け）

## 🔧 新規セットアップ手順

### 1. フォルダ構成作成

```bash
# メインフォルダ
mkdir -p 00_Inbox 01_DailyNotes 02_Tasks 03_Ideas 10_Knowledge 11_Projects 12_Resources 20_Finance 21_Health 30_Archive 80_Attachments 90_Meta

# サブフォルダ作成
mkdir -p 00_Inbox/{unprocessed,pending,staged}
mkdir -p 01_DailyNotes/{current,archive}
mkdir -p 02_Tasks/{backlog,active,waiting,completed,templates}
mkdir -p 03_Ideas/{brainstorm,concepts,innovation}
mkdir -p 10_Knowledge/{technical,processes,tools,learnings}
mkdir -p 11_Projects/{active,planning,on-hold,completed}
mkdir -p 12_Resources/{references,bookmarks,documents}
mkdir -p 20_Finance/{expenses,income,subscriptions,budgets,reports}
mkdir -p 21_Health/{activities,sleep,wellness,medical,analytics}
mkdir -p 80_Attachments/{Images,Audio,Documents,Other}
mkdir -p 90_Meta/Templates
```

### 2. 構造確認

```bash
find . -type d | grep -E "^\./(00_|01_|02_|03_|10_|11_|12_|20_|21_|30_|80_|90_)" | sort
```

### 3. マッピングテスト

```bash
uv run python -c "
from src.obsidian.models import VaultFolder, FolderMapping
print('Finance mapping:', FolderMapping.get_folder_for_category('finance').value)
print('Task mapping:', FolderMapping.get_folder_for_category('task').value)
print('Health mapping:', FolderMapping.get_folder_for_category('health').value)
print('Knowledge mapping:', FolderMapping.get_folder_for_category('learning').value)
"
```

## 📊 フォルダ統計

- **総フォルダ数**: 51個
- **メインカテゴリ**: 12個
- **サブフォルダ**: 39個
- **グループ数**: 5グループ（日常・知識・記録・アーカイブ・システム）

## ✨ 使用上の利点

1. **高速アクセス** - 頻繁に使うフォルダが上位表示
2. **論理的分類** - 機能別に10番台でグループ化
3. **拡張性** - 各グループ内で新フォルダ追加が容易
4. **視認性** - 数字プレフィックスで明確な順序

## 🔧 カスタマイズ

必要に応じて以下のサブフォルダを追加できます：

```bash
# 例：新しいサブカテゴリ追加
mkdir -p 02_Tasks/urgent          # 緊急タスク
mkdir -p 10_Knowledge/certifications  # 資格・認定
mkdir -p 20_Finance/investments   # 投資記録
```

---

## 📅 更新履歴

- **2025-09-04**: 新フォルダ構成を確立

---

*Generated by MindBridge System*
