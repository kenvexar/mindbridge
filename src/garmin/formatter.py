"""
Garmin health data formatting utilities
"""

from src.garmin.models import (
    ActivityData,
    DataError,
    HealthData,
    HeartRateData,
    SleepData,
    StepsData,
)


def format_health_data_for_markdown(health_data: HealthData) -> str:
    """
    健康データをMarkdown形式にフォーマット

    Args:
        health_data: 健康データオブジェクト

    Returns:
        Markdown形式の文字列
    """
    if not health_data.has_any_data:
        return _format_no_data_section(health_data)

    sections = []

    # ヘッダー
    sections.append("## 🏃 Health Data\n")

    # データ品質の表示
    if health_data.data_quality != "good":
        quality_icon = _get_quality_icon(health_data.data_quality)
        sections.append(
            f"**データ品質**: {quality_icon} {_get_quality_description(health_data.data_quality)}\n"
        )

    # 睡眠データ
    if health_data.sleep and health_data.sleep.is_valid:
        sections.append(_format_sleep_data(health_data.sleep))

    # 歩数・活動データ
    if health_data.steps and health_data.steps.is_valid:
        sections.append(_format_steps_data(health_data.steps))

    # 心拍数データ
    if health_data.heart_rate and health_data.heart_rate.is_valid:
        sections.append(_format_heart_rate_data(health_data.heart_rate))

    # アクティビティデータ
    if health_data.activities:
        sections.append(_format_activities_data(health_data.activities))

    # エラー情報（デバッグ用、エラーがある場合のみ）
    if health_data.detailed_errors:
        sections.append(_format_errors_section(health_data.detailed_errors))

    # フッター（キャッシュ情報含む）
    footer_info = (
        f"*取得日時: {health_data.retrieved_at.strftime('%Y-%m-%d %H:%M:%S')}*"
    )
    if health_data.is_cached_data and health_data.cache_age_hours:
        if health_data.cache_age_hours < 1:
            cache_age_str = f"{int(health_data.cache_age_hours * 60)}分前"
        else:
            cache_age_str = f"{health_data.cache_age_hours:.1f}時間前"
        footer_info += f" (キャッシュデータ: {cache_age_str})"
    sections.append(f"\n{footer_info}\n")

    return "\n".join(sections)


def _format_sleep_data(sleep_data: SleepData) -> str:
    """睡眠データをフォーマット"""
    lines = ["### 😴 睡眠"]

    if sleep_data.total_sleep_hours:
        hours = int(sleep_data.total_sleep_hours)
        minutes = int((sleep_data.total_sleep_hours - hours) * 60)
        lines.append(f"- **総睡眠時間**: {hours}時間{minutes:02d}分")

        # 睡眠の内訳
        breakdown_parts = []
        if sleep_data.deep_sleep_hours:
            deep_hours = int(sleep_data.deep_sleep_hours)
            deep_minutes = int((sleep_data.deep_sleep_hours - deep_hours) * 60)
            breakdown_parts.append(f"深い睡眠: {deep_hours}時間{deep_minutes:02d}分")

        if sleep_data.light_sleep_hours:
            light_hours = int(sleep_data.light_sleep_hours)
            light_minutes = int((sleep_data.light_sleep_hours - light_hours) * 60)
            breakdown_parts.append(f"浅い睡眠: {light_hours}時間{light_minutes:02d}分")

        if sleep_data.rem_sleep_hours:
            rem_hours = int(sleep_data.rem_sleep_hours)
            rem_minutes = int((sleep_data.rem_sleep_hours - rem_hours) * 60)
            breakdown_parts.append(f"REM睡眠: {rem_hours}時間{rem_minutes:02d}分")

        if breakdown_parts:
            lines.append(f"  - {' / '.join(breakdown_parts)}")

    if sleep_data.sleep_score:
        score_icon = _get_sleep_score_icon(sleep_data.sleep_score)
        lines.append(f"- **睡眠スコア**: {score_icon} {sleep_data.sleep_score}/100")

    if sleep_data.bedtime and sleep_data.wake_time:
        bedtime_str = sleep_data.bedtime.strftime("%H:%M")
        waketime_str = sleep_data.wake_time.strftime("%H:%M")
        lines.append(f"- **就寝時刻**: {bedtime_str} → **起床時刻**: {waketime_str}")

    return "\n".join(lines) + "\n"


def _format_steps_data(steps_data: StepsData) -> str:
    """歩数データをフォーマット"""
    lines = ["### 🚶 歩数・活動"]

    if steps_data.total_steps:
        lines.append(f"- **歩数**: {steps_data.total_steps:,}歩")

        # 歩数に応じたアイコン
        step_icon = _get_step_count_icon(steps_data.total_steps)
        lines[-1] = lines[-1].replace("**歩数**", f"**歩数** {step_icon}")

    if steps_data.distance_km:
        lines.append(f"- **移動距離**: {steps_data.distance_km:.2f} km")

    if steps_data.calories_burned:
        lines.append(f"- **消費カロリー**: {steps_data.calories_burned} kcal")

    if steps_data.floors_climbed:
        lines.append(f"- **上った階数**: {steps_data.floors_climbed}階")

    if steps_data.active_minutes:
        lines.append(f"- **アクティブ時間**: {steps_data.active_minutes}分")

    return "\n".join(lines) + "\n"


