"""Core template processor with variable replacement"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any


class TemplateProcessor:
    """テンプレート変数置換とレンダリング処理"""

    async def render_template(
        self, template: str, context: dict[str, Any]
    ) -> tuple[str, Any]:
        """テンプレートをレンダリングし、フロントマターとコンテンツを分離"""
        frontmatter_match = re.match(
            r"^---\s*\n(.*?)\n---\s*\n(.*)$", template, re.DOTALL
        )

        if frontmatter_match:
            frontmatter_content = frontmatter_match.group(1)
            body_content = frontmatter_match.group(2)

            compiled_frontmatter = await self._compile_template(
                frontmatter_content, context
            )
            compiled_body = await self._compile_template(body_content, context)

            return compiled_body, compiled_frontmatter
        else:
            compiled_content = await self._compile_template(template, context)
            return compiled_content, None

    async def _compile_template(self, template: str, context: dict[str, Any]) -> str:
        """テンプレートコンパイル"""
        compiled = template

        # Process template inheritance first (extends/block)
        compiled = await self._process_template_inheritance(compiled, context)

        # Basic variable replacement
        for key, value in context.items():
            if isinstance(value, str | int | float | bool):
                pattern = r"\{\{\s*" + re.escape(key) + r"\s*\}\}"
                compiled = re.sub(pattern, str(value), compiled)

        compiled = await self._process_conditional_sections(compiled, context)
        compiled = await self._process_each_sections(compiled, context)
        compiled = await self._process_custom_functions(compiled, context)
        compiled = await self._process_includes(compiled, context)

        return compiled

    async def _process_conditional_sections(
        self, content: str, context: dict[str, Any]
    ) -> str:
        """条件分岐セクションを処理 (if/elif/else をサポート)"""
        # First, handle complex if-elif-else structures by parsing them manually
        content = self._process_complex_conditionals(content, context)
        
        # Then handle simple if-else patterns
        simple_patterns = [
            r"\{\{\s*#if\s+(.+?)\s*\}\}(.*?)\{\{\s*/if\s*\}\}",  # {{#if}} {{/if}}
            r"\{\{\s*if\s+(.+?)\s*\}\}(.*?)\{\{\s*endif\s*\}\}",  # {{if}} {{endif}}
        ]
        
        for pattern in simple_patterns:
            content = re.sub(
                pattern,
                lambda m: self._evaluate_condition(m.group(1), m.group(2), context),
                content,
                flags=re.DOTALL,
            )
        return content

    def _process_complex_conditionals(self, content: str, context: dict[str, Any]) -> str:
        """複雑な if-elif-else 構造を処理"""
        # Find all if-elif-else blocks and process them
        pattern = r'\{\{\s*#if\s+.+?\s*\}\}.*?\{\{\s*/if\s*\}\}'
        
        def process_block(match):
            block = match.group(0)
            return self._parse_and_evaluate_block(block, context)
        
        return re.sub(pattern, process_block, content, flags=re.DOTALL)
    
    def _parse_and_evaluate_block(self, block: str, context: dict[str, Any]) -> str:
        """単一の if-elif-else ブロックを解析して評価"""
        # Split into tokens to handle the structure properly
        tokens = re.split(r'(\{\{[^}]+\}\})', block)
        
        conditions = []
        contents = []
        current_content: list[str] = []
        state = "none"  # none, if, elif, else
        
        for token in tokens:
            token = token.strip()
            if not token:
                continue
                
            # Check for condition tokens
            if_match = re.match(r'\{\{\s*#if\s+(.+?)\s*\}\}', token)
            elif_match = re.match(r'\{\{\s*#elif\s+(.+?)\s*\}\}', token)
            else_match = re.match(r'\{\{\s*#else\s*\}\}', token)
            endif_match = re.match(r'\{\{\s*/if\s*\}\}', token)
            
            if if_match:
                conditions.append(if_match.group(1))
                if current_content:
                    contents.append(''.join(current_content))
                    current_content = []
                state = "if"
            elif elif_match:
                conditions.append(elif_match.group(1))
                if current_content:
                    contents.append(''.join(current_content))
                    current_content = []
                state = "elif"
            elif else_match:
                conditions.append("true")  # else always matches if reached
                if current_content:
                    contents.append(''.join(current_content))
                    current_content = []
                state = "else"
            elif endif_match:
                if current_content:
                    contents.append(''.join(current_content))
                break
            else:
                if state in ["if", "elif", "else"]:
                    current_content.append(token)
        
        # Evaluate conditions in order
        for i, condition in enumerate(conditions):
            if i < len(contents):
                try:
                    if condition == "true":  # else clause
                        return contents[i].strip()
                    # Use complex condition evaluation for all conditions
                    elif self._evaluate_complex_condition(condition, context):
                        return contents[i].strip()
                except Exception as e:
                    # Log debug info for troubleshooting
                    import structlog
                    logger = structlog.get_logger()
                    logger.debug(f"Condition evaluation failed: {condition}, error: {e}")
                    continue
        
        return ""

    async def _process_each_sections(
        self, content: str, context: dict[str, Any]
    ) -> str:
        """each セクション（リスト処理）を処理"""
        # Support both handlebars-style {{#each items}} and {{each item in items}} syntax
        patterns = [
            (r"\{\{\s*#each\s+(\w+)\s*\}\}(.*?)\{\{\s*/each\s*\}\}", True),  # {{#each items}} handlebars-style
            (r"\{\{\s*each\s+(\w+)\s+in\s+(\w+)\s*\}\}(.*?)\{\{\s*endeach\s*\}\}", False)  # {{each item in items}}
        ]

        for pattern, is_handlebars in patterns:
            if is_handlebars:
                def process_handlebars_each(match):
                    list_name = match.group(1)
                    template = match.group(2)

                    if list_name not in context:
                        return ""

                    items = context[list_name]
                    if not isinstance(items, list):
                        return ""

                    result = []
                    for index, item in enumerate(items):
                        item_context = context.copy()
                        if isinstance(item, dict):
                            item_context.update(item)
                        else:
                            item_context["@item"] = item
                        item_context["@index"] = index
                        
                        rendered = template
                        # Process template variables
                        for key, value in item_context.items():
                            if isinstance(value, str | int | float | bool):
                                rendered = re.sub(
                                    r"\{\{\s*" + re.escape(key) + r"\s*\}\}",
                                    str(value),
                                    rendered,
                                )
                        result.append(rendered)

                    return "\n".join(result)
                
                content = re.sub(pattern, process_handlebars_each, content, flags=re.DOTALL)
            else:
                def process_each(match):
                    var_name = match.group(1)
                    list_name = match.group(2)
                    template = match.group(3)

                    if list_name not in context:
                        return ""

                    items = context[list_name]
                    if not isinstance(items, list):
                        return ""

                    result = []
                    for item in items:
                        item_context = context.copy()
                        item_context[var_name] = item
                        rendered = template
                        for key, value in item_context.items():
                            if isinstance(value, str | int | float | bool):
                                rendered = re.sub(
                                    r"\{\{\s*" + re.escape(key) + r"\s*\}\}",
                                    str(value),
                                    rendered,
                                )
                        result.append(rendered)

                    return "\n".join(result)
                
                content = re.sub(pattern, process_each, content, flags=re.DOTALL)

        return content

    def _evaluate_condition(
        self, condition: str, content: str, context: dict[str, Any]
    ) -> str:
        """条件を評価"""
        condition = condition.strip()
        
        # Support complex conditions with "and", "or", "not"
        try:
            result = self._evaluate_complex_condition(condition, context)
            return content if result else ""
        except Exception:
            # Fallback to simple condition evaluation
            pass

        if " == " in condition:
            left, right = condition.split(" == ", 1)
            left_val = context.get(left.strip())
            right_val = right.strip().strip('"\'')
            return content if str(left_val) == right_val else ""
        elif " != " in condition:
            left, right = condition.split(" != ", 1)
            left_val = context.get(left.strip())
            right_val = right.strip().strip('"\'')
            return content if str(left_val) != right_val else ""
        elif " >= " in condition:
            left, right = condition.split(" >= ", 1)
            left_val = context.get(left.strip())
            try:
                return (
                    content
                    if isinstance(left_val, int | float)
                    and left_val >= float(right.strip())
                    else ""
                )
            except ValueError:
                return ""
        elif " <= " in condition:
            left, right = condition.split(" <= ", 1)
            left_val = context.get(left.strip())
            try:
                return (
                    content
                    if isinstance(left_val, int | float)
                    and left_val <= float(right.strip())
                    else ""
                )
            except ValueError:
                return ""
        elif " > " in condition:
            left, right = condition.split(" > ", 1)
            left_val = context.get(left.strip())
            try:
                return (
                    content
                    if isinstance(left_val, int | float)
                    and left_val > float(right.strip())
                    else ""
                )
            except ValueError:
                return ""
        elif " < " in condition:
            left, right = condition.split(" < ", 1)
            left_val = context.get(left.strip())
            try:
                return (
                    content
                    if isinstance(left_val, int | float)
                    and left_val < float(right.strip())
                    else ""
                )
            except ValueError:
                return ""
        else:
            # Support for legacy "#if" syntax
            condition = condition.replace("#", "").strip()
            var_value = context.get(condition)
            if isinstance(var_value, bool):
                return content if var_value else ""
            elif isinstance(var_value, int | float):
                return content if var_value != 0 else ""
            elif isinstance(var_value, str):
                return content if var_value else ""
            elif isinstance(var_value, list):
                return content if len(var_value) > 0 else ""
            else:
                return content if var_value else ""

    def _evaluate_complex_condition(self, condition: str, context: dict[str, Any]) -> bool:
        """複雑な条件式を評価 (and, or, not をサポート)"""
        # Handle "not" operator
        if condition.startswith("not "):
            inner_condition = condition[4:].strip()
            return not self._evaluate_complex_condition(inner_condition, context)
            
        # Handle "and" operator
        if " and " in condition:
            parts = condition.split(" and ", 1)
            left_result = self._evaluate_complex_condition(parts[0].strip(), context)
            right_result = self._evaluate_complex_condition(parts[1].strip(), context)
            return left_result and right_result
            
        # Handle "or" operator
        if " or " in condition:
            parts = condition.split(" or ", 1)
            left_result = self._evaluate_complex_condition(parts[0].strip(), context)
            right_result = self._evaluate_complex_condition(parts[1].strip(), context)
            return left_result or right_result
            
        # Handle simple conditions
        return self._evaluate_simple_condition(condition, context)
    
    def _evaluate_simple_condition(self, condition: str, context: dict[str, Any]) -> bool:
        """単純な条件式を評価"""
        condition = condition.strip()
        
        if " == " in condition:
            left, right = condition.split(" == ", 1)
            left_val = context.get(left.strip())
            right_val_str = right.strip().strip('"\'')
            try:
                right_val_float = float(right_val_str)
                return left_val == right_val_float
            except ValueError:
                return str(left_val) == right_val_str
                
        elif " != " in condition:
            left, right = condition.split(" != ", 1)
            left_val = context.get(left.strip())
            right_val_str = right.strip().strip('"\'')
            try:
                right_val_float = float(right_val_str)
                return left_val != right_val_float
            except ValueError:
                return str(left_val) != right_val_str
                
        elif " >= " in condition:
            left, right = condition.split(" >= ", 1)
            left_val = context.get(left.strip())
            try:
                return isinstance(left_val, int | float) and left_val >= float(right.strip())
            except (ValueError, TypeError):
                return False
                
        elif " <= " in condition:
            left, right = condition.split(" <= ", 1)
            left_val = context.get(left.strip())
            try:
                return isinstance(left_val, int | float) and left_val <= float(right.strip())
            except (ValueError, TypeError):
                return False
                
        elif " > " in condition:
            left, right = condition.split(" > ", 1)
            left_val = context.get(left.strip())
            try:
                return isinstance(left_val, int | float) and left_val > float(right.strip())
            except (ValueError, TypeError):
                return False
                
        elif " < " in condition:
            left, right = condition.split(" < ", 1)
            left_val = context.get(left.strip())
            try:
                return isinstance(left_val, int | float) and left_val < float(right.strip())
            except (ValueError, TypeError):
                return False
        else:
            # Simple variable evaluation
            var_value = context.get(condition)
            if isinstance(var_value, bool):
                return var_value
            elif isinstance(var_value, int | float):
                return var_value != 0
            elif isinstance(var_value, str):
                return bool(var_value)
            elif isinstance(var_value, list):
                return len(var_value) > 0
            else:
                return bool(var_value)

    async def _process_custom_functions(
        self, content: str, context: dict[str, Any]
    ) -> str:
        """カスタム関数を処理"""
        function_pattern = r"\{\{\s*(\w+)\((.*?)\)\s*\}\}"

        def process_function(match):
            func_name = match.group(1)
            args = match.group(2)

            if func_name == "tag_list":
                if args in context and isinstance(context[args], list):
                    tags = context[args]
                    return " ".join(f"#{tag}" for tag in tags)
                return ""
            elif func_name == "date_format":
                parts = [p.strip().strip('"\'') for p in args.split(",")]
                if len(parts) >= 2:
                    var_name = parts[0]
                    format_str = parts[1]
                    if var_name in context:
                        value = context[var_name]
                        if isinstance(value, datetime):
                            return value.strftime(format_str)
                return args
            elif func_name == "now":
                if args:
                    try:
                        return datetime.now().strftime(args.strip('"\''))
                    except ValueError:
                        return datetime.now().isoformat()
                return datetime.now().isoformat()
            elif func_name == "today":
                if args:
                    try:
                        return datetime.now().strftime(args.strip('"\''))
                    except ValueError:
                        return datetime.now().strftime("%Y-%m-%d")
                return datetime.now().strftime("%Y-%m-%d")
            elif func_name == "truncate":
                parts = args.split(",")
                if len(parts) >= 2:
                    var_name = parts[0].strip()
                    try:
                        max_len = int(parts[1].strip())
                        if var_name in context:
                            text = str(context[var_name])
                            return (
                                text[:max_len] + "..." if len(text) > max_len else text
                            )
                    except ValueError:
                        pass
                return args
            elif func_name == "number_format":
                parts = args.split(",")
                if len(parts) >= 2:
                    var_name = parts[0].strip()
                    format_type = parts[1].strip().strip('"\'').strip()
                    if var_name in context:
                        value = context[var_name]
                        if format_type == "currency" and isinstance(value, int | float):
                            return f"¥{value:,.0f}"
                        elif format_type == "percent" and isinstance(value, int | float):
                            return f"{value * 100:.1f}%"
                return args
            elif func_name == "length":
                if args in context:
                    value = context[args]
                    if hasattr(value, "__len__"):
                        return str(len(value))
                return "0"
            elif func_name == "default":
                parts = args.split(",")
                if len(parts) >= 2:
                    var_name = parts[0].strip()
                    default_val = parts[1].strip().strip('"\'').strip()
                    value = context.get(var_name, default_val)
                    if value is None:
                        return default_val
                    return str(value)
                return args
            elif func_name == "conditional":
                parts = args.split(",")
                if len(parts) >= 3:
                    var_name = parts[0].strip()
                    true_val = parts[1].strip().strip('"\'').strip()
                    false_val = parts[2].strip().strip('"\'').strip()
                    condition_result = context.get(var_name, False)
                    return true_val if condition_result else false_val
                return args

            return match.group(0)

        return re.sub(function_pattern, process_function, content)

    async def _process_includes(self, content: str, context: dict[str, Any]) -> str:
        """インクルード処理"""
        include_pattern = r"\{\{\s*include\s+['\"](.+?)['\"]\s*\}\}"

        async def replace_include(template_name: str) -> str:
            return f"<!-- Include: {template_name} -->"

        def sync_replace(match):
            return f"<!-- Include: {match.group(1)} -->"

        return re.sub(include_pattern, sync_replace, content)

    async def _process_template_inheritance(
        self, content: str, context: dict[str, Any]
    ) -> str:
        """テンプレート継承処理 (extends/block)"""
        # Check if this template extends another
        extends_match = re.match(r'^\s*\{\{\s*extends\s+["\'](.+?)["\']\s*\}\}', content.strip())
        if not extends_match:
            return content
            
        parent_template_name = extends_match.group(1)
        child_content = content[extends_match.end():].strip()
        
        # Load parent template
        try:
            from .loader import TemplateLoader
            loader = TemplateLoader(Path(context.get('vault_path', '.')))  
            parent_content = await loader.load_template(parent_template_name)
        except Exception:
            # If parent template not found, return child content without inheritance
            return child_content
        
        # Extract blocks from child template
        child_blocks = self._extract_blocks(child_content)
        
        # Process parent template with child blocks
        return self._merge_parent_with_blocks(parent_content, child_blocks)
    
    def _extract_blocks(self, content: str) -> dict[str, str]:
        """子テンプレートからブロックを抽出"""
        blocks = {}
        
        # Find all block definitions: {{block "name"}} content {{/block}}
        block_pattern = r'\{\{\s*block\s+["\'](\w+)["\']\s*\}\}(.*?)\{\{\s*/block\s*\}\}'
        
        for match in re.finditer(block_pattern, content, re.DOTALL):
            block_name = match.group(1)
            block_content = match.group(2).strip()
            blocks[block_name] = block_content
            
        return blocks
    
    def _merge_parent_with_blocks(self, parent_content: str, child_blocks: dict[str, str]) -> str:
        """親テンプレートと子ブロックをマージ"""
        def replace_block(match):
            block_name = match.group(1)
            default_content = match.group(2).strip()
            
            # Use child block content if available, otherwise use default
            return child_blocks.get(block_name, default_content)
        
        # Replace block definitions with child content
        block_pattern = r'\{\{\s*block\s+["\'](\w+)["\']\s*\}\}(.*?)\{\{\s*/block\s*\}\}'
        return re.sub(block_pattern, replace_block, parent_content, flags=re.DOTALL)


class ConditionalProcessor:
    """条件分岐処理専用クラス"""

    async def process(self, content: str, context: dict[str, Any]) -> str:
        """条件分岐を処理"""
        # Support both {{#if condition}} {{/if}} and {{if condition}} {{endif}} syntax
        patterns = [
            r"\{\{\s*#if\s+(.+?)\s*\}\}(.*?)\{\{\s*/if\s*\}\}",  # {{#if}} {{/if}}
            r"\{\{\s*if\s+(.+?)\s*\}\}(.*?)\{\{\s*endif\s*\}\}",  # {{if}} {{endif}}
        ]
        
        for pattern in patterns:
            content = re.sub(
                pattern,
                lambda m: self._evaluate_condition(m.group(1), m.group(2), context),
                content,
                flags=re.DOTALL,
            )
        return content

    def _evaluate_condition(
        self, condition: str, content: str, context: dict[str, Any]
    ) -> str:
        """条件を評価（ TemplateProcessor と同じロジック）"""
        condition = condition.strip().replace("#", "").strip()
        var_value = context.get(condition)
        if isinstance(var_value, bool):
            return content if var_value else ""
        elif isinstance(var_value, int | float):
            return content if var_value != 0 else ""
        elif isinstance(var_value, str):
            return content if var_value else ""
        elif isinstance(var_value, list):
            return content if len(var_value) > 0 else ""
        else:
            return content if var_value else ""


class CustomFunctionProcessor:
    """カスタム関数処理クラス"""

    async def process(self, content: str, context: dict[str, Any]) -> str:
        """カスタム関数を処理"""
        function_pattern = r"\{\{\s*(\w+)\((.*?)\)\s*\}\}"

        def process_function(match):
            func_name = match.group(1)
            args = match.group(2)

            if func_name == "now":
                if args:
                    try:
                        return datetime.now().strftime(args.strip('"\''))
                    except ValueError:
                        return datetime.now().isoformat()
                return datetime.now().isoformat()
            elif func_name == "today":
                if args:
                    try:
                        return datetime.now().strftime(args.strip('"\''))
                    except ValueError:
                        return datetime.now().strftime("%Y-%m-%d")
                return datetime.now().strftime("%Y-%m-%d")
            elif func_name == "upper":
                if args in context:
                    return str(context[args]).upper()
                return args.upper()
            elif func_name == "lower":
                if args in context:
                    return str(context[args]).lower()
                return args.lower()
            elif func_name == "capitalize":
                if args in context:
                    return str(context[args]).capitalize()
                return args.capitalize()
            elif func_name == "length":
                if args in context:
                    value = context[args]
                    if hasattr(value, "__len__"):
                        return str(len(value))
                return "0"
            elif func_name == "join":
                parts = args.split(",")
                if len(parts) >= 2:
                    list_name = parts[0].strip()
                    separator = parts[1].strip().strip('"\'')
                    if list_name in context and isinstance(context[list_name], list):
                        return separator.join(str(x) for x in context[list_name])
                return ""
            elif func_name == "default":
                parts = args.split(",")
                if len(parts) >= 2:
                    var_name = parts[0].strip()
                    default_val = parts[1].strip().strip('"\'')
                    return str(context.get(var_name, default_val))
                return args
            elif func_name == "truncate":
                parts = args.split(",")
                if len(parts) >= 2:
                    var_name = parts[0].strip()
                    try:
                        max_len = int(parts[1].strip())
                        if var_name in context:
                            text = str(context[var_name])
                            return (
                                text[:max_len] + "..." if len(text) > max_len else text
                            )
                    except ValueError:
                        pass
                return args
            elif func_name == "date_format":
                parts = args.split(",")
                if len(parts) >= 2:
                    var_name = parts[0].strip()
                    format_str = parts[1].strip().strip('"\'')
                    if var_name in context:
                        value = context[var_name]
                        if isinstance(value, datetime):
                            return value.strftime(format_str)
                return args

            return match.group(0)

        return re.sub(function_pattern, process_function, content)