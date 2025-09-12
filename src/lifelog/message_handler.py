"""
ライフログ メッセージハンドラー

Discord メッセージからライフログエントリーを自動分析・生成
"""

import re
from typing import Any

import structlog

from ..ai.processor import AIProcessor
from .manager import LifelogManager
from .models import LifelogCategory, LifelogEntry, LifelogType, MoodLevel

logger = structlog.get_logger(__name__)


class LifelogMessageHandler:
    """Discord メッセージからライフログを自動生成"""

    def __init__(self, lifelog_manager: LifelogManager, ai_processor: AIProcessor):
        self.lifelog_manager = lifelog_manager
        self.ai_processor = ai_processor

        # ライフログ検出パターン
        self.lifelog_patterns = {
            # 健康・運動
            "health": [
                r"(?:走った|ジョギング|ランニング|筋トレ|運動|ヨガ|ストレッチ)",
                r"(?:\d+(?:km|キロ|歩)|歩数|体重|血圧)",
                r"(?:睡眠|寝た|起きた|疲れ|元気)",
            ],
            # 気分・感情
            "mood": [
                r"(?:気分|調子|疲れ|元気|嬉しい|悲しい|楽しい|つらい)",
                r"(?:ストレス|リラックス|集中|やる気|モチベーション)",
            ],
            # 学習・スキル
            "learning": [
                r"(?:勉強|学習|読書|本|資格|スキル|練習)",
                r"(?:理解|覚え|習得|マスター|完了)",
            ],
            # 仕事・プロジェクト
            "work": [
                r"(?:仕事|会議|プレゼン|資料|プロジェクト|タスク|完了)",
                r"(?:締切|納期|クライアント|チーム|上司)",
            ],
            # 人間関係・社交
            "relationship": [
                r"(?:友達|家族|恋人|同僚|会った|話した|連絡)",
                r"(?:飲み会|パーティー|デート|食事|コミュニケーション)",
            ],
            # 娯楽・趣味
            "entertainment": [
                r"(?:映画|音楽|ゲーム|漫画|アニメ|TV|YouTube)",
                r"(?:趣味|楽しい|面白い|つまらない|感動)",
            ],
            # 財務・支出
            "finance": [
                r"(?:\d+円|支払|購入|買った|お金|費用|予算)",
                r"(?:給料|収入|支出|節約|投資|貯金)",
            ],
        }

        # 数値抽出パターン
        self.numeric_patterns = {
            "distance": r"(\d+(?:\.\d+)?)\s*(?:km|キロ|m|メートル)",
            "time": r"(\d+(?:\.\d+)?)\s*(?:時間|分|秒|h|min)",
            "steps": r"(\d+)\s*(?:歩|steps)",
            "weight": r"(\d+(?:\.\d+)?)\s*(?:kg|キログラム)",
            "money": r"(\d+(?:,\d{3})*)\s*円",
            "count": r"(\d+)\s*(?:回|冊|個|件|人)",
        }

    async def analyze_message_for_lifelog(
        self, message_content: str, user_id: str | None = None
    ) -> LifelogEntry | None:
        """メッセージを分析してライフログエントリーを生成"""

        try:
            # まず基本的なパターンマッチングで判定
            category = self._detect_category(message_content)
            if not category:
                # AI 分析で詳細な判定を試行
                category = await self._ai_detect_category(message_content)
                if not category:
                    return None

            # エントリーの詳細情報を抽出
            entry_data = await self._extract_entry_details(message_content, category)

            # ライフログエントリーを作成
            entry = LifelogEntry(
                category=category,
                type=entry_data.get("type", LifelogType.EVENT),
                title=entry_data.get("title", "Discord メッセージから"),
                content=entry_data.get("content", message_content),
                tags=entry_data.get("tags", []),
                mood=entry_data.get("mood"),
                energy_level=entry_data.get("energy"),
                numeric_value=entry_data.get("numeric_value"),
                unit=entry_data.get("unit"),
                location=entry_data.get("location"),
                metadata={"original_message": message_content, "user_id": user_id},
                source="discord_auto",
            )

            logger.info(
                "ライフログエントリーを自動生成",
                category=category.value,
                title=entry.title,
            )

            return entry

        except Exception as e:
            logger.error("ライフログメッセージ分析でエラー", error=str(e))
            return None

    def _detect_category(self, content: str) -> LifelogCategory | None:
        """パターンマッチングでカテゴリを検出"""
        content_lower = content.lower()

        # カテゴリ別スコア計算
        category_scores = {}

        for category, patterns in self.lifelog_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, content_lower))
                score += matches

            if score > 0:
                category_scores[category] = score

        if not category_scores:
            return None

        # 最高スコアのカテゴリを返す
        best_category = max(category_scores.keys(), key=lambda k: category_scores[k])

        # カテゴリマッピング
        category_mapping = {
            "health": LifelogCategory.HEALTH,
            "mood": LifelogCategory.MOOD,
            "learning": LifelogCategory.LEARNING,
            "work": LifelogCategory.WORK,
            "relationship": LifelogCategory.RELATIONSHIP,
            "entertainment": LifelogCategory.ENTERTAINMENT,
            "finance": LifelogCategory.FINANCE,
        }

        return category_mapping.get(best_category)

    async def _ai_detect_category(self, content: str) -> LifelogCategory | None:
        """AI を使用してカテゴリを検出"""
        try:
            prompt = f"""
以下のメッセージがライフログとして記録すべき内容かどうか判定し、
該当する場合はカテゴリを返してください。

メッセージ: "{content}"

カテゴリ一覧:
- health: 健康、運動、睡眠、体調関連
- work: 仕事、プロジェクト、タスク、会議関連
- learning: 学習、読書、スキル習得関連
- finance: 支出、収入、金銭管理関連
- relationship: 人間関係、社交活動関連
- entertainment: 娯楽、趣味、エンターテイメント関連
- mood: 気分、感情、心理状態関連
- routine: 日常的な活動、ルーティン
- reflection: 振り返り、考察、気づき

回答は以下の形式で:
- 該当しない場合: "none"
- 該当する場合: カテゴリ名のみ (例: "health")
"""

            response = await self.ai_processor.process_text(prompt, 123456)

            if (
                response
                and response.summary
                and response.summary.summary.strip().lower() != "none"
            ):
                category_name = response.summary.summary.strip().lower()
                category_mapping = {
                    "health": LifelogCategory.HEALTH,
                    "work": LifelogCategory.WORK,
                    "learning": LifelogCategory.LEARNING,
                    "finance": LifelogCategory.FINANCE,
                    "relationship": LifelogCategory.RELATIONSHIP,
                    "entertainment": LifelogCategory.ENTERTAINMENT,
                    "mood": LifelogCategory.MOOD,
                    "routine": LifelogCategory.ROUTINE,
                    "reflection": LifelogCategory.REFLECTION,
                }

                return category_mapping.get(category_name)

        except Exception as e:
            logger.warning("AI カテゴリ検出でエラー", error=str(e))

        return None

    async def _extract_entry_details(
        self, content: str, category: LifelogCategory
    ) -> dict[str, Any]:
        """エントリーの詳細情報を抽出"""

        details: dict[str, Any] = {
            "content": content,
            "type": LifelogType.EVENT,
            "tags": [],
        }

        # 気分を抽出
        mood = self._extract_mood(content)
        if mood:
            details["mood"] = mood
            if category == LifelogCategory.MOOD:
                details["type"] = LifelogType.METRIC

        # エネルギーレベルを抽出
        energy = self._extract_energy(content)
        if energy:
            details["energy"] = energy

        # 数値データを抽出
        numeric_data = self._extract_numeric_data(content)
        if numeric_data:
            details.update(numeric_data)
            details["type"] = LifelogType.METRIC

        # タグを抽出
        tags = self._extract_tags(content)
        if tags:
            details["tags"] = tags

        # AI を使用してタイトルを生成
        title = await self._generate_title(content, category)
        if title:
            details["title"] = title

        # カテゴリ別の特別処理
        if category == LifelogCategory.HEALTH:
            details = await self._process_health_content(content, details)
        elif category == LifelogCategory.WORK:
            details = await self._process_work_content(content, details)
        elif category == LifelogCategory.FINANCE:
            details = await self._process_finance_content(content, details)

        return details

    def _extract_mood(self, content: str) -> MoodLevel | None:
        """気分を抽出"""
        # 数値での気分指定 (1-5)
        mood_pattern = r"(?:気分|mood):?\s*([1-5])"
        match = re.search(mood_pattern, content, re.IGNORECASE)
        if match:
            try:
                return MoodLevel(int(match.group(1)))
            except ValueError:
                pass

        # テキストからの気分推定
        mood_keywords = {
            5: ["最高", "素晴らしい", "完璧", "超嬉しい", "大満足"],
            4: ["良い", "嬉しい", "楽しい", "満足", "元気"],
            3: ["普通", "まあまあ", "そこそこ", "平均的"],
            2: ["微妙", "疲れた", "だるい", "イマイチ"],
            1: ["最悪", "辛い", "悲しい", "絶望", "ひどい"],
        }

        content_lower = content.lower()
        for level, keywords in mood_keywords.items():
            for keyword in keywords:
                if keyword in content_lower:
                    return MoodLevel(level)

        return None

    def _extract_energy(self, content: str) -> int | None:
        """エネルギーレベルを抽出"""
        energy_pattern = r"(?:エネルギー|energy|体力):?\s*([1-5])"
        match = re.search(energy_pattern, content, re.IGNORECASE)
        if match:
            try:
                energy = int(match.group(1))
                if 1 <= energy <= 5:
                    return energy
            except ValueError:
                pass

        return None

    def _extract_numeric_data(self, content: str) -> dict[str, Any]:
        """数値データを抽出"""
        result: dict[str, Any] = {}

        for data_type, pattern in self.numeric_patterns.items():
            match = re.search(pattern, content)
            if match:
                try:
                    value = float(match.group(1).replace(",", ""))

                    # 単位マッピング
                    unit_mapping = {
                        "distance": "km",
                        "time": "時間",
                        "steps": "歩",
                        "weight": "kg",
                        "money": "円",
                        "count": "回",
                    }

                    result["numeric_value"] = value
                    result["unit"] = unit_mapping.get(data_type, "")
                    break  # 最初にマッチしたものを使用

                except ValueError:
                    continue

        return result

    def _extract_tags(self, content: str) -> list[str]:
        """タグを抽出"""
        # #tag 形式（単語境界を考慮、助詞を除外）
        hashtag_pattern = r"#(\w+?)(?=で\s|で$|\s|$|[^\w])"
        raw_hashtags = re.findall(hashtag_pattern, content)
        # 助詞を除外
        hashtags = [
            tag
            for tag in raw_hashtags
            if not tag.endswith(("で", "に", "を", "が", "は", "と", "の"))
        ]

        # キーワードベースの自動タグ
        auto_tags = []
        content_lower = content.lower()

        tag_keywords = {
            "運動": ["走", "ジョギング", "筋トレ", "ヨガ", "運動"],
            "読書": ["本", "読書", "読んだ", "図書"],
            "会議": ["会議", "ミーティング", "打ち合わせ"],
            "完了": ["完了", "終了", "達成", "クリア"],
            "購入": ["買った", "購入", "買い物"],
        }

        for tag, keywords in tag_keywords.items():
            for keyword in keywords:
                if keyword in content_lower:
                    auto_tags.append(tag)
                    break

        return list(set(hashtags + auto_tags))

    async def _generate_title(
        self, content: str, category: LifelogCategory
    ) -> str | None:
        """AI を使用してタイトルを生成"""
        try:
            prompt = f"""
以下のメッセージから簡潔で分かりやすいタイトル（ 20 文字以内）を生成してください。
カテゴリ: {category.value}
メッセージ: "{content}"

タイトルのみ返してください。
"""

            title_result = await self.ai_processor.process_text(prompt, 123456)
            if title_result and title_result.summary:
                title = title_result.summary.summary.strip()
                if len(title) <= 30:
                    return title

        except Exception as e:
            logger.warning("AI タイトル生成でエラー", error=str(e))

        return None

    async def _process_health_content(
        self, content: str, details: dict[str, Any]
    ) -> dict[str, Any]:
        """健康関連コンテンツの特別処理"""
        # 活動の種類を判定
        activity_keywords = {
            "ランニング": ["走", "ジョギング", "ランニング"],
            "筋トレ": ["筋トレ", "トレーニング", "ジム"],
            "ヨガ": ["ヨガ", "ストレッチ"],
            "睡眠": ["寝た", "睡眠", "起きた"],
        }

        content_lower = content.lower()
        for activity, keywords in activity_keywords.items():
            for keyword in keywords:
                if keyword in content_lower:
                    if "tags" not in details:
                        details["tags"] = []
                    details["tags"].append(activity)
                    break

        return details

    async def _process_work_content(
        self, content: str, details: dict[str, Any]
    ) -> dict[str, Any]:
        """仕事関連コンテンツの特別処理"""
        # 作業の完了を検出
        completion_keywords = ["完了", "終了", "達成", "仕上げた", "finished"]
        content_lower = content.lower()

        for keyword in completion_keywords:
            if keyword in content_lower:
                details["type"] = LifelogType.EVENT
                if "tags" not in details:
                    details["tags"] = []
                details["tags"].append("完了")
                break

        return details

    async def _process_finance_content(
        self, content: str, details: dict[str, Any]
    ) -> dict[str, Any]:
        """財務関連コンテンツの特別処理"""
        # 支出か収入かを判定
        expense_keywords = ["買った", "購入", "支払", "使った", "出費"]
        income_keywords = ["もらった", "収入", "給料", "ボーナス"]

        content_lower = content.lower()

        for keyword in expense_keywords:
            if keyword in content_lower:
                if "tags" not in details:
                    details["tags"] = []
                details["tags"].append("支出")
                break

        for keyword in income_keywords:
            if keyword in content_lower:
                if "tags" not in details:
                    details["tags"] = []
                details["tags"].append("収入")
                break

        return details

    async def should_create_lifelog(self, message_content: str) -> bool:
        """メッセージがライフログ作成に適しているかを判定"""
        # 短すぎるメッセージは除外
        if len(message_content) < 10:
            return False

        # ボットコマンドは除外
        if message_content.startswith(("!", "/", "?", ".")):
            return False

        # 単純な返答は除外
        simple_responses = [
            "はい",
            "いいえ",
            "了解",
            "ありがとう",
            "おつかれ",
            "hello",
            "thanks",
        ]
        if message_content.lower().strip() in simple_responses:
            return False

        # パターンマッチングで判定
        if self._detect_category(message_content):
            return True

        # AI による詳細判定
        category = await self._ai_detect_category(message_content)
        return category is not None
