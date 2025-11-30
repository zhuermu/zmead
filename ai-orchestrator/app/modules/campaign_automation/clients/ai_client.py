"""
AI Client - Handles AI-powered ad copy generation with fallback strategy.

This module provides the AIClient class for generating ad copy using Gemini AI:
- Primary: Gemini 2.5 Pro for high-quality copy
- Fallback 1: Gemini 2.5 Flash for faster generation
- Fallback 2: Template-based copy as last resort

Requirements: 2.4, 2.5
"""

from typing import Optional

import structlog

from app.services.gemini_client import GeminiClient, GeminiError

logger = structlog.get_logger(__name__)


class AIClient:
    """
    AI Client for ad copy generation.
    
    Provides AI-powered ad copy generation with a three-tier fallback strategy:
    1. Gemini 2.5 Pro - High quality, detailed copy
    2. Gemini 2.5 Flash - Faster generation, good quality
    3. Template copy - Simple fallback when AI fails
    
    Requirements: 2.4, 2.5
    """
    
    # Default template for fallback
    DEFAULT_TEMPLATE = "限时优惠！立即购买"
    
    # Maximum copy length (Meta Ads limit)
    MAX_COPY_LENGTH = 125
    
    def __init__(self, gemini_client: GeminiClient):
        """
        Initialize AI Client.
        
        Args:
            gemini_client: Gemini client instance
        """
        self.gemini_client = gemini_client
        logger.info("ai_client_initialized")
    
    async def generate_ad_copy(
        self,
        product_url: str,
        creative_id: str,
        platform: str,
        max_length: int = MAX_COPY_LENGTH,
    ) -> str:
        """
        Generate AI-powered ad copy with fallback strategy.
        
        Fallback strategy:
        1. Try Gemini 2.5 Pro (chat_completion)
        2. If fails, try Gemini 2.5 Flash (fast_completion)
        3. If still fails, use template copy
        
        Args:
            product_url: Product URL for context
            creative_id: Creative ID for reference
            platform: Platform name (meta, tiktok, google)
            max_length: Maximum copy length in characters (default 125)
            
        Returns:
            Generated ad copy text
            
        Requirements: 2.4, 2.5
        """
        log = logger.bind(
            product_url=product_url,
            creative_id=creative_id,
            platform=platform,
            max_length=max_length,
        )
        
        log.info("generate_ad_copy_start")
        
        # If no product URL, return template
        if not product_url:
            log.info("no_product_url_using_template")
            return self.DEFAULT_TEMPLATE
        
        # Build prompt
        prompt = self._build_prompt(product_url, platform, max_length)
        
        # Try Gemini Pro first
        try:
            log.info("trying_gemini_pro")
            copy = await self.gemini_client.chat_completion(
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,  # More creative for ad copy
            )
            
            # Validate and truncate if needed
            copy = self._validate_copy(copy, max_length)
            
            log.info("gemini_pro_success", copy_length=len(copy))
            return copy
            
        except GeminiError as e:
            log.warning("gemini_pro_failed_trying_flash", error=str(e), error_code=e.code)
            
            # Try Gemini Flash as fallback
            try:
                log.info("trying_gemini_flash")
                copy = await self.gemini_client.fast_completion(
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                )
                
                # Validate and truncate if needed
                copy = self._validate_copy(copy, max_length)
                
                log.info("gemini_flash_success", copy_length=len(copy))
                return copy
                
            except GeminiError as e:
                log.error("all_ai_models_failed_using_template", error=str(e), error_code=e.code)
                return self._get_template_copy(product_url)
    
    def _build_prompt(
        self,
        product_url: str,
        platform: str,
        max_length: int,
    ) -> str:
        """
        Build prompt for ad copy generation.
        
        Args:
            product_url: Product URL
            platform: Platform name
            max_length: Maximum copy length
            
        Returns:
            Formatted prompt string
        """
        return f"""为以下产品生成吸引人的广告文案（{max_length} 字以内）：

产品链接：{product_url}
平台：{platform}

要求：
1. 突出产品卖点和独特价值
2. 包含明确的行动号召（CTA）
3. 符合{platform}平台的广告规范
4. 语言简洁有力，吸引点击
5. 不超过{max_length}个字符

请直接返回广告文案，不要包含任何解释或额外内容。"""
    
    def _validate_copy(self, copy: str, max_length: int) -> str:
        """
        Validate and clean ad copy.
        
        Args:
            copy: Generated copy
            max_length: Maximum allowed length
            
        Returns:
            Validated and cleaned copy
        """
        if not copy:
            return self.DEFAULT_TEMPLATE
        
        # Remove leading/trailing whitespace
        copy = copy.strip()
        
        # Remove quotes if present
        if copy.startswith('"') and copy.endswith('"'):
            copy = copy[1:-1].strip()
        if copy.startswith("'") and copy.endswith("'"):
            copy = copy[1:-1].strip()
        
        # Truncate if too long
        if len(copy) > max_length:
            logger.warning("copy_too_long_truncating", original_length=len(copy), max_length=max_length)
            copy = copy[:max_length-3] + "..."
        
        return copy
    
    def _get_template_copy(self, product_url: str) -> str:
        """
        Get template-based copy as last resort.
        
        Args:
            product_url: Product URL
            
        Returns:
            Template copy with product URL
        """
        return f"{self.DEFAULT_TEMPLATE} {product_url}"
