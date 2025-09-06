"""Template validation and error handling"""

import re
from typing import Any

from src.utils.logger import logger


class TemplateValidator:
    """テンプレート検証とエラーチェック"""

    async def validate_template(
        self, template: str, context: dict[str, Any]
    ) -> tuple[bool, list[str]]:
        """テンプレートを検証し、エラーリストを返す"""
        errors = []

        # 基本的な構文チェック
        if not isinstance(template, str):
            errors.append("Template must be a string")
            return False, errors

        # ブロック構文のペアチェック
        block_errors = self._check_block_pairs(template)
        errors.extend(block_errors)

        # 変数の存在チェック
        variable_errors = self._check_variables(template, context)
        errors.extend(variable_errors)

        # 条件文の構文チェック
        condition_errors = self._check_conditions(template)
        errors.extend(condition_errors)

        # each 文の構文チェック
        each_errors = self._check_each_statements(template)
        errors.extend(each_errors)

        # カスタム関数の構文チェック
        function_errors = self._check_custom_functions(template)
        errors.extend(function_errors)

        is_valid = len(errors) == 0
        if not is_valid:
            logger.warning(f"Template validation failed: {errors}")

        return is_valid, errors

    def _check_block_pairs(self, template: str) -> list[str]:
        """ブロック構文のペアをチェック"""
        errors: list[str] = []

        # if-endif pairs (support both {{ if }} and {{#if}} syntax)
        if_count = len(re.findall(r"\{\{\s*#?if\s+", template))
        endif_count = len(re.findall(r"\{\{\s*/?endif\s*\}\}", template)) + len(
            re.findall(r"\{\{\s*/if\s*\}\}", template)
        )
        if if_count != endif_count:
            errors.append(
                f"Mismatched if/endif blocks: {if_count} if, {endif_count} endif"
            )

        # each-endeach pairs
        each_count = len(re.findall(r"\{\{\s*each\s+", template))
        endeach_count = len(re.findall(r"\{\{\s*endeach\s*\}\}", template)) + len(
            re.findall(r"\{\{\s*/each\s*\}\}", template)
        )
        if each_count != endeach_count:
            errors.append(
                f"Mismatched each/endeach blocks: {each_count} each, {endeach_count} endeach"
            )

        return errors

    def _check_variables(self, template: str, context: dict[str, Any]) -> list[str]:
        """変数の存在をチェック"""
        errors = []

        # Control flow keywords that should be ignored
        control_keywords = {
            "if",
            "endif",
            "else",
            "elif",
            "each",
            "endeach",
            "block",
            "extends",
            "include",
            "with",
            "endwith",
        }

        # Extract loop variables from each statements
        loop_variables = set()
        each_pattern = r"\{\{\s*each\s+(\w+)\s+in\s+\w+\s*\}\}"
        for match in re.finditer(each_pattern, template):
            loop_variables.add(match.group(1))

        # Find all variables but exclude complex expressions and control keywords
        variable_pattern = r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}"

        variables = re.findall(variable_pattern, template)
        for var in variables:
            # Skip control flow keywords
            if var in control_keywords:
                continue

            # Skip loop variables (defined within each loops)
            if var in loop_variables:
                continue

            # Skip variables that are part of complex expressions (with operators, pipes, etc.)
            if var not in context:
                errors.append(f"Undefined variable: {var}")

        return errors

    def _check_conditions(self, template: str) -> list[str]:
        """条件文の構文をチェック"""
        errors = []
        condition_pattern = r"\{\{\s*if\s+(.+?)\s*\}\}"

        conditions = re.findall(condition_pattern, template)
        for condition in conditions:
            if not self._is_valid_condition(condition):
                errors.append(f"Invalid condition syntax: {condition}")

        return errors

    def _check_each_statements(self, template: str) -> list[str]:
        """each 文の構文をチェック"""
        errors = []
        each_pattern = r"\{\{\s*each\s+(\w+)\s+in\s+(\w+)\s*\}\}"

        each_matches = re.findall(each_pattern, template)
        for var_name, list_name in each_matches:
            if not var_name.isidentifier():
                errors.append(f"Invalid variable name in each: {var_name}")
            if not list_name.isidentifier():
                errors.append(f"Invalid list name in each: {list_name}")

        return errors

    def _check_custom_functions(self, template: str) -> list[str]:
        """カスタム関数の構文をチェック"""
        errors = []
        function_pattern = r"\{\{\s*(\w+)\((.*?)\)\s*\}\}"

        functions = re.findall(function_pattern, template)
        valid_functions = {
            "now",
            "today",
            "upper",
            "lower",
            "capitalize",
            "length",
            "join",
            "default",
            "truncate",
            "date_format",
            "tag_list",
            "number_format",
            "conditional",
        }

        for func_name, _args in functions:
            if func_name not in valid_functions:
                errors.append(f"Unknown function: {func_name}")

        return errors

    def _is_valid_condition(self, condition: str) -> bool:
        """条件の妥当性をチェック"""
        condition = condition.strip()

        # Simple variable check
        if re.match(r"^\w+$", condition):
            return True

        # Comparison operators
        comparison_operators = [" == ", " != ", " > ", " < ", " >= ", " <= "]
        for op in comparison_operators:
            if op in condition:
                parts = condition.split(op, 1)
                if len(parts) == 2 and all(part.strip() for part in parts):
                    return True

        return False
