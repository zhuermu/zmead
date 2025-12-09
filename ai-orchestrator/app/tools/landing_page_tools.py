"""Landing Page Tools for landing page generation and optimization.

This module provides Agent Custom Tools for landing page operations:
- generate_page_content_tool: Generate complete landing page HTML using Gemini
- generate_landing_page_tool: Full workflow: extract info → extract images → generate HTML → save
- translate_content_tool: Translate content using Gemini
- optimize_copy_tool: Optimize copy for conversions using Gemini

These tools can call LLMs (Gemini) for AI capabilities.
They call the module functions directly (not through capability.py).
"""

import structlog
from typing import Any

from app.services.gemini_client import GeminiClient, GeminiError
from app.services.mcp_client import MCPClient, MCPError
from app.tools.base import (
    AgentTool,
    ToolCategory,
    ToolExecutionError,
    ToolMetadata,
    ToolParameter,
)

logger = structlog.get_logger(__name__)


# Style guidelines for different templates - Premium design specifications
STYLE_GUIDELINES = {
    "modern": {
        "description": "简洁现代风格 - Apple风格的极致简约与优雅",
        "colors": "primary: #3B82F6 (blue), secondary: #EFF6FF, accent: #2563EB, background: #FFFFFF, text: #1F2937",
        "typography": "system-ui font stack, heading: 600-700 weight, body: 400 weight, generous line-height",
        "characteristics": """
- Clean, minimal aesthetic with Apple-like attention to detail
- Generous whitespace (100px+ section padding)
- Subtle shadows and smooth transitions
- Single accent color used sparingly
- Photography-focused with large, high-quality images
- Floating navigation or minimal header
- Soft, subtle gradients in backgrounds""",
    },
    "bold": {
        "description": "大胆醒目风格 - 深色奢华感与渐变视觉冲击",
        "colors": "primary: gradient from #8B5CF6 to #EC4899, secondary: #1E1B4B, accent: #F472B6, background: #0F172A, text: #F8FAFC",
        "typography": "large bold headers (64-96px), uppercase options for impact, high contrast white text",
        "characteristics": """
- Dark, sophisticated backgrounds (#0F172A, #1E1B4B)
- Vibrant gradient accents (purple to pink, blue to cyan)
- Large, impactful typography with generous letter-spacing
- Glassmorphism effects (backdrop-blur, semi-transparent cards)
- Neon-like glow effects on CTAs
- Dynamic hover animations
- High-contrast imagery with dark overlays""",
    },
    "minimal": {
        "description": "极简主义 - 日式美学的留白艺术",
        "colors": "primary: #000000, secondary: #F9FAFB, accent: #374151, background: #FFFFFF, text: #111827",
        "typography": "ultra-light to medium weights, generous tracking, refined proportions",
        "characteristics": """
- Maximum whitespace utilization (150px+ section padding)
- Black and white with single accent color
- Thin, elegant typography
- Subtle, refined interactions
- Grid-based layout with strict alignment
- Photography with neutral tones
- No shadows, minimal borders (1px max)
- Focus on content and negative space""",
    },
    "elegant": {
        "description": "优雅奢华风格 - 高端品牌的精致质感",
        "colors": "primary: #D4AF37 (gold), secondary: #1C1917, accent: #B8860B, background: #FFFEF7 (cream), text: #292524",
        "typography": "serif headers (Georgia, Playfair Display feel), refined spacing, italic accents",
        "characteristics": """
- Premium, luxury aesthetic (think Chanel, Dior)
- Gold accents with cream/ivory backgrounds
- Serif typography for headings, elegant curves
- Subtle texture overlays
- Refined borders and dividers
- Sophisticated color palette (gold, cream, charcoal)
- Generous padding with asymmetric layouts
- Refined hover states with smooth transitions""",
    },
    "startup": {
        "description": "活力科技风格 - 现代SaaS的友好与活力",
        "colors": "primary: #10B981 (emerald), secondary: #ECFDF5, accent: #059669, background: #FFFFFF, text: #1F2937",
        "typography": "modern sans-serif, friendly and approachable, medium weights",
        "characteristics": """
- Energetic, approachable design
- Rounded corners throughout (12-24px)
- Colorful gradient buttons
- Playful illustrations or icons
- Card-based layouts with soft shadows
- Animated micro-interactions
- Badge/pill elements for features
- Friendly, conversational copy tone""",
    },
}


