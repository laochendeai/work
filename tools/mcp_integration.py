#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP Server Integration Scripts
Real implementations for interfacing with MCP servers
"""

import asyncio
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class MCPServerClient:
    """Generic MCP Server Client"""

    def __init__(self, server_name: str, config: Dict[str, Any]):
        self.server_name = server_name
        self.config = config
        self.logger = logging.getLogger(f"mcp.{server_name}")
        self._process = None

    async def start(self) -> bool:
        """Start the MCP server process"""
        try:
            cmd = [self.config["command"]] + self.config["args"]

            # Set environment variables
            env = os.environ.copy()
            env.update(self.config.get("env", {}))

            self.logger.info(f"Starting MCP server: {self.server_name}")
            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                env=env,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Wait a moment for server to start
            await asyncio.sleep(1)

            # Check if process is still running
            if self._process.returncode is not None:
                stderr = await self._process.stderr.read()
                self.logger.error(f"MCP server failed to start: {stderr.decode()}")
                return False

            return True

        except Exception as e:
            self.logger.error(f"Failed to start MCP server {self.server_name}: {e}")
            return False

    async def call_method(self, method: str, params: Dict[str, Any] = None) -> Any:
        """Call a method on the MCP server"""
        if not self._process or self._process.returncode is not None:
            if not await self.start():
                raise RuntimeError(f"Could not start MCP server {self.server_name}")

        try:
            # Create JSON-RPC request
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": method,
                "params": params or {}
            }

            # Send request
            request_json = json.dumps(request) + "\n"
            self._process.stdin.write(request_json.encode())
            await self._process.stdin.drain()

            # Read response
            response_line = await self._process.stdout.readline()
            response = json.loads(response_line.decode())

            if "error" in response:
                raise RuntimeError(f"MCP server error: {response['error']}")

            return response.get("result")

        except Exception as e:
            self.logger.error(f"Error calling MCP method {method}: {e}")
            raise

    async def stop(self):
        """Stop the MCP server"""
        if self._process:
            self._process.terminate()
            await self._process.wait()
            self._process = None

class WebSearchMCP(MCPServerClient):
    """Web Search MCP Client"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__("web-search-prime", config)

    async def search_procurement_sites(
        self,
        keywords: List[str],
        region: str = "china",
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """Search for procurement websites"""
        try:
            query = " ".join(keywords)
            params = {
                "query": query,
                "region": region,
                "max_results": max_results,
                "filter": {
                    "domain_suffix": ["gov.cn", "com.cn"],
                    "exclude_patterns": ["blog", "news", "forum"]
                }
            }

            results = await self.call_method("search", params)

            # Process results
            processed_results = []
            for result in results.get("items", []):
                processed_results.append({
                    "url": result.get("url"),
                    "title": result.get("title"),
                    "description": result.get("description"),
                    "domain": self._extract_domain(result.get("url", "")),
                    "confidence": result.get("relevance_score", 0.5)
                })

            return processed_results

        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return []

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc

class WebsiteAnalyzerMCP(MCPServerClient):
    """Website Analyzer MCP Client"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__("website-analyzer", config)

    async def analyze_website(self, url: str) -> Dict[str, Any]:
        """Analyze website structure and content"""
        try:
            params = {
                "url": url,
                "analyze_links": True,
                "detect_patterns": True,
                "check_procurement": True,
                "depth": "deep"
            }

            analysis = await self.call_method("analyze", params)

            return {
                "url": url,
                "has_procurement_section": analysis.get("has_procurement_section", False),
                "has_pagination": analysis.get("has_pagination", False),
                "has_listing_pages": analysis.get("has_listing_pages", False),
                "has_detail_pages": analysis.get("has_detail_pages", False),
                "estimated_update_frequency": analysis.get("update_frequency", "unknown"),
                "url_patterns": analysis.get("detected_patterns", []),
                "requires_javascript": analysis.get("requires_javascript", False),
                "has_anti_crawler": analysis.get("has_anti_crawler", False),
                "quality_score": analysis.get("quality_score", 0.5)
            }

        except Exception as e:
            self.logger.error(f"Website analysis failed for {url}: {e}")
            return {"url": url, "error": str(e)}

class ContentValidatorMCP(MCPServerClient):
    """Content Validator MCP Client"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__("content-validator", config)

    async def validate_procurement_content(self, url: str) -> Dict[str, Any]:
        """Validate if site contains procurement data"""
        try:
            params = {
                "url": url,
                "check_keywords": ["中标", "采购", "招标", "成交", "公告"],
                "min_content_length": 500,
                "check_contact_info": True,
                "validate_recent": True,
                "recent_days": 30
            }

            validation = await self.call_method("validate", params)

            return {
                "has_recent_announcements": validation.get("has_recent_content", False),
                "has_contact_info": validation.get("has_contact_info", False),
                "procurement_keywords_found": validation.get("found_keywords", []),
                "average_announcements_per_day": validation.get("avg_daily_posts", 0),
                "last_announcement_date": validation.get("last_post_date"),
                "validation_score": validation.get("score", 0.5)
            }

        except Exception as e:
            self.logger.error(f"Content validation failed for {url}: {e}")
            return {"url": url, "error": str(e)}

class MCPManager:
    """Manager for all MCP servers"""

    def __init__(self, config_path: str = "config/mcp_servers.yaml"):
        self.config_path = Path(config_path)
        self.logger = logging.getLogger("mcp_manager")
        self.servers = {}
        self._load_config()

    def _load_config(self):
        """Load MCP server configuration"""
        try:
            import yaml
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            self.servers_config = config.get("mcpServers", {})

        except Exception as e:
            self.logger.error(f"Failed to load MCP config: {e}")
            self.servers_config = {}

    async def initialize(self):
        """Initialize all MCP servers"""
        self.logger.info("Initializing MCP servers...")

        # Initialize specific servers
        if "web-search-prime" in self.servers_config:
            self.search_client = WebSearchMCP(self.servers_config["web-search-prime"])
            await self.search_client.start()

        if "website-analyzer" in self.servers_config:
            self.analyzer_client = WebsiteAnalyzerMCP(self.servers_config["website-analyzer"])
            await self.analyzer_client.start()

        if "content-validator" in self.servers_config:
            self.validator_client = ContentValidatorMCP(self.servers_config["content-validator"])
            await self.validator_client.start()

        self.logger.info("MCP servers initialized")

    async def shutdown(self):
        """Shutdown all MCP servers"""
        self.logger.info("Shutting down MCP servers...")

        if hasattr(self, 'search_client'):
            await self.search_client.stop()

        if hasattr(self, 'analyzer_client'):
            await self.analyzer_client.stop()

        if hasattr(self, 'validator_client'):
            await self.validator_client.stop()

        self.logger.info("MCP servers shutdown complete")

# Singleton instance
mcp_manager = MCPManager()