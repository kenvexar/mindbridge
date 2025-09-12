"""
ライフログ Obsidian テンプレート

ライフログエントリーを Obsidian ノートに変換するためのテンプレート
"""

from datetime import date

from .models import (
    DailyLifeSummary,
    HabitTracker,
    LifeGoal,
    LifelogCategory,
    LifelogEntry,
    LifelogType,
    WeeklyLifeReport,
)


class LifelogTemplates:
    """ライフログ用 Obsidian テンプレート生成"""

    @staticmethod
    def generate_entry_note(entry: LifelogEntry) -> str:
        """個別エントリーノートを生成"""

        # YAML フロントマター
        frontmatter = f"""---
type: lifelog_entry
category: {entry.category}
entry_type: {entry.type}
created: {entry.created_at.strftime("%Y-%m-%d %H:%M:%S")}
timestamp: {entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")}
source: {entry.source}"""

        if entry.tags:
            tags_str = ", ".join([f'"{tag}"' for tag in entry.tags])
            frontmatter += f"\ntags: [{tags_str}]"

        if entry.mood:
            frontmatter += f"\nmood: {entry.mood}"

        if entry.energy_level:
            frontmatter += f"\nenergy: {entry.energy_level}"

        if entry.numeric_value:
            frontmatter += f"\nvalue: {entry.numeric_value}"
            if entry.unit:
                frontmatter += f"\nunit: {entry.unit}"

        if entry.location:
            frontmatter += f"\nlocation: {entry.location}"

        if entry.related_habit_id:
            frontmatter += f"\nrelated_habit: {entry.related_habit_id}"

        if entry.related_goal_id:
            frontmatter += f"\nrelated_goal: {entry.related_goal_id}"

        frontmatter += "\n---\n"

        # ノート本文
        content = f"""# {entry.title}

## 詳細

{entry.content}
"""

        # カテゴリ別の追加情報
        if entry.category == LifelogCategory.HEALTH:
            content += LifelogTemplates._add_health_section(entry)
        elif entry.category == LifelogCategory.WORK:
            content += LifelogTemplates._add_work_section(entry)
        elif entry.category == LifelogCategory.LEARNING:
            content += LifelogTemplates._add_learning_section(entry)
        elif entry.category == LifelogCategory.MOOD:
            content += LifelogTemplates._add_mood_section(entry)
        elif entry.category == LifelogCategory.FINANCE:
            content += LifelogTemplates._add_finance_section(entry)

        # メタデータセクション
        content += f"""
## メタデータ

- **記録日時**: {entry.timestamp.strftime("%Y 年%m 月%d 日 %H:%M")}
- **カテゴリ**: {LifelogTemplates._get_category_display(entry.category)}
- **タイプ**: {LifelogTemplates._get_type_display(entry.type)}
"""

        if entry.mood:
            mood_emoji = {1: "😞", 2: "😔", 3: "😐", 4: "😊", 5: "😄"}
            content += (
                f"- **気分**: {mood_emoji.get(entry.mood, '😐')} {entry.mood}/5\n"
            )

        if entry.energy_level:
            energy_emoji = "⚡" * entry.energy_level
            content += f"- **エネルギー**: {energy_emoji} {entry.energy_level}/5\n"

        if entry.numeric_value:
            content += f"- **数値**: {entry.numeric_value} {entry.unit or ''}\n"

        if entry.tags:
            tag_links = [f"#{tag}" for tag in entry.tags]
            content += f"- **タグ**: {', '.join(tag_links)}\n"

        return frontmatter + content

    @staticmethod
    def generate_daily_summary_note(summary: DailyLifeSummary) -> str:
        """日次サマリーノートを生成"""

        date_str = summary.date.strftime("%Y-%m-%d")

        frontmatter = f"""---
type: lifelog_daily_summary
date: {date_str}
total_entries: {summary.total_entries}
completion_rate: {summary.completion_rate:.1f}
generated: {summary.generated_at.strftime("%Y-%m-%d %H:%M:%S")}
---

"""

        content = f"""# 📊 Daily Life Summary - {summary.date.strftime("%Y 年%m 月%d 日")}

## 📈 基本統計

- **総エントリー数**: {summary.total_entries}件
- **アクティブカテゴリ**: {len(summary.categories_active)}種類
- **習慣完了率**: {summary.completion_rate:.1f}%

## 😊 気分・エネルギー

"""

        if summary.mood_average:
            mood_emoji = {1: "😞", 2: "😔", 3: "😐", 4: "😊", 5: "😄"}
            mood_icon = mood_emoji.get(round(summary.mood_average), "😐")
            content += f"- **平均気分**: {mood_icon} {summary.mood_average:.1f}/5\n"

        if summary.energy_average:
            energy_bars = "▓" * round(summary.energy_average) + "░" * (
                5 - round(summary.energy_average)
            )
            content += f"- **平均エネルギー**: [{energy_bars}] {summary.energy_average:.1f}/5\n"

        if summary.mood_trend:
            trend_emoji = {"improving": "📈", "stable": "➡️", "declining": "📉"}
            content += f"- **気分トレンド**: {trend_emoji.get(summary.mood_trend, '➡️')} {summary.mood_trend}\n"

        # 習慣セクション
        if summary.habits_completed or summary.habits_missed:
            content += """
## ✅ 習慣トラッキング

"""
            if summary.habits_completed:
                content += "### 完了した習慣\n\n"
                for habit in summary.habits_completed:
                    content += f"- [x] {habit}\n"
                content += "\n"

            if summary.habits_missed:
                content += "### 未完了の習慣\n\n"
                for habit in summary.habits_missed:
                    content += f"- [ ] {habit}\n"
                content += "\n"

        # 主要イベント
        if summary.key_events:
            content += "## 🎯 主要イベント\n\n"
            for event in summary.key_events:
                content += f"- {event}\n"
            content += "\n"

        # 達成事項
        if summary.achievements:
            content += "## 🏆 達成事項\n\n"
            for achievement in summary.achievements:
                content += f"- {achievement}\n"
            content += "\n"

        # 課題・困難
        if summary.challenges:
            content += "## ⚠️ 課題・困難\n\n"
            for challenge in summary.challenges:
                content += f"- {challenge}\n"
            content += "\n"

        # AI 洞察
        if summary.ai_insights:
            content += "## 🤖 AI 分析・洞察\n\n"
            for insight in summary.ai_insights:
                content += f"- {insight}\n"
            content += "\n"

        # 推奨事項
        if summary.recommendations:
            content += "## 💡 明日への提案\n\n"
            for recommendation in summary.recommendations:
                content += f"- {recommendation}\n"
            content += "\n"

        # カテゴリ分布（視覚的表現）
        if summary.categories_active:
            content += "## 📊 活動分布\n\n"
            for category in summary.categories_active:
                display_name = LifelogTemplates._get_category_display(category)
                content += f"- {display_name}\n"
            content += "\n"

        # 関連リンク
        from datetime import timedelta

        prev_date = summary.date - timedelta(days=1)
        next_date = summary.date + timedelta(days=1)

        content += f"""## 🔗 関連リンク

- [[Daily Summary {prev_date.strftime("%Y-%m-%d")}|前日のサマリー]]
- [[Daily Summary {next_date.strftime("%Y-%m-%d")}|翌日のサマリー]]
- [[Weekly Summary {summary.date.strftime("%Y-W%U")}|今週のサマリー]]

---

*このサマリーは自動生成されました ({summary.generated_at.strftime("%Y-%m-%d %H:%M")})*
"""

        return frontmatter + content

    @staticmethod
    def generate_weekly_report_note(report: WeeklyLifeReport) -> str:
        """週次レポートノートを生成"""

        f"{report.week_start.strftime('%Y-%m-%d')}_to_{report.week_end.strftime('%Y-%m-%d')}"

        frontmatter = f"""---
type: lifelog_weekly_report
week_start: {report.week_start.strftime("%Y-%m-%d")}
week_end: {report.week_end.strftime("%Y-%m-%d")}
total_entries: {report.total_entries}
daily_average: {report.daily_average:.1f}
generated: {report.generated_at.strftime("%Y-%m-%d %H:%M:%S")}
---

"""

        content = f"""# 📅 Weekly Life Report - {report.week_start.strftime("%Y 年%m 月%d 日")} 〜 {report.week_end.strftime("%m 月%d 日")}

## 📊 週間統計

- **総エントリー数**: {report.total_entries}件
- **1 日平均**: {report.daily_average:.1f}件
"""

        if report.most_active_day:
            content += f"- **最も活発だった日**: {report.most_active_day}\n"

        content += "\n## 📈 気分・エネルギートレンド\n\n"

        if report.mood_trend:
            # 簡単な気分チャート
            mood_chart = ""
            for i, mood in enumerate(report.mood_trend):
                day = ["月", "火", "水", "木", "金", "土", "日"][i % 7]
                mood_bar = "●" * round(mood) + "○" * (5 - round(mood))
                mood_chart += f"{day}: {mood_bar} ({mood:.1f})\n"
            content += f"### 気分変化\n```\n{mood_chart}```\n\n"

        if report.energy_trend:
            # エネルギーチャート
            energy_chart = ""
            for i, energy in enumerate(report.energy_trend):
                day = ["月", "火", "水", "木", "金", "土", "日"][i % 7]
                energy_bar = "▓" * round(energy) + "░" * (5 - round(energy))
                energy_chart += f"{day}: {energy_bar} ({energy:.1f})\n"
            content += f"### エネルギー変化\n```\n{energy_chart}```\n\n"

        # 習慣パフォーマンス
        if report.habit_success_rates:
            content += "## ✅ 習慣パフォーマンス\n\n"
            for habit, rate in report.habit_success_rates.items():
                success_bar = "█" * (round(rate) // 10) + "░" * (
                    10 - (round(rate) // 10)
                )
                status_emoji = "🟢" if rate >= 80 else "🟡" if rate >= 50 else "🔴"
                content += (
                    f"- {status_emoji} **{habit}**: [{success_bar}] {rate:.1f}%\n"
                )
            content += "\n"

        # 習慣トレンド
        if report.improving_habits:
            content += "### 📈 向上中の習慣\n\n"
            for habit in report.improving_habits:
                content += f"- ✅ {habit}\n"
            content += "\n"

        if report.declining_habits:
            content += "### 📉 要改善の習慣\n\n"
            for habit in report.declining_habits:
                content += f"- ⚠️ {habit}\n"
            content += "\n"

        # カテゴリ分析
        if report.category_distribution:
            content += "## 🏷️ 活動カテゴリ分析\n\n"
            total = sum(report.category_distribution.values())
            for category, count in sorted(
                report.category_distribution.items(), key=lambda x: x[1], reverse=True
            ):
                percentage = (count / total) * 100
                display_name = LifelogTemplates._get_category_display_jp(category)
                bar = "█" * (round(percentage) // 5) + "░" * (
                    20 - (round(percentage) // 5)
                )
                content += (
                    f"- **{display_name}**: [{bar}] {count}件 ({percentage:.1f}%)\n"
                )
            content += "\n"

        # 重点・軽視分野
        if report.focus_areas:
            content += "### 🎯 重点分野\n\n"
            for area in report.focus_areas:
                display_name = LifelogTemplates._get_category_display_jp(area)
                content += f"- {display_name}\n"
            content += "\n"

        if report.neglected_areas:
            content += "### 💭 軽視されがちな分野\n\n"
            for area in report.neglected_areas:
                display_name = LifelogTemplates._get_category_display_jp(area)
                content += f"- {display_name}\n"
            content += "\n"

        # 週間ハイライト
        if report.achievements:
            content += "## 🏆 今週の達成事項\n\n"
            for achievement in report.achievements:
                content += f"- {achievement}\n"
            content += "\n"

        if report.learnings:
            content += "## 📚 今週の学び\n\n"
            for learning in report.learnings:
                content += f"- {learning}\n"
            content += "\n"

        if report.next_week_goals:
            content += "## 🎯 来週の目標\n\n"
            for goal in report.next_week_goals:
                content += f"- [ ] {goal}\n"
            content += "\n"

        # 関連リンク
        from datetime import timedelta

        prev_week = report.week_start - timedelta(days=7)
        next_week = report.week_start + timedelta(days=7)

        content += f"""## 🔗 関連リンク

- [[Weekly Report {prev_week.strftime("%Y-W%U")}|前週のレポート]]
- [[Weekly Report {next_week.strftime("%Y-W%U")}|来週のレポート]]
- [[Monthly Report {report.week_start.strftime("%Y-%m")}|今月のレポート]]

---

*このレポートは自動生成されました ({report.generated_at.strftime("%Y-%m-%d %H:%M")})*
"""

        return frontmatter + content

    @staticmethod
    def generate_habit_tracker_note(habit: HabitTracker) -> str:
        """習慣トラッカーノートを生成"""

        frontmatter = f"""---
type: lifelog_habit_tracker
habit_id: {habit.id}
name: {habit.name}
category: {habit.category}
target_frequency: {habit.target_frequency}
current_streak: {habit.current_streak}
best_streak: {habit.best_streak}
total_completions: {habit.total_completions}
active: {habit.active}
created: {habit.created_at.strftime("%Y-%m-%d")}
---

"""

        content = f"""# 🎯 習慣トラッカー: {habit.name}

## 基本情報

- **習慣名**: {habit.name}
- **説明**: {habit.description or "説明なし"}
- **カテゴリ**: {LifelogTemplates._get_category_display(habit.category)}
- **頻度目標**: {habit.target_frequency}
- **開始日**: {habit.start_date.strftime("%Y 年%m 月%d 日")}

## 進捗状況

- **現在の連続記録**: {habit.current_streak} 日 🔥
- **最高連続記録**: {habit.best_streak} 日 🏆
- **総完了回数**: {habit.total_completions} 回 ✅
- **ステータス**: {"🟢 アクティブ" if habit.active else "🔴 非アクティブ"}

## 数値目標

"""

        if habit.target_value:
            content += f"- **目標値**: {habit.target_value} {habit.target_unit or ''}\n"
        else:
            content += "- 数値目標は設定されていません\n"

        # リマインダー設定
        if habit.reminder_enabled and habit.reminder_time:
            content += f"""
## リマインダー

- **リマインダー**: 🔔 有効
- **時刻**: {habit.reminder_time.strftime("%H:%M")}
"""
        else:
            content += """
## リマインダー

- **リマインダー**: 🔕 無効
"""

        # 習慣完了記録セクション（今後の実装で自動生成）
        content += f"""
## 📅 完了記録

*ここに習慣の完了履歴が表示されます*

## 📈 分析・洞察

*ここに習慣に関する分析やトレンドが表示されます*

## 🔗 関連エントリー

*この習慣に関連するライフログエントリーがここに表示されます*

---

*最終更新: {habit.updated_at.strftime("%Y-%m-%d %H:%M")}*
"""

        return frontmatter + content

    @staticmethod
    def generate_goal_tracker_note(goal: LifeGoal) -> str:
        """目標トラッカーノートを生成"""

        frontmatter = f"""---
type: lifelog_goal_tracker
goal_id: {goal.id}
title: {goal.title}
category: {goal.category}
status: {goal.status}
priority: {goal.priority}
progress: {goal.progress_percentage:.1f}
created: {goal.created_at.strftime("%Y-%m-%d")}
---

"""

        # ステータス絵文字
        status_emoji = {
            "active": "🎯",
            "completed": "🏆",
            "paused": "⏸️",
            "cancelled": "❌",
        }

        # 優先度表示
        priority_display = "⭐" * goal.priority

        # 進捗バー
        progress_filled = round(goal.progress_percentage / 10)
        progress_bar = "█" * progress_filled + "░" * (10 - progress_filled)

        content = f"""# {status_emoji.get(goal.status, "🎯")} 目標: {goal.title}

## 基本情報

- **目標**: {goal.title}
- **説明**: {goal.description}
- **カテゴリ**: {LifelogTemplates._get_category_display(goal.category)}
- **優先度**: {priority_display} ({goal.priority}/5)
- **ステータス**: {goal.status}

## 進捗状況

**進捗率**: [{progress_bar}] {goal.progress_percentage:.1f}%

"""

        if goal.target_value:
            content += f"- **現在値**: {goal.current_value} {goal.target_unit or ''}\n"
            content += f"- **目標値**: {goal.target_value} {goal.target_unit or ''}\n"
            if goal.target_value > 0:
                remaining = goal.target_value - goal.current_value
                content += f"- **残り**: {remaining} {goal.target_unit or ''}\n"

        if goal.target_date:
            content += f"- **期限**: {goal.target_date.strftime('%Y 年%m 月%d 日')}\n"
            days_left = (goal.target_date - date.today()).days
            if days_left > 0:
                content += f"- **残り日数**: {days_left}日\n"
            elif days_left == 0:
                content += "- **期限**: ⚠️ 今日が期限です\n"
            else:
                content += f"- **期限**: ❗ {abs(days_left)}日超過\n"

        # 関連習慣
        if goal.related_habits:
            content += """
## 関連習慣

"""
            for habit_id in goal.related_habits:
                content += f"- [[Habit_{habit_id}|関連習慣 {habit_id}]]\n"

        # 親・子目標
        if goal.parent_goal_id:
            content += f"""
## 関連目標

- **親目標**: [[Goal_{goal.parent_goal_id}|{goal.parent_goal_id}]]
"""

        # 進捗記録セクション
        content += f"""
## 📈 進捗履歴

*ここに進捗の履歴が表示されます*

## 💭 振り返り・メモ

*目標に関する気づきや振り返りを記録してください*

## 🔗 関連エントリー

*この目標に関連するライフログエントリーがここに表示されます*

---

*最終更新: {goal.updated_at.strftime("%Y-%m-%d %H:%M")}*
"""

        return frontmatter + content

    @staticmethod
    def _add_health_section(entry: LifelogEntry) -> str:
        """健康関連の追加セクション"""
        section = "\n## 🏃 健康データ\n\n"

        if entry.numeric_value and entry.unit:
            if "km" in entry.unit or "歩" in entry.unit:
                section += f"- **運動量**: {entry.numeric_value} {entry.unit}\n"
            elif "kg" in entry.unit:
                section += f"- **体重**: {entry.numeric_value} {entry.unit}\n"
            elif "時間" in entry.unit:
                section += f"- **時間**: {entry.numeric_value} {entry.unit}\n"

        if entry.location:
            section += f"- **場所**: {entry.location}\n"

        return section

    @staticmethod
    def _add_work_section(entry: LifelogEntry) -> str:
        """仕事関連の追加セクション"""
        section = "\n## 💼 仕事詳細\n\n"

        if "完了" in entry.content or "達成" in entry.content:
            section += "- **ステータス**: ✅ 完了\n"
        elif "進行中" in entry.content:
            section += "- **ステータス**: 🔄 進行中\n"
        elif "開始" in entry.content:
            section += "- **ステータス**: 🎯 開始\n"

        return section

    @staticmethod
    def _add_learning_section(entry: LifelogEntry) -> str:
        """学習関連の追加セクション"""
        section = "\n## 📚 学習記録\n\n"

        if entry.numeric_value and entry.unit:
            if "時間" in entry.unit:
                section += f"- **学習時間**: {entry.numeric_value} {entry.unit}\n"
            elif "冊" in entry.unit:
                section += f"- **読書量**: {entry.numeric_value} {entry.unit}\n"
            elif "ページ" in entry.unit:
                section += f"- **ページ数**: {entry.numeric_value} {entry.unit}\n"

        return section

    @staticmethod
    def _add_mood_section(entry: LifelogEntry) -> str:
        """気分関連の追加セクション"""
        section = "\n## 😊 感情・気分\n\n"

        if entry.mood:
            mood_labels = {
                1: "とても悪い",
                2: "悪い",
                3: "普通",
                4: "良い",
                5: "とても良い",
            }
            section += f"- **気分レベル**: {mood_labels.get(entry.mood.value, '不明')} ({entry.mood.value}/5)\n"

        return section

    @staticmethod
    def _add_finance_section(entry: LifelogEntry) -> str:
        """財務関連の追加セクション"""
        section = "\n## 💰 財務情報\n\n"

        if entry.numeric_value:
            if "支出" in entry.tags:
                section += f"- **支出額**: {entry.numeric_value:,.0f}円\n"
            elif "収入" in entry.tags:
                section += f"- **収入額**: {entry.numeric_value:,.0f}円\n"
            else:
                section += f"- **金額**: {entry.numeric_value:,.0f}円\n"

        return section

    @staticmethod
    def _get_category_display(category: LifelogCategory) -> str:
        """カテゴリの表示名を取得"""
        display_map = {
            LifelogCategory.HEALTH: "🏃 健康・運動",
            LifelogCategory.WORK: "💼 仕事・プロジェクト",
            LifelogCategory.LEARNING: "📚 学習・スキル",
            LifelogCategory.FINANCE: "💰 財務・金銭",
            LifelogCategory.RELATIONSHIP: "👥 人間関係",
            LifelogCategory.ENTERTAINMENT: "🎮 娯楽・趣味",
            LifelogCategory.ROUTINE: "🔄 日常・ルーティン",
            LifelogCategory.REFLECTION: "💭 振り返り・考察",
            LifelogCategory.GOAL: "🎯 目標・計画",
            LifelogCategory.MOOD: "😊 気分・感情",
        }
        return display_map.get(category, str(category))

    @staticmethod
    def _get_category_display_jp(category_str: str) -> str:
        """カテゴリ文字列の日本語表示名を取得"""
        display_map = {
            "health": "🏃 健康・運動",
            "work": "💼 仕事・プロジェクト",
            "learning": "📚 学習・スキル",
            "finance": "💰 財務・金銭",
            "relationship": "👥 人間関係",
            "entertainment": "🎮 娯楽・趣味",
            "routine": "🔄 日常・ルーティン",
            "reflection": "💭 振り返り・考察",
            "goal": "🎯 目標・計画",
            "mood": "😊 気分・感情",
        }
        return display_map.get(category_str, category_str)

    @staticmethod
    def _get_type_display(entry_type: LifelogType) -> str:
        """エントリータイプの表示名を取得"""
        display_map = {
            LifelogType.EVENT: "📅 イベント",
            LifelogType.HABIT: "🔄 習慣",
            LifelogType.METRIC: "📊 メトリクス",
            LifelogType.REFLECTION: "💭 振り返り",
            LifelogType.GOAL_PROGRESS: "🎯 目標進捗",
        }
        return display_map.get(entry_type, str(entry_type))