class GeneratePageContentTool(AgentTool):
    """Tool for generating complete landing page HTML using Gemini.

    This tool generates complete, responsive HTML landing pages including
    embedded CSS, product galleries, features, and call-to-actions.
    Supports generating multiple AB test versions with different styles.
    """

    def __init__(self, gemini_client: GeminiClient | None = None):
        """Initialize the generate page content tool.

        Args:
            gemini_client: Gemini client for content generation
        """
        metadata = ToolMetadata(
            name="generate_page_content_tool",
            description=(
                "Generate complete, responsive landing page HTML using AI. "
                "Creates full HTML5 documents with embedded CSS, including "
                "hero section, product gallery, features, benefits, and CTAs. "
                "Supports AB testing by generating multiple versions with different styles."
            ),
            category=ToolCategory.AGENT_CUSTOM,
            parameters=[
                ToolParameter(
                    name="product_info",
                    type="object",
                    description="Product information including name, description, features, benefits",
                    required=True,
                ),
                ToolParameter(
                    name="product_images",
                    type="array",
                    description="List of product image URLs to include in the landing page",
                    required=False,
                ),
                ToolParameter(
                    name="styles",
                    type="array",
                    description="List of styles for AB testing (e.g., ['modern', 'bold']). Each style generates a separate version.",
                    required=False,
                    default=["modern", "bold"],
                ),
                ToolParameter(
                    name="language",
                    type="string",
                    description="Content language (e.g., 'zh' for Chinese, 'en' for English)",
                    required=False,
                    default="zh",
                ),
                ToolParameter(
                    name="target_audience",
                    type="string",
                    description="Target audience description",
                    required=False,
                ),
            ],
            returns="object with multiple HTML versions for AB testing",
            credit_cost=15.0,
            tags=["landing_page", "content", "generation", "ai", "html"],
        )

        super().__init__(metadata)

        self.gemini_client = gemini_client or GeminiClient()

    async def execute(
        self,
        parameters: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute page content generation.

        Args:
            parameters: Tool parameters
            context: Execution context

        Returns:
            Generated landing page HTML versions

        Raises:
            ToolExecutionError: If generation fails
        """
        product_info = parameters.get("product_info", {})
        product_images = parameters.get("product_images", [])
        styles = parameters.get("styles", ["modern", "bold"])
        language = parameters.get("language", "zh")
        target_audience = parameters.get("target_audience")
        product_url = parameters.get("product_url", product_info.get("url", "#"))
        color_scheme = parameters.get("color_scheme", {})

        log = logger.bind(
            tool=self.name,
            styles=styles,
            language=language,
            has_images=len(product_images) > 0,
            has_target_audience=bool(target_audience),
            product_url=product_url[:50] if product_url else None,
            has_color_scheme=bool(color_scheme),
        )
        log.info("generate_page_content_start")

        versions = []
        version_labels = ["A", "B", "C", "D", "E"]

        for idx, style in enumerate(styles[:5]):  # Max 5 versions
            version_id = version_labels[idx] if idx < len(version_labels) else str(idx + 1)

            try:
                # Build generation prompt with product_url and color scheme
                prompt = self._build_html_prompt(
                    product_info, product_images, style, language, target_audience, product_url, color_scheme
                )

                log.info(f"generating_version_{version_id}", style=style)

                # Generate using Gemini
                messages = [{"role": "user", "content": prompt}]

                html_content = await self.gemini_client.chat_completion(
                    messages=messages,
                    temperature=0.7,
                )

                # Clean up the HTML (remove markdown code blocks if present)
                html_content = self._clean_html_output(html_content)

                style_info = STYLE_GUIDELINES.get(style, STYLE_GUIDELINES["modern"])

                versions.append({
                    "version_id": version_id,
                    "html_content": html_content,
                    "style": style,
                    "description": style_info["description"],
                })

                log.info(f"version_{version_id}_generated", style=style, html_length=len(html_content))

            except GeminiError as e:
                log.error(f"version_{version_id}_failed", style=style, error=str(e))
                versions.append({
                    "version_id": version_id,
                    "html_content": None,
                    "style": style,
                    "error": str(e),
                })

        successful_versions = [v for v in versions if v.get("html_content")]

        log.info(
            "generate_page_content_complete",
            total_versions=len(versions),
            successful_versions=len(successful_versions),
        )

        return {
            "success": len(successful_versions) > 0,
            "versions": versions,
            "successful_count": len(successful_versions),
            "message": f"Generated {len(successful_versions)} landing page versions for AB testing",
        }

    def _clean_html_output(self, html: str) -> str:
        """Clean up HTML output from Gemini.

        Args:
            html: Raw HTML output

        Returns:
            Cleaned HTML
        """
        import re

        # Remove markdown code blocks
        html = re.sub(r'^```html?\s*\n?', '', html, flags=re.IGNORECASE)
        html = re.sub(r'\n?```\s*$', '', html)

        # Ensure it starts with DOCTYPE
        html = html.strip()
        if not html.lower().startswith('<!doctype'):
            # Try to find DOCTYPE in the content
            doctype_match = re.search(r'<!DOCTYPE[^>]*>', html, re.IGNORECASE)
            if doctype_match:
                html = html[doctype_match.start():]

        return html

    def _build_html_prompt(
        self,
        product_info: dict[str, Any],
        product_images: list[dict[str, Any]] | list[str],
        style: str,
        language: str,
        target_audience: str | None,
        product_url: str | None = None,
        color_scheme: dict[str, Any] | None = None,
    ) -> str:
        """Build HTML generation prompt.

        Args:
            product_info: Product information
            product_images: Product image URLs
            style: Template style
            language: Content language
            target_audience: Target audience
            product_url: Original product page URL for purchase links
            color_scheme: Color scheme extracted from product images

        Returns:
            Generation prompt
        """
        product_name = product_info.get("name", "产品")
        description = product_info.get("description", "")
        features = product_info.get("features", [])
        benefits = product_info.get("benefits", [])
        # Get product URL from product_info if not passed directly
        buy_url = product_url or product_info.get("url", "#")

        style_info = STYLE_GUIDELINES.get(style, STYLE_GUIDELINES["modern"])

        # Build color scheme section if available
        color_section = ""
        if color_scheme:
            gradient_info = ""
            if color_scheme.get('gradient_start') and color_scheme.get('gradient_end'):
                gradient_info = f"""- Button Gradient: linear-gradient(135deg, {color_scheme.get('gradient_start')} 0%, {color_scheme.get('gradient_end')} 100%)"""

            color_section = f"""
## Color Scheme (MUST use these colors - professionally extracted from product images):
- Primary Color: {color_scheme.get('primary_color', '#1a1a2e')} (use for headers, key elements)
- Secondary Color: {color_scheme.get('secondary_color', '#16213e')} (use for alternate section backgrounds)
- Accent Color: {color_scheme.get('accent_color', '#e94560')} (MUST use for CTA buttons - high visibility)
- Text Color: {color_scheme.get('text_color', '#ffffff')} (main body text)
- Background Color: {color_scheme.get('background_color', '#0f0f1a')} (page background)
{gradient_info}
- Design Direction: {color_scheme.get('style_description', 'Modern premium theme')}

CRITICAL COLOR USAGE RULES:
1. CTA buttons MUST use the accent color (or gradient if provided) - make them impossible to miss
2. Use secondary color for alternate sections to create visual rhythm
3. Ensure text has sufficient contrast against all backgrounds
4. Apply primary color to headlines, icons, and key visual elements
5. Create visual hierarchy through strategic color application
"""

        # Format image URLs
        image_urls = []
        for img in product_images[:5]:  # Max 5 images
            if isinstance(img, dict):
                image_urls.append(img.get("url", ""))
            else:
                image_urls.append(str(img))
        image_urls = [url for url in image_urls if url]

        image_section = ""
        if image_urls:
            image_section = f"""
## Product Images (MUST use these exact URLs - do NOT modify or replace them):
{chr(10).join(f'- {url}' for url in image_urls)}

CRITICAL: You MUST include ALL the above image URLs in your HTML using <img src="..."> tags.
These are the actual product images from the source page. Display them prominently in the hero section and product gallery.
"""
        else:
            image_section = """
## Product Images: No images provided.
IMPORTANT: Do NOT use external placeholder services (via.placeholder.com, placeholder.com, etc.) as they have CORS issues.
Instead, create visually appealing placeholder areas using:
- CSS gradient backgrounds with the brand colors
- SVG icons or shapes embedded inline
- CSS-only decorative patterns
- Solid color blocks with product name text overlay
"""

        audience_section = ""
        if target_audience:
            audience_section = f"\nTarget Audience: {target_audience}"

        lang_instruction = "所有文案内容使用中文" if language == "zh" else f"All copy should be in {language}"

        prompt = f"""You are an award-winning web designer specializing in high-converting e-commerce landing pages. Create a stunning, premium-quality landing page that looks like it was designed by a top agency.

## Product Information
- Product Name: {product_name}
- Description: {description}
- Key Features: {', '.join(features[:5]) if features else 'Not specified'}
- Key Benefits: {', '.join(benefits[:5]) if benefits else 'Not specified'}{audience_section}
- Purchase URL: {buy_url}
{image_section}
{color_section}
## Design Style: {style}
- Style Description: {style_info['description']}
- Default Color Scheme: {style_info['colors']}
- Typography: {style_info['typography']}
- Characteristics: {style_info['characteristics']}

NOTE: If a Color Scheme section is provided above, prioritize those extracted colors as they were specifically chosen to match the product aesthetics. Blend them harmoniously with the style guidelines.

## Technical Requirements
1. Generate a COMPLETE HTML5 document starting with <!DOCTYPE html>
2. ALL CSS must be embedded in a <style> tag (NO external CSS files)
3. Mobile-responsive design using CSS media queries (breakpoints: 768px, 1024px, 1440px)
4. {lang_instruction}
5. ALL "Buy Now", "Purchase", "立即购买", "马上抢购" buttons MUST link to: {buy_url}

## Premium Design Requirements (CRITICAL for high-quality output)

### Visual Hierarchy & Spacing
- Use generous whitespace (padding: 80-120px between sections on desktop)
- Create clear visual hierarchy with font sizes (hero: 48-72px, section titles: 32-48px, body: 16-18px)
- Use consistent spacing scale (8, 16, 24, 32, 48, 64, 80, 120px)

### Typography Excellence
- Use modern font stack: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif
- For Chinese: 'PingFang SC', 'Microsoft YaHei', sans-serif
- Letter-spacing: 0.02em for headings, normal for body
- Line-height: 1.2 for headings, 1.6-1.8 for body text

### Color & Contrast
- Use the extracted color scheme as the PRIMARY palette
- Add subtle gradients for depth (linear-gradient with 10-20% color variation)
- Ensure WCAG AA contrast (4.5:1 for text, 3:1 for large text)
- Use semi-transparent overlays on images for text readability (rgba backgrounds)

### Professional Effects (subtle, not overdone)
- Smooth transitions: transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1)
- Subtle shadows for cards: box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06)
- Elevated shadows for buttons: box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1)
- Border-radius: 8-16px for cards, 6-8px for buttons
- Hover effects: scale(1.02) for cards, brightness increase for buttons

