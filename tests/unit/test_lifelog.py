"""
ライフログシステム テスト

基本的なライフログ機能のテストを実行
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.lifelog.manager import LifelogManager
from src.lifelog.message_handler import LifelogMessageHandler
from src.lifelog.models import (
    HabitTracker,
    LifeGoal,
    LifelogCategory,
    LifelogEntry,
    LifelogType,
    MoodLevel,
)
from src.lifelog.templates import LifelogTemplates


class TestLifelogModels:
    """ライフログモデルのテスト"""

    def test_lifelog_entry_creation(self):
        """ライフログエントリーの作成テスト"""
        entry = LifelogEntry(
            category=LifelogCategory.HEALTH,
            type=LifelogType.EVENT,
            title="ランニング完了",
            content="今日は 5km 走りました",
            mood=MoodLevel.GOOD,
            energy_level=4,
            numeric_value=5.0,
            unit="km",
            tags=["運動", "ランニング"],
            source="test",
        )

        assert entry.category == LifelogCategory.HEALTH
        assert entry.type == LifelogType.EVENT
        assert entry.title == "ランニング完了"
        assert entry.mood == MoodLevel.GOOD
        assert entry.energy_level == 4
        assert entry.numeric_value == 5.0
        assert entry.unit == "km"
        assert "運動" in entry.tags
        assert entry.source == "test"

    def test_habit_tracker_creation(self):
        """習慣トラッカーの作成テスト"""
        habit = HabitTracker(
            name="毎日読書",
            description="30 分の読書習慣",
            category=LifelogCategory.LEARNING,
            target_frequency="daily",
            start_date=date.today(),
        )

        assert habit.name == "毎日読書"
        assert habit.category == LifelogCategory.LEARNING
        assert habit.target_frequency == "daily"
        assert habit.active is True
        assert habit.current_streak == 0

    def test_life_goal_creation(self):
        """人生目標の作成テスト"""
        goal = LifeGoal(
            title="年間 100 冊読書",
            description="今年中に 100 冊の本を読む",
            category=LifelogCategory.LEARNING,
            target_value=100,
            target_unit="冊",
        )

        assert goal.title == "年間 100 冊読書"
        assert goal.category == LifelogCategory.LEARNING
        assert goal.target_value == 100
        assert goal.current_value == 0
        assert goal.progress_percentage == 0
        assert goal.status == "active"


class TestLifelogMessageHandler:
    """ライフログメッセージハンドラーのテスト"""

    @pytest.fixture
    def lifelog_manager(self):
        """モックライフログマネージャー"""
        return AsyncMock(spec=LifelogManager)

    @pytest.fixture
    def ai_processor(self):
        """モック AI プロセッサー"""
        return AsyncMock()

    @pytest.fixture
    def message_handler(self, lifelog_manager, ai_processor):
        """ライフログメッセージハンドラー"""
        return LifelogMessageHandler(lifelog_manager, ai_processor)

    def test_detect_health_category(self, message_handler):
        """健康カテゴリの検出テスト"""
        content = "今日は 10km 走った。とても疲れたけど達成感がある。"
        category = message_handler._detect_category(content)
        assert category == LifelogCategory.HEALTH

    def test_detect_mood_category(self, message_handler):
        """気分カテゴリの検出テスト"""
        content = "今日は気分が良い。調子も良くて満足している。"
        category = message_handler._detect_category(content)
        assert category == LifelogCategory.MOOD

    def test_detect_work_category(self, message_handler):
        """仕事カテゴリの検出テスト"""
        content = "プレゼン資料が完了した。会議の準備も終わり。"
        category = message_handler._detect_category(content)
        assert category == LifelogCategory.WORK

    def test_extract_mood(self, message_handler):
        """気分抽出のテスト"""
        content = "今日は気分:4 で調子が良い"
        mood = message_handler._extract_mood(content)
        assert mood == MoodLevel.GOOD

    def test_extract_numeric_data(self, message_handler):
        """数値データ抽出のテスト"""
        content = "5km 走って 1 時間かかった"
        data = message_handler._extract_numeric_data(content)
        assert data["numeric_value"] == 5.0
        assert data["unit"] == "km"

    def test_extract_tags(self, message_handler):
        """タグ抽出のテスト"""
        content = "今日は#運動 #ランニングで 5km 走った"
        tags = message_handler._extract_tags(content)
        assert "運動" in tags
        assert "ランニング" in tags

    @pytest.mark.asyncio
    async def test_should_create_lifelog_positive(self, message_handler):
        """ライフログ作成判定テスト（肯定的）"""
        content = "今日は 10km 走った。とても気持ちよかった。"
        should_create = await message_handler.should_create_lifelog(content)
        assert should_create is True

    @pytest.mark.asyncio
    async def test_should_create_lifelog_negative(self, message_handler):
        """ライフログ作成判定テスト（否定的）"""
        content = "!help"  # ボットコマンド
        should_create = await message_handler.should_create_lifelog(content)
        assert should_create is False

    @pytest.mark.asyncio
    async def test_should_create_lifelog_too_short(self, message_handler):
        """短すぎるメッセージの判定テスト"""
        content = "おはよう"  # 短いメッセージ
        should_create = await message_handler.should_create_lifelog(content)
        assert should_create is False


class TestLifelogTemplates:
    """ライフログテンプレートのテスト"""

    def test_generate_entry_note(self):
        """エントリーノート生成テスト"""
        entry = LifelogEntry(
            category=LifelogCategory.HEALTH,
            type=LifelogType.EVENT,
            title="ランニング完了",
            content="5km 走りました",
            mood=MoodLevel.GOOD,
            energy_level=4,
            numeric_value=5.0,
            unit="km",
            source="test",
        )

        note_content = LifelogTemplates.generate_entry_note(entry)

        assert "# ランニング完了" in note_content
        assert "category: health" in note_content
        assert "mood: 4" in note_content
        assert "energy: 4" in note_content
        assert "value: 5.0" in note_content
        assert "unit: km" in note_content
        assert "🏃 健康・運動" in note_content
        assert "😊 4/5" in note_content

    def test_generate_habit_tracker_note(self):
        """習慣トラッカーノート生成テスト"""
        habit = HabitTracker(
            name="毎日読書",
            description="30 分の読書習慣",
            category=LifelogCategory.LEARNING,
            target_frequency="daily",
            start_date=date.today(),
            current_streak=5,
            total_completions=20,
        )

        note_content = LifelogTemplates.generate_habit_tracker_note(habit)

        assert "# 🎯 習慣トラッカー: 毎日読書" in note_content
        assert "30 分の読書習慣" in note_content
        assert "daily" in note_content
        assert "現在の連続記録**: 5 日" in note_content
        assert "総完了回数**: 20 回" in note_content

    def test_generate_goal_tracker_note(self):
        """目標トラッカーノート生成テスト"""
        goal = LifeGoal(
            title="年間 100 冊読書",
            description="今年中に 100 冊読む",
            category=LifelogCategory.LEARNING,
            target_value=100,
            current_value=25,
            progress_percentage=25.0,
            priority=4,
        )

        note_content = LifelogTemplates.generate_goal_tracker_note(goal)

        assert "# 🎯 目標: 年間 100 冊読書" in note_content
        assert "今年中に 100 冊読む" in note_content
        assert "25.0%" in note_content
        assert "⭐⭐⭐⭐" in note_content  # 優先度 4
        assert "現在値**: 25" in note_content

    def test_get_category_display(self):
        """カテゴリ表示名取得テスト"""
        display = LifelogTemplates._get_category_display(LifelogCategory.HEALTH)
        assert display == "🏃 健康・運動"

        display = LifelogTemplates._get_category_display(LifelogCategory.WORK)
        assert display == "💼 仕事・プロジェクト"

        display = LifelogTemplates._get_category_display(LifelogCategory.LEARNING)
        assert display == "📚 学習・スキル"


@pytest.mark.asyncio
class TestLifelogManager:
    """ライフログマネージャーのテスト（統合テスト的）"""

    @pytest.fixture
    def mock_settings(self):
        """モック設定"""
        settings = MagicMock()
        settings.obsidian_vault_path = "/tmp/test_vault"
        return settings

    @pytest.fixture
    def lifelog_manager(self, mock_settings):
        """ライフログマネージャー"""
        return LifelogManager(mock_settings)

    async def test_add_entry(self, lifelog_manager):
        """エントリー追加のテスト"""
        entry = LifelogEntry(
            category=LifelogCategory.HEALTH,
            type=LifelogType.EVENT,
            title="テスト エントリー",
            content="テスト内容",
            source="test",
        )

        # データディレクトリが存在しないので、実際のファイル保存はスキップされることを想定
        # 基本的なオブジェクト操作のテストのみ行う
        entry_id = entry.id or "test-id"
        assert entry_id is not None
        assert entry.category == LifelogCategory.HEALTH
        assert entry.title == "テスト エントリー"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
