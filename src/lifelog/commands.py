"""
ライフログ Discord コマンド

Discord 経由でライフログ機能を利用するためのコマンド実装
"""

import re
from datetime import date, datetime, timedelta
from typing import Any

import discord
import structlog
from discord.ext import commands

from .analyzer import LifelogAnalyzer
from .manager import LifelogManager
from .models import (
    HabitTracker,
    LifeGoal,
    LifelogCategory,
    LifelogEntry,
    LifelogType,
    MoodLevel,
)

logger = structlog.get_logger(__name__)


class LifelogCommands:
    """ライフログ関連の Discord コマンド"""

    def __init__(
        self, lifelog_manager: LifelogManager, lifelog_analyzer: LifelogAnalyzer
    ):
        self.lifelog_manager = lifelog_manager
        self.analyzer = lifelog_analyzer

    async def register_commands(self, bot: commands.Bot):
        """ボットにコマンドを登録"""

        @bot.command(name="log", help="ライフログエントリーを記録")  # type: ignore[arg-type]
        async def log_entry(ctx, category: str, *, content: str):
            """ライフログを記録

            使用例:
            !log health 今日は 10km 走った 気分:5 エネルギー:4
            !log work プレゼン資料完成
            !log mood 今日はとても調子が良い
            """
            try:
                # カテゴリの解析
                parsed_category = self._parse_category(category)
                if not parsed_category:
                    await ctx.send(
                        "❌ 無効なカテゴリです。使用可能: health, work, learning, finance, mood, routine, goal"
                    )
                    return

                # コンテンツから追加情報を抽出
                parsed_data = self._parse_content(content)

                # エントリー作成
                entry = LifelogEntry(
                    category=parsed_category,
                    type=LifelogType.EVENT,
                    title=parsed_data.get("title", f"{category}の記録"),
                    content=parsed_data["content"],
                    tags=parsed_data.get("tags", []),
                    mood=parsed_data.get("mood"),
                    energy_level=parsed_data.get("energy"),
                    numeric_value=parsed_data.get("value"),
                    unit=parsed_data.get("unit"),
                    location=parsed_data.get("location"),
                    source="discord",
                )

                entry_id = await self.lifelog_manager.add_entry(entry)

                # 確認メッセージ
                embed = discord.Embed(
                    title="✅ ライフログを記録しました",
                    description=f"**{category}** カテゴリに記録",
                    color=0x00FF00,
                )
                embed.add_field(name="内容", value=parsed_data["content"], inline=False)

                if entry.mood:
                    embed.add_field(
                        name="気分", value=f"{entry.mood.value}/5", inline=True
                    )
                if entry.energy_level:
                    embed.add_field(
                        name="エネルギー", value=f"{entry.energy_level}/5", inline=True
                    )
                if entry.numeric_value:
                    embed.add_field(
                        name="値",
                        value=f"{entry.numeric_value} {entry.unit or ''}",
                        inline=True,
                    )

                embed.set_footer(text=f"ID: {entry_id}")
                await ctx.send(embed=embed)

            except Exception as e:
                logger.error("ライフログ記録でエラー", error=str(e))
                await ctx.send(f"❌ エラーが発生しました: {str(e)}")

        @bot.command(name="mood", help="気分を記録")  # type: ignore[arg-type]
        async def log_mood(ctx, mood_value: int, *, description: str = ""):
            """気分を記録

            使用例:
            !mood 4 今日は調子が良い
            !mood 2 ちょっと疲れている
            """
            try:
                if not 1 <= mood_value <= 5:
                    await ctx.send("❌ 気分は 1-5 の範囲で入力してください")
                    return

                mood = MoodLevel(mood_value)
                title = f"気分記録: {mood_value}/5"
                content = description or "気分を記録しました"

                entry = LifelogEntry(
                    category=LifelogCategory.MOOD,
                    type=LifelogType.METRIC,
                    title=title,
                    content=content,
                    mood=mood,
                    source="discord",
                )

                await self.lifelog_manager.add_entry(entry)

                # 気分の絵文字マッピング
                mood_emojis = {1: "😞", 2: "😔", 3: "😐", 4: "😊", 5: "😄"}

                embed = discord.Embed(
                    title=f"{mood_emojis[mood_value]} 気分を記録しました",
                    description=f"**{mood_value}/5** - {content}",
                    color=0x3498DB,
                )

                await ctx.send(embed=embed)

            except Exception as e:
                logger.error("気分記録でエラー", error=str(e))
                await ctx.send(f"❌ エラーが発生しました: {str(e)}")

        @bot.command(name="habit", help="習慣を記録または管理")  # type: ignore[arg-type]
        async def habit_command(ctx, action: str, *, args: str = ""):
            """習慣管理

            使用例:
            !habit create 運動 daily 毎日 30 分の運動
            !habit done 運動
            !habit list
            !habit status 運動
            """
            try:
                if action == "create":
                    await self._create_habit(ctx, args)
                elif action == "done":
                    await self._complete_habit(ctx, args)
                elif action == "list":
                    await self._list_habits(ctx)
                elif action == "status":
                    await self._habit_status(ctx, args)
                else:
                    await ctx.send(
                        "❌ 無効なアクション。使用可能: create, done, list, status"
                    )

            except Exception as e:
                logger.error("習慣コマンドでエラー", error=str(e))
                await ctx.send(f"❌ エラーが発生しました: {str(e)}")

        @bot.command(name="goal", help="目標を管理")  # type: ignore[arg-type]
        async def goal_command(ctx, action: str, *, args: str = ""):
            """目標管理

            使用例:
            !goal create 読書 50 冊読む 2024-12-31
            !goal update 読書 25
            !goal list
            !goal status 読書
            """
            try:
                if action == "create":
                    await self._create_goal(ctx, args)
                elif action == "update":
                    await self._update_goal(ctx, args)
                elif action == "list":
                    await self._list_goals(ctx)
                elif action == "status":
                    await self._goal_status(ctx, args)
                else:
                    await ctx.send(
                        "❌ 無効なアクション。使用可能: create, update, list, status"
                    )

            except Exception as e:
                logger.error("目標コマンドでエラー", error=str(e))
                await ctx.send(f"❌ エラーが発生しました: {str(e)}")

        @bot.command(name="lifestats", help="ライフログ統計を表示")  # type: ignore[arg-type]
        async def life_stats(ctx, period: str = "today"):
            """ライフログ統計

            使用例:
            !lifestats today
            !lifestats week
            !lifestats month
            """
            try:
                if period == "today":
                    await self._show_daily_stats(ctx)
                elif period == "week":
                    await self._show_weekly_stats(ctx)
                elif period == "month":
                    await self._show_monthly_stats(ctx)
                else:
                    await ctx.send("❌ 無効な期間。使用可能: today, week, month")

            except Exception as e:
                logger.error("統計表示でエラー", error=str(e))
                await ctx.send(f"❌ エラーが発生しました: {str(e)}")

        @bot.command(name="lifetrend", help="ライフトレンドを分析")  # type: ignore[arg-type]
        async def life_trend(ctx, metric: str = "mood", days: int = 7):
            """トレンド分析

            使用例:
            !lifetrend mood 7
            !lifetrend energy 14
            """
            try:
                await self._show_trend_analysis(ctx, metric, days)
            except Exception as e:
                logger.error("トレンド分析でエラー", error=str(e))
                await ctx.send(f"❌ エラーが発生しました: {str(e)}")

    def _parse_category(self, category_str: str) -> LifelogCategory | None:
        """カテゴリ文字列を解析"""
        category_map = {
            "health": LifelogCategory.HEALTH,
            "work": LifelogCategory.WORK,
            "learning": LifelogCategory.LEARNING,
            "finance": LifelogCategory.FINANCE,
            "relationship": LifelogCategory.RELATIONSHIP,
            "entertainment": LifelogCategory.ENTERTAINMENT,
            "routine": LifelogCategory.ROUTINE,
            "reflection": LifelogCategory.REFLECTION,
            "goal": LifelogCategory.GOAL,
            "mood": LifelogCategory.MOOD,
            # 日本語エイリアス
            "健康": LifelogCategory.HEALTH,
            "仕事": LifelogCategory.WORK,
            "学習": LifelogCategory.LEARNING,
            "財務": LifelogCategory.FINANCE,
            "気分": LifelogCategory.MOOD,
        }
        return category_map.get(category_str.lower())

    def _parse_content(self, content: str) -> dict[str, Any]:
        """コンテンツから追加情報を抽出"""
        result: dict[str, Any] = {"content": content}

        # 気分を抽出 (気分:4, mood:4)
        mood_pattern = r"(?:気分|mood):?(\d)"
        mood_match = re.search(mood_pattern, content, re.IGNORECASE)
        if mood_match:
            try:
                mood_value = int(mood_match.group(1))
                if 1 <= mood_value <= 5:
                    result["mood"] = MoodLevel(mood_value)
                    # コンテンツから気分表記を削除
                    result["content"] = re.sub(
                        mood_pattern, "", content, flags=re.IGNORECASE
                    ).strip()
            except ValueError:
                pass

        # エネルギーを抽出
        energy_pattern = r"(?:エネルギー|energy):?(\d)"
        energy_match = re.search(energy_pattern, content, re.IGNORECASE)
        if energy_match:
            try:
                energy_value = int(energy_match.group(1))
                if 1 <= energy_value <= 5:
                    result["energy"] = energy_value
                    result["content"] = re.sub(
                        energy_pattern, "", result["content"], flags=re.IGNORECASE
                    ).strip()
            except ValueError:
                pass

        # 数値と単位を抽出 (例: 5km, 2 時間, 1000 円)
        value_pattern = r"(\d+(?:\.\d+)?)\s*([a-zA-Z]+|円|時間|分|秒|kg|km|m)"
        value_match = re.search(value_pattern, content)
        if value_match:
            try:
                result["value"] = float(value_match.group(1))
                result["unit"] = value_match.group(2)
            except ValueError:
                pass

        # タグを抽出 (#tag)
        tag_pattern = r"#(\w+)"
        tags = re.findall(tag_pattern, content)
        if tags:
            result["tags"] = tags
            # コンテンツからタグを削除
            result["content"] = re.sub(tag_pattern, "", result["content"]).strip()

        # 場所を抽出 (@location)
        location_pattern = r"@(\w+)"
        location_match = re.search(location_pattern, content)
        if location_match:
            result["location"] = location_match.group(1)
            result["content"] = re.sub(location_pattern, "", result["content"]).strip()

        return result

    async def _create_habit(self, ctx, args: str):
        """習慣を作成"""
        parts = args.split(" ", 2)
        if len(parts) < 3:
            await ctx.send("❌ 使用法: !habit create <名前> <頻度> <説明>")
            return

        name, frequency, description = parts

        habit = HabitTracker(
            name=name,
            description=description,
            category=LifelogCategory.ROUTINE,
            target_frequency=frequency,
            start_date=date.today(),
        )

        habit_id = await self.lifelog_manager.create_habit(habit)

        embed = discord.Embed(
            title="✅ 新しい習慣を作成しました",
            description=f"**{name}** ({frequency})",
            color=0x2ECC71,
        )
        embed.add_field(name="説明", value=description, inline=False)
        embed.set_footer(text=f"ID: {habit_id}")

        await ctx.send(embed=embed)

    async def _complete_habit(self, ctx, habit_name: str):
        """習慣完了を記録"""
        if not habit_name:
            await ctx.send("❌ 習慣名を指定してください")
            return

        # 習慣を検索
        habits = await self.lifelog_manager.get_active_habits()
        matching_habit = None

        for habit in habits:
            if habit.name.lower() == habit_name.lower():
                matching_habit = habit
                break

        if not matching_habit:
            await ctx.send(f"❌ 習慣「{habit_name}」が見つかりません")
            return

        if not matching_habit.id:
            await ctx.send(f"❌ 習慣「{habit_name}」の ID が設定されていません")
            return

        # 完了を記録
        success = await self.lifelog_manager.log_habit_completion(
            matching_habit.id, True
        )

        if success:
            embed = discord.Embed(
                title="🎉 習慣を完了しました",
                description=f"**{matching_habit.name}** を実行しました",
                color=0x27AE60,
            )
            embed.add_field(
                name="総完了回数",
                value=f"{matching_habit.total_completions + 1}回",
                inline=True,
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ 習慣の記録に失敗しました")

    async def _list_habits(self, ctx):
        """習慣一覧を表示"""
        habits = await self.lifelog_manager.get_active_habits()

        if not habits:
            await ctx.send("📋 現在アクティブな習慣はありません")
            return

        embed = discord.Embed(title="📋 アクティブな習慣", color=0x3498DB)

        for habit in habits[:10]:  # 最大 10 個
            status = f"🎯 {habit.target_frequency}"
            if habit.total_completions > 0:
                status += f" | 完了: {habit.total_completions}回"
            if habit.current_streak > 0:
                status += f" | 連続: {habit.current_streak}日"

            embed.add_field(
                name=habit.name, value=f"{habit.description}\n{status}", inline=False
            )

        await ctx.send(embed=embed)

    async def _create_goal(self, ctx, args: str):
        """目標を作成"""
        parts = args.split(" ", 2)
        if len(parts) < 2:
            await ctx.send("❌ 使用法: !goal create <名前> <説明> [期限 YYYY-MM-DD]")
            return

        name = parts[0]
        rest = parts[1] if len(parts) > 1 else ""

        # 期限があるかチェック
        date_pattern = r"(\d{4}-\d{2}-\d{2})"
        date_match = re.search(date_pattern, rest)
        target_date = None

        if date_match:
            try:
                target_date = datetime.strptime(date_match.group(1), "%Y-%m-%d").date()
                description = re.sub(date_pattern, "", rest).strip()
            except ValueError:
                description = rest
        else:
            description = rest

        goal = LifeGoal(
            title=name,
            description=description or f"{name}の目標",
            category=LifelogCategory.GOAL,
            target_date=target_date,
        )

        await self.lifelog_manager.create_goal(goal)

        embed = discord.Embed(
            title="🎯 新しい目標を作成しました",
            description=f"**{name}**",
            color=0xF39C12,
        )
        embed.add_field(name="説明", value=description, inline=False)
        if target_date:
            embed.add_field(
                name="期限", value=target_date.strftime("%Y 年%m 月%d 日"), inline=True
            )

        await ctx.send(embed=embed)

    async def _show_daily_stats(self, ctx):
        """日次統計を表示"""
        today = date.today()
        summary = await self.lifelog_manager.get_daily_summary(today)

        embed = discord.Embed(
            title=f"📊 今日の統計 ({today.strftime('%Y-%m-%d')})", color=0x9B59B6
        )

        embed.add_field(
            name="総エントリー数", value=f"{summary.total_entries}件", inline=True
        )
        embed.add_field(
            name="アクティブカテゴリ",
            value=f"{len(summary.categories_active)}種類",
            inline=True,
        )

        if summary.mood_average:
            embed.add_field(
                name="平均気分", value=f"{summary.mood_average:.1f}/5", inline=True
            )

        if summary.energy_average:
            embed.add_field(
                name="平均エネルギー",
                value=f"{summary.energy_average:.1f}/5",
                inline=True,
            )

        embed.add_field(
            name="習慣完了率", value=f"{summary.completion_rate:.1f}%", inline=True
        )

        if summary.key_events:
            events_text = "\n".join([f"• {event}" for event in summary.key_events])
            embed.add_field(name="主要イベント", value=events_text, inline=False)

        await ctx.send(embed=embed)

    async def _show_trend_analysis(self, ctx, metric: str, days: int):
        """トレンド分析を表示"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)

        entries = await self.lifelog_manager.get_entries_by_date_range(
            start_date, end_date
        )

        if not entries:
            await ctx.send("📊 指定期間のデータがありません")
            return

        # メトリック別の分析
        if metric == "mood":
            mood_data = []
            for entry in entries:
                if entry.mood:
                    mood_data.append((entry.timestamp.date(), entry.mood.value))

            if mood_data:
                avg_mood = sum(mood for _, mood in mood_data) / len(mood_data)

                embed = discord.Embed(
                    title=f"📈 気分トレンド ({days}日間)", color=0xE74C3C
                )
                embed.add_field(name="平均気分", value=f"{avg_mood:.1f}/5", inline=True)
                embed.add_field(
                    name="データ点数", value=f"{len(mood_data)}件", inline=True
                )

                # 簡単なトレンド判定
                if len(mood_data) >= 3:
                    recent = mood_data[-3:]
                    trend_avg = sum(mood for _, mood in recent) / len(recent)
                    if trend_avg > avg_mood + 0.3:
                        trend = "📈 改善傾向"
                    elif trend_avg < avg_mood - 0.3:
                        trend = "📉 低下傾向"
                    else:
                        trend = "➡️ 安定"
                    embed.add_field(name="トレンド", value=trend, inline=True)

                await ctx.send(embed=embed)
            else:
                await ctx.send("📊 指定期間に気分データがありません")
        else:
            await ctx.send("❌ 対応していないメトリックです。使用可能: mood")

    async def _habit_status(self, ctx, args: str):
        """習慣の状態を表示"""
        if not args.strip():
            await ctx.send("❌ 習慣名を指定してください")
            return

        habit_name = args.strip()
        habit = await self.lifelog_manager.get_habit(habit_name)

        if not habit:
            await ctx.send(f"❌ 習慣 '{habit_name}' が見つかりません")
            return

        embed = discord.Embed(title=f"📊 習慣: {habit.name}", color=0x3498DB)
        embed.add_field(name="説明", value=habit.description, inline=False)
        embed.add_field(name="目標", value=habit.target_frequency, inline=True)
        embed.add_field(
            name="総完了回数", value=f"{habit.total_completions}回", inline=True
        )
        embed.add_field(name="連続記録", value=f"{habit.current_streak}日", inline=True)

        await ctx.send(embed=embed)

    async def _update_goal(self, ctx, args: str):
        """目標を更新"""
        parts = args.strip().split(None, 1)
        if len(parts) < 2:
            await ctx.send("❌ 使用法: !goal update <目標名> <進捗値>")
            return

        goal_name, progress_str = parts
        try:
            progress = float(progress_str)
        except ValueError:
            await ctx.send("❌ 進捗値は数値で入力してください")
            return

        success = await self.lifelog_manager.update_goal_progress(goal_name, progress)
        if success:
            await ctx.send(f"✅ 目標 '{goal_name}' の進捗を {progress} に更新しました")
        else:
            await ctx.send(f"❌ 目標 '{goal_name}' が見つかりません")

    async def _list_goals(self, ctx):
        """目標一覧を表示"""
        goals = await self.lifelog_manager.get_active_goals()

        if not goals:
            await ctx.send("🎯 現在アクティブな目標はありません")
            return

        embed = discord.Embed(title="🎯 アクティブな目標", color=0xE74C3C)

        for goal in goals[:10]:  # 最大 10 個
            progress_pct = (
                (goal.current_value / goal.target_value * 100)
                if goal.target_value > 0
                else 0
            )
            progress_bar = "█" * int(progress_pct // 10) + "░" * (
                10 - int(progress_pct // 10)
            )

            status = f"{progress_bar} {progress_pct:.1f}%\n"
            status += f"進捗: {goal.current_value}/{goal.target_value}"
            if goal.target_date:
                status += f"\n 期限: {goal.target_date.strftime('%Y-%m-%d')}"

            embed.add_field(name=goal.title, value=status, inline=False)

        await ctx.send(embed=embed)

    async def _goal_status(self, ctx, args: str):
        """目標の状態を表示"""
        if not args.strip():
            await ctx.send("❌ 目標名を指定してください")
            return

        goal_name = args.strip()
        goal = await self.lifelog_manager.get_goal(goal_name)

        if not goal:
            await ctx.send(f"❌ 目標 '{goal_name}' が見つかりません")
            return

        progress_pct = (
            (goal.current_value / goal.target_value * 100)
            if goal.target_value and goal.target_value > 0
            else 0
        )
        progress_bar = "█" * int(progress_pct // 10) + "░" * (
            10 - int(progress_pct // 10)
        )

        embed = discord.Embed(title=f"🎯 目標: {goal.title}", color=0xE74C3C)
        embed.add_field(name="説明", value=goal.description or "なし", inline=False)
        embed.add_field(
            name="進捗", value=f"{progress_bar} {progress_pct:.1f}%", inline=False
        )
        embed.add_field(name="現在値", value=str(goal.current_value), inline=True)
        embed.add_field(name="目標値", value=str(goal.target_value), inline=True)

        if goal.target_date:
            remaining_days = (goal.target_date - date.today()).days
            embed.add_field(
                name="期限",
                value=f"{goal.target_date.strftime('%Y-%m-%d')} (残り{remaining_days}日)",
                inline=True,
            )

        await ctx.send(embed=embed)

    async def _show_weekly_stats(self, ctx):
        """週次統計を表示"""
        today = date.today()
        start_date = today - timedelta(days=today.weekday())  # 今週の月曜日
        end_date = start_date + timedelta(days=6)  # 今週の日曜日

        summary = await self.lifelog_manager.get_weekly_summary(start_date, end_date)

        embed = discord.Embed(
            title=f"📅 週次統計 ({start_date.strftime('%m/%d')} - {end_date.strftime('%m/%d')})",
            color=0x9B59B6,
        )

        embed.add_field(name="記録数", value=f"{summary.total_entries}件", inline=True)
        embed.add_field(
            name="平均気分",
            value=f"{summary.avg_mood:.1f}" if summary.avg_mood else "なし",
            inline=True,
        )
        embed.add_field(
            name="習慣完了", value=f"{summary.habit_completions}回", inline=True
        )

        await ctx.send(embed=embed)

    async def _show_monthly_stats(self, ctx):
        """月次統計を表示"""
        today = date.today()
        start_date = today.replace(day=1)
        if today.month == 12:
            end_date = today.replace(year=today.year + 1, month=1, day=1) - timedelta(
                days=1
            )
        else:
            end_date = today.replace(month=today.month + 1, day=1) - timedelta(days=1)

        summary = await self.lifelog_manager.get_monthly_summary(start_date, end_date)

        embed = discord.Embed(
            title=f"📊 月次統計 ({start_date.strftime('%Y 年%m 月')})", color=0x34495E
        )

        embed.add_field(name="記録数", value=f"{summary.total_entries}件", inline=True)
        embed.add_field(
            name="平均気分",
            value=f"{summary.avg_mood:.1f}" if summary.avg_mood else "なし",
            inline=True,
        )
        embed.add_field(
            name="習慣完了", value=f"{summary.habit_completions}回", inline=True
        )

        await ctx.send(embed=embed)