### Image Presentation
- Hero image should be full-width or occupy 50-60% of viewport
- Product gallery: use CSS Grid with gap: 16-24px
- Images should have subtle border-radius (8-12px)
- Add subtle box-shadow to product images
- Use object-fit: cover with aspect-ratio for consistency

### CTA Buttons (Conversion-Focused)
- Primary CTA: Large (min 200px wide, 56px tall), prominent color, bold text
- Add hover animation (slight lift + shadow increase)
- Use action-oriented text: "立即抢购" / "Get Yours Now" / "Shop Now"
- Include urgency cues in surrounding text (limited time, popular item, etc.)

## Required Sections (create these with premium aesthetics)

1. **Hero Section** (Full viewport height or 80vh minimum)
   - Large, impactful headline with product name
   - Compelling subheadline (value proposition)
   - Primary CTA button (prominent, attention-grabbing)
   - Hero product image with professional presentation
   - Optional: subtle background animation or gradient

2. **Product Gallery** (Showcase section)
   - Display ALL provided product images
   - Clean grid layout (2-3 columns on desktop, 1-2 on mobile)
   - Image zoom/scale effect on hover
   - Adequate spacing between images

3. **Features Section** (Icon-driven)
   - 3-5 key features in visually appealing cards or grid
   - Use inline SVG icons (simple, modern style)
   - Brief, punchy descriptions
   - Consistent icon size (48-64px)

