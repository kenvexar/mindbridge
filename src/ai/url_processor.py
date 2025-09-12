"""
URL content processor for web scraping and summarization
"""

import asyncio
import re
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import aiohttp
from bs4 import BeautifulSoup

from src.utils.mixins import LoggerMixin


class URLContentExtractor(LoggerMixin):
    """URL内容抽出システム"""

    def __init__(self) -> None:
        """初期化"""
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ja,en-US;q=0.7,en;q=0.3",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        # タイムアウト設定
        self.timeout = aiohttp.ClientTimeout(total=30, connect=10)

        self.logger.info("URL content extractor initialized")

    def extract_urls_from_text(self, text: str) -> list[str]:
        """
        テキストから有効なURLを抽出

        Args:
            text: 対象テキスト

        Returns:
            有効なURLのリスト
        """
        # URLパターン（http/httpsのみ）
        url_pattern = r'https?://[^\s<>"\'{}|\\^`\[\]]+[^\s<>"\'{}|\\^`\[\].,;!?)]'

        urls = re.findall(url_pattern, text, re.IGNORECASE)

        # 無効なURLパターンをフィルタリング
        valid_urls = []
        for url in urls:
            # Discord不完全リンクや無効リンクを除外
            if (
                not url.endswith("/channels/")  # Discord無効リンク
                and not url
                == "https://discord.com/channels/"  # 完全なDiscord無効リンク
                and len(url) > 10  # 最小限の有効性チェック
                and self.is_valid_url(url)  # 詳細な有効性チェック
            ):
                valid_urls.append(url)

        # 重複を削除して返す
        return list(set(valid_urls))

    async def fetch_url_content(
        self, url: str, max_content_length: int = 50000
    ) -> dict[str, Any] | None:
        """
        URLの内容を取得

        Args:
            url: 対象URL
            max_content_length: 最大コンテンツ長

        Returns:
            URL内容データ（失敗時はNone）
        """
        try:
            self.logger.debug("Fetching URL content", url=url)

            async with (
                aiohttp.ClientSession(
                    timeout=self.timeout, headers=self.headers
                ) as session,
                session.get(url) as response,
            ):
                if response.status != 200:
                    self.logger.warning(
                        "HTTP error when fetching URL",
                        url=url,
                        status=response.status,
                    )
                    return None

                # Content-Typeをチェック
                content_type = response.headers.get("content-type", "").lower()
                if (
                    "text/html" not in content_type
                    and "application/xhtml" not in content_type
                ):
                    self.logger.debug(
                        "Unsupported content type",
                        url=url,
                        content_type=content_type,
                    )
                    return None

                # 内容を読み込み（サイズ制限あり）
                raw_content = await response.read()
                if len(raw_content) > max_content_length:
                    self.logger.warning(
                        "Content too large, truncating",
                        url=url,
                        size=len(raw_content),
                    )
                    raw_content = raw_content[:max_content_length]

                # HTMLをパース
                soup = BeautifulSoup(raw_content, "html.parser")

                # メタデータを抽出
                title = self._extract_title(soup)
                description = self._extract_description(soup)

                # メインコンテンツを抽出
                main_content = self._extract_main_content(soup)

                # 結果を構築
                result = {
                    "url": url,
                    "title": title,
                    "description": description,
                    "content": main_content,
                    "extracted_at": datetime.now().isoformat(),
                    "content_length": len(main_content),
                    "status_code": response.status,
                }

                self.logger.debug(
                    "URL content fetched successfully",
                    url=url,
                    title=title[:50] if title else "No title",
                    content_length=len(main_content),
                )

                return result

        except TimeoutError:
            self.logger.warning("Timeout when fetching URL", url=url)
            return None

        except aiohttp.ClientError as e:
            self.logger.warning("Client error when fetching URL", url=url, error=str(e))
            return None

        except Exception as e:
            self.logger.error(
                "Unexpected error when fetching URL",
                url=url,
                error=str(e),
                exc_info=True,
            )
            return None

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """タイトルを抽出"""
        # <title>タグから
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text().strip()
            if title:
                return title

        # Open Graphプロパティから
        og_title = soup.find("meta", property="og:title")
        if og_title and hasattr(og_title, "get"):
            content = og_title.get("content")
            if isinstance(content, str):
                return content.strip()

        # Twitter Cardから
        twitter_title = soup.find("meta", attrs={"name": "twitter:title"})
        if twitter_title and hasattr(twitter_title, "get"):
            content = twitter_title.get("content")
            if isinstance(content, str):
                return content.strip()

        # h1タグから
        h1_tag = soup.find("h1")
        if h1_tag:
            return h1_tag.get_text().strip()

        return "Untitled"

    def _extract_description(self, soup: BeautifulSoup) -> str:
        """説明を抽出"""
        # meta descriptionから
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and hasattr(meta_desc, "get"):
            content = meta_desc.get("content")
            if isinstance(content, str):
                return content.strip()

        # Open Graphプロパティから
        og_desc = soup.find("meta", property="og:description")
        if og_desc and hasattr(og_desc, "get"):
            content = og_desc.get("content")
            if isinstance(content, str):
                return content.strip()

        # Twitter Cardから
        twitter_desc = soup.find("meta", attrs={"name": "twitter:description"})
        if twitter_desc and hasattr(twitter_desc, "get"):
            content = twitter_desc.get("content")
            if isinstance(content, str):
                return content.strip()

        return ""

    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """メインコンテンツを抽出"""
        # スクリプトとスタイルを削除
        for script in soup(["script", "style", "meta", "link", "noscript"]):
            script.decompose()

        # コメントを削除
        from bs4 import Comment

        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        # メインコンテンツ要素を特定（優先順位順）
        main_selectors = [
            "main",
            "article",
            ".content",
            ".main-content",
            "#content",
            "#main",
            ".post-content",
            ".entry-content",
            ".article-body",
            "body",
        ]

        for selector in main_selectors:
            elements = soup.select(selector)
            if elements:
                main_element = elements[0]
                break
        else:
            main_element = soup.body or soup

        # 不要な要素を削除
        unwanted_selectors = [
            "nav",
            "header",
            "footer",
            "aside",
            ".sidebar",
            ".navigation",
            ".menu",
            ".ads",
            ".advertisement",
            ".social-share",
            ".comments",
            ".related-posts",
            ".tags",
            ".breadcrumb",
            ".pagination",
        ]

        for selector in unwanted_selectors:
            for unwanted in main_element.select(selector):
                unwanted.decompose()

        # テキストを抽出
        text = main_element.get_text(separator="\n", strip=True)

        # 空行を整理
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        # 重複行を除去（連続する同じ行）
        cleaned_lines = []
        prev_line = ""
        for line in lines:
            if line != prev_line:
                cleaned_lines.append(line)
                prev_line = line

        return "\n".join(cleaned_lines)

    async def process_urls_in_text(
        self, text: str, max_urls: int = 3
    ) -> dict[str, Any]:
        """
        テキスト内のURLを処理

        Args:
            text: 対象テキスト
            max_urls: 処理するURL数の上限

        Returns:
            処理結果
        """
        try:
            urls = self.extract_urls_from_text(text)

            if not urls:
                return {"found_urls": [], "processed_urls": [], "failed_urls": []}

            # URL数を制限
            if len(urls) > max_urls:
                self.logger.info(
                    "Limiting URL processing", found=len(urls), limit=max_urls
                )
                urls = urls[:max_urls]

            processed_urls = []
            failed_urls = []

            # 各URLを処理
            tasks = [self.fetch_url_content(url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for url, result in zip(urls, results, strict=False):
                if isinstance(result, Exception):
                    failed_urls.append({"url": url, "error": str(result)})
                elif result is not None:
                    processed_urls.append(result)
                else:
                    failed_urls.append({"url": url, "error": "Failed to fetch content"})

            self.logger.info(
                "URL processing completed",
                found=len(urls),
                processed=len(processed_urls),
                failed=len(failed_urls),
            )

            return {
                "found_urls": urls,
                "processed_urls": processed_urls,
                "failed_urls": failed_urls,
            }

        except Exception as e:
            self.logger.error(
                "Failed to process URLs in text", error=str(e), exc_info=True
            )
            return {
                "found_urls": [],
                "processed_urls": [],
                "failed_urls": [],
                "error": str(e),
            }

    def is_valid_url(self, url: str) -> bool:
        """URLの妥当性をチェック"""
        try:
            parsed = urlparse(url)
            return all(
                [
                    parsed.scheme in ("http", "https"),
                    parsed.netloc,
                    not any(
                        domain in parsed.netloc.lower()
                        for domain in [
                            "localhost",
                            "127.0.0.1",
                            "192.168.",
                            "10.",
                            "172.",
                        ]
                    ),
                ]
            )
        except Exception:
            return False
