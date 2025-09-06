"""Template loader for managing template files"""

import re
from pathlib import Path

import aiofiles

from src.utils.logger import logger


class TemplateLoader:
    """テンプレートの読み込みと管理を担当"""

    def __init__(self, vault_path: Path):
        self.vault_path = Path(vault_path)
        self.template_path = self.vault_path / "90_Meta" / "Templates"
        self.cached_templates: dict[str, str] = {}
        self.template_inheritance_cache: dict[str, str] = {}

    async def load_template(self, template_name: str) -> str:
        """テンプレートファイルを読み込む"""
        if template_name in self.cached_templates:
            return self.cached_templates[template_name]

        template_file = self.template_path / f"{template_name}.md"
        if not template_file.exists():
            raise FileNotFoundError(f"Template not found: {template_name}")

        async with aiofiles.open(template_file, encoding="utf-8") as f:
            content = await f.read()

        processed_content = await self._process_template_inheritance(content)
        self.cached_templates[template_name] = processed_content
        logger.debug(f"Loaded and cached template: {template_name}")
        return processed_content

    async def _process_template_inheritance(self, content: str) -> str:
        """テンプレート継承を処理"""
        if content in self.template_inheritance_cache:
            return self.template_inheritance_cache[content]

        # Check for new Handlebars-style extends syntax
        extends_match = re.match(
            r'^\s*\{\{\s*extends\s+["\'](.+?)["\']\s*\}\}', content.strip()
        )
        if not extends_match:
            # Fall back to old comment style for backward compatibility
            extends_match = re.search(r"^<!-- extends: (.+) -->", content, re.MULTILINE)
            if not extends_match:
                self.template_inheritance_cache[content] = content
                return content

        parent_name = extends_match.group(1).strip()
        try:
            parent_content = await self.load_template(parent_name)
        except FileNotFoundError:
            # If parent template not found, return original content
            self.template_inheritance_cache[content] = content
            return content

        # Extract child content after extends directive
        child_content = content[extends_match.end() :].strip()

        # Extract blocks from child template
        child_blocks = self._extract_blocks(child_content)

        # Process parent template with child blocks
        result_content = self._merge_parent_with_blocks(parent_content, child_blocks)

        self.template_inheritance_cache[content] = result_content
        return result_content

    def _extract_blocks(self, content: str) -> dict[str, str]:
        """子テンプレートからブロックを抽出"""
        blocks = {}

        # Find all block definitions: {{block "name"}} content {{/block}}
        block_pattern = (
            r'\{\{\s*block\s+["\'](\w+)["\']\s*\}\}(.*?)\{\{\s*/block\s*\}\}'
        )

        for match in re.finditer(block_pattern, content, re.DOTALL):
            block_name = match.group(1)
            block_content = match.group(2).strip()
            blocks[block_name] = block_content

        return blocks

    def _merge_parent_with_blocks(
        self, parent_content: str, child_blocks: dict[str, str]
    ) -> str:
        """親テンプレートと子ブロックをマージ"""

        def replace_block(match):
            block_name = match.group(1)
            default_content = match.group(2).strip()

            # Use child block content if available, otherwise use default
            return child_blocks.get(block_name, default_content)

        # Replace block definitions with child content
        block_pattern = (
            r'\{\{\s*block\s+["\'](\w+)["\']\s*\}\}(.*?)\{\{\s*/block\s*\}\}'
        )
        return re.sub(block_pattern, replace_block, parent_content, flags=re.DOTALL)

    async def _process_template_blocks(self, child: str, parent: str) -> str:
        """テンプレートブロックを処理"""
        content = parent
        block_pattern = r"<!-- block: (.+?) -->(.*?)<!-- endblock -->"

        child_blocks = {
            match.group(1): match.group(2).strip()
            for match in re.finditer(block_pattern, child, re.DOTALL)
        }

        def replace_block(match):
            block_name = match.group(1)
            default_content = match.group(2).strip()
            return child_blocks.get(block_name, default_content)

        content = re.sub(block_pattern, replace_block, content, flags=re.DOTALL)
        content = re.sub(r"<!-- extends: .+ -->", "", content)
        return content.strip()