4. **Benefits Section** (Emotional appeal)
   - Focus on customer transformation/value
   - Use compelling visuals or icons
   - Highlight what makes this product special

5. **Social Proof** (Trust-building)
   - Star ratings (use inline SVG stars)
   - Customer satisfaction stats or badges
   - Trust indicators (secure checkout, guarantee icons)

6. **Final CTA Section** (Urgency-driven)
   - Repeat main value proposition
   - Large, unmissable CTA button
   - Supporting urgency text (limited availability, special offer, etc.)

## Strict Prohibitions
- NEVER use external placeholder image services (CORS errors)
- NEVER use Lorem ipsum text - write real, compelling copy
- NEVER create cluttered layouts - embrace whitespace
- NEVER use harsh, jarring color combinations
- NEVER make text unreadable (always maintain contrast)

## Quality Benchmarks
The output should look like a landing page from:
- Apple Product Pages (clean, minimal, premium)
- Shopify Premium Themes (conversion-optimized)
- Award-winning Dribbble/Behance designs (visually stunning)

Output ONLY the complete HTML code. No explanations, no markdown formatting."""

        return prompt


class GenerateLandingPageTool(AgentTool):
    """Tool for complete landing page workflow.

    This tool orchestrates the full landing page creation process:
    1. Extract product information from URL
    2. Extract product images from URL
    3. Generate HTML landing pages (AB versions)
    4. Save landing pages to backend via MCP
    """

    def __init__(
        self,
        gemini_client: GeminiClient | None = None,
        mcp_client: MCPClient | None = None,
    ):
        """Initialize the generate landing page tool.

        Args:
            gemini_client: Gemini client for AI operations
            mcp_client: MCP client for backend operations
        """
        metadata = ToolMetadata(
            name="generate_landing_page_tool",
            description=(
                "Complete landing page creation workflow. "
                "Automatically extracts product information and images from URL, "
                "generates responsive HTML landing pages with AB testing versions, "
                "and saves them to the backend for publishing. "
                "Use this tool when user wants to create a landing page from a product URL."
            ),
            category=ToolCategory.AGENT_CUSTOM,
            parameters=[
                ToolParameter(
                    name="product_url",
                    type="string",
                    description="Product page URL to create landing page from",
                    required=True,
                ),
                ToolParameter(
                    name="page_name",
                    type="string",
                    description="Landing page name (optional, auto-generated from product name if not provided)",
                    required=False,
                ),
                ToolParameter(
                    name="language",
                    type="string",
                    description="Content language. Use 'auto' to detect from product page, or specify explicitly like 'zh', 'en', 'ja'. User's explicit request takes priority over auto-detection.",
                    required=False,
                    default="auto",
                ),
                ToolParameter(
                    name="styles",
                    type="array",
                    description="Design styles for AB testing (default: ['modern', 'bold'])",
                    required=False,
                    default=["modern", "bold"],
                ),
                ToolParameter(
                    name="auto_save",
                    type="boolean",
                    description="Whether to automatically save to backend (default: true)",
                    required=False,
                    default=True,
                ),
            ],
            returns="object with created landing pages, product info, and images used",
            credit_cost=20.0,
            tags=["landing_page", "workflow", "generation", "ai"],
        )

        super().__init__(metadata)

        self.gemini_client = gemini_client or GeminiClient()
        self.mcp_client = mcp_client or MCPClient()

    async def execute(
        self,
        parameters: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute the complete landing page workflow.

        Args:
            parameters: Tool parameters
            context: Execution context with user_id

        Returns:
            Created landing pages and metadata

        Raises:
            ToolExecutionError: If workflow fails
        """
        user_id = context.get("user_id") if context else None
        product_url = parameters.get("product_url")
        page_name = parameters.get("page_name")
        # Language priority: user explicit > auto-detect from product page
        language = parameters.get("language", "auto")
        styles = parameters.get("styles", ["modern", "bold"])
        auto_save = parameters.get("auto_save", True)

        # Track if user explicitly specified language (not "auto")
        user_specified_language = language != "auto"

        log = logger.bind(
            tool=self.name,
            user_id=user_id,
            product_url=product_url,
            language=language,
            styles=styles,
            auto_save=auto_save,
        )
        log.info("generate_landing_page_start")

        if not product_url:
            raise ToolExecutionError(
                message="product_url is required",
                tool_name=self.name,
                error_code="INVALID_PARAMS",
            )

        result = {
            "success": False,
            "product_info": None,
            "images": [],
            "landing_pages": [],
            "errors": [],
        }

        try:
            # Step 1: Extract product information
            log.info("step1_extract_product_info")
            product_info = await self._extract_product_info(product_url, log)
            result["product_info"] = product_info

            # Auto-generate page name if not provided
            if not page_name:
                product_name = product_info.get("name", "产品")
                page_name = f"{product_name}-落地页"

            # Language priority: user explicit request > auto-detect from product page
            detected_language = product_info.get("language", "en")
            if not user_specified_language:
                # User didn't specify language, use detected from product page
                language = detected_language
                log.info("using_detected_language", language=language, detected=detected_language)
            else:
                # User explicitly specified language, use it regardless of product page language
                log.info("using_user_specified_language", language=language, detected=detected_language)

            # Step 2: Extract product image URLs (download happens at preview time)
            log.info("step2_extract_product_images")
            images = await self._extract_product_images(product_url, log)
            result["images"] = images

            # Step 2.5: Analyze image colors for color scheme
            log.info("step2_5_analyze_image_colors")
            image_urls = [img.get("url") for img in images if img.get("url")]
            color_scheme = await self._analyze_image_colors(image_urls, log)
            result["color_scheme"] = color_scheme

            # Step 3: Generate HTML versions with product_url and color scheme
            log.info("step3_generate_html_versions")
            html_versions = await self._generate_html_versions(
                product_info, images, styles, language, product_url, color_scheme, log
            )

            if not html_versions:
                raise ToolExecutionError(
                    message="Failed to generate any landing page versions",
                    tool_name=self.name,
                    error_code="GENERATION_FAILED",
                )

            # Step 4: Save to backend (if auto_save is enabled)
            if auto_save and user_id:
                log.info("step4_save_to_backend")
                saved_pages = await self._save_landing_pages(
                    html_versions, page_name, product_url, language, user_id, log
                )
                result["landing_pages"] = saved_pages
            else:
                # Return HTML content without saving
                result["landing_pages"] = [
                    {
                        "version": v["version_id"],
                        "style": v["style"],
                        "description": v.get("description", ""),
                        "html_content": v["html_content"],
                        "saved": False,
                    }
                    for v in html_versions
                    if v.get("html_content")
                ]

            result["success"] = True
            result["message"] = f"成功生成并保存了{len(result['landing_pages'])}个落地页版本，可用于AB测试"

            log.info(
                "generate_landing_page_complete",
                pages_created=len(result["landing_pages"]),
            )

        except ToolExecutionError:
            raise
        except Exception as e:
            log.error("unexpected_error", error=str(e), exc_info=True)
            raise ToolExecutionError(
                message=f"Landing page generation failed: {str(e)}",
                tool_name=self.name,
            )

        return result

    async def _extract_product_info(
        self, product_url: str, log: Any
    ) -> dict[str, Any]:
        """Extract product information from URL including language detection.

        Args:
            product_url: Product page URL
            log: Logger instance

        Returns:
            Product information dict with detected language
        """
        try:
            prompt = f"""Extract structured product information from this URL: {product_url}

Provide the following information in JSON format:
- name: Product name
- description: Product description (2-3 sentences)
- features: Array of 3-5 key features
- benefits: Array of 3-5 key benefits
- target_audience: Target audience description
- language: Detected page language code (e.g., "en" for English, "zh" for Chinese, "ja" for Japanese, "ko" for Korean, "de" for German, "fr" for French, "es" for Spanish)

IMPORTANT: Detect the language based on the product page content, NOT the URL. Return the ISO 639-1 language code.

Output ONLY valid JSON, no explanations."""

            messages = [{"role": "user", "content": prompt}]

            result_text = await self.gemini_client.chat_completion(
                messages=messages,
                temperature=0.1,
            )

            # Parse JSON response
            import json
            import re

            # Clean up JSON
            result_text = re.sub(r'^```json?\s*\n?', '', result_text, flags=re.IGNORECASE)
            result_text = re.sub(r'\n?```\s*$', '', result_text)

            try:
                product_info = json.loads(result_text)
            except json.JSONDecodeError:
                # Fallback to basic info
                product_info = {
                    "name": "产品",
                    "description": "优质产品",
                    "features": ["功能1", "功能2", "功能3"],
                    "benefits": ["好处1", "好处2", "好处3"],
                    "language": "en",
                }

            log.info(
                "product_info_extracted",
                product_name=product_info.get("name"),
                detected_language=product_info.get("language", "en"),
            )
            return product_info

        except GeminiError as e:
            log.warning("product_info_extraction_failed", error=str(e))
            return {
                "name": "产品",
                "description": "优质产品",
                "features": [],
                "benefits": [],
            }

    async def _extract_product_images(
        self, product_url: str, log: Any
    ) -> list[dict[str, Any]]:
        """Extract product image URLs from product page.

        Only extracts URLs, does not download images.
        Image downloading is done at preview time in the backend.

        Supports:
        - Amazon: Uses Gemini to analyze page and extract image URLs
        - Shopify: og:image, JSON-LD, product gallery
        - Generic: og:image, JSON-LD structured data

        Args:
            product_url: Product page URL
            log: Logger instance

        Returns:
            List of image objects with original URLs
        """
        import httpx
        import re
        import json

        images = []
        seen_urls = set()

        # Detect platform
        is_amazon = "amazon.com" in product_url or "amazon.cn" in product_url or "amzn." in product_url

        try:
            # For Amazon, use Gemini to extract image URLs (bypasses anti-scraping)
            if is_amazon:
                log.info("using_gemini_for_amazon_images")
                images = await self._extract_images_via_gemini(product_url, log)
                if images:
                    log.info("amazon_images_extracted_via_gemini", count=len(images))
                    return images[:5]
                # Fallback to direct extraction if Gemini fails
                log.info("gemini_extraction_failed_trying_direct")

            # Direct HTML extraction for non-Amazon or as fallback
            async with httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate, br",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                },
            ) as client:
                response = await client.get(product_url)
                response.raise_for_status()
                html = response.text

            # Extract og:image (works on most sites)
            og_pattern = r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"'
            for match in re.finditer(og_pattern, html, re.IGNORECASE):
                img_url = match.group(1)
                if img_url and img_url not in seen_urls:
                    seen_urls.add(img_url)
                    images.append({"url": img_url, "alt": "Product Image"})

            # Also try content="..." property="og:image" order
            og_pattern2 = r'<meta[^>]*content="([^"]+)"[^>]*property="og:image"'
            for match in re.finditer(og_pattern2, html, re.IGNORECASE):
                img_url = match.group(1)
                if img_url and img_url not in seen_urls:
                    seen_urls.add(img_url)
                    images.append({"url": img_url, "alt": "Product Image"})

            # Extract from JSON-LD structured data
            json_ld_pattern = r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>'
            for match in re.finditer(json_ld_pattern, html, re.DOTALL | re.IGNORECASE):
                try:
                    data = json.loads(match.group(1))
                    # Handle array of objects
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and item.get("@type") == "Product":
                                data = item
                                break
                        else:
                            continue

                    if isinstance(data, dict) and data.get("@type") == "Product":
                        img_data = data.get("image", [])
                        if isinstance(img_data, str):
                            img_data = [img_data]
                        elif isinstance(img_data, dict):
                            img_data = [img_data.get("url", "")]
                        for img_url in img_data[:5]:
                            if img_url and img_url not in seen_urls:
                                seen_urls.add(img_url)
                                images.append({"url": img_url, "alt": data.get("name", "Product")})
                except Exception:
                    continue

            # Amazon-specific: extract from data-a-dynamic-image or imgTagWrapperId
            if is_amazon and not images:
                # Try to find high-res image URLs in the page
                hiRes_pattern = r'"hiRes"\s*:\s*"([^"]+)"'
                for match in re.finditer(hiRes_pattern, html):
                    img_url = match.group(1)
                    if img_url and img_url not in seen_urls and img_url.startswith("http"):
                        seen_urls.add(img_url)
                        images.append({"url": img_url, "alt": "Product Image"})

                # Try data-old-hires attribute
                data_hires_pattern = r'data-old-hires="([^"]+)"'
                for match in re.finditer(data_hires_pattern, html):
                    img_url = match.group(1)
                    if img_url and img_url not in seen_urls:
                        seen_urls.add(img_url)
                        images.append({"url": img_url, "alt": "Product Image"})

            log.info("product_images_extracted", count=len(images), platform="amazon" if is_amazon else "generic")
            return images[:5]

        except Exception as e:
            log.warning("product_images_extraction_failed", error=str(e))
            return []

    async def _extract_images_via_gemini(
        self, product_url: str, log: Any
    ) -> list[dict[str, Any]]:
        """Use Gemini to extract product image URLs from a page.

        This is useful for sites with anti-scraping measures like Amazon.

        Args:
            product_url: Product page URL
            log: Logger instance

        Returns:
            List of image objects with URLs
        """
        try:
            prompt = f"""Visit this product page and extract the main product image URLs: {product_url}

Return a JSON array of image objects with this format:
[
  {{"url": "https://...", "alt": "Product Image 1"}},
  {{"url": "https://...", "alt": "Product Image 2"}}
]

Requirements:
1. Extract ONLY the main product photos showing the actual product itself
2. Return the highest resolution image URLs available
3. For Amazon, look for images from "images-na.ssl-images-amazon.com" or "m.media-amazon.com"
4. Return up to 5 images maximum
5. Return ONLY the JSON array, no explanation

IMPORTANT - MUST EXCLUDE these types of images:
- Size charts / 尺码表
- Height/weight comparison tables / 身高体重对照表
- Measurement guides / 测量指南
- Shipping information graphics / 物流信息图
- Brand logos or store banners / 品牌logo或店铺横幅
- Icon graphics or infographics / 图标或信息图
- Customer review photos / 买家秀图片
- Color swatches or pattern samples / 颜色色块
- Certificate or warranty images / 证书或保修图
- Text-heavy promotional graphics / 文字型促销图

Only include images that show the ACTUAL PRODUCT being sold (e.g., clothing on model, product from different angles, product in use).

If you cannot access the page or find images, return an empty array: []"""

            messages = [{"role": "user", "content": prompt}]

            result_text = await self.gemini_client.chat_completion(
                messages=messages,
                temperature=0.1,
            )

            # Parse JSON response
            import json
            import re

            result_text = re.sub(r'^```json?\s*\n?', '', result_text, flags=re.IGNORECASE)
            result_text = re.sub(r'\n?```\s*$', '', result_text)
            result_text = result_text.strip()

            try:
                images = json.loads(result_text)
                if isinstance(images, list):
                    # Validate URLs
                    valid_images = []
                    for img in images:
                        if isinstance(img, dict) and img.get("url", "").startswith("http"):
                            valid_images.append(img)
                    return valid_images[:5]
            except json.JSONDecodeError:
                log.warning("gemini_image_extraction_json_parse_failed", result=result_text[:200])

            return []

        except GeminiError as e:
            log.warning("gemini_image_extraction_failed", error=str(e))
            return []

    async def _analyze_image_colors(
        self,
        image_urls: list[str],
        log: Any,
    ) -> dict[str, Any]:
        """Analyze product images to extract color scheme using Gemini vision.

        Args:
            image_urls: List of product image URLs
            log: Logger instance

        Returns:
            Color scheme dict with primary, secondary, accent colors
        """
        if not image_urls:
            return {
                "primary_color": "#1a1a2e",
                "secondary_color": "#16213e",
                "accent_color": "#e94560",
                "text_color": "#ffffff",
                "background_color": "#0f0f1a",
                "style_description": "Modern dark theme with vibrant accent",
            }

        try:
            # Use first 2 images for color analysis
            images_to_analyze = image_urls[:2]

            prompt = f"""You are a professional color consultant and brand designer. Analyze the product images to create a premium, cohesive color palette for a high-converting landing page.

Image URLs to analyze:
{chr(10).join(f'- {url}' for url in images_to_analyze)}

ANALYSIS APPROACH:
1. Identify the dominant colors in the product itself
2. Determine the product's aesthetic category (luxury, casual, tech, fashion, etc.)
3. Choose complementary colors that enhance the product's appeal
4. Ensure the palette creates a premium, professional impression

Provide a color scheme in JSON format:
- primary_color: The main brand/product color extracted from the product (hex code)
- secondary_color: A sophisticated complementary color for section backgrounds (hex code)
- accent_color: A vibrant, attention-grabbing color for CTA buttons - should contrast well and create urgency (hex code)
- text_color: Primary text color with excellent readability (hex code)
- background_color: Page background - can be light (#FFFFFF-#F5F5F5) or dark (#0F172A-#1F2937) depending on product aesthetic (hex code)
- gradient_start: Optional gradient start color for buttons/accents (hex code)
- gradient_end: Optional gradient end color for buttons/accents (hex code)
- style_description: A descriptive phrase for the overall aesthetic (e.g., "Luxurious dark theme with gold accents", "Clean minimalist with ocean blue tones")

COLOR HARMONY RULES:
- For luxury/fashion products: Consider dark backgrounds with metallic accents (gold, silver)
- For tech products: Modern blues, purples, or dark themes with neon accents
- For lifestyle products: Warm, inviting palettes with natural tones
- For sports/fitness: Bold, energetic colors with high contrast
- Accent color MUST stand out significantly from background for CTAs
- Ensure WCAG AA contrast ratio (4.5:1) between text and background

Output ONLY valid JSON, no explanations."""

            messages = [{"role": "user", "content": prompt}]

            result_text = await self.gemini_client.chat_completion(
                messages=messages,
                temperature=0.3,
            )

            # Parse JSON response
            import json
            import re

            result_text = re.sub(r'^```json?\s*\n?', '', result_text, flags=re.IGNORECASE)
            result_text = re.sub(r'\n?```\s*$', '', result_text)

            try:
                color_scheme = json.loads(result_text)
                log.info(
                    "image_colors_analyzed",
                    primary=color_scheme.get("primary_color"),
                    accent=color_scheme.get("accent_color"),
                )
                return color_scheme
            except json.JSONDecodeError:
                log.warning("color_analysis_json_parse_failed")
                return {
                    "primary_color": "#1a1a2e",
                    "secondary_color": "#16213e",
                    "accent_color": "#e94560",
                    "text_color": "#ffffff",
                    "background_color": "#0f0f1a",
                    "style_description": "Modern dark theme",
                }

        except GeminiError as e:
            log.warning("image_color_analysis_failed", error=str(e))
            return {
                "primary_color": "#1a1a2e",
                "secondary_color": "#16213e",
                "accent_color": "#e94560",
                "text_color": "#ffffff",
                "background_color": "#0f0f1a",
                "style_description": "Modern dark theme",
            }

    async def _generate_html_versions(
        self,
        product_info: dict[str, Any],
        images: list[dict[str, Any]],
        styles: list[str],
        language: str,
        product_url: str,
        color_scheme: dict[str, Any],
        log: Any,
    ) -> list[dict[str, Any]]:
        """Generate HTML landing page versions.

        Args:
            product_info: Product information
            images: Product images
            styles: Design styles
            language: Content language
            product_url: Original product page URL for purchase links
            color_scheme: Color scheme extracted from product images
            log: Logger instance

        Returns:
            List of HTML version objects
        """
        generator = GeneratePageContentTool(gemini_client=self.gemini_client)

        result = await generator.execute(
            parameters={
                "product_info": product_info,
                "product_images": images,
                "styles": styles,
                "language": language,
                "product_url": product_url,
                "color_scheme": color_scheme,
            },
            context={},
        )

        return [v for v in result.get("versions", []) if v.get("html_content")]

    async def _save_landing_pages(
        self,
        html_versions: list[dict[str, Any]],
        page_name: str,
        product_url: str,
        language: str,
        user_id: int,
        log: Any,
    ) -> list[dict[str, Any]]:
        """Save landing pages to backend via MCP.

        Args:
            html_versions: HTML version objects
            page_name: Base page name
            product_url: Product URL
            language: Content language
            user_id: User ID
            log: Logger instance

        Returns:
            List of saved landing page objects
        """
        saved_pages = []

        for version in html_versions:
            version_id = version.get("version_id", "A")
            style = version.get("style", "modern")
            full_name = f"{page_name}-{version_id}"

            try:
                result = await self.mcp_client.call_tool(
                    tool_name="create_landing_page",
                    parameters={
                        "user_id": user_id,
                        "name": full_name,
                        "product_url": product_url,
                        "template": style,
                        "language": language,
                        "html_content": version["html_content"],
                    },
                )

                saved_pages.append({
                    "id": result.get("id"),
                    "version": version_id,
                    "name": full_name,
                    "style": style,
                    "description": version.get("description", ""),
                    "url": result.get("url"),
                    "status": result.get("status", "draft"),
                    "saved": True,
                })

                log.info(
                    "landing_page_saved",
                    version=version_id,
                    page_id=result.get("id"),
                )

            except MCPError as e:
                log.error("landing_page_save_failed", version=version_id, error=str(e))
                saved_pages.append({
                    "version": version_id,
                    "name": full_name,
                    "style": style,
                    "html_content": version["html_content"],
                    "saved": False,
                    "error": str(e),
                })

        return saved_pages


