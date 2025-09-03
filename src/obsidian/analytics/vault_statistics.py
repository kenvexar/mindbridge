"""Vault statistics calculation and caching."""

import time
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import aiofiles
import structlog

from src.obsidian.analytics.stats_models import CategoryStats, VaultStats

logger = structlog.get_logger(__name__)


class VaultStatistics:
    """Handles vault statistics calculation and caching."""

    def __init__(self, vault_path: Path, cache_duration: int = 300):
        self.vault_path = vault_path
        self.cache_duration = cache_duration  # 5 minutes default

        self._stats_cache: VaultStats | None = None
        self._cache_time: float = 0

    async def get_vault_stats(self, force_refresh: bool = False) -> VaultStats:
        """Get comprehensive vault statistics with caching."""
        current_time = time.time()

        # Check cache validity
        if (
            not force_refresh
            and self._stats_cache is not None
            and (current_time - self._cache_time) < self.cache_duration
        ):
            logger.debug("Returning cached vault stats")
            return self._stats_cache

        logger.info("Calculating vault statistics")

        try:
            # Calculate fresh statistics
            stats = await self._calculate_vault_stats()

            # Update cache
            self._stats_cache = stats
            self._cache_time = current_time

            logger.info(
                "Vault statistics calculated",
                total_notes=stats.total_notes,
                total_characters=stats.total_characters,
                calculation_time=time.time() - current_time,
            )

            return stats

        except Exception as e:
            logger.error("Failed to calculate vault statistics", error=str(e))
            # Return cached stats if available, otherwise empty stats
            if self._stats_cache:
                return self._stats_cache
            return self._create_empty_stats()

    async def _calculate_vault_stats(self) -> VaultStats:
        """Calculate comprehensive vault statistics."""
        # Get all markdown files
        markdown_files = []
        folder_count = 0

        for path in self.vault_path.rglob("*"):
            if path.is_dir() and not any(part.startswith(".") for part in path.parts):
                folder_count += 1
            elif path.suffix == ".md" and not any(
                part.startswith(".") for part in path.parts
            ):
                markdown_files.append(path)

        # Process files for detailed stats
        notes_data = []
        total_characters = 0
        total_words = 0
        category_counter: Counter[str] = Counter()
        tag_counter: Counter[str] = Counter()
        creation_dates = []

        for file_path in markdown_files:
            note_data = await self._analyze_note_file(file_path)
            if note_data:
                notes_data.append(note_data)
                total_characters += note_data["character_count"]
                total_words += note_data["word_count"]

                if note_data["category"]:
                    category_counter[note_data["category"]] += 1

                for tag in note_data["tags"]:
                    tag_counter[tag] += 1

                if note_data["created_date"]:
                    creation_dates.append(note_data["created_date"])

        # Calculate time-based stats
        today = date.today()
        time_stats = self._calculate_time_based_stats(creation_dates, today)

        # Calculate category stats
        category_stats = await self._calculate_category_stats(notes_data)

        # Find largest/smallest notes
        largest_note = None
        smallest_note = None
        if notes_data:
            largest = max(notes_data, key=lambda x: x["character_count"])
            smallest = min(notes_data, key=lambda x: x["character_count"])
            largest_note = (largest["title"], largest["character_count"])
            smallest_note = (smallest["title"], smallest["character_count"])

        # Calculate averages
        note_count = len(notes_data)
        avg_note_size = total_characters / note_count if note_count > 0 else 0
        avg_words_per_note = total_words / note_count if note_count > 0 else 0

        # Creation timeline
        timeline: dict[str, int] = defaultdict(int)
        for creation_date in creation_dates:
            timeline[creation_date.isoformat()] += 1

        # Find busiest day
        busiest_day = None
        if timeline:
            busiest_day_str = max(timeline, key=timeline.get)  # type: ignore[arg-type]
            busiest_day = date.fromisoformat(busiest_day_str)

        # Determine vault creation date
        vault_created = None
        if creation_dates:
            vault_created = datetime.combine(min(creation_dates), datetime.min.time())

        return VaultStats(
            total_notes=note_count,
            total_characters=total_characters,
            total_words=total_words,
            total_folders=folder_count,
            notes_today=time_stats["today"],
            notes_this_week=time_stats["week"],
            notes_this_month=time_stats["month"],
            notes_this_year=time_stats["year"],
            avg_note_size=avg_note_size,
            avg_words_per_note=avg_words_per_note,
            category_stats=category_stats,
            most_used_tags=tag_counter.most_common(10),
            total_unique_tags=len(tag_counter),
            busiest_day=busiest_day,
            creation_timeline=dict(timeline),
            largest_note=largest_note,
            smallest_note=smallest_note,
            last_updated=datetime.now(),
            vault_created=vault_created,
        )

    async def _analyze_note_file(self, file_path: Path) -> dict[str, Any] | None:
        """Analyze individual note file."""
        try:
            async with aiofiles.open(file_path, encoding="utf-8") as f:
                content = await f.read()

            # Basic metrics
            character_count = len(content)
            word_count = len(content.split())

            # Parse metadata
            title = file_path.stem
            tags = []
            category = None
            created_date = None

            lines = content.split("\n")

            # Extract title from h1
            for line in lines:
                if line.startswith("# "):
                    title = line[2:].strip()
                    break

            # Extract metadata
            in_metadata = False
            for line in lines:
                if line.strip() == "---":
                    if not in_metadata:
                        in_metadata = True
                        continue
                    else:
                        break
                elif in_metadata and ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip().lower()
                    value = value.strip()

                    if key == "created":
                        try:
                            created_date = date.fromisoformat(value.split()[0])
                        except ValueError:
                            pass
                    elif key == "tags":
                        # Parse tags
                        tags_str = value.strip("[]")
                        tags = [
                            tag.strip().strip("\"'")
                            for tag in tags_str.split(",")
                            if tag.strip()
                        ]
                    elif key == "category":
                        category = value

            # If no created date in metadata, use file creation time
            if not created_date:
                try:
                    creation_time = file_path.stat().st_ctime
                    created_date = datetime.fromtimestamp(creation_time).date()
                except OSError:
                    pass

            return {
                "title": title,
                "character_count": character_count,
                "word_count": word_count,
                "tags": tags,
                "category": category,
                "created_date": created_date,
                "file_path": file_path,
            }

        except Exception as e:
            logger.warning(
                "Failed to analyze note file", error=str(e), file_path=str(file_path)
            )
            return None

    def _calculate_time_based_stats(
        self, creation_dates: list[date], today: date
    ) -> dict[str, int]:
        """Calculate time-based note creation statistics."""
        stats = {
            "today": 0,
            "week": 0,
            "month": 0,
            "year": 0,
        }

        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        year_start = today.replace(month=1, day=1)

        for creation_date in creation_dates:
            if creation_date == today:
                stats["today"] += 1
            if creation_date >= week_start:
                stats["week"] += 1
            if creation_date >= month_start:
                stats["month"] += 1
            if creation_date >= year_start:
                stats["year"] += 1

        return stats

    async def _calculate_category_stats(
        self, notes_data: list[dict[str, Any]]
    ) -> list[CategoryStats]:
        """Calculate statistics by category."""
        category_groups = defaultdict(list)

        for note in notes_data:
            category = note["category"] or "Uncategorized"
            category_groups[category].append(note)

        category_stats = []
        for category, notes in category_groups.items():
            total_chars = sum(note["character_count"] for note in notes)
            total_words = sum(note["word_count"] for note in notes)
            avg_size = total_chars / len(notes)

            # Collect all tags in this category
            all_tags = []
            for note in notes:
                all_tags.extend(note["tags"])
            unique_tags = list(set(all_tags))

            # Find most recent update
            last_updated = None
            for note in notes:
                if note["created_date"]:
                    note_datetime = datetime.combine(
                        note["created_date"], datetime.min.time()
                    )
                    if not last_updated or note_datetime > last_updated:
                        last_updated = note_datetime

            category_stats.append(
                CategoryStats(
                    category=category,
                    note_count=len(notes),
                    total_characters=total_chars,
                    total_words=total_words,
                    avg_note_size=avg_size,
                    last_updated=last_updated,
                    tags=unique_tags,
                )
            )

        # Sort by note count descending
        category_stats.sort(key=lambda x: x.note_count, reverse=True)
        return category_stats

    def _create_empty_stats(self) -> VaultStats:
        """Create empty statistics object."""
        return VaultStats(
            total_notes=0,
            total_characters=0,
            total_words=0,
            total_folders=0,
            notes_today=0,
            notes_this_week=0,
            notes_this_month=0,
            notes_this_year=0,
            avg_note_size=0.0,
            avg_words_per_note=0.0,
            category_stats=[],
            most_used_tags=[],
            total_unique_tags=0,
            busiest_day=None,
            creation_timeline={},
            largest_note=None,
            smallest_note=None,
            last_updated=datetime.now(),
            vault_created=None,
        )

    def invalidate_cache(self) -> None:
        """Manually invalidate statistics cache."""
        self._stats_cache = None
        self._cache_time = 0
        logger.debug("Vault statistics cache invalidated")
