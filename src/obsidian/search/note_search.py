"""Advanced note search functionality."""

import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

import aiofiles
import structlog

from src.obsidian.search.search_models import SearchCriteria, SearchResult

logger = structlog.get_logger(__name__)


class NoteSearch:
    """Handles advanced search functionality for Obsidian notes."""

    def __init__(self, vault_path: Path):
        self.vault_path = vault_path

    async def search_notes(self, criteria: SearchCriteria) -> list[SearchResult]:
        """Search notes based on criteria."""
        try:
            # Get all markdown files
            markdown_files = await self._get_markdown_files(criteria.exclude_folders)

            results = []
            for file_path in markdown_files:
                # Check if file matches criteria
                search_result = await self._evaluate_file_match(file_path, criteria)
                if search_result:
                    results.append(search_result)

            # Sort by relevance score
            results.sort(key=lambda x: x.relevance_score, reverse=True)

            # Apply result limit
            if criteria.max_results > 0:
                results = results[: criteria.max_results]

            logger.info(
                "Search completed",
                query=criteria.query,
                total_results=len(results),
                files_searched=len(markdown_files),
            )

            return results

        except Exception as e:
            logger.error("Search failed", error=str(e), criteria=criteria.query)
            return []

    async def _get_markdown_files(
        self, exclude_folders: list[str] | None = None
    ) -> list[Path]:
        """Get all markdown files in vault."""
        exclude_folders = exclude_folders or [".trash", ".obsidian"]
        markdown_files = []

        def should_exclude_path(path: Path) -> bool:
            for exclude in exclude_folders:
                if exclude in str(path):
                    return True
            return False

        # Walk through vault directory
        for path in self.vault_path.rglob("*.md"):
            if not should_exclude_path(path):
                markdown_files.append(path)

        return markdown_files

    async def _evaluate_file_match(
        self, file_path: Path, criteria: SearchCriteria
    ) -> SearchResult | None:
        """Evaluate if file matches search criteria."""
        try:
            # Parse file
            parsed_data = await self._parse_markdown_file(file_path)
            if not parsed_data:
                return None

            relevance_score = 0.0
            match_highlights = []

            # Text query matching
            if criteria.query:
                text_score, highlights = self._evaluate_text_match(
                    parsed_data, criteria.query
                )
                if text_score <= 0:
                    return None  # No text match, skip this file
                relevance_score += text_score
                match_highlights.extend(highlights)

            # Tag filtering
            if criteria.tags:
                if not self._matches_tags(parsed_data.get("tags", []), criteria.tags):
                    return None

            # Category filtering
            if criteria.category:
                if parsed_data.get("category") != criteria.category:
                    return None

            # Date filtering
            if criteria.date_from or criteria.date_to:
                file_date = parsed_data.get("created_date")
                # Convert string dates to date objects if needed
                date_from = (
                    datetime.fromisoformat(criteria.date_from).date()
                    if isinstance(criteria.date_from, str)
                    else criteria.date_from
                )
                date_to = (
                    datetime.fromisoformat(criteria.date_to).date()
                    if isinstance(criteria.date_to, str)
                    else criteria.date_to
                )
                if not self._matches_date_range(file_date, date_from, date_to):
                    return None

            # Create search result
            content_preview = self._create_content_preview(
                parsed_data.get("content", ""), criteria.query
            )

            return SearchResult(
                file_path=file_path,
                title=parsed_data.get("title", file_path.stem),
                content_preview=content_preview,
                relevance_score=relevance_score,
                tags=parsed_data.get("tags", []),
                created_date=parsed_data.get("created_date"),
                category=parsed_data.get("category"),
                match_highlights=match_highlights,
            )

        except Exception as e:
            logger.warning(
                "Failed to evaluate file", error=str(e), file_path=str(file_path)
            )
            return None

    async def _parse_markdown_file(self, file_path: Path) -> dict[str, Any] | None:
        """Parse markdown file and extract metadata."""
        try:
            async with aiofiles.open(file_path, encoding="utf-8") as f:
                content = await f.read()

            parsed_data: dict[str, Any] = {
                "title": file_path.stem,
                "content": content,
                "tags": [],
                "category": None,
                "created_date": None,
            }

            lines = content.split("\n")

            # Extract title from first h1
            for line in lines:
                if line.startswith("# "):
                    parsed_data["title"] = line[2:].strip()
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
                            parsed_data["created_date"] = date.fromisoformat(
                                value.split()[0]
                            ).isoformat()
                        except ValueError:
                            pass
                    elif key == "tags":
                        # Parse tags
                        tags_str = value.strip("[]")
                        parsed_data["tags"] = [
                            tag.strip().strip("\"'")
                            for tag in tags_str.split(",")
                            if tag.strip()
                        ]
                    elif key == "category":
                        parsed_data["category"] = value

            return parsed_data

        except Exception as e:
            logger.warning(
                "Failed to parse markdown file", error=str(e), file_path=str(file_path)
            )
            return None

    def _evaluate_text_match(
        self, parsed_data: dict[str, Any], query: str
    ) -> tuple[float, list[str]]:
        """Evaluate text match and return score with highlights."""
        if not query:
            return 1.0, []

        query_lower = query.lower()
        title = parsed_data.get("title", "").lower()
        content = parsed_data.get("content", "").lower()

        score = 0.0
        highlights = []

        # Title matches (higher weight)
        if query_lower in title:
            score += 10.0
            highlights.append(f"Title: {parsed_data.get('title', '')}")

        # Content matches
        content_matches = len(re.findall(re.escape(query_lower), content))
        if content_matches > 0:
            score += content_matches * 2.0

            # Extract surrounding context for highlights
            content_lines = parsed_data.get("content", "").split("\n")
            for i, line in enumerate(content_lines):
                if query_lower in line.lower():
                    highlights.append(f"Line {i + 1}: {line.strip()}")
                    if len(highlights) >= 3:  # Limit highlights
                        break

        # Tag matches
        tags = parsed_data.get("tags", [])
        for tag in tags:
            if query_lower in tag.lower():
                score += 5.0
                highlights.append(f"Tag: {tag}")

        return score, highlights

    def _matches_tags(self, file_tags: list[str], search_tags: list[str]) -> bool:
        """Check if file tags match search criteria."""
        file_tags_lower = [tag.lower() for tag in file_tags]
        search_tags_lower = [tag.lower() for tag in search_tags]

        # All search tags must be present
        return all(tag in file_tags_lower for tag in search_tags_lower)

    def _matches_date_range(
        self, file_date: date | None, date_from: date | None, date_to: date | None
    ) -> bool:
        """Check if file date falls within search range."""
        if not file_date:
            return False

        if date_from and file_date < date_from:
            return False

        if date_to and file_date > date_to:
            return False

        return True

    def _create_content_preview(self, content: str, query: str | None = None) -> str:
        """Create content preview with query context."""
        if not content:
            return ""

        # Remove metadata section
        lines = content.split("\n")
        content_lines = []
        skip_metadata = False

        for line in lines:
            if line.strip() == "---":
                if not skip_metadata:
                    skip_metadata = True
                    continue
                else:
                    skip_metadata = False
                    continue
            elif not skip_metadata:
                content_lines.append(line)

        clean_content = "\n".join(content_lines).strip()

        # Find relevant excerpt if query provided
        if query and query.lower() in clean_content.lower():
            # Find first occurrence and extract surrounding context
            query_pos = clean_content.lower().find(query.lower())
            start = max(0, query_pos - 100)
            end = min(len(clean_content), query_pos + 200)
            excerpt = clean_content[start:end]

            if start > 0:
                excerpt = "..." + excerpt
            if end < len(clean_content):
                excerpt = excerpt + "..."

            return excerpt
        else:
            # Return first 200 characters
            preview = clean_content[:200]
            if len(clean_content) > 200:
                preview += "..."
            return preview
