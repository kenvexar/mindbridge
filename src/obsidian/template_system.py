"""
Advanced template system for Obsidian notes with component-based architecture
Following SOLID principles for better maintainability and testability
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol, cast

import aiofiles

from src.ai.models import AIProcessingResult, ProcessingCategory
from src.obsidian.models import NoteFrontmatter, ObsidianNote, VaultFolder
from src.utils.mixins import LoggerMixin


class ITemplateProcessor(Protocol):
    """Template processor interface for dependency inversion."""

    async def process(self, content: str, context: dict[str, Any]) -> str:
        """Process template content with given context."""
        ...


class TemplateLoader:
    """Handles template loading and inheritance chain resolution."""

    def __init__(self, template_path: Path, logger):
        self.template_path = template_path
        self.cached_templates: dict[str, dict[str, Any]] = {}
        self.template_inheritance_cache: dict[str, str] = {}
        self.logger = logger

    async def load_template(self, template_name: str) -> str | None:
        """
        テンプレートを読み込み（改良版キャッシュ機能付き）
        Implements ITemplateLoader interface.

        Args:
            template_name: テンプレート名（拡張子なし）

        Returns:
            テンプレート内容、見つからない場合は None
        """
        try:
            # キャッシュから取得を試行
            if template_name in self.cached_templates:
                cached_data = self.cached_templates[template_name]
                template_file = self.template_path / f"{template_name}.md"

                # ファイルの更新時間をチェック
                if template_file.exists():
                    file_mtime = template_file.stat().st_mtime
                    if cached_data.get("mtime") == file_mtime:
                        self.logger.debug(
                            "Template loaded from cache", template=template_name
                        )
                        return cached_data["content"]

            # ファイルからテンプレートを読み込み
            template_file = self.template_path / f"{template_name}.md"

            if not template_file.exists():
                self.logger.warning(
                    "Template file not found",
                    template=template_name,
                    path=str(template_file),
                )
                return None

            async with aiofiles.open(template_file, encoding="utf-8") as f:
                content = await f.read()

            # テンプレート継承の処理
            content = await self._process_template_inheritance(content, template_name)

            # キャッシュに保存（改良版）
            file_mtime = template_file.stat().st_mtime
            self.cached_templates[template_name] = {
                "content": content,
                "mtime": file_mtime,
            }

            self.logger.info("Template loaded successfully", template=template_name)
            return content

        except Exception as e:
            self.logger.error(
                "Failed to load template",
                template=template_name,
                error=str(e),
                exc_info=True,
            )
            return None

    async def _process_template_inheritance(
        self, content: str, template_name: str
    ) -> str:
        """Process template inheritance chain - extracted from TemplateEngine."""
        try:
            # extends 構文の検出: {{extends "parent_template"}}
            extends_pattern = r'\{\{extends\s+["\']([^"\']+)["\']\s*\}\}'
            extends_match = re.search(extends_pattern, content)

            if not extends_match:
                return content

            parent_template_name = extends_match.group(1)

            # 循環参照チェック
            inheritance_chain = [template_name]
            current_template = parent_template_name
            while current_template in self.template_inheritance_cache:
                if current_template in inheritance_chain:
                    raise ValueError(
                        f"Circular template inheritance detected: {' -> '.join(inheritance_chain + [current_template])}"
                    )
                inheritance_chain.append(current_template)
                current_template = self.template_inheritance_cache.get(current_template)

            # 親テンプレートを読み込み
            parent_content = await self.load_template(parent_template_name)
            if not parent_content:
                raise ValueError(f"Parent template not found: {parent_template_name}")

            # 継承関係をキャッシュ
            self.template_inheritance_cache[template_name] = parent_template_name

            # extends ディレクティブを削除
            content = re.sub(extends_pattern, "", content, flags=re.MULTILINE)

            # ブロック置換の処理
            content = self._process_template_blocks(parent_content, content)

            return content

        except Exception as e:
            self.logger.error(
                "Failed to process template inheritance",
                template=template_name,
                error=str(e),
                exc_info=True,
            )
            return content  # エラー時は元のテンプレートを返す  # Simplified for now

    def _process_template_blocks(self, parent_content: str, child_content: str) -> str:
        """親テンプレートのブロックを子テンプレートの内容で置換"""
        # 子テンプレートからブロックを抽出: {{block "block_name"}}content{{/block}}
        child_blocks = {}
        block_pattern = r'\{\{block\s+["\']([^"\']+)["\']\s*\}\}(.*?)\{\{/block\s*\}\}'

        for match in re.finditer(block_pattern, child_content, re.DOTALL):
            block_name = match.group(1)
            block_content = match.group(2).strip()
            child_blocks[block_name] = block_content

        # 親テンプレートのブロックを子テンプレートの内容で置換
        def replace_block(match):
            block_name = match.group(1)
            default_content = match.group(2).strip()
            return child_blocks.get(block_name, default_content)

        result = re.sub(block_pattern, replace_block, parent_content, flags=re.DOTALL)
        return result


class ConditionalProcessor:
    """Handles conditional sections in templates.
    Implements IConditionalProcessor interface."""

    def __init__(self, logger):
        self.logger = logger

    async def process(self, content: str, context: dict[str, Any]) -> str:
        """Process conditional sections - extracted from TemplateEngine.
        Implements IConditionalProcessor interface."""
        # if-elif-else 構文に対応: {{#if condition}}...{{#elif condition}}...{{#else}}...{{/if}}

        def replace_conditional(match: re.Match[str]) -> str:
            full_match = match.group(0)
            # より複雑な if-elif-else 構造を解析
            return self._parse_complex_conditional(full_match, context)

        # 複数回処理してネストした条件にも対応
        processed = content
        for _ in range(5):  # 最大 5 回の繰り返し処理
            # 複雑な if-elif-else 構造を処理（全体的なパターン）
            complex_if_pattern = r"\{\{\s*#if\s+([^}]+)\s*\}\}(.*?)\{\{\s*/if\s*\}\}"
            new_processed = re.sub(
                complex_if_pattern, replace_conditional, processed, flags=re.DOTALL
            )

            # シンプルな if 文から処理
            simple_if_pattern = r"\{\{\s*#if\s+(\w+)\s*\}\}((?:(?!\{\{\s*(?:#elif|#else|/if)\s*\}\}).)*?)\{\{\s*/if\s*\}\}"
            new_processed = re.sub(
                simple_if_pattern,
                lambda m: self._process_simple_if(m, context),
                new_processed,
                flags=re.DOTALL,
            )

            if new_processed == processed:
                break
            processed = new_processed

        return processed

    def _process_simple_if(self, match: re.Match[str], context: dict[str, Any]) -> str:
        """シンプルな if 文を処理"""
        condition = match.group(1).strip()
        content = match.group(2)

        if self._evaluate_condition(condition, context):
            return content
        return ""

    def _parse_complex_conditional(
        self, full_match: str, context: dict[str, Any]
    ) -> str:
        """Complex conditional parsing - extracted from TemplateEngine"""
        try:
            if_match = self._extract_if_condition(full_match)
            if not if_match:
                return ""

            remaining_content = full_match[if_match.end() :]
            conditions_and_content = [("if", if_match.group(1).strip(), "")]

            self._parse_conditional_blocks(remaining_content, conditions_and_content)
            return self._evaluate_conditions(conditions_and_content, context)

        except Exception as e:
            self.logger.error("Failed to parse complex conditional", error=str(e))
            return ""

    def _extract_if_condition(self, full_match: str) -> re.Match[str] | None:
        """Extract the initial if condition from the template."""
        return re.search(r"\{\{\s*#if\s+([^}]+)\s*\}\}", full_match)

    def _parse_conditional_blocks(
        self, remaining_content: str, conditions_and_content: list
    ) -> None:
        """Parse elif, else, and endif blocks from the template."""
        patterns = {
            "elif": r"\{\{\s*#elif\s+([^}]+)\s*\}\}",
            "else": r"\{\{\s*#else\s*\}\}",
            "endif": r"\{\{\s*/if\s*\}\}",
        }

        current_pos = 0
        while current_pos < len(remaining_content):
            next_tag = self._find_next_template_tag(
                remaining_content, current_pos, patterns
            )

            if not next_tag:
                break

            next_pos, next_type, next_match = next_tag
            block_content = remaining_content[current_pos:next_pos].strip()

            self._update_current_block_content(conditions_and_content, block_content)

            if not self._process_template_tag(
                next_type, next_match, conditions_and_content, next_pos
            ):
                current_pos = next_pos + len(next_match.group(0))
            else:
                break  # endif encountered

    def _find_next_template_tag(
        self, content: str, start_pos: int, patterns: dict[str, str]
    ) -> tuple[int, str, re.Match[str]] | None:
        """Find the next template tag (elif, else, or endif)."""
        matches = []
        for tag_type, pattern in patterns.items():
            match = re.search(pattern, content[start_pos:])
            if match:
                matches.append((match.start() + start_pos, tag_type, match))

        if not matches:
            return None

        matches.sort()
        return matches[0]

    def _update_current_block_content(
        self, conditions_and_content: list, block_content: str
    ) -> None:
        """Update the content of the current condition block."""
        if conditions_and_content:
            current = conditions_and_content[-1]
            conditions_and_content[-1] = (current[0], current[1], block_content)

    def _process_template_tag(
        self,
        tag_type: str,
        match: re.Match[str],
        conditions_and_content: list,
        pos: int,
    ) -> bool:
        """Process a template tag and return True if endif encountered."""
        if tag_type == "elif":
            elif_condition = match.group(1).strip()
            conditions_and_content.append(("elif", elif_condition, ""))
        elif tag_type == "else":
            conditions_and_content.append(("else", "", ""))
        elif tag_type == "endif":
            return True
        return False

    def _evaluate_conditions(
        self, conditions_and_content: list, context: dict[str, Any]
    ) -> str:
        """Evaluate conditions and return the appropriate content."""
        for cond_type, condition, content in conditions_and_content:
            if cond_type == "else" or self._evaluate_condition(condition, context):
                return content
        return ""

    def _evaluate_condition(self, condition: str, context: dict[str, Any]) -> bool:
        """Evaluate conditional expression - extracted from TemplateEngine"""
        try:
            condition = condition.strip()

            # NOT 演算子を最初に処理
            if condition.startswith("not "):
                return not self._evaluate_condition(condition[4:].strip(), context)

            # 複合条件（AND/OR）の処理
            if result := self._evaluate_logical_operators(condition, context):
                return result[0] if result[1] else False

            # 比較演算子の処理
            comparison_result = self._evaluate_comparison_operators(condition, context)
            if comparison_result is not None:
                return comparison_result

            # シンプルな真偽値評価
            condition_value = context.get(condition, False)
            return self._is_truthy(condition_value)

        except Exception as e:
            self.logger.error(
                "Failed to evaluate condition", condition=condition, error=str(e)
            )
            return False

    def _evaluate_logical_operators(
        self, condition: str, context: dict[str, Any]
    ) -> tuple[bool, bool] | None:
        """Evaluate AND/OR logical operators."""
        if " and " in condition:
            conditions = condition.split(" and ")
            result = all(
                self._evaluate_condition(cond.strip(), context) for cond in conditions
            )
            return (result, True)

        if " or " in condition:
            conditions = condition.split(" or ")
            result = any(
                self._evaluate_condition(cond.strip(), context) for cond in conditions
            )
            return (result, True)

        return None

    def _evaluate_comparison_operators(
        self, condition: str, context: dict[str, Any]
    ) -> bool | None:
        """Evaluate comparison operators (==, !=, >=, <=, >, <)."""
        operators = {
            " == ": lambda left, right: str(left) == str(right),
            " != ": lambda left, right: str(left) != str(right),
            " >= ": self._numeric_compare(lambda left, right: left >= right),
            " <= ": self._numeric_compare(lambda left, right: left <= right),
            " > ": self._numeric_compare(lambda left, right: left > right),
            " < ": self._numeric_compare(lambda left, right: left < right),
        }

        for operator, compare_func in operators.items():
            if operator in condition:
                left, right = condition.split(operator, 1)
                left_val = self._get_condition_value(left.strip(), context)
                right_val = self._get_condition_value(right.strip(), context)
                return compare_func(left_val, right_val)

        return None

    def _numeric_compare(self, compare_func):
        """Create a numeric comparison function with error handling."""

        def wrapper(left_val, right_val):
            try:
                return compare_func(float(left_val), float(right_val))
            except (ValueError, TypeError):
                return False

        return wrapper

    def _get_condition_value(self, value_str: str, context: dict[str, Any]) -> Any:
        """Get value for condition evaluation"""
        value_str = value_str.strip()

        # String literals
        if (value_str.startswith('"') and value_str.endswith('"')) or (
            value_str.startswith("'") and value_str.endswith("'")
        ):
            return value_str[1:-1]

        # Number literals
        try:
            if "." in value_str:
                return float(value_str)
            else:
                return int(value_str)
        except ValueError:
            pass

        # Boolean literals
        if value_str.lower() == "true":
            return True
        elif value_str.lower() == "false":
            return False

        # Context variables
        return context.get(value_str, "")

    def _is_truthy(self, value: Any) -> bool:
        """Check if value is truthy"""
        if isinstance(value, bool):
            return value
        elif isinstance(value, str):
            return value.strip() != ""
        elif isinstance(value, int | float):
            return value != 0
        elif isinstance(value, list | dict):
            return len(value) > 0
        elif value is None:
            return False
        else:
            return bool(value)


class CustomFunctionProcessor:
    """Handles custom functions in templates.
    Implements ICustomFunctionProcessor interface."""

    def __init__(self, logger):
        self.logger = logger

    async def process(self, content: str, context: dict[str, Any]) -> str:
        """Process custom functions - migrated from TemplateEngine.
        Implements ICustomFunctionProcessor interface."""

        # Include 処理は一旦スキップ（循環依存回避のため）

        # 文字数制限: {{truncate(text, length)}}
        def truncate_func(match: re.Match[str]) -> str:
            args_str = match.group(1)
            args = [arg.strip() for arg in args_str.split(",")]
            if len(args) >= 2:
                text_key = args[0].strip()
                try:
                    length = int(args[1].strip())

                    if text_key in context:
                        text = str(context[text_key])
                        return text[:length] + "..." if len(text) > length else text
                    else:
                        self.logger.debug(f"Text key '{text_key}' not found in context")
                except ValueError:
                    self.logger.debug(f"Invalid length parameter: {args[1]}")
            return ""

        content = re.sub(r"\{\{truncate\((.*?)\)\}\}", truncate_func, content)

        # 日付フォーマット: {{date_format(date, format)}}
        # 日付オフセット機能付き: {{date_format(date, format, offset)}}
        def date_format_func(match: re.Match[str]) -> str:
            args_str = match.group(1)
            args = [arg.strip() for arg in args_str.split(",")]
            if len(args) >= 2:
                date_key = args[0].strip()
                format_str = args[1].strip().strip("\"'")

                # オフセット（日数）がある場合
                offset_days = 0
                if len(args) >= 3:
                    try:
                        offset_days = int(args[2].strip())
                    except ValueError:
                        self.logger.debug(f"Invalid offset parameter: {args[2]}")

                if date_key in context and isinstance(context[date_key], datetime):
                    date_value = cast("datetime", context[date_key])
                    # オフセットを適用
                    if offset_days != 0:
                        from datetime import timedelta

                        date_value = date_value + timedelta(days=offset_days)
                    return date_value.strftime(format_str)
                else:
                    self.logger.debug(
                        f"Date key '{date_key}' not found or not datetime"
                    )
            return ""

        content = re.sub(r"\{\{date_format\((.*?)\)\}\}", date_format_func, content)

        # タグリスト: {{tag_list(tags)}}
        def tag_list_func(match: re.Match[str]) -> str:
            tags_key = match.group(1).strip()
            if tags_key in context and isinstance(context[tags_key], list):
                tags = context[tags_key]
                filtered_tags = [tag for tag in tags if tag]  # 空文字や None を除外
                return " ".join(f"#{tag}" for tag in filtered_tags)
            else:
                self.logger.debug(f"Tags key '{tags_key}' not found or not list")
            return ""

        content = re.sub(r"\{\{tag_list\((.*?)\)\}\}", tag_list_func, content)

        # 数値フォーマット {{number_format(number, format)}}
        def number_format_func(match: re.Match[str]) -> str:
            args_str = match.group(1)
            args = [arg.strip() for arg in args_str.split(",")]
            if len(args) >= 2:
                number_key = args[0].strip()
                format_str = args[1].strip().strip("\"'")

                if number_key in context:
                    try:
                        number = float(context[number_key])
                        if format_str == "currency":
                            return f"¥{number:,.0f}"
                        elif format_str == "percent":
                            return f"{number:.1%}"
                        elif format_str.startswith("decimal"):
                            decimals = (
                                int(format_str.split("_")[1])
                                if "_" in format_str
                                else 2
                            )
                            return f"{number:.{decimals}f}"
                        else:
                            return f"{number:,}"
                    except (ValueError, TypeError):
                        self.logger.debug(
                            f"Invalid number value for key '{number_key}'"
                        )
            return ""

        content = re.sub(r"\{\{number_format\((.*?)\)\}\}", number_format_func, content)

        # 条件式 {{conditional(condition, true_value, false_value)}}
        def conditional_func(match: re.Match[str]) -> str:
            args_str = match.group(1)
            args = [arg.strip().strip("\"'") for arg in args_str.split(",")]
            if len(args) >= 3:
                condition = args[0]
                true_val = args[1]
                false_val = args[2]

                condition_result = context.get(condition, False)
                if isinstance(condition_result, bool):
                    return true_val if condition_result else false_val
                elif isinstance(condition_result, str):
                    return true_val if condition_result.strip() != "" else false_val
                else:
                    return true_val if condition_result else false_val
            return ""

        content = re.sub(r"\{\{conditional\((.*?)\)\}\}", conditional_func, content)

        # 配列の長さ {{length(array)}}
        def length_func(match: re.Match[str]) -> str:
            array_key = match.group(1).strip()
            if array_key in context:
                value = context[array_key]
                if isinstance(value, list | dict | str):
                    return str(len(value))
            return "0"

        content = re.sub(r"\{\{length\((.*?)\)\}\}", length_func, content)

        # デフォルト値 {{default(value, default)}}
        def default_func(match: re.Match[str]) -> str:
            args_str = match.group(1)
            args = [arg.strip().strip("\"'") for arg in args_str.split(",")]
            if len(args) >= 2:
                value_key = args[0]
                default_val = args[1]

                value = context.get(value_key)
                if value is None or (isinstance(value, str) and value.strip() == ""):
                    return default_val
                return str(value)
            return ""

        content = re.sub(r"\{\{default\((.*?)\)\}\}", default_func, content)

        return content


class TemplateValidator:
    """Validates template syntax and structure.
    Implements ITemplateValidator interface."""

    def __init__(self, logger):
        self.logger = logger

    async def validate_template(self, content: str) -> list[str]:
        """Validate template and return list of issues - extracted from TemplateEngine.
        Implements ITemplateValidator interface."""
        issues: list[str] = []
        # Validation logic will be moved here
        return issues


class TemplateEngine(LoggerMixin):
    """高度なテンプレートエンジン"""

    def __init__(self, vault_path: Path):
        """
        Initialize template engine with component-based architecture.

        Args:
            vault_path: Obsidian vault path
        """
        from src.obsidian.models import VaultFolder

        self.vault_path = vault_path
        self.template_path = vault_path / VaultFolder.TEMPLATES.value

        # Initialize component-based architecture
        self.template_loader = TemplateLoader(self.template_path, self.logger)
        self.conditional_processor = ConditionalProcessor(self.logger)
        self.custom_function_processor = CustomFunctionProcessor(self.logger)
        self.template_validator = TemplateValidator(self.logger)

        # Legacy support - will be deprecated
        self.cached_templates: dict[str, dict[str, Any]] = {}
        self.template_inheritance_cache: dict[str, str] = {}

        self.logger.info("Template engine initialized with component architecture")

    async def load_template(self, template_name: str) -> str | None:
        """
        Load template using new component-based architecture.

        Args:
            template_name: テンプレート名（拡張子なし）

        Returns:
            テンプレート内容、見つからない場合は None
        """
        # Delegate to the specialized template loader component
        result = await self.template_loader.load_template(template_name)

        # Keep legacy cached_templates in sync for backward compatibility
        if result and template_name in self.template_loader.cached_templates:
            self.cached_templates[template_name] = (
                self.template_loader.cached_templates[template_name]
            )

        return result

    async def _process_template_inheritance(
        self, content: str, template_name: str
    ) -> str:
        """テンプレート継承を処理"""
        try:
            # extends 構文の検出: {{extends "parent_template"}}
            extends_pattern = r'\{\{extends\s+["\']([^"\']+)["\']\s*\}\}'
            extends_match = re.search(extends_pattern, content)

            if not extends_match:
                return content

            parent_template_name = extends_match.group(1)

            # 循環参照チェック
            inheritance_chain = [template_name]
            current_template = parent_template_name
            while current_template in self.template_inheritance_cache:
                if current_template in inheritance_chain:
                    raise ValueError(
                        f"Circular template inheritance detected: {' -> '.join(inheritance_chain + [current_template])}"
                    )
                inheritance_chain.append(current_template)
                current_template = self.template_inheritance_cache.get(current_template)

            # 親テンプレートを読み込み
            parent_content = await self.load_template(parent_template_name)
            if not parent_content:
                raise ValueError(f"Parent template not found: {parent_template_name}")

            # 継承関係をキャッシュ
            self.template_inheritance_cache[template_name] = parent_template_name

            # extends ディレクティブを削除
            content = re.sub(extends_pattern, "", content, flags=re.MULTILINE)

            # ブロック置換の処理
            content = self._process_template_blocks(parent_content, content)

            return content

        except Exception as e:
            self.logger.error(
                "Failed to process template inheritance",
                template=template_name,
                error=str(e),
                exc_info=True,
            )
            return content  # エラー時は元のテンプレートを返す

    def _process_template_blocks(self, parent_content: str, child_content: str) -> str:
        """親テンプレートのブロックを子テンプレートの内容で置換"""
        # 子テンプレートからブロックを抽出: {{block "block_name"}}content{{/block}}
        child_blocks = {}
        block_pattern = r'\{\{block\s+["\']([^"\']+)["\']\s*\}\}(.*?)\{\{/block\s*\}\}'

        for match in re.finditer(block_pattern, child_content, re.DOTALL):
            block_name = match.group(1)
            block_content = match.group(2).strip()
            child_blocks[block_name] = block_content

        # 親テンプレートのブロックを子テンプレートの内容で置換
        def replace_block(match):
            block_name = match.group(1)
            default_content = match.group(2).strip()
            return child_blocks.get(block_name, default_content)

        result = re.sub(block_pattern, replace_block, parent_content, flags=re.DOTALL)
        return result

    async def _compile_template(self, content: str) -> dict[str, Any]:
        """テンプレートをコンパイル（事前処理）"""
        try:
            compiled: dict[str, Any] = {
                "placeholders": [],
                "conditionals": [],
                "loops": [],
                "functions": [],
                "includes": [],
            }

            # プレースホルダーを抽出
            placeholder_pattern = r"\{\{([^#\/\{\}]+)\}\}"
            compiled["placeholders"] = list(
                set(re.findall(placeholder_pattern, content))
            )

            # 条件文を抽出
            conditional_pattern = r"\{\{\s*#if\s+(\w+)\s*\}\}"
            compiled["conditionals"] = list(
                set(re.findall(conditional_pattern, content))
            )

            # ループを抽出
            loop_pattern = r"\{\{\s*#each\s+(\w+)\s*\}\}"
            compiled["loops"] = list(set(re.findall(loop_pattern, content)))

            # 関数呼び出しを抽出
            function_pattern = r"\{\{(\w+)\([^)]*\)\}\}"
            compiled["functions"] = list(set(re.findall(function_pattern, content)))

            # インクルードを抽出
            include_pattern = r'\{\{include\s+["\']([^"\']+)["\']\s*\}\}'
            compiled["includes"] = list(set(re.findall(include_pattern, content)))

            return compiled

        except Exception as e:
            self.logger.warning("Failed to compile template", error=str(e))
            return {
                "placeholders": [],
                "conditionals": [],
                "loops": [],
                "functions": [],
                "includes": [],
            }

    async def render_template(
        self, template_content: str, context: dict[str, Any]
    ) -> str:
        """
        テンプレートをレンダリング - now using component-based architecture

        Args:
            template_content: テンプレート内容
            context: 置換用コンテキスト

        Returns:
            レンダリング済み内容
        """
        try:
            rendered = template_content

            # Include 処理を先に実行
            rendered = await self._process_includes(rendered, context)

            # Component-based processing
            # 条件付きセクション: {{#if condition}}content{{/if}}
            rendered = await self.conditional_processor.process(rendered, context)

            # 繰り返しセクション: {{#each items}}content{{/each}}
            rendered = await self._process_each_sections(rendered, context)

            # カスタム関数: {{function_name(args)}}
            rendered = await self.custom_function_processor.process(rendered, context)

            # 基本的なプレースホルダーの置換
            for placeholder, value in context.items():
                # 基本的なプレースホルダー: {{placeholder}}
                pattern = r"\{\{\s*" + re.escape(placeholder) + r"\s*\}\}"
                replacement = self._format_value(value)
                rendered = re.sub(pattern, replacement, rendered)

            # 未処理のテンプレート変数を清理
            rendered = self._clean_unprocessed_template_vars(rendered)

            # 🔧 FINAL FIX: レンダリング後に確実に自動生成メッセージを除去
            rendered = self._remove_bot_attribution_messages(rendered)

            self.logger.debug("Template rendered successfully with components")
            return rendered

        except Exception as e:
            self.logger.error("Failed to render template", error=str(e), exc_info=True)
            return template_content  # 失敗した場合は元のテンプレートを返す  # 失敗した場合は元のテンプレートを返す  # 失敗した場合は元のテンプレートを返す  # 失敗した場合は元のテンプレートを返す  # 失敗した場合は元のテンプレートを返す  # 失敗した場合は元のテンプレートを返す  # 失敗した場合は元のテンプレートを返す  # 失敗した場合は元のテンプレートを返す

    def _format_value(self, value: Any) -> str:
        """値をフォーマット"""
        if value is None:
            return ""
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, int | float):
            return str(value)
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(value, list):
            return ", ".join(str(item) for item in value)
        return str(value)

    async def _process_conditional_sections(
        self, content: str, context: dict[str, Any]
    ) -> str:
        """条件付きセクションを処理（ elif 対応版）"""
        # if-elif-else 構文に対応: {{#if condition}}...{{#elif condition}}...{{#else}}...{{/if}}

        def replace_conditional(match: re.Match[str]) -> str:
            full_match = match.group(0)

            # より複雑な if-elif-else 構造を解析
            return self._parse_complex_conditional(full_match, context)

        # 複数回処理してネストした条件にも対応
        processed = content
        for _ in range(5):  # 最大 5 回の繰り返し処理
            # シンプルな if 文から処理
            simple_if_pattern = r"\{\{\s*#if\s+(\w+)\s*\}\}((?:(?!\{\{\s*(?:#elif|#else|/if)\s*\}\}).)*?)\{\{\s*/if\s*\}\}"
            new_processed = re.sub(
                simple_if_pattern,
                lambda m: self._process_simple_if(m, context),
                processed,
                flags=re.DOTALL,
            )

            # 複雑な if-elif-else 構造を処理
            complex_if_pattern = r"\{\{\s*#if\s+([^}]+)\s*\}\}(.*?)\{\{\s*/if\s*\}\}"
            new_processed = re.sub(
                complex_if_pattern, replace_conditional, new_processed, flags=re.DOTALL
            )

            if new_processed == processed:
                break
            processed = new_processed

        return processed

    def _process_simple_if(self, match: re.Match[str], context: dict[str, Any]) -> str:
        """シンプルな if 文を処理"""
        condition = match.group(1).strip()
        section_content = match.group(2)

        condition_result = self._evaluate_condition(condition, context)

        self.logger.debug(
            "Processing simple conditional",
            condition=condition,
            result=condition_result,
            content_preview=section_content[:50],
        )

        return section_content if condition_result else ""

    def _parse_complex_conditional(
        self, conditional_block: str, context: dict[str, Any]
    ) -> str:
        """複雑な if-elif-else 構造を解析"""
        try:
            # if 文の解析
            if_match = re.search(r"\{\{\s*#if\s+([^}]+)\s*\}\}", conditional_block)
            if not if_match:
                return ""

            # 条件とコンテンツブロックを順次解析
            remaining_content = conditional_block[if_match.end() :]
            conditions_and_content = []

            # if 条件
            if_condition = if_match.group(1).strip()
            conditions_and_content.append(("if", if_condition, ""))

            # elif 条件を検索
            elif_pattern = r"\{\{\s*#elif\s+([^}]+)\s*\}\}"
            else_pattern = r"\{\{\s*#else\s*\}\}"
            endif_pattern = r"\{\{\s*/if\s*\}\}"

            current_pos = 0

            while current_pos < len(remaining_content):
                elif_match = re.search(elif_pattern, remaining_content[current_pos:])
                else_match = re.search(else_pattern, remaining_content[current_pos:])
                endif_match = re.search(endif_pattern, remaining_content[current_pos:])

                # 次に現れるタグを特定
                next_matches = []
                if elif_match:
                    next_matches.append(
                        (elif_match.start() + current_pos, "elif", elif_match)
                    )
                if else_match:
                    next_matches.append(
                        (else_match.start() + current_pos, "else", else_match)
                    )
                if endif_match:
                    next_matches.append(
                        (endif_match.start() + current_pos, "endif", endif_match)
                    )

                if not next_matches:
                    break

                # 最も近いタグを選択
                next_matches.sort()
                next_pos, next_type, next_match = next_matches[0]

                # 現在のブロックのコンテンツを抽出
                block_content = remaining_content[current_pos:next_pos].strip()

                # 前の条件にコンテンツを設定
                if conditions_and_content:
                    conditions_and_content[-1] = (
                        conditions_and_content[-1][0],
                        conditions_and_content[-1][1],
                        block_content,
                    )

                if next_type == "elif":
                    elif_condition = next_match.group(1).strip()
                    conditions_and_content.append(("elif", elif_condition, ""))
                    current_pos = next_pos + len(next_match.group(0))
                elif next_type == "else":
                    conditions_and_content.append(("else", "", ""))
                    current_pos = next_pos + len(next_match.group(0))
                elif next_type == "endif":
                    if (
                        len(conditions_and_content) > 0
                        and conditions_and_content[-1][2] == ""
                    ):
                        # 最後のブロックのコンテンツを設定
                        final_content = remaining_content[current_pos:next_pos].strip()
                        conditions_and_content[-1] = (
                            conditions_and_content[-1][0],
                            conditions_and_content[-1][1],
                            final_content,
                        )
                    break

            # 条件を順次評価
            for cond_type, condition, content in conditions_and_content:
                if cond_type == "else":
                    return content  # else 句は無条件で実行

                if self._evaluate_condition(condition, context):
                    return content

            return ""  # どの条件も満たされない場合

        except Exception as e:
            self.logger.error("Failed to parse complex conditional", error=str(e))
            return ""

    def _evaluate_condition(self, condition: str, context: dict[str, Any]) -> bool:
        """条件を評価（拡張版）"""
        try:
            condition = condition.strip()

            # NOT 演算子を最初に処理
            if condition.startswith("not "):
                return not self._evaluate_condition(condition[4:].strip(), context)

            # AND/OR 演算子を優先的に処理（複合条件）
            if " and " in condition:
                conditions = condition.split(" and ")
                return all(
                    self._evaluate_condition(cond.strip(), context)
                    for cond in conditions
                )

            if " or " in condition:
                conditions = condition.split(" or ")
                return any(
                    self._evaluate_condition(cond.strip(), context)
                    for cond in conditions
                )

            # 比較演算子をサポート
            if " == " in condition:
                left, right = condition.split(" == ", 1)
                left_val = self._get_condition_value(left.strip(), context)
                right_val = self._get_condition_value(right.strip(), context)
                return str(left_val) == str(right_val)

            if " != " in condition:
                left, right = condition.split(" != ", 1)
                left_val = self._get_condition_value(left.strip(), context)
                right_val = self._get_condition_value(right.strip(), context)
                return str(left_val) != str(right_val)

            if " >= " in condition:
                left, right = condition.split(" >= ", 1)
                left_val = self._get_condition_value(left.strip(), context)
                right_val = self._get_condition_value(right.strip(), context)
                try:
                    return float(left_val) >= float(right_val)
                except (ValueError, TypeError):
                    return False

            if " <= " in condition:
                left, right = condition.split(" <= ", 1)
                left_val = self._get_condition_value(left.strip(), context)
                right_val = self._get_condition_value(right.strip(), context)
                try:
                    return float(left_val) <= float(right_val)
                except (ValueError, TypeError):
                    return False

            if " > " in condition:
                left, right = condition.split(" > ", 1)
                left_val = self._get_condition_value(left.strip(), context)
                right_val = self._get_condition_value(right.strip(), context)
                try:
                    return float(left_val) > float(right_val)
                except (ValueError, TypeError):
                    return False

            if " < " in condition:
                left, right = condition.split(" < ", 1)
                left_val = self._get_condition_value(left.strip(), context)
                right_val = self._get_condition_value(right.strip(), context)
                try:
                    return float(left_val) < float(right_val)
                except (ValueError, TypeError):
                    return False

            # シンプルな真偽値評価
            condition_value = context.get(condition, False)
            return self._is_truthy(condition_value)

        except Exception as e:
            self.logger.error(
                "Failed to evaluate condition", condition=condition, error=str(e)
            )
            return False

    def _get_condition_value(self, expr: str, context: dict[str, Any]) -> Any:
        """条件式の値を取得"""
        expr = expr.strip()

        # 文字列リテラル（クォート付き）を最初にチェック
        if (expr.startswith('"') and expr.endswith('"')) or (
            expr.startswith("'") and expr.endswith("'")
        ):
            return expr[1:-1]

        # リテラル値の判定
        if expr in ["true", "True"]:
            return True
        if expr in ["false", "False"]:
            return False
        if expr in ["null", "None"]:
            return None

        # 数値の判定
        try:
            if "." in expr:
                return float(expr)
            return int(expr)
        except ValueError:
            pass

        # 変数の値を取得
        return context.get(expr, "")

    def _is_truthy(self, value: Any) -> bool:
        """値の真偽を判定"""
        if isinstance(value, bool):
            return value
        elif isinstance(value, str):
            return value.strip() != "" and value.lower() not in ["false", "0", "none"]
        elif isinstance(value, int | float):
            return value != 0
        elif isinstance(value, list):
            return len(value) > 0
        elif value is None:
            return False
        else:
            return bool(value)

    async def validate_template(self, template_name: str) -> dict[str, Any]:
        """テンプレートの構文を検証"""
        validation_result: dict[str, Any] = {
            "valid": True,
            "errors": list[str](),
            "warnings": list[str](),
            "metadata": dict[str, Any](),
        }

        try:
            template_content = await self.load_template(template_name)
            if not template_content:
                validation_result["valid"] = False
                validation_result["errors"].append(
                    f"Template '{template_name}' not found"
                )
                return validation_result

            # 基本的な構文チェック
            validation_result = self._validate_template_syntax(
                template_content, validation_result
            )

            # 循環参照チェック
            validation_result = await self._validate_inheritance_chain(
                template_name, validation_result
            )

            # 未使用変数の検出
            validation_result = self._validate_template_variables(
                template_content, validation_result
            )

            self.logger.info(
                "Template validation completed",
                template=template_name,
                valid=validation_result["valid"],
                error_count=len(validation_result["errors"]),
                warning_count=len(validation_result["warnings"]),
            )

            return validation_result

        except Exception as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Validation failed: {str(e)}")
            self.logger.error(
                "Template validation failed", template=template_name, error=str(e)
            )
            return validation_result

    def _validate_template_syntax(
        self, content: str, result: dict[str, Any]
    ) -> dict[str, Any]:
        """テンプレート構文の基本検証"""
        try:
            # 括弧の対応チェック
            open_brackets = content.count("{{")
            close_brackets = content.count("}}")
            if open_brackets != close_brackets:
                result["errors"].append(
                    f"Mismatched brackets: {open_brackets} opening, {close_brackets} closing"
                )
                result["valid"] = False

            # if-endif 対応チェック
            if_count = len(re.findall(r"\{\{\s*#if\s+", content))
            endif_count = len(re.findall(r"\{\{\s*/if\s*\}\}", content))
            if if_count != endif_count:
                result["errors"].append(
                    f"Mismatched if statements: {if_count} #if, {endif_count} /if"
                )
                result["valid"] = False

            # each-endeach 対応チェック
            each_count = len(re.findall(r"\{\{\s*#each\s+", content))
            endeach_count = len(re.findall(r"\{\{\s*/each\s*\}\}", content))
            if each_count != endeach_count:
                result["errors"].append(
                    f"Mismatched each statements: {each_count} #each, {endeach_count} /each"
                )
                result["valid"] = False

            # block-endblock 対応チェック
            block_count = len(re.findall(r"\{\{\s*block\s+", content))
            endblock_count = len(re.findall(r"\{\{\s*/block\s*\}\}", content))
            if block_count != endblock_count:
                result["errors"].append(
                    f"Mismatched block statements: {block_count} block, {endblock_count} /block"
                )
                result["valid"] = False

            # 不正な関数呼び出しの検出
            invalid_functions = re.findall(r"\{\{([a-zA-Z_]\w*)\([^)]*\)\}\}", content)
            known_functions = [
                "date_format",
                "tag_list",
                "truncate",
                "number_format",
                "conditional",
                "length",
                "default",
            ]
            for func in invalid_functions:
                if func not in known_functions:
                    result["warnings"].append(f"Unknown function: {func}")

            return result

        except Exception as e:
            result["errors"].append(f"Syntax validation failed: {str(e)}")
            result["valid"] = False
            return result

    async def _validate_inheritance_chain(
        self, template_name: str, result: dict[str, Any]
    ) -> dict[str, Any]:
        """テンプレート継承の循環参照チェック"""
        try:
            visited: set[str] = set()
            current: str | None = template_name

            while current:
                if current in visited:
                    result["errors"].append(
                        f"Circular inheritance detected in chain: {' -> '.join(visited)} -> {current}"
                    )
                    result["valid"] = False
                    break

                visited.add(current)

                # 親テンプレートを検索
                template_content = await self.load_template(current)
                if not template_content:
                    break

                extends_match = re.search(
                    r'\{\{extends\s+["\']([^"\']+)["\']\s*\}\}', template_content
                )
                current = extends_match.group(1) if extends_match else None

            return result

        except Exception as e:
            result["errors"].append(f"Inheritance validation failed: {str(e)}")
            result["valid"] = False
            return result

    def _validate_template_variables(
        self, content: str, result: dict[str, Any]
    ) -> dict[str, Any]:
        """テンプレート変数の検証"""
        try:
            # 使用されている変数を抽出
            variables = set()

            # 基本的なプレースホルダー
            basic_vars = re.findall(r"\{\{([a-zA-Z_]\w*)\}\}", content)
            variables.update(basic_vars)

            # 条件文の変数
            condition_vars = re.findall(r"\{\{\s*#if\s+([a-zA-Z_]\w*)", content)
            variables.update(condition_vars)

            # ループの変数
            loop_vars = re.findall(r"\{\{\s*#each\s+([a-zA-Z_]\w*)", content)
            variables.update(loop_vars)

            # 関数内の変数
            function_vars = re.findall(r"\{\{[a-zA-Z_]\w*\(([a-zA-Z_]\w*)", content)
            variables.update(function_vars)

            # 一般的に使用される変数リスト
            common_vars = {
                "current_date",
                "current_time",
                "date_iso",
                "date_ymd",
                "date_japanese",
                "time_hm",
                "content",
                "author_name",
                "channel_name",
                "ai_processed",
                "ai_summary",
                "ai_key_points",
                "ai_tags",
                "ai_category",
                "ai_confidence",
                "title",
                "filename",
            }

            # 未知の変数を特定
            unknown_vars = variables - common_vars
            if unknown_vars:
                result["warnings"].append(
                    f"Potentially undefined variables: {', '.join(sorted(unknown_vars))}"
                )

            result["metadata"]["variables_used"] = sorted(variables)
            result["metadata"]["unknown_variables"] = sorted(unknown_vars)

            return result

        except Exception as e:
            result["warnings"].append(f"Variable validation failed: {str(e)}")
            return result

    async def validate_all_templates(self) -> dict[str, dict[str, Any]]:
        """全テンプレートの検証"""
        results = {}

        try:
            templates = await self.list_available_templates()
            for template_name in templates:
                results[template_name] = await self.validate_template(template_name)

            # 全体統計
            total_templates = len(results)
            valid_templates = sum(1 for r in results.values() if r["valid"])

            self.logger.info(
                "All templates validated",
                total=total_templates,
                valid=valid_templates,
                invalid=total_templates - valid_templates,
            )

            return results

        except Exception as e:
            self.logger.error("Failed to validate all templates", error=str(e))
            return {"error": {"errors": [str(e)], "valid": False}}

    async def _process_each_sections(
        self, content: str, context: dict[str, Any]
    ) -> str:
        """繰り返しセクションを処理"""
        # よりシンプルで確実なパターンを使用
        pattern = r"\{\{\s*#each\s+(\w+)\s*\}\}(.*?)\{\{\s*/each\s*\}\}"

        def replace_each(match: re.Match[str]) -> str:
            items_key = match.group(1)
            section_content = match.group(2)

            self.logger.debug(f"Processing each section for key: {items_key}")
            self.logger.debug(f"Section content: {repr(section_content[:100])}")

            if items_key not in context:
                self.logger.debug(f"Items key '{items_key}' not found in context")
                return ""

            items = context[items_key]
            if not isinstance(items, list):
                self.logger.debug(f"Items '{items_key}' is not a list: {type(items)}")
                return ""

            if not items:
                self.logger.debug(f"Items list '{items_key}' is empty")
                return ""

            self.logger.debug(f"Processing {len(items)} items for {items_key}")

            results = []
            for i, item in enumerate(items):
                # 各アイテムに対して置換
                item_content = section_content

                # インデックスとアイテム全体の置換を先に行う
                item_content = re.sub(r"\{\{\s*@index\s*\}\}", str(i), item_content)
                item_content = re.sub(
                    r"\{\{\s*@item\s*\}\}", self._format_value(item), item_content
                )

                # アイテムが辞書の場合、個別のプロパティを置換
                if isinstance(item, dict):
                    for key, value in item.items():
                        item_pattern = r"\{\{\s*" + re.escape(key) + r"\s*\}\}"
                        item_content = re.sub(
                            item_pattern, self._format_value(value), item_content
                        )

                self.logger.debug(f"Item {i} content: {repr(item_content[:50])}")
                results.append(item_content)

            result = "\n".join(results)
            self.logger.debug(f"Final each result: {repr(result[:100])}")
            return result

        return str(re.sub(pattern, replace_each, content, flags=re.DOTALL))

    async def _process_custom_functions(
        self, content: str, context: dict[str, Any]
    ) -> str:
        """カスタム関数を処理（拡張版）"""

        # インクルード処理: {{include "template_name"}}
        content = await self._process_includes(content, context)

        # 日付フォーマット: {{date_format(date, format)}}
        def date_format_func(match: re.Match[str]) -> str:
            args_str = match.group(1)
            args = [arg.strip() for arg in args_str.split(",")]
            if len(args) >= 2:
                date_key = args[0].strip()
                format_str = args[1].strip().strip("\"'")

                if date_key in context and isinstance(context[date_key], datetime):
                    date_value = cast("datetime", context[date_key])
                    return date_value.strftime(format_str)
                else:
                    self.logger.debug(
                        f"Date key '{date_key}' not found or not datetime"
                    )
            return ""

        content = re.sub(r"\{\{date_format\((.*?)\)\}\}", date_format_func, content)

        # タグリスト: {{tag_list(tags)}}
        def tag_list_func(match: re.Match[str]) -> str:
            tags_key = match.group(1).strip()
            if tags_key in context and isinstance(context[tags_key], list):
                tags = context[tags_key]
                filtered_tags = [tag for tag in tags if tag]  # 空文字や None を除外
                return " ".join(f"#{tag}" for tag in filtered_tags)
            else:
                self.logger.debug(f"Tags key '{tags_key}' not found or not list")
            return ""

        content = re.sub(r"\{\{tag_list\((.*?)\)\}\}", tag_list_func, content)

        # 文字数制限: {{truncate(text, length)}}
        def truncate_func(match: re.Match[str]) -> str:
            args_str = match.group(1)
            args = [arg.strip() for arg in args_str.split(",")]
            if len(args) >= 2:
                text_key = args[0].strip()
                try:
                    length = int(args[1].strip())

                    if text_key in context:
                        text = str(context[text_key])
                        return text[:length] + "..." if len(text) > length else text
                    else:
                        self.logger.debug(f"Text key '{text_key}' not found in context")
                except ValueError:
                    self.logger.debug(f"Invalid length parameter: {args[1]}")
            return ""

        content = re.sub(r"\{\{truncate\((.*?)\)\}\}", truncate_func, content)

        # 新機能: 数値フォーマット {{number_format(number, format)}}
        def number_format_func(match: re.Match[str]) -> str:
            args_str = match.group(1)
            args = [arg.strip() for arg in args_str.split(",")]
            if len(args) >= 2:
                number_key = args[0].strip()
                format_str = args[1].strip().strip("\"'")

                if number_key in context:
                    try:
                        number = float(context[number_key])
                        if format_str == "currency":
                            return f"¥{number:,.0f}"
                        elif format_str == "percent":
                            return f"{number:.1%}"
                        elif format_str.startswith("decimal"):
                            decimals = (
                                int(format_str.split("_")[1])
                                if "_" in format_str
                                else 2
                            )
                            return f"{number:.{decimals}f}"
                        else:
                            return f"{number:,}"
                    except (ValueError, TypeError):
                        self.logger.debug(
                            f"Invalid number value for key '{number_key}'"
                        )
            return ""

        content = re.sub(r"\{\{number_format\((.*?)\)\}\}", number_format_func, content)

        # 新機能: 条件式 {{conditional(condition, true_value, false_value)}}
        def conditional_func(match: re.Match[str]) -> str:
            args_str = match.group(1)
            args = [arg.strip().strip("\"'") for arg in args_str.split(",")]
            if len(args) >= 3:
                condition = args[0]
                true_val = args[1]
                false_val = args[2]

                condition_result = context.get(condition, False)
                if isinstance(condition_result, bool):
                    return true_val if condition_result else false_val
                elif isinstance(condition_result, str):
                    return true_val if condition_result.strip() != "" else false_val
                else:
                    return true_val if condition_result else false_val
            return ""

        content = re.sub(r"\{\{conditional\((.*?)\)\}\}", conditional_func, content)

        # 新機能: 配列の長さ {{length(array)}}
        def length_func(match: re.Match[str]) -> str:
            array_key = match.group(1).strip()
            if array_key in context:
                value = context[array_key]
                if isinstance(value, list | dict | str):
                    return str(len(value))
            return "0"

        content = re.sub(r"\{\{length\((.*?)\)\}\}", length_func, content)

        # 新機能: デフォルト値 {{default(value, default)}}
        def default_func(match: re.Match[str]) -> str:
            args_str = match.group(1)
            args = [arg.strip().strip("\"'") for arg in args_str.split(",")]
            if len(args) >= 2:
                value_key = args[0]
                default_val = args[1]

                value = context.get(value_key)
                if value is None or (isinstance(value, str) and value.strip() == ""):
                    return default_val
                return str(value)
            return ""

        content = re.sub(r"\{\{default\((.*?)\)\}\}", default_func, content)

        return content

    async def _process_includes(self, content: str, context: dict[str, Any]) -> str:
        """インクルード処理"""
        include_pattern = r'\{\{include\s+["\']([^"\']+)["\']\s*\}\}'

        async def replace_include(match):
            include_name = match.group(1)
            try:
                include_content = await self.load_template(include_name)
                if include_content:
                    # インクルードしたテンプレートも同じコンテキストでレンダリング
                    return await self.render_template(include_content, context)
                else:
                    self.logger.warning(f"Include template not found: {include_name}")
                    return f"<!-- Include not found: {include_name} -->"
            except Exception as e:
                self.logger.error(
                    f"Failed to process include: {include_name}", error=str(e)
                )
                return f"<!-- Include error: {include_name} -->"

        # 非同期 replace 処理
        while True:
            match = re.search(include_pattern, content)
            if not match:
                break
            replacement = await replace_include(match)
            content = content[: match.start()] + replacement + content[match.end() :]

        return content

    def _clean_unprocessed_template_vars(self, content: str) -> str:
        """未処理のテンプレート変数を除去"""
        # 残存する条件文の開始タグと終了タグを除去
        content = re.sub(r"\{\{\s*#if\s+\w+\s*\}\}", "", content)
        content = re.sub(r"\{\{\s*/if\s*\}\}", "", content)

        # 残存する each 文のタグを除去
        content = re.sub(r"\{\{\s*#each\s+\w+\s*\}\}", "", content)
        content = re.sub(r"\{\{\s*/each\s*\}\}", "", content)

        # その他の未処理プレースホルダーを除去
        content = re.sub(r"\{\{\s*[^}]+\s*\}\}", "", content)

        # 連続する空行を整理（ 3 行以上の空行を 2 行に）
        content = re.sub(r"\n\s*\n\s*\n+", "\n\n", content)

        # 先頭の空行を除去
        content = content.lstrip("\n")

        # 末尾の余分な空行を除去（最大 2 行まで）
        content = re.sub(r"\n{3,}$", "\n\n", content)

        return content

    async def create_template_context(
        self,
        message_data: dict[str, Any],
        ai_result: AIProcessingResult | None = None,
        additional_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        テンプレート用のコンテキストを作成

        Args:
            message_data: メッセージデータ
            ai_result: AI 処理結果
            additional_context: 追加のコンテキスト

        Returns:
            テンプレート置換用コンテキスト
        """
        context = {}

        # 基本情報 - target_date があればそれを使用、なければ現在時刻
        target_date = (
            additional_context.get("target_date") if additional_context else None
        )
        current_time = target_date if target_date else datetime.now()

        context.update(
            {
                "current_date": current_time,
                "current_time": current_time,
                "date_iso": current_time.isoformat(),
                "date_ymd": current_time.strftime("%Y-%m-%d"),
                "date_japanese": current_time.strftime("%Y 年%m 月%d 日"),
                "time_hm": current_time.strftime("%H:%M"),
            }
        )

        # メッセージデータから抽出
        if message_data:
            metadata = message_data.get("metadata", {})
            basic_info = metadata.get("basic", {})
            content_info = metadata.get("content", {})
            timing_info = metadata.get("timing", {})
            attachments = metadata.get("attachments", [])

            # 🔧 FIX: 音声文字起こしが統合された cleaned_content を優先使用
            # cleaned_content があれば使用、なければ raw_content を使用
            raw_content = content_info.get("cleaned_content") or content_info.get(
                "raw_content", ""
            )

            # 🔧 DEBUG: コンテンツ抽出をデバッグ
            self.logger.info(
                f"🔧 DEBUG: Content extraction - cleaned_content: '{content_info.get('cleaned_content')}', "
                f"raw_content: '{content_info.get('raw_content')}', final raw_content: '{raw_content}'"
            )

            if isinstance(raw_content, dict):
                # content が dict 形式の場合、実際のテキストを抽出
                if "content" in raw_content:
                    raw_content = raw_content["content"]
                else:
                    raw_content = str(raw_content)

            # エスケープ文字の処理
            clean_content = self._clean_content_text(raw_content)

            # 🔧 DEBUG: 最終的なクリーンコンテンツをデバッグ
            self.logger.info(
                f"🔧 DEBUG: Final clean_content: '{clean_content}' (length: {len(clean_content)})"
            )

            # 作成者名の取得 (display_name または name)
            author_info = basic_info.get("author", {})
            author_name = author_info.get("display_name") or author_info.get("name", "")

            context.update(
                {
                    "message_id": basic_info.get("id"),
                    "content": clean_content,
                    "content_length": len(clean_content),
                    "author_name": author_name,
                    "author_username": author_info.get("username", ""),
                    "channel_name": basic_info.get("channel", {}).get("name", ""),
                    "attachments": attachments,
                    "attachment_count": len(attachments),
                    "has_attachments": len(attachments) > 0,
                    "message_created_at": timing_info.get("created_at", {}),
                }
            )

        # AI 処理結果から抽出 (YAML safe values)
        if ai_result:
            # AI 要約の適切な処理
            ai_summary = ""
            if ai_result.summary and ai_result.summary.summary:
                ai_summary = self._clean_content_text(ai_result.summary.summary)
                # YAML エラーを防ぐため改行や特殊文字を処理
                ai_summary = ai_summary.replace("\n", " ").replace("\r", " ").strip()

            # タグをYAML配列形式で準備
            ai_tags = ai_result.tags.tags if ai_result.tags else []

            # キーポイントもYAML safe に
            ai_key_points = (
                [
                    self._clean_content_text(point)
                    .replace("\n", " ")
                    .replace("\r", " ")
                    .strip()
                    for point in ai_result.summary.key_points
                ]
                if ai_result.summary and ai_result.summary.key_points
                else []
            )

            context.update(
                {
                    "ai_processed": "true",  # YAML boolean として文字列で出力
                    "ai_summary": f'"{ai_summary}"',  # クォートで囲んで安全に
                    "ai_key_points": ai_key_points,
                    "ai_tags": ai_tags,
                    "ai_category": (
                        ai_result.category.category.value if ai_result.category else ""
                    ),
                    "ai_confidence": (
                        ai_result.category.confidence_score
                        if ai_result.category
                        else 0.0
                    ),
                    "ai_reasoning": (
                        f'"{self._clean_content_text(ai_result.category.reasoning).replace("\n", " ").replace("\r", " ").strip()}"'
                        if ai_result.category and ai_result.category.reasoning
                        else '""'
                    ),
                    "processing_time": (
                        ai_result.processing_time_ms
                        if hasattr(ai_result, "processing_time_ms")
                        else 0
                    ),
                }
            )
        else:
            context.update(
                {
                    "ai_processed": "false",  # YAML boolean として文字列で出力
                    "ai_summary": '""',
                    "ai_key_points": [],
                    "ai_tags": [],
                    "ai_category": "",
                    "ai_confidence": 0.0,
                    "ai_reasoning": '""',
                    "processing_time": 0,
                }
            )

        # 追加のコンテキスト
        if additional_context:
            context.update(additional_context)

        return context

    def _clean_content_text(self, text: Any) -> str:
        """コンテンツテキストを適切に清潔化する"""
        if not text:
            return ""

        # 入力が辞書やオブジェクトの場合、文字列表現から実際のテキストを抽出
        if isinstance(text, dict):
            if "content" in text:
                text = str(text["content"])
            else:
                # dict 全体を str() したものではなく、空文字列を返す
                self.logger.warning(
                    "Unexpected dict format in content", dict_keys=list(text.keys())
                )
                return ""
        elif not isinstance(text, str):
            text = str(text)

        # dict 文字列形式のパターンを検出してクリーンアップ
        if text.startswith("{'content':") or text.startswith('{"content":'):
            # dict 形式の文字列から実際の content を抽出する試み
            try:
                import ast

                dict_obj = ast.literal_eval(text)
                if isinstance(dict_obj, dict) and "content" in dict_obj:
                    text = str(dict_obj["content"])
                else:
                    self.logger.warning("Could not extract content from dict string")
                    return ""
            except (ValueError, SyntaxError) as e:
                self.logger.warning("Failed to parse dict string", error=str(e))
                return ""

        # エスケープされた改行文字を実際の改行に変換
        text = text.replace("\\\\n", "\n")
        text = text.replace("\\n", "\n")
        text = text.replace("\\\\t", "\t")
        text = text.replace("\\t", "\t")
        text = text.replace("\\\\r", "\r")
        text = text.replace("\\r", "\r")

        # その他のエスケープ文字を処理
        text = text.replace('\\\\"', '"')
        text = text.replace("\\'", "'")
        text = text.replace("\\\\", "\\")

        # 余分な空白を整理（ただし改行は保持）
        lines = text.split("\n")
        cleaned_lines = [line.strip() for line in lines]
        text = "\n".join(cleaned_lines).strip()

        return text

    def _determine_folder_from_ai_category(
        self, ai_result: AIProcessingResult | None
    ) -> str:
        """
        AI 分類結果に基づいて Obsidian フォルダを決定

        Args:
            ai_result: AI 処理結果

        Returns:
            フォルダパス文字列
        """
        if not ai_result or not ai_result.category:
            self.logger.debug("No AI result or category, using INBOX")
            return VaultFolder.INBOX.value

        category = ai_result.category.category

        # デバッグ情報を詳細にログ出力
        self.logger.info(
            "Processing AI category for folder determination",
            ai_category_type=type(category).__name__,
            ai_category_value=category.value
            if hasattr(category, "value")
            else str(category),
            ai_category_raw=repr(category),
            confidence=ai_result.category.confidence_score,
        )

        # AI 分類カテゴリから Obsidian フォルダへのマッピング
        category_to_folder = {
            ProcessingCategory.FINANCE: VaultFolder.FINANCE,
            ProcessingCategory.TASKS: VaultFolder.TASKS,
            ProcessingCategory.HEALTH: VaultFolder.HEALTH,
            ProcessingCategory.LEARNING: VaultFolder.KNOWLEDGE,  # LEARNING は KNOWLEDGE フォルダに
            ProcessingCategory.PROJECT: VaultFolder.PROJECTS,
            ProcessingCategory.WORK: VaultFolder.PROJECTS,  # 仕事関連はプロジェクトフォルダに
            ProcessingCategory.IDEA: VaultFolder.IDEAS,
            ProcessingCategory.LIFE: VaultFolder.DAILY_NOTES,  # 生活関連は DAILY_NOTES に
            ProcessingCategory.OTHER: VaultFolder.INBOX,
        }

        folder = category_to_folder.get(category, VaultFolder.INBOX)

        self.logger.info(
            "Determined folder from AI category",
            ai_category=category.value if hasattr(category, "value") else str(category),
            obsidian_folder=folder.value,
            confidence=ai_result.category.confidence_score,
        )

        return folder.value

    async def generate_note_from_template(
        self,
        template_name: str,
        message_data: dict[str, Any],
        ai_result: AIProcessingResult | None = None,
        additional_context: dict[str, Any] | None = None,
    ) -> ObsidianNote | None:
        """
        テンプレートからノートを生成

        Args:
            template_name: テンプレート名
            message_data: メッセージデータ
            ai_result: AI 処理結果
            additional_context: 追加のコンテキスト

        Returns:
            生成された ObsidianNote 、失敗した場合は None
        """
        try:
            # テンプレートを読み込み
            template_content = await self.load_template(template_name)
            if not template_content:
                self.logger.warning(
                    "Template not found, creating default template",
                    template_name=template_name,
                    template_path=str(self.template_path),
                )
                # デフォルトテンプレートを作成
                await self._create_default_template(template_name)
                template_content = await self.load_template(template_name)
                if not template_content:
                    self.logger.error("Failed to create default template")
                    return None

            # AI 分類結果からターゲットフォルダを事前に決定
            target_folder = self._determine_folder_from_ai_category(ai_result)

            # コンテキストを作成
            context = await self.create_template_context(
                message_data, ai_result, additional_context
            )

            # AI 分類によるフォルダ情報をコンテキストに追加
            context["target_folder"] = target_folder

            self.logger.info(
                "🔧 DEBUG: Template processing start",
                template_name=template_name,
                target_folder=target_folder,
                ai_category=ai_result.category.category.value
                if ai_result and ai_result.category
                else None,
                context_target_folder=context.get("target_folder"),
            )

            # テンプレートをレンダリング
            rendered_content = await self.render_template(template_content, context)

            # フロントマターと本文を分離
            frontmatter_dict, content = self._parse_template_content(rendered_content)

            self.logger.info(
                "🔧 DEBUG: After template parsing",
                frontmatter_keys=list(frontmatter_dict.keys()),
                obsidian_folder_in_frontmatter=frontmatter_dict.get("obsidian_folder"),
                target_folder_in_context=context.get("target_folder"),
            )

            # NoteFrontmatter オブジェクトを作成
            # 必要なフィールドが不足している場合はデフォルト値を設定
            self._prepare_frontmatter_dict(frontmatter_dict, context)

            self.logger.info(
                "🔧 DEBUG: After prepare frontmatter dict",
                final_obsidian_folder=frontmatter_dict.get("obsidian_folder"),
            )

            frontmatter = NoteFrontmatter(**frontmatter_dict)

            # ファイル名とパスを生成（メッセージ固有の一意名）
            if "message_id" in context:
                # メッセージ固有のファイル名を生成
                from datetime import datetime, timedelta, timezone

                from src.obsidian.models import NoteFilename

                # 日本時間でタイムスタンプ生成
                jst = timezone(timedelta(hours=9))
                timestamp = datetime.now(jst)
                ai_category = (
                    ai_result.category.category.value
                    if ai_result and ai_result.category
                    else None
                )
                title = context.get("content", "")[
                    :30
                ]  # 最初の 30 文字をタイトルに使用

                filename = NoteFilename.generate_message_note_filename(
                    timestamp=timestamp, category=ai_category, title=title
                )
            else:
                # 従来のファイル名生成
                filename = context.get(
                    "filename", f"{context['date_ymd']}-{template_name}.md"
                )
                if not filename.endswith(".md"):
                    filename += ".md"

            # カスタムファイルパスが指定されている場合はそれを使用
            if additional_context and "file_path" in additional_context:
                file_path = additional_context["file_path"]
            else:
                # AI 分類結果に基づいてフォルダを決定
                file_path = self.vault_path / target_folder / filename

            # ObsidianNote オブジェクトを作成（日本時間使用）
            jst = timezone(timedelta(hours=9))
            current_jst = datetime.now(jst)

            note = ObsidianNote(
                filename=filename,
                file_path=file_path,
                frontmatter=frontmatter,
                content=content,
                created_at=current_jst,
                modified_at=current_jst,
            )

            self.logger.info(
                "Note generated from template",
                template=template_name,
                filename=filename,
                target_folder=target_folder if ai_result else "INBOX",
                ai_category=ai_result.category.category.value
                if ai_result and ai_result.category
                else None,
            )

            return note

        except Exception as e:
            self.logger.error(
                "Failed to generate note from template",
                template=template_name,
                error=str(e),
                exc_info=True,
            )
            return None

    async def generate_message_note(
        self,
        message_data: dict[str, Any],
        ai_result: AIProcessingResult | None = None,
        vault_folder: VaultFolder | None = None,
        template_name: str = "message_note",
    ) -> ObsidianNote | None:
        """
        Discord メッセージ用ノートを生成（ templates.py の MessageNoteTemplate.generate_note と同等機能）

        Args:
            message_data: メッセージメタデータ
            ai_result: AI 処理結果
            vault_folder: 保存先フォルダ（指定されない場合は自動決定）
            template_name: 使用するテンプレート名

        Returns:
            生成された ObsidianNote 、失敗した場合は None
        """
        try:
            # メッセージ情報の抽出
            metadata = message_data.get("metadata", {})
            content_info = metadata.get("content", {})
            timing_info = metadata.get("timing", {})

            # AI 処理結果の抽出
            ai_category = None
            if ai_result and ai_result.category:
                ai_category = ai_result.category.category.value

            # タイムスタンプの処理
            created_at = datetime.fromisoformat(
                timing_info.get("created_at", {}).get("iso", datetime.now().isoformat())
            )

            # フォルダの決定
            if not vault_folder:
                if ai_result and ai_result.category:
                    from src.obsidian.organizer import FolderMapping

                    vault_folder = FolderMapping.get_folder_for_category(
                        ai_result.category.category.value
                    )
                else:
                    # デフォルトで受信箱に送る
                    vault_folder = VaultFolder.INBOX

            # タイトルの生成
            ai_summary = None
            if ai_result and ai_result.summary:
                ai_summary = ai_result.summary.summary

            title = self._extract_title_from_content(
                content_info.get("raw_content", ""), ai_summary
            )

            # ファイル名の生成
            from src.obsidian.models import NoteFilename

            filename = NoteFilename.generate_message_note_filename(
                timestamp=created_at, category=ai_category, title=title
            )

            # 追加のコンテキスト
            additional_context = {
                "filename": filename,
                "vault_folder": vault_folder.value,
                "title": title,
                "created_at": created_at,
            }

            # テンプレートから生成
            note = await self.generate_note_from_template(
                template_name, message_data, ai_result, additional_context
            )

            if note:
                # ファイルパスを正しく設定
                note.file_path = self.vault_path / vault_folder.value / filename
                note.filename = filename
                note.created_at = created_at

            return note

        except Exception as e:
            self.logger.error(
                "Failed to generate message note",
                error=str(e),
                exc_info=True,
            )
            return None

    async def generate_daily_note(
        self,
        date: datetime,
        daily_stats: dict[str, Any] | None = None,
        template_name: str = "daily_note",
    ) -> ObsidianNote | None:
        """
        日次ノートを生成（ templates.py の DailyNoteTemplate.generate_note と同等機能）

        Args:
            date: 対象日
            daily_stats: 日次統計情報
            template_name: 使用するテンプレート名

        Returns:
            生成された ObsidianNote 、失敗した場合は None
        """
        try:
            # ファイル名とパス
            from src.obsidian.models import NoteFilename

            filename = NoteFilename.generate_daily_note_filename(date)
            year = date.strftime("%Y")
            month = date.strftime("%m-%B")
            file_path = (
                self.vault_path
                / VaultFolder.DAILY_NOTES.value
                / year
                / month
                / filename
            )

            # 追加コンテキスト
            additional_context = {
                "filename": filename,
                "file_path": file_path,  # 正しいパスを明示的に指定
                "vault_folder": VaultFolder.DAILY_NOTES.value,
                "target_date": date,
                "daily_stats": daily_stats or {},
                "total_messages": daily_stats.get("total_messages", 0)
                if daily_stats
                else 0,
                "processed_messages": daily_stats.get("processed_messages", 0)
                if daily_stats
                else 0,
                "ai_processing_time_total": daily_stats.get(
                    "ai_processing_time_total", 0
                )
                if daily_stats
                else 0,
                "categories": daily_stats.get("categories", {}) if daily_stats else {},
            }

            # 日次統計用のダミーメッセージデータ
            message_data = {
                "metadata": {
                    "basic": {},
                    "content": {
                        "raw_content": f"Daily note for {date.strftime('%Y-%m-%d')}"
                    },
                    "timing": {"created_at": {"iso": date.isoformat()}},
                }
            }

            # テンプレートから生成
            note = await self.generate_note_from_template(
                template_name, message_data, None, additional_context
            )

            if note:
                # ファイルパスが正しく設定されていることを確認
                note.file_path = file_path
                note.filename = filename
                note.created_at = date

            return note

        except Exception as e:
            self.logger.error(
                "Failed to generate daily note",
                error=str(e),
                exc_info=True,
            )
            return None

    def _extract_title_from_content(
        self, content: str, ai_summary: str | None = None
    ) -> str:
        """コンテンツからタイトルを抽出（ templates.py から移植）"""

        # AI 要約がある場合はそれを基にタイトル生成
        if ai_summary:
            # エスケープ文字を適切に処理
            clean_summary = self._clean_content_text(ai_summary)
            # 要約の最初の行をタイトルとして使用
            first_line = clean_summary.split("\n")[0].strip()
            if first_line:
                # 不要な記号を除去
                title = first_line.lstrip("・-*").strip()
                if len(title) > 5:  # 十分な長さがある場合
                    return title[:50]  # 最大 50 文字

        # コンテンツから抽出
        if content:
            # エスケープ文字を適切に処理
            clean_content = self._clean_content_text(content)
            if clean_content:
                # 最初の行または最初の 50 文字を使用
                first_line = clean_content.split("\n")[0].strip()
                if first_line:
                    return first_line[:50]

        # デフォルトタイトル
        return "Discord Memo"

    def _parse_template_content(self, content: str) -> tuple[dict[str, Any], str]:
        """テンプレート内容からフロントマターと本文を分離"""
        frontmatter_dict: dict[str, Any] = {}
        main_content = content

        # YAML フロントマターの検出と解析
        frontmatter_pattern = r"^---\n(.*?)\n---\n(.*)"
        match = re.match(frontmatter_pattern, content, re.DOTALL)

        if match:
            try:
                import yaml

                frontmatter_yaml = match.group(1)
                main_content = match.group(2)

                # YAML safe loading with error handling
                frontmatter_dict = yaml.safe_load(frontmatter_yaml) or {}

                # Post-process YAML values for safety
                frontmatter_dict = self._sanitize_yaml_values(frontmatter_dict)

            except ImportError:
                self.logger.warning(
                    "PyYAML not available, skipping frontmatter parsing"
                )
            except yaml.YAMLError as e:
                self.logger.warning(
                    "YAML parsing error",
                    error=str(e),
                    yaml_content=frontmatter_yaml[:200],
                )
                # Try to fix common YAML issues
                try:
                    fixed_yaml = self._fix_common_yaml_issues(frontmatter_yaml)
                    frontmatter_dict = yaml.safe_load(fixed_yaml) or {}
                    frontmatter_dict = self._sanitize_yaml_values(frontmatter_dict)
                except Exception:
                    self.logger.error(
                        "Failed to fix YAML issues, using empty frontmatter"
                    )
            except Exception as e:
                self.logger.warning("Failed to parse YAML frontmatter", error=str(e))

        # 🔧 FIX: 自動生成メッセージを除去
        main_content = self._remove_bot_attribution_messages(main_content)

        return frontmatter_dict, main_content

    def _remove_bot_attribution_messages(self, content: str) -> str:
        """自動生成メッセージを除去する"""
        import re

        # 日本語と英語の自動生成メッセージを削除
        patterns_to_remove = [
            r"\*Created by Discord-Obsidian Memo Bot\*[。\s]*",
            r"^---\s*\*Created by Discord-Obsidian Memo Bot\*\s*$",
            r"^\*Created by Discord-Obsidian Memo Bot\*\s*$",
            # 日本語パターンを追加
            r"\*このノートは Discord-Obsidian Memo Bot によって自動生成されました\*[。\s]*",
            r"^---\s*\*このノートは Discord-Obsidian Memo Bot によって自動生成されました\*\s*$",
            r"^\*このノートは Discord-Obsidian Memo Bot によって自動生成されました\*\s*$",
            r".*Discord-Obsidian.*Memo.*Bot.*自動生成.*",
            r".*自動生成.*Discord-Obsidian.*Memo.*Bot.*",
        ]

        for pattern in patterns_to_remove:
            content = re.sub(pattern, "", content, flags=re.MULTILINE | re.IGNORECASE)

        # 余分な改行を整理
        content = re.sub(r"\n\n\n+", "\n\n", content)
        content = content.strip()

        return content

    def _sanitize_yaml_values(self, data: dict[str, Any]) -> dict[str, Any]:
        """YAML値を安全な形式に変換"""
        sanitized: dict[str, Any] = {}
        for key, value in data.items():
            if isinstance(value, bool):
                # Python boolean を YAML boolean 文字列に変換
                sanitized[key] = "true" if value else "false"
            elif isinstance(value, str):
                # 文字列の安全性チェック
                if value.startswith('"') and value.endswith('"'):
                    sanitized[key] = value  # 既にクォートされている
                elif any(
                    char in value
                    for char in ["\n", "\r", ":", "[", "]", "{", "}", "&", "*"]
                ):
                    sanitized[key] = (
                        f'"{value.replace(chr(34), chr(92) + chr(34))}"'  # エスケープしてクォート
                    )
                else:
                    sanitized[key] = value
            elif isinstance(value, list):
                # リストを YAML 配列形式に確実に変換
                sanitized[key] = [
                    str(item) if not isinstance(item, int | float) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        return sanitized

    def _fix_common_yaml_issues(self, yaml_content: str) -> str:
        """よくある YAML 構文エラーを修正"""
        lines = yaml_content.split("\n")
        fixed_lines = []

        for line in lines:
            # Python boolean を YAML boolean に変換
            line = re.sub(r":\s*True\s*$", ": true", line)
            line = re.sub(r":\s*False\s*$", ": false", line)

            # Python リスト形式を YAML 配列形式に変換
            if re.match(r"^\s*\w+:\s*\[.*\]$", line):
                key_match = re.match(r"^(\s*)(\w+):\s*\[(.*)\]$", line)
                if key_match:
                    indent, key, content = key_match.groups()
                    if content.strip():
                        # リスト項目を抽出してYAML配列形式に変換
                        items = [
                            item.strip().strip("'\"")
                            for item in content.split(",")
                            if item.strip()
                        ]
                        fixed_lines.append(f"{indent}{key}:")
                        for item in items:
                            fixed_lines.append(f"{indent}  - {item}")
                    else:
                        fixed_lines.append(f"{indent}{key}: []")
                else:
                    fixed_lines.append(line)
            else:
                # マルチライン文字列の処理
                if ": *" in line and not line.strip().endswith("*"):
                    # 不正なエイリアス参照を修正
                    line = re.sub(r":\s*\*\s*$", ': ""', line)
                elif ": &" in line and not re.search(r"&\w+", line):
                    # 不正なエイリアス定義を修正
                    line = re.sub(r":\s*&\s*$", ': ""', line)

                # 空の複数行文字列を修正 (ai_summary: """" -> ai_summary: "")
                line = re.sub(r':\s*""""\s*$', ': ""', line)

                # 不正なクォート文字を修正
                line = re.sub(r':\s*"""([^"]*)"""\s*$', r': "\1"', line)

                fixed_lines.append(line)

        return "\n".join(fixed_lines)

    def _prepare_frontmatter_dict(
        self, frontmatter_dict: dict[str, Any], context: dict[str, Any]
    ) -> None:
        """フロントマターディクショナリを NoteFrontmatter モデルに適合するよう準備"""
        # デバッグ用ログ（ error レベルで確実に表示）
        self.logger.error(
            "=== FRONTMATTER DEBUG START ===",
            existing_obsidian_folder=frontmatter_dict.get("obsidian_folder"),
            target_folder_from_context=context.get("target_folder"),
            frontmatter_keys=list(frontmatter_dict.keys()),
            context_keys=list(context.keys()),
        )

        # AI 分類による target_folder が利用可能な場合は常にそれを優先
        if "target_folder" in context and context["target_folder"]:
            previous_value = frontmatter_dict.get("obsidian_folder", "None")
            frontmatter_dict["obsidian_folder"] = context["target_folder"]
            self.logger.error(
                "=== AI FOLDER OVERRIDE APPLIED ===",
                target_folder=context["target_folder"],
                previous_value=previous_value,
                final_value=frontmatter_dict["obsidian_folder"],
            )
        elif "obsidian_folder" not in frontmatter_dict:
            # note type に基づいてフォルダを決定（フォールバック）
            note_type = frontmatter_dict.get("type", "general")
            folder_mapping = {
                "idea": VaultFolder.IDEAS.value,
                "task": VaultFolder.TASKS.value,
                "meeting": VaultFolder.PROJECTS.value,
                "daily": VaultFolder.INBOX.value,  # daily_note テンプレートでも AI 分類を優先
            }
            frontmatter_dict["obsidian_folder"] = folder_mapping.get(
                note_type, VaultFolder.INBOX.value
            )
            self.logger.error(
                "=== USING FALLBACK FOLDER MAPPING ===",
                note_type=note_type,
                obsidian_folder=frontmatter_dict["obsidian_folder"],
            )
        else:
            self.logger.error(
                "=== OBSIDIAN FOLDER ALREADY EXISTS - NO OVERRIDE ===",
                existing_value=frontmatter_dict["obsidian_folder"],
                target_folder_available=bool(context.get("target_folder")),
                target_folder_value=context.get("target_folder"),
            )

        self.logger.error(
            "=== FRONTMATTER DEBUG END ===",
            final_obsidian_folder=frontmatter_dict.get("obsidian_folder"),
        )

    async def ensure_template_directory(self) -> bool:
        """テンプレートディレクトリが存在することを確認"""
        try:
            self.template_path.mkdir(parents=True, exist_ok=True)
            self.logger.info("Template directory ensured", path=str(self.template_path))
            return True
        except Exception as e:
            self.logger.error(
                "Failed to create template directory",
                path=str(self.template_path),
                error=str(e),
                exc_info=True,
            )
            return False

    async def list_available_templates(self) -> list[str]:
        """利用可能なテンプレート一覧を取得"""
        try:
            if not self.template_path.exists():
                await self.ensure_template_directory()
                return []

            templates = []
            for template_file in self.template_path.glob("*.md"):
                templates.append(template_file.stem)

            self.logger.debug("Available templates listed", count=len(templates))
            return sorted(templates)

        except Exception as e:
            self.logger.error("Failed to list templates", error=str(e), exc_info=True)
            return []

    async def create_default_templates(self) -> bool:
        """デフォルトテンプレートを作成"""
        try:
            await self.ensure_template_directory()

            # デフォルトテンプレートの定義
            default_templates = {
                "daily_note": self._get_daily_note_template(),
                "idea_note": self._get_idea_note_template(),
                "meeting_note": self._get_meeting_note_template(),
                "task_note": self._get_task_note_template(),
            }

            for template_name, template_content in default_templates.items():
                template_file = self.template_path / f"{template_name}.md"

                # 既存のテンプレートは上書きしない
                if template_file.exists():
                    continue

                async with aiofiles.open(template_file, "w", encoding="utf-8") as f:
                    await f.write(template_content)

                self.logger.info("Default template created", template=template_name)

            return True

        except Exception as e:
            self.logger.error(
                "Failed to create default templates", error=str(e), exc_info=True
            )
            return False

    async def create_advanced_templates(self) -> bool:
        """高度な機能を使用したサンプルテンプレートを作成"""
        try:
            await self.ensure_template_directory()

            # サンプルテンプレート群
            advanced_templates = {
                "base_note": self._get_base_note_template(),
                "message_note_advanced": self._get_advanced_message_template(),
                "project_status": self._get_project_status_template(),
                "weekly_review": self._get_weekly_review_template(),
            }

            for template_name, template_content in advanced_templates.items():
                template_file = self.template_path / f"{template_name}.md"

                # 既存のテンプレートは上書きしない
                if template_file.exists():
                    continue

                async with aiofiles.open(template_file, "w", encoding="utf-8") as f:
                    await f.write(template_content)

                self.logger.info("Advanced template created", template=template_name)

            return True

        except Exception as e:
            self.logger.error(
                "Failed to create advanced templates", error=str(e), exc_info=True
            )
            return False

    def _get_base_note_template(self) -> str:
        """基本ノートテンプレート（継承用ベース）"""
        return """---
type: {{default(note_type, "general")}}
created: {{date_iso}}
modified: {{date_iso}}
tags:
  - {{default(note_type, "general")}}
{{#if ai_tags}}
{{#each ai_tags}}
  - {{@item}}
{{/each}}
{{/if}}
author: {{default(author_name, "System")}}
---

{{block "title"}}
# 📝 {{default(title, "新しいノート")}}
{{/block}}

{{block "metadata"}}
## 📋 基本情報

- **作成日**: {{date_format(current_date, "%Y 年%m 月%d 日 %H:%M")}}
- **作成者**: {{default(author_name, "不明")}}
{{#if channel_name}}
- **チャンネル**: #{{channel_name}}
{{/if}}
{{/block}}

{{block "content"}}
## 📝 内容

{{default(content, "内容を入力してください。")}}
{{/block}}

{{block "footer"}}
---
*最終更新: {{date_format(current_date, "%Y-%m-%d %H:%M")}}*
{{/block}}"""

    def _get_advanced_message_template(self) -> str:
        """高度なメッセージテンプレート"""
        return """{{extends "base_note"}}

{{block "title"}}
# 💬 {{conditional(ai_summary, truncate(ai_summary, 50), "Discord メッセージ")}}
{{/block}}

{{block "content"}}
{{#if ai_processed}}
## 🤖 AI 分析

**要約**: {{ai_summary}}

{{#if ai_key_points and length(ai_key_points) > 0}}
### 重要なポイント
{{#each ai_key_points}}
- {{@item}}
{{/each}}
{{/if}}

**カテゴリ**: {{ai_category}}
**信頼度**: {{number_format(ai_confidence, "percent")}}

{{#if ai_confidence < 0.7}}
> ⚠️ 注意: AI 分析の信頼度が低いです。内容を確認してください。
{{/if}}

{{/if}}

## 📝 元のメッセージ

{{content}}

{{#if has_attachments}}
## 📎 添付ファイル

{{#each attachments}}
- [{{@item.name}}]({{@item.url}}) ({{@item.size}} bytes)
{{/each}}
{{/if}}

## 🔍 メタデータ

- **メッセージ ID**: `{{message_id}}`
- **文字数**: {{number_format(content_length, "decimal_0")}}文字
{{#if processing_time > 0}}
- **処理時間**: {{number_format(processing_time, "decimal_0")}}ms
{{/if}}
{{/block}}"""

    def _get_project_status_template(self) -> str:
        """プロジェクト状況テンプレート"""
        return """---
type: project
status: {{default(project_status, "active")}}
priority: {{default(priority, "medium")}}
created: {{date_iso}}
due_date: {{default(due_date, "")}}
tags:
  - project
  - {{default(project_status, "active")}}
---

# 🚀 {{default(project_name, "プロジェクト名")}}

## 📊 プロジェクト概要

**ステータス**: {{conditional(project_status == "completed", "✅ 完了", conditional(project_status == "active", "🔄 進行中", "⏸️ 保留"))}}
**優先度**: {{conditional(priority == "high", "🔴 高", conditional(priority == "low", "🟢 低", "🟡 中"))}}

{{#if due_date}}
**期限**: {{date_format(due_date, "%Y 年%m 月%d 日")}}
{{/if}}

## 🎯 目標・成果物

{{default(objectives, "目標を設定してください。")}}

## 📅 マイルストーン

{{#if milestones and length(milestones) > 0}}
{{#each milestones}}
- {{conditional(@item.completed, "✅", "⏳")}} {{@item.title}} {{#if @item.due_date}}(期限: {{date_format(@item.due_date, "%m/%d")}}){{/if}}
{{/each}}
{{#else}}
- [ ] マイルストーン 1
- [ ] マイルストーン 2
{{/if}}

## 📝 進捗メモ

{{default(progress_notes, "進捗状況を記録してください。")}}

## ⚠️ 課題・リスク

{{#if risks and length(risks) > 0}}
{{#each risks}}
- **{{@item.level}}**: {{@item.description}}
{{/each}}
{{#else}}
現在、特定の課題・リスクはありません。
{{/if}}

## 📈 次のアクション

- [ ] アクション項目 1
- [ ] アクション項目 2

---
*更新日: {{date_format(current_date, "%Y-%m-%d")}}*"""

    def _get_weekly_review_template(self) -> str:
        """週次レビューテンプレート"""
        return """---
type: review
period: weekly
week_start: {{date_format(current_date, "%Y-%m-%d")}}
created: {{date_iso}}
tags:
  - review
  - weekly
  - {{date_format(current_date, "%Y-W%U")}}
---

# 📊 週次レビュー - {{date_format(current_date, "%Y 年第%U 週")}}

## 📅 レビュー期間

**開始**: {{date_format(current_date, "%Y 年%m 月%d 日")}}
**終了**: {{date_format(current_date, "%Y 年%m 月%d 日")}}

## 🎯 今週の成果

### 完了したタスク
{{#if completed_tasks and length(completed_tasks) > 0}}
{{#each completed_tasks}}
- ✅ {{@item}}
{{/each}}
{{#else}}
- 完了したタスクを記録してください
{{/if}}

### 主要な成果・達成
{{default(achievements, "今週の主要な成果を記録してください。")}}

## 📈 数値データ

{{#if weekly_stats}}
- **処理メッセージ数**: {{number_format(weekly_stats.total_messages, "decimal_0")}}件
- **アクティブ日数**: {{weekly_stats.active_days}}/7 日
- **平均日次処理数**: {{number_format(weekly_stats.avg_daily_messages, "decimal_1")}}件
{{/if}}

## 🤔 振り返り

### うまくいったこと
{{default(what_went_well, "うまくいったことを記録してください。")}}

### 改善できること
{{default(what_to_improve, "改善できることを記録してください。")}}

### 学んだこと
{{default(lessons_learned, "今週学んだことを記録してください。")}}

## 🎯 来週の計画

### 優先タスク
- [ ] 高優先度タスク 1
- [ ] 高優先度タスク 2
- [ ] 高優先度タスク 3

### 注力分野
{{default(focus_areas, "来週の注力分野を設定してください。")}}

## 📊 カテゴリ別分析

{{#if category_stats and length(category_stats) > 0}}
{{#each category_stats}}
- **{{@index}}**: {{number_format(@item, "decimal_0")}}件
{{/each}}
{{/if}}

---
*レビュー作成日: {{date_format(current_date, "%Y 年%m 月%d 日")}}*"""

    def _get_daily_note_template(self) -> str:
        """デイリーノートテンプレート（改良版）"""
        return """---
type: daily
date: {{date_ymd}}
tags:
  - daily
  - {{date_format(current_date, "%Y-%m")}}
ai_processed: {{ai_processed}}
{{#if ai_processed}}
ai_summary: {{ai_summary}}
ai_category: {{ai_category}}
ai_confidence: {{ai_confidence}}
{{/if}}
created: {{date_iso}}
modified: {{date_iso}}
---

# 📅 {{date_format(current_date, "%Y 年%m 月%d 日")}}の記録

{{#if content}}
## 💭 内容

{{content}}

{{#elif ai_summary}}
## 💭 要約

{{ai_summary}}

{{#else}}
## 💭 今日の出来事

今日の重要な出来事や気づきを記録する。

{{/if}}

{{#if ai_processed}}
## 🤖 AI 分析結果

**カテゴリ**: {{ai_category}} {{#if ai_confidence}}(信頼度: {{number_format(ai_confidence, "percent")}}){{/if}}

{{#if ai_key_points and length(ai_key_points) > 0}}
### 🎯 主要ポイント
{{#each ai_key_points}}
- {{@item}}
{{/each}}
{{/if}}

{{#if ai_reasoning}}
**分析根拠**: {{ai_reasoning}}
{{/if}}

{{#else}}
## 📝 今日のタスク

- [ ] 重要なタスク 1
- [ ] 重要なタスク 2

## 🎯 今日の目標

## 💡 学んだこと・気づき

{{/if}}

## 📊 統計情報

{{#if daily_stats}}
- **処理メッセージ数**: {{default(total_messages, "0")}}件
- **AI 処理メッセージ数**: {{default(processed_messages, "0")}}件
{{#if ai_processing_time_total > 0}}
- **AI 処理時間**: {{number_format(ai_processing_time_total, "decimal_2")}}ms
{{/if}}

{{#if categories and length(categories) > 0}}
### カテゴリ別分析
{{#each categories}}
- **{{@index}}**: {{@item}}件
{{/each}}
{{/if}}
{{/if}}

## 🔗 関連リンク

{{#if channel_name}}
- **Discord チャンネル**: #{{channel_name}}
{{/if}}
- **昨日**: [[{{date_format(current_date, "%Y-%m-%d", -1)}}]]
- **明日**: [[{{date_format(current_date, "%Y-%m-%d", 1)}}]]

{{#if ai_tags and length(ai_tags) > 0}}
## 🏷️ タグ

{{tag_list(ai_tags)}}
{{/if}}"""

    def _get_idea_note_template(self) -> str:
        """アイデアノートテンプレート"""
        return """---
type: idea
created: {{date_iso}}
tags:
  - idea
{{#if ai_category}}
  - {{ai_category}}
{{/if}}
{{#if ai_tags}}
{{#each ai_tags}}
  - {{@item}}
{{/each}}
{{/if}}
ai_processed: {{ai_processed}}
{{#if ai_processed}}
ai_summary: {{ai_summary}}
ai_confidence: {{ai_confidence}}
{{/if}}
---

# 💡 {{#if ai_summary}}{{truncate(ai_summary, 50)}}{{else}}新しいアイデア{{/if}}

{{#if content}}
## 📝 内容

{{content}}

{{else}}
## 📝 内容

アイデアの内容をここに記録する。

{{/if}}
{{#if ai_processed}}
## 🤖 AI 分析

**要約**: {{ai_summary}}

{{#if ai_key_points}}
### 主要ポイント
{{#each ai_key_points}}
- {{@item}}
{{/each}}
{{/if}}

**分類**: {{ai_category}} (信頼度: {{ai_confidence}})

{{#if ai_reasoning}}
**根拠**: {{ai_reasoning}}
{{/if}}
{{/if}}

## 🔄 次のアクション

- [ ] アイデアを詳細化する
- [ ] 実現可能性を検討する
- [ ] 関連する情報を収集する

{{#if ai_tags}}
## 🏷️ タグ

{{tag_list(ai_tags)}}

{{/if}}
## 📅 作成日時

{{date_format(current_date, "%Y 年%m 月%d 日 %H:%M")}}"""

    def _get_meeting_note_template(self) -> str:
        """会議ノートテンプレート"""
        return """---
type: meeting
date: {{date_ymd}}
tags:
  - meeting
  - {{ai_category}}
ai_processed: {{ai_processed}}
participants: []
---

# 🏢 会議メモ - {{date_format(current_date, "%Y-%m-%d")}}

## ℹ️ 基本情報

- **日時**: {{date_format(current_date, "%Y 年%m 月%d 日 %H:%M")}}
- **参加者**:
- **場所**:

## 📋 議題

{{#if ai_key_points}}
{{#each ai_key_points}}
1. {{@item}}
{{/each}}
{{else}}
1. 議題項目 1
2. 議題項目 2
{{/if}}

## 💬 討議内容

{{#if content}}
{{content}}
{{else}}
会議の内容をここに記録する。
{{/if}}

{{#if ai_processed}}
## 🤖 AI 要約

{{ai_summary}}

**カテゴリ**: {{ai_category}} ({{ai_confidence}})
{{/if}}

## ✅ アクションアイテム

- [ ] TODO 項目 1
- [ ] TODO 項目 2

## 📝 次回までの課題

-

## 🔗 関連資料

-
"""

    def _get_task_note_template(self) -> str:
        """タスクノートテンプレート"""
        return """---
type: task
created: {{date_iso}}
status: pending
priority: medium
tags:
  - task
  - {{ai_category}}
{{#if ai_tags}}
{{#each ai_tags}}
  - {{@item}}
{{/each}}
{{/if}}
due_date:
ai_processed: {{ai_processed}}
---

# ✅ {{#if ai_summary}}{{truncate(ai_summary, 60)}}{{else}}新しいタスク{{/if}}

## 📋 タスク詳細

{{#if content}}
{{content}}
{{else}}
タスクの詳細をここに記録する。
{{/if}}

{{#if ai_processed}}
## 🤖 AI 分析

**要約**: {{ai_summary}}

{{#if ai_key_points}}
### アクションポイント
{{#each ai_key_points}}
- [ ] {{@item}}
{{/each}}
{{/if}}

**カテゴリ**: {{ai_category}} (信頼度: {{ai_confidence}})
{{/if}}

## ⏰ スケジュール

- **作成日**: {{date_format(current_date, "%Y-%m-%d")}}
- **期限**: 未設定
- **見積時間**:

## 📊 進捗

- [ ] 準備段階
- [ ] 実行中
- [ ] レビュー
- [ ] 完了

## 💭 メモ

作業中のメモや気づきをここに記録する。

## 🔗 関連リンク

-
"""

    async def _create_default_template(self, template_name: str) -> None:
        """Create a default template file if it doesn't exist."""
        try:
            # テンプレートディレクトリの作成
            self.template_path.mkdir(parents=True, exist_ok=True)

            # デフォルトテンプレートコンテンツ
            default_content = """---
title: "{{title}}"
tags: [{{#if tags}}{{#each tags}}"{{this}}"{{#unless @last}}, {{/unless}}{{/each}}{{else}}"memo"{{/if}}]
created: "{{date_format(current_date, '%Y-%m-%d %H:%M:%S')}}"
author: "{{author_name}}"
obsidian_folder: "{{target_folder}}"
---

# {{title}}

{{content}}

{{#if ai_summary}}
## 📋 要約
{{ai_summary}}
{{/if}}

{{#if ai_tags}}
## 🏷️ タグ
{{#each ai_tags}}- {{this}}
{{/each}}
{{/if}}

---
作成日: {{date_format(current_date, "%Y-%m-%d %H:%M")}}
"""

            template_file = self.template_path / f"{template_name}.md"
            async with aiofiles.open(template_file, "w", encoding="utf-8") as f:
                await f.write(default_content)

            self.logger.info(
                "Default template created",
                template_name=template_name,
                file_path=str(template_file),
            )

        except Exception as e:
            self.logger.error(
                "Failed to create default template",
                template_name=template_name,
                error=str(e),
            )