def _format_heart_rate_data(heart_rate_data: HeartRateData) -> str:
    """心拍数データをフォーマット"""
    lines = ["### ❤️ 心拍数"]

    if heart_rate_data.resting_heart_rate:
        hr_icon = _get_heart_rate_icon(heart_rate_data.resting_heart_rate)
        lines.append(
            f"- **安静時心拍数**: {hr_icon} {heart_rate_data.resting_heart_rate} bpm"
        )

    if heart_rate_data.average_heart_rate:
        lines.append(f"- **平均心拍数**: {heart_rate_data.average_heart_rate} bpm")

    if heart_rate_data.max_heart_rate:
        lines.append(f"- **最大心拍数**: {heart_rate_data.max_heart_rate} bpm")

    if heart_rate_data.heart_rate_zones:
        lines.append("- **心拍数ゾーン**:")
        for zone, minutes in heart_rate_data.heart_rate_zones.items():
            if minutes > 0:
                lines.append(f"  - {zone}: {minutes}分")

    return "\n".join(lines) + "\n"


def _format_activities_data(activities: list[ActivityData]) -> str:
    """アクティビティデータをフォーマット"""
    if not activities:
        return ""

    lines = ["### 🏋️ アクティビティ"]

    for activity in activities:
        # アクティビティタイプとアイコン
        activity_icon = _get_activity_icon(activity.activity_type)
        activity_name = (
            activity.activity_name or activity.activity_type.replace("_", " ").title()
        )

        # 基本情報
        basic_info = f"{activity_icon} **{activity_name}**"

        # 詳細情報の構築
        details = []
        if activity.duration_minutes:
            hours = activity.duration_minutes // 60
            minutes = activity.duration_minutes % 60
            if hours > 0:
                details.append(f"{hours}時間{minutes}分")
            else:
                details.append(f"{minutes}分")

        if activity.distance_km:
            details.append(f"{activity.distance_km:.2f}km")

        if activity.calories:
            details.append(f"{activity.calories}kcal")

        if activity.average_heart_rate:
            details.append(f"平均心拍数: {activity.average_heart_rate}bpm")

        if activity.start_time:
            start_time_str = activity.start_time.strftime("%H:%M")
            details.append(f"開始: {start_time_str}")

        # 行の構築
        if details:
            lines.append(f"- {basic_info}: {' / '.join(details)}")
        else:
            lines.append(f"- {basic_info}")

    return "\n".join(lines) + "\n"


def _format_errors_section(errors: list[DataError]) -> str:
    """エラー情報をフォーマット"""
    if not errors:
        return ""

    lines = ["### ⚠️ データ取得エラー"]
    for error in errors:
        user_msg = error.user_message or error.message
        lines.append(f"- {user_msg}")

    return "\n".join(lines) + "\n"


def _format_no_data_section(health_data: HealthData) -> str:
    """データが取得できない場合のセクション"""
    lines = ["## 🏃 Health Data", ""]

    if health_data.errors:
        lines.append("⚠️ **健康データの取得に失敗しました**\n")
        for error in health_data.errors:
            lines.append(f"- {error}")
        lines.append("")
    else:
        lines.append("📊 **本日の健康データは取得できませんでした**\n")

    lines.append(
        f"*確認日時: {health_data.retrieved_at.strftime('%Y-%m-%d %H:%M:%S')}*\n"
    )

    return "\n".join(lines)


# ヘルパー関数群


def _get_quality_icon(quality: str) -> str:
    """データ品質に応じたアイコンを取得"""
    quality_icons = {"good": "✅", "partial": "⚠️", "poor": "🟡", "no_data": "❌"}
    return quality_icons.get(quality, "❓")


def _get_quality_description(quality: str) -> str:
    """データ品質の説明を取得"""
    descriptions = {
        "good": "全データ取得済み",
        "partial": "一部データのみ取得",
        "poor": "最小限のデータのみ",
        "no_data": "データ取得失敗",
    }
    return descriptions.get(quality, "不明")


def _get_sleep_score_icon(score: int) -> str:
    """睡眠スコアに応じたアイコンを取得"""
    if score >= 80:
        return "🌟"
    if score >= 70:
        return "😊"
    if score >= 60:
        return "😐"
    return "😴"


def _get_step_count_icon(steps: int) -> str:
    """歩数に応じたアイコンを取得"""
    if steps >= 10000:
        return "🏆"
    if steps >= 8000:
        return "👍"
    if steps >= 5000:
        return "📈"
    return "📊"


def _get_heart_rate_icon(resting_hr: int) -> str:
    """安静時心拍数に応じたアイコンを取得"""
    if resting_hr < 60:
        return "💪"  # アスリートレベル
    if resting_hr < 80:
        return "❤️"  # 正常範囲
    return "⚠️"  # やや高め


def _get_activity_icon(activity_type: str) -> str:
    """アクティビティタイプに応じたアイコンを取得"""
    activity_icons = {
        "running": "🏃",
        "walking": "🚶",
        "cycling": "🚴",
        "swimming": "🏊",
        "strength_training": "🏋️",
        "yoga": "🧘",
        "hiking": "🥾",
        "tennis": "🎾",
        "golf": "⛳",
        "basketball": "🏀",
        "football": "⚽",
        "gym": "🏋️",
        "cardio": "💓",
        "workout": "💪",
    }

    # 完全一致を試行
    if activity_type.lower() in activity_icons:
        return activity_icons[activity_type.lower()]

    # 部分一致を試行
    for key, icon in activity_icons.items():
        if key in activity_type.lower():
            return icon

    return "🏃"  # デフォルトアイコン
