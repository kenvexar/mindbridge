"""
ライフログ マネージャー

ライフログエントリーの作成、管理、分析を統括するメインマネージャー
"""

import json
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

import structlog

from ..config.settings import Settings
from .integrations.bridge import create_default_bridge
from .integrations.models import IntegrationData
from .models import (
    DailyLifeSummary,
    HabitTracker,
    LifeGoal,
    LifelogCategory,
    LifelogEntry,
    LifelogType,
)

logger = structlog.get_logger(__name__)


class LifelogManager:
    """ライフログ統合管理システム"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.data_dir = Path(settings.obsidian_vault_path) / "90_Meta" / "lifelog_data"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # データファイルパス
        self.entries_file = self.data_dir / "entries.json"
        self.habits_file = self.data_dir / "habits.json"
        self.goals_file = self.data_dir / "goals.json"

        # インメモリキャッシュ
        self._entries: dict[str, LifelogEntry] = {}
        self._habits: dict[str, HabitTracker] = {}
        self._goals: dict[str, LifeGoal] = {}

        self._initialized = False
        self.integration_bridge = create_default_bridge()

    async def initialize(self):
        """データの初期読み込み"""
        if self._initialized:
            return

        try:
            await self._load_data()
            self._initialized = True
            logger.info("ライフログマネージャーを初期化しました")
        except Exception as e:
            logger.error("ライフログマネージャーの初期化に失敗", error=str(e))
            raise

    async def _load_data(self):
        """データファイルから読み込み"""
        # エントリー読み込み
        if self.entries_file.exists():
            with open(self.entries_file, encoding="utf-8") as f:
                entries_data = json.load(f)
                for entry_id, entry_dict in entries_data.items():
                    # datetime 文字列を datetime オブジェクトに変換
                    if "timestamp" in entry_dict:
                        entry_dict["timestamp"] = datetime.fromisoformat(
                            entry_dict["timestamp"]
                        )
                    if "created_at" in entry_dict:
                        entry_dict["created_at"] = datetime.fromisoformat(
                            entry_dict["created_at"]
                        )
                    if "updated_at" in entry_dict:
                        entry_dict["updated_at"] = datetime.fromisoformat(
                            entry_dict["updated_at"]
                        )

                    self._entries[entry_id] = LifelogEntry(**entry_dict)

        # 習慣読み込み
        if self.habits_file.exists():
            with open(self.habits_file, encoding="utf-8") as f:
                habits_data = json.load(f)
                for habit_id, habit_dict in habits_data.items():
                    # date 文字列を date オブジェクトに変換
                    if "start_date" in habit_dict:
                        habit_dict["start_date"] = date.fromisoformat(
                            habit_dict["start_date"]
                        )
                    if "end_date" in habit_dict and habit_dict["end_date"]:
                        habit_dict["end_date"] = date.fromisoformat(
                            habit_dict["end_date"]
                        )
                    if "created_at" in habit_dict:
                        habit_dict["created_at"] = datetime.fromisoformat(
                            habit_dict["created_at"]
                        )
                    if "updated_at" in habit_dict:
                        habit_dict["updated_at"] = datetime.fromisoformat(
                            habit_dict["updated_at"]
                        )

                    self._habits[habit_id] = HabitTracker(**habit_dict)

        # 目標読み込み
        if self.goals_file.exists():
            with open(self.goals_file, encoding="utf-8") as f:
                goals_data = json.load(f)
                for goal_id, goal_dict in goals_data.items():
                    # date 文字列を date オブジェクトに変換
                    if "target_date" in goal_dict and goal_dict["target_date"]:
                        goal_dict["target_date"] = date.fromisoformat(
                            goal_dict["target_date"]
                        )
                    if "created_at" in goal_dict:
                        goal_dict["created_at"] = datetime.fromisoformat(
                            goal_dict["created_at"]
                        )
                    if "updated_at" in goal_dict:
                        goal_dict["updated_at"] = datetime.fromisoformat(
                            goal_dict["updated_at"]
                        )

                    self._goals[goal_id] = LifeGoal(**goal_dict)

    async def _save_data(self):
        """データファイルに保存"""
        # エントリー保存
        entries_dict = {}
        for entry_id, entry in self._entries.items():
            entry_dict = entry.model_dump()
            # datetime オブジェクトを文字列に変換
            if "timestamp" in entry_dict:
                entry_dict["timestamp"] = entry_dict["timestamp"].isoformat()
            if "created_at" in entry_dict:
                entry_dict["created_at"] = entry_dict["created_at"].isoformat()
            if "updated_at" in entry_dict:
                entry_dict["updated_at"] = entry_dict["updated_at"].isoformat()
            entries_dict[entry_id] = entry_dict

        with open(self.entries_file, "w", encoding="utf-8") as f:
            json.dump(entries_dict, f, ensure_ascii=False, indent=2)

        # 習慣保存
        habits_dict = {}
        for habit_id, habit in self._habits.items():
            habit_dict = habit.model_dump()
            # date オブジェクトを文字列に変換
            if "start_date" in habit_dict:
                habit_dict["start_date"] = habit_dict["start_date"].isoformat()
            if "end_date" in habit_dict and habit_dict["end_date"]:
                habit_dict["end_date"] = habit_dict["end_date"].isoformat()
            if "created_at" in habit_dict:
                habit_dict["created_at"] = habit_dict["created_at"].isoformat()
            if "updated_at" in habit_dict:
                habit_dict["updated_at"] = habit_dict["updated_at"].isoformat()
            habits_dict[habit_id] = habit_dict

        with open(self.habits_file, "w", encoding="utf-8") as f:
            json.dump(habits_dict, f, ensure_ascii=False, indent=2)

        # 目標保存
        goals_dict = {}
        for goal_id, goal in self._goals.items():
            goal_dict = goal.model_dump()
            # date オブジェクトを文字列に変換
            if "target_date" in goal_dict and goal_dict["target_date"]:
                goal_dict["target_date"] = goal_dict["target_date"].isoformat()
            if "created_at" in goal_dict:
                goal_dict["created_at"] = goal_dict["created_at"].isoformat()
            if "updated_at" in goal_dict:
                goal_dict["updated_at"] = goal_dict["updated_at"].isoformat()
            goals_dict[goal_id] = goal_dict

        with open(self.goals_file, "w", encoding="utf-8") as f:
            json.dump(goals_dict, f, ensure_ascii=False, indent=2)

    # === エントリー管理 ===

    async def add_entry(self, entry: LifelogEntry) -> str:
        """ライフログエントリーを追加"""
        if not entry.id:
            entry.id = str(uuid.uuid4())

        entry.created_at = datetime.now()
        entry.updated_at = datetime.now()

        self._entries[entry.id] = entry
        await self._save_data()

        logger.info(
            "ライフログエントリーを追加",
            entry_id=entry.id,
            category=entry.category,
            type=entry.type,
        )

        return entry.id

    async def update_entry(self, entry_id: str, updates: dict[str, Any]) -> bool:
        """エントリーを更新"""
        if entry_id not in self._entries:
            logger.warning("存在しないエントリーの更新を試行", entry_id=entry_id)
            return False

        entry = self._entries[entry_id]
        for key, value in updates.items():
            if hasattr(entry, key):
                setattr(entry, key, value)

        entry.updated_at = datetime.now()
        await self._save_data()

        logger.info("ライフログエントリーを更新", entry_id=entry_id)
        return True

    async def get_entry(self, entry_id: str) -> LifelogEntry | None:
        """エントリーを取得"""
        return self._entries.get(entry_id)

    async def get_entries_by_date_range(
        self, start_date: date, end_date: date, category: LifelogCategory | None = None
    ) -> list[LifelogEntry]:
        """日付範囲でエントリーを取得"""
        entries = []
        for entry in self._entries.values():
            entry_date = entry.timestamp.date()
            if start_date <= entry_date <= end_date:
                if category is None or entry.category == category:
                    entries.append(entry)

        return sorted(entries, key=lambda x: x.timestamp, reverse=True)

    async def get_entries_by_category(
        self, category: LifelogCategory
    ) -> list[LifelogEntry]:
        """カテゴリでエントリーを取得"""
        return [entry for entry in self._entries.values() if entry.category == category]

    async def delete_entry(self, entry_id: str) -> bool:
        """エントリーを削除"""
        if entry_id in self._entries:
            del self._entries[entry_id]
            await self._save_data()
            logger.info("ライフログエントリーを削除", entry_id=entry_id)
            return True
        return False

    # === 習慣管理 ===

    async def create_habit(self, habit: HabitTracker) -> str:
        """習慣を作成"""
        if not habit.id:
            habit.id = str(uuid.uuid4())

        habit.created_at = datetime.now()
        habit.updated_at = datetime.now()

        self._habits[habit.id] = habit
        await self._save_data()

        logger.info("習慣を作成", habit_id=habit.id, name=habit.name)
        return habit.id

    async def log_habit_completion(
        self, habit_id: str, completed: bool, value: float | None = None
    ) -> bool:
        """習慣の完了を記録"""
        if habit_id not in self._habits:
            return False

        habit = self._habits[habit_id]
        today = date.today()

        if completed:
            # 完了記録を作成
            entry = LifelogEntry(
                category=habit.category,
                type=LifelogType.HABIT,
                title=f"{habit.name}を完了",
                content=f"習慣「{habit.name}」を実行しました",
                numeric_value=value,
                unit=habit.target_unit,
                related_habit_id=habit_id,
                source="habit_tracker",
            )
            await self.add_entry(entry)

            # 習慣統計を更新
            habit.total_completions += 1

            # ストリーク計算ロジック
            await self._update_habit_streak(habit, today, completed=True)

        else:
            # 未完了の場合もストリークをリセット
            await self._update_habit_streak(habit, today, completed=False)

        habit.updated_at = datetime.now()
        await self._save_data()

        return True

    async def _update_habit_streak(
        self, habit: HabitTracker, target_date: date, completed: bool
    ) -> None:
        """習慣のストリーク情報を更新"""
        from datetime import timedelta

        if not habit.id:
            return

        if completed:
            # 前日までの連続記録をチェック
            yesterday = target_date - timedelta(days=1)
            was_previous_day_completed = await self._was_habit_completed_on_date(
                habit.id, yesterday
            )

            if was_previous_day_completed or habit.current_streak == 0:
                # 連続記録を延長 or 新規開始
                habit.current_streak += 1
            else:
                # 前日が未完了だった場合は新規開始
                habit.current_streak = 1

            # ベストストリークを更新
            if habit.current_streak > habit.best_streak:
                habit.best_streak = habit.current_streak

        else:
            # 未完了の場合はストリークをリセット
            habit.current_streak = 0

    async def _was_habit_completed_on_date(
        self, habit_id: str, target_date: date
    ) -> bool:
        """指定日に習慣が完了していたかチェック"""
        entries = await self.get_entries_by_date_range(target_date, target_date)

        for entry in entries:
            if entry.type == LifelogType.HABIT and entry.related_habit_id == habit_id:
                return True

        return False

    async def get_habit(self, habit_id: str) -> HabitTracker | None:
        """習慣を取得"""
        return self._habits.get(habit_id)

    async def get_active_habits(self) -> list[HabitTracker]:
        """アクティブな習慣を取得"""
        return [habit for habit in self._habits.values() if habit.active]

    # === 目標管理 ===

    async def create_goal(self, goal: LifeGoal) -> str:
        """目標を作成"""
        if not goal.id:
            goal.id = str(uuid.uuid4())

        goal.created_at = datetime.now()
        goal.updated_at = datetime.now()

        self._goals[goal.id] = goal
        await self._save_data()

        logger.info("目標を作成", goal_id=goal.id, title=goal.title)
        return goal.id

    async def update_goal_progress(self, goal_id: str, current_value: float) -> bool:
        """目標進捗を更新"""
        if goal_id not in self._goals:
            return False

        goal = self._goals[goal_id]
        goal.current_value = current_value

        # 進捗率を計算
        if goal.target_value and goal.target_value > 0:
            goal.progress_percentage = min(
                (current_value / goal.target_value) * 100, 100
            )

            # 完了チェック
            if goal.progress_percentage >= 100 and goal.status == "active":
                goal.status = "completed"

                # 完了記録を作成
                entry = LifelogEntry(
                    category=goal.category,
                    type=LifelogType.GOAL_PROGRESS,
                    title=f"目標達成: {goal.title}",
                    content=f"目標「{goal.title}」を達成しました！",
                    related_goal_id=goal_id,
                    source="goal_tracker",
                )
                await self.add_entry(entry)

        goal.updated_at = datetime.now()
        await self._save_data()

        return True

    async def get_goal(self, goal_id: str) -> LifeGoal | None:
        """目標を取得"""
        return self._goals.get(goal_id)

    async def get_active_goals(self) -> list[LifeGoal]:
        """アクティブな目標を取得"""
        return [goal for goal in self._goals.values() if goal.status == "active"]

    # === 分析・レポート ===

    async def get_daily_summary(self, target_date: date) -> DailyLifeSummary:
        """日次サマリーを生成"""
        # 当日のエントリーを取得
        entries = await self.get_entries_by_date_range(target_date, target_date)

        # 基本統計
        total_entries = len(entries)
        categories_active = list(set(entry.category for entry in entries))

        # 気分・エネルギー平均
        mood_values = [entry.mood.value for entry in entries if entry.mood]
        energy_values = [entry.energy_level for entry in entries if entry.energy_level]

        mood_average = sum(mood_values) / len(mood_values) if mood_values else None
        energy_average = (
            sum(energy_values) / len(energy_values) if energy_values else None
        )

        # 習慣完了チェック
        habit_entries = [e for e in entries if e.type == LifelogType.HABIT]
        habits_completed = [
            e.related_habit_id for e in habit_entries if e.related_habit_id
        ]

        # 主要イベント抽出 (簡単な例)
        key_events = [
            entry.title for entry in entries if entry.type == LifelogType.EVENT
        ]

        summary = DailyLifeSummary(
            date=target_date,
            total_entries=total_entries,
            categories_active=categories_active,
            mood_average=mood_average,
            energy_average=energy_average,
            habits_completed=habits_completed,
            key_events=key_events[:5],  # 最大 5 つ
            completion_rate=len(habits_completed) / max(len(self._habits), 1) * 100,
        )

        return summary

    async def get_category_statistics(
        self, start_date: date, end_date: date
    ) -> dict[LifelogCategory, int]:
        """カテゴリ別統計を取得"""
        entries = await self.get_entries_by_date_range(start_date, end_date)
        category_counts: dict[LifelogCategory, int] = {}

        for entry in entries:
            category = entry.category
            category_counts[category] = category_counts.get(category, 0) + 1

        return category_counts

    # === 外部システム連携 ===

    async def import_from_tasks(self, tasks):
        """タスクシステムからデータをインポート"""
        for task in tasks:
            if hasattr(task, "status") and getattr(task, "status", None) == "completed":
                entry = LifelogEntry(
                    category=LifelogCategory.WORK,
                    type=LifelogType.EVENT,
                    title=f"タスク完了: {task.title}",
                    content=task.description or "",
                    related_task_id=str(task.id) if task.id else None,
                    source="tasks_system",
                )
                await self.add_entry(entry)

    async def import_from_expenses(self, expenses):
        """財務システムからデータをインポート"""
        for expense in expenses:
            entry = LifelogEntry(
                category=LifelogCategory.FINANCE,
                type=LifelogType.EVENT,
                title=f"支出: {expense.description}",
                content=f"{expense.amount}円 - {expense.category}",
                numeric_value=expense.amount,
                unit="円",
                source="finance_system",
            )
            await self.add_entry(entry)

    async def import_from_health(self, health_insights):
        """健康分析システムからデータをインポート"""
        for insight in health_insights:
            entry = LifelogEntry(
                category=LifelogCategory.HEALTH,
                type=LifelogType.METRIC,
                title=f"健康インサイト: {insight.insight_type}",
                content=insight.description,
                source="health_system",
            )
            await self.add_entry(entry)

    # === 外部連携統合 ===

    async def integrate_external_data(
        self, integration_data: list["IntegrationData"]
    ) -> int:
        """外部連携データをライフログエントリーに統合"""
        if not integration_data:
            return 0

        integrated_count = 0

        try:
            for data in integration_data:
                # 重複チェック（ external_id + integration_name でユニーク性を保証）
                duplicate_entry = await self._find_duplicate_entry(
                    data.source_id, data.integration_type
                )

                if duplicate_entry:
                    logger.debug(
                        "重複データをスキップ",
                        external_id=data.source_id,
                        integration_name=data.integration_type,
                    )
                    continue

                # IntegrationData から LifelogEntry に変換
                lifelog_entry = await self._convert_integration_data_to_entry(data)

                if lifelog_entry:
                    await self.add_entry(lifelog_entry)
                    integrated_count += 1

                    logger.debug(
                        "外部連携データを統合",
                        external_id=data.source_id,
                        integration_name=data.integration_type,
                        category=lifelog_entry.category.value,
                        title=lifelog_entry.title,
                    )
                else:
                    logger.warning(
                        "外部連携データの変換に失敗",
                        external_id=data.source_id,
                        integration_name=data.integration_type,
                        data_type=data.metadata.get("data_type", "unknown"),
                    )

            if integrated_count > 0:
                logger.info(
                    "外部連携データの統合完了",
                    total_processed=len(integration_data),
                    integrated_count=integrated_count,
                    skipped_count=len(integration_data) - integrated_count,
                )

            return integrated_count

        except Exception as e:
            logger.error("外部連携データ統合でエラー", error=str(e))
            return integrated_count

    async def _find_duplicate_entry(
        self, external_id: str, integration_name: str
    ) -> Optional["LifelogEntry"]:
        """重複エントリーを検索"""
        for entry in self._entries.values():
            if (
                entry.metadata
                and entry.metadata.get("external_id") == external_id
                and entry.metadata.get("integration_name") == integration_name
            ):
                return entry
        return None

    async def _convert_integration_data_to_entry(
        self, data: "IntegrationData"
    ) -> Optional["LifelogEntry"]:
        """IntegrationData を LifelogEntry に変換"""
        try:
            return await self.integration_bridge.convert(data)

        except Exception as e:
            logger.error(
                "統合データ変換でエラー",
                integration_name=data.integration_type,
                data_type=data.metadata.get("data_type", "unknown"),
                error=str(e),
            )
            return None

    async def get_integration_statistics(self, days: int = 30) -> dict[str, Any]:
        """外部連携データの統計情報を取得"""
        from datetime import date, timedelta

        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        entries = await self.get_entries_by_date_range(start_date, end_date)

        # 外部連携から作成されたエントリーを抽出
        integration_entries = [
            entry
            for entry in entries
            if entry.metadata and entry.metadata.get("integration_name")
        ]

        if not integration_entries:
            return {
                "total_integration_entries": 0,
                "integration_breakdown": {},
                "category_distribution": {},
                "recent_entries": [],
            }

        # 統合別の統計
        integration_breakdown: dict[str, dict[str, Any]] = {}
        for entry in integration_entries:
            integration_name = entry.metadata.get("integration_name", "unknown")
            if integration_name not in integration_breakdown:
                integration_breakdown[integration_name] = {
                    "count": 1,
                    "latest_entry": entry.timestamp,
                }
            else:
                integration_breakdown[integration_name]["count"] += 1
                if (
                    integration_breakdown[integration_name]["latest_entry"] is None
                    or entry.timestamp
                    > integration_breakdown[integration_name]["latest_entry"]
                ):
                    integration_breakdown[integration_name]["latest_entry"] = (
                        entry.timestamp
                    )

        # カテゴリ分布
        category_distribution: dict[str, int] = {}
        for entry in integration_entries:
            category = entry.category.value
            category_distribution[category] = category_distribution.get(category, 0) + 1

        # 最新のエントリー（最大 10 件）
        recent_entries = sorted(
            integration_entries, key=lambda x: x.timestamp, reverse=True
        )[:10]

        recent_entries_info = [
            {
                "title": entry.title,
                "integration": entry.metadata.get("integration_name"),
                "category": entry.category.value,
                "timestamp": entry.timestamp.isoformat(),
                "source": entry.source,
            }
            for entry in recent_entries
        ]

        return {
            "total_integration_entries": len(integration_entries),
            "integration_breakdown": {
                name: {
                    "count": stats["count"],
                    "latest_entry": stats["latest_entry"].isoformat()
                    if stats["latest_entry"]
                    else None,
                }
                for name, stats in integration_breakdown.items()
            },
            "category_distribution": category_distribution,
            "recent_entries": recent_entries_info,
            "analysis_period_days": days,
        }