class TranslateContentTool(AgentTool):
    """Tool for translating content using Gemini.

    This tool translates landing page content while maintaining
    tone, style, and marketing effectiveness.
    """

    def __init__(self, gemini_client: GeminiClient | None = None):
        """Initialize the translate content tool.

        Args:
            gemini_client: Gemini client for translation
        """
        metadata = ToolMetadata(
            name="translate_content_tool",
            description=(
                "Translate landing page content using AI. "
                "Maintains tone, style, and marketing effectiveness "
                "while adapting to target language and culture."
            ),
            category=ToolCategory.AGENT_CUSTOM,
            parameters=[
                ToolParameter(
                    name="content",
                    type="string",
                    description="Content to translate",
                    required=True,
                ),
                ToolParameter(
                    name="target_language",
                    type="string",
                    description="Target language code (e.g., 'zh', 'es', 'fr')",
                    required=True,
                ),
                ToolParameter(
                    name="source_language",
                    type="string",
                    description="Source language code (default: 'en')",
                    required=False,
                    default="en",
                ),
            ],
            returns="object with translated content",
            credit_cost=3.0,
            tags=["landing_page", "translation", "localization", "ai"],
        )

        super().__init__(metadata)
        self.gemini_client = gemini_client or GeminiClient()

    async def execute(
        self,
        parameters: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute content translation."""
        content = parameters.get("content", "")
        target_language = parameters.get("target_language")
        source_language = parameters.get("source_language", "en")

        log = logger.bind(
            tool=self.name,
            source_language=source_language,
            target_language=target_language,
        )
        log.info("translate_content_start")

        try:
            prompt = f"""Translate the following marketing content from {source_language} to {target_language}.

Content:
{content}

Important: Maintain the original tone, style, and marketing effectiveness.
Adapt idioms and cultural references appropriately for the target audience.

Provide a natural, culturally appropriate translation that maintains marketing impact."""

            messages = [{"role": "user", "content": prompt}]

            translated_text = await self.gemini_client.chat_completion(
                messages=messages,
                temperature=0.3,
            )

            log.info("translate_content_complete")

            return {
                "success": True,
                "translated_content": translated_text,
                "source_language": source_language,
                "target_language": target_language,
                "message": f"Content translated to {target_language}",
            }

        except GeminiError as e:
            log.error("gemini_error", error=str(e))
            raise ToolExecutionError(
                message=f"Content translation failed: {e.message}",
                tool_name=self.name,
                error_code=e.code,
            )


class OptimizeCopyTool(AgentTool):
    """Tool for optimizing copy for conversions using Gemini."""

    def __init__(self, gemini_client: GeminiClient | None = None):
        """Initialize the optimize copy tool."""
        metadata = ToolMetadata(
            name="optimize_copy_tool",
            description=(
                "Optimize landing page copy for better conversions using AI. "
                "Analyzes current copy and provides improved versions "
                "with better clarity, persuasion, and call-to-actions."
            ),
            category=ToolCategory.AGENT_CUSTOM,
            parameters=[
                ToolParameter(
                    name="content",
                    type="string",
                    description="Current landing page copy",
                    required=True,
                ),
                ToolParameter(
                    name="optimization_goal",
                    type="string",
                    description="Primary optimization goal",
                    required=False,
                    default="conversions",
                    enum=["conversions", "clarity", "engagement", "trust"],
                ),
            ],
            returns="object with optimized copy and suggestions",
            credit_cost=3.0,
            tags=["landing_page", "optimization", "copywriting", "ai"],
        )

        super().__init__(metadata)
        self.gemini_client = gemini_client or GeminiClient()

    async def execute(
        self,
        parameters: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute copy optimization."""
        content = parameters.get("content", "")
        optimization_goal = parameters.get("optimization_goal", "conversions")

        log = logger.bind(tool=self.name, optimization_goal=optimization_goal)
        log.info("optimize_copy_start")

        goal_descriptions = {
            "conversions": "maximize conversion rate and drive action",
            "clarity": "improve clarity and understanding",
            "engagement": "increase engagement and time on page",
            "trust": "build trust and credibility",
        }

        goal_desc = goal_descriptions.get(optimization_goal, optimization_goal)

        try:
            prompt = f"""Optimize this landing page copy to {goal_desc}.

Current Copy:
{content}

Provide:
1. Optimized Version: Improved copy with specific changes
2. Key Improvements: What was changed and why
3. A/B Test Suggestions: Alternative versions to test

Focus on:
- Clear value proposition
- Compelling headlines
- Strong call-to-actions
- Persuasive language
- Removing friction"""

            messages = [{"role": "user", "content": prompt}]

            optimized_text = await self.gemini_client.chat_completion(
                messages=messages,
                temperature=0.5,
            )

            log.info("optimize_copy_complete")

            return {
                "success": True,
                "optimized_copy": optimized_text,
                "optimization_goal": optimization_goal,
                "message": "Copy optimized successfully",
            }

        except GeminiError as e:
            log.error("gemini_error", error=str(e))
            raise ToolExecutionError(
                message=f"Copy optimization failed: {e.message}",
                tool_name=self.name,
                error_code=e.code,
            )


# Factory function to create all landing page tools
def create_landing_page_tools(
    gemini_client: GeminiClient | None = None,
    mcp_client: MCPClient | None = None,
) -> list[AgentTool]:
    """Create all landing page tools.

    Args:
        gemini_client: Gemini client instance
        mcp_client: MCP client instance

    Returns:
        List of landing page tools
    """
    return [
        GeneratePageContentTool(gemini_client=gemini_client),
        GenerateLandingPageTool(gemini_client=gemini_client, mcp_client=mcp_client),
        TranslateContentTool(gemini_client=gemini_client),
        OptimizeCopyTool(gemini_client=gemini_client),
    ]
