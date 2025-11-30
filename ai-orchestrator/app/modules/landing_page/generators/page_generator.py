"""
Page Generator for Landing Page module.

This module provides the PageGenerator class for generating landing page
structures from product information using AI-powered headline optimization.

Requirements: 2.1, 2.2, 2.3, 2.4
"""

import json
import uuid
from typing import Literal

import structlog
from pydantic import BaseModel

from app.services.gemini_client import GeminiClient

from ..models import (
    CTASection,
    FAQItem,
    Feature,
    HeroSection,
    LandingPageContent,
    ProductInfo,
    Review,
    ThemeConfig,
)

logger = structlog.get_logger(__name__)


# Template configurations
TEMPLATE_CONFIGS = {
    "modern": {
        "primary_color": "#3B82F6",
        "secondary_color": "#10B981",
        "font_family": "Inter",
        "style": "clean and professional",
    },
    "minimal": {
        "primary_color": "#1F2937",
        "secondary_color": "#6B7280",
        "font_family": "Helvetica",
        "style": "simple and elegant",
    },
    "vibrant": {
        "primary_color": "#F59E0B",
        "secondary_color": "#EF4444",
        "font_family": "Poppins",
        "style": "bold and energetic",
    },
}


class HeroGenerationResult(BaseModel):
    """Structured output for hero section generation."""

    headline: str
    subheadline: str
    cta_text: str


class FeatureGenerationResult(BaseModel):
    """Structured output for feature extraction."""

    features: list[dict]


class FAQGenerationResult(BaseModel):
    """Structured output for FAQ generation."""

    faqs: list[dict]


class PageGenerator:
    """落地页结构生成器

    Generates landing page structures from product information with:
    - AI-optimized headlines using Gemini 2.5 Pro
    - Feature extraction from product info
    - Review section handling
    - FAQ generation
    - Template-based theming

    Requirements: 2.1, 2.2, 2.3, 2.4
    """

    SUPPORTED_TEMPLATES = ["modern", "minimal", "vibrant"]
    DEFAULT_TEMPLATE = "modern"
    MAX_FEATURES = 3
    MAX_REVIEWS = 3
    MAX_FAQS = 5

    def __init__(self, gemini_client: GeminiClient | None = None):
        """Initialize PageGenerator.

        Args:
            gemini_client: Gemini client for AI generation. Creates new if None.
        """
        self.gemini = gemini_client or GeminiClient()

    async def generate(
        self,
        product_info: ProductInfo,
        template: str = "modern",
        language: str = "en",
        pixel_id: str | None = None,
    ) -> LandingPageContent:
        """生成落地页结构

        Generates a complete landing page structure from product information.

        Args:
            product_info: Product information extracted from e-commerce platform
            template: Template name (modern, minimal, vibrant)
            language: Language code (en, es, fr, zh)
            pixel_id: Facebook Pixel ID for tracking

        Returns:
            Complete LandingPageContent structure

        Requirements: 2.1
        """
        # Validate template
        if template not in self.SUPPORTED_TEMPLATES:
            logger.warning(
                "invalid_template_using_default",
                template=template,
                default=self.DEFAULT_TEMPLATE,
            )
            template = self.DEFAULT_TEMPLATE

        landing_page_id = f"lp_{uuid.uuid4().hex[:8]}"

        logger.info(
            "page_generation_start",
            landing_page_id=landing_page_id,
            template=template,
            language=language,
            product_title=product_info.title,
        )

        # Generate hero section with AI-optimized headlines
        hero = await self.generate_hero_section(product_info, template, language)

        # Extract/generate features
        features = await self.extract_features(product_info, language)

        # Process reviews (limit to top 3)
        reviews = self._process_reviews(product_info.reviews)

        # Generate FAQ
        faq = await self._generate_faq(product_info, language)

        # Create CTA section
        cta = self._create_cta_section(product_info)

        # Get theme config for template
        theme = self._get_theme_config(template)

        landing_page = LandingPageContent(
            landing_page_id=landing_page_id,
            template=template,
            language=language,
            hero=hero,
            features=features,
            reviews=reviews,
            faq=faq,
            cta=cta,
            theme=theme,
            pixel_id=pixel_id,
        )

        logger.info(
            "page_generation_complete",
            landing_page_id=landing_page_id,
            feature_count=len(features),
            review_count=len(reviews),
            faq_count=len(faq),
        )

        return landing_page

    async def generate_hero_section(
        self,
        product_info: ProductInfo,
        template: str,
        language: str = "en",
    ) -> HeroSection:
        """生成 Hero 区域，使用 AI 优化标题

        Uses Gemini 2.5 Pro to generate optimized headlines with emotional
        appeal and urgency.

        Args:
            product_info: Product information
            template: Template name for style guidance
            language: Target language

        Returns:
            HeroSection with AI-optimized content

        Requirements: 2.2
        """
        template_config = TEMPLATE_CONFIGS.get(template, TEMPLATE_CONFIGS["modern"])
        style = template_config["style"]

        # Language-specific instructions
        lang_instructions = {
            "en": "Generate in English",
            "es": "Generate in Spanish (Español)",
            "fr": "Generate in French (Français)",
            "zh": "Generate in Chinese (中文)",
        }
        lang_instruction = lang_instructions.get(language, "Generate in English")

        prompt = f"""You are an expert landing page copywriter. Generate compelling hero section content for a product landing page.

Product Information:
- Title: {product_info.title}
- Price: {product_info.currency} {product_info.price}
- Description: {product_info.description[:500]}
- Key Features: {', '.join(product_info.features[:5]) if product_info.features else 'Not specified'}

Requirements:
- Style: {style}
- {lang_instruction}
- Headline: Create an emotionally compelling headline (max 10 words) that highlights the main benefit
- Subheadline: Write a supporting statement (max 20 words) that reinforces the value proposition
- CTA Text: Create an action-oriented button text that includes the price (max 5 words)

The headline should:
1. Create emotional appeal
2. Highlight the key benefit
3. Be concise and memorable

Return a JSON object with: headline, subheadline, cta_text"""

        logger.info(
            "hero_generation_start",
            product_title=product_info.title,
            template=template,
            language=language,
        )

        try:
            result = await self.gemini.structured_output(
                messages=[{"role": "user", "content": prompt}],
                schema=HeroGenerationResult,
                temperature=0.7,
            )

            hero = HeroSection(
                headline=result.headline,
                subheadline=result.subheadline,
                image=product_info.main_image,
                cta_text=result.cta_text,
            )

            logger.info(
                "hero_generation_complete",
                headline=hero.headline[:50],
            )

            return hero

        except Exception as e:
            logger.error("hero_generation_failed", error=str(e))
            # Fallback to basic hero section
            return self._create_fallback_hero(product_info)

    async def extract_features(
        self,
        product_info: ProductInfo,
        language: str = "en",
        count: int = 3,
    ) -> list[Feature]:
        """提取核心卖点

        Extracts or generates 3 core selling points from product information.
        Uses AI to generate features if product doesn't have enough.

        Args:
            product_info: Product information
            language: Target language
            count: Number of features to extract (default 3)

        Returns:
            List of Feature objects

        Requirements: 2.3
        """
        count = min(count, self.MAX_FEATURES)

        # If product has enough features, use them directly
        if product_info.features and len(product_info.features) >= count:
            return [
                Feature(
                    title=self._truncate(feature, 50),
                    description=feature,
                    icon=self._suggest_icon(feature),
                )
                for feature in product_info.features[:count]
            ]

        # Use AI to generate/enhance features
        logger.info(
            "feature_extraction_with_ai",
            existing_features=len(product_info.features) if product_info.features else 0,
            target_count=count,
        )

        lang_instructions = {
            "en": "Generate in English",
            "es": "Generate in Spanish",
            "fr": "Generate in French",
            "zh": "Generate in Chinese",
        }
        lang_instruction = lang_instructions.get(language, "Generate in English")

        prompt = f"""Extract or generate {count} key selling points for this product.

Product Information:
- Title: {product_info.title}
- Description: {product_info.description[:500]}
- Existing Features: {', '.join(product_info.features) if product_info.features else 'None'}

Requirements:
- {lang_instruction}
- Each feature should have a short title (max 5 words) and description (max 20 words)
- Focus on benefits, not just features
- Suggest an appropriate icon name for each (e.g., "shield", "clock", "star", "check", "heart")

Return a JSON object with a "features" array containing objects with: title, description, icon"""

        try:
            result = await self.gemini.structured_output(
                messages=[{"role": "user", "content": prompt}],
                schema=FeatureGenerationResult,
                temperature=0.5,
            )

            features = [
                Feature(
                    title=f.get("title", "Feature")[:50],
                    description=f.get("description", "")[:200],
                    icon=f.get("icon", "star"),
                )
                for f in result.features[:count]
            ]

            logger.info("feature_extraction_complete", count=len(features))
            return features

        except Exception as e:
            logger.error("feature_extraction_failed", error=str(e))
            # Fallback to basic features from product info
            return self._create_fallback_features(product_info, count)

    def _process_reviews(self, reviews: list[Review]) -> list[Review]:
        """Process and limit reviews to top 3.

        Requirements: 2.4
        """
        if not reviews:
            return []

        # Sort by rating (highest first) and take top 3
        sorted_reviews = sorted(reviews, key=lambda r: r.rating, reverse=True)
        return sorted_reviews[: self.MAX_REVIEWS]

    async def _generate_faq(
        self,
        product_info: ProductInfo,
        language: str = "en",
    ) -> list[FAQItem]:
        """Generate FAQ section using AI.

        Args:
            product_info: Product information
            language: Target language

        Returns:
            List of FAQItem objects
        """
        lang_instructions = {
            "en": "Generate in English",
            "es": "Generate in Spanish",
            "fr": "Generate in French",
            "zh": "Generate in Chinese",
        }
        lang_instruction = lang_instructions.get(language, "Generate in English")

        prompt = f"""Generate 3-5 frequently asked questions for this product landing page.

Product Information:
- Title: {product_info.title}
- Price: {product_info.currency} {product_info.price}
- Description: {product_info.description[:300]}

Requirements:
- {lang_instruction}
- Questions should address common customer concerns
- Include questions about shipping, returns, and product quality
- Answers should be concise (max 50 words each)

Return a JSON object with a "faqs" array containing objects with: question, answer"""

        try:
            result = await self.gemini.structured_output(
                messages=[{"role": "user", "content": prompt}],
                schema=FAQGenerationResult,
                temperature=0.5,
            )

            faqs = [
                FAQItem(
                    question=f.get("question", ""),
                    answer=f.get("answer", ""),
                )
                for f in result.faqs[: self.MAX_FAQS]
            ]

            return faqs

        except Exception as e:
            logger.error("faq_generation_failed", error=str(e))
            return self._create_fallback_faq(language)

    def _create_cta_section(self, product_info: ProductInfo) -> CTASection:
        """Create CTA section from product info."""
        return CTASection(
            text=f"Buy Now - {product_info.currency} {product_info.price}",
            url=product_info.main_image,  # Placeholder, should be checkout URL
        )

    def _get_theme_config(self, template: str) -> ThemeConfig:
        """Get theme configuration for template."""
        config = TEMPLATE_CONFIGS.get(template, TEMPLATE_CONFIGS["modern"])
        return ThemeConfig(
            primary_color=config["primary_color"],
            secondary_color=config["secondary_color"],
            font_family=config["font_family"],
        )

    def _create_fallback_hero(self, product_info: ProductInfo) -> HeroSection:
        """Create fallback hero section when AI fails."""
        return HeroSection(
            headline=product_info.title[:60],
            subheadline=product_info.description[:100] if product_info.description else "",
            image=product_info.main_image,
            cta_text=f"Buy Now - {product_info.currency} {product_info.price}",
        )

    def _create_fallback_features(
        self,
        product_info: ProductInfo,
        count: int,
    ) -> list[Feature]:
        """Create fallback features when AI fails."""
        features = []

        # Use existing features if available
        if product_info.features:
            for feature in product_info.features[:count]:
                features.append(
                    Feature(
                        title=self._truncate(feature, 50),
                        description=feature,
                        icon=self._suggest_icon(feature),
                    )
                )

        # Fill remaining with generic features
        generic_features = [
            Feature(title="Premium Quality", description="High-quality materials and craftsmanship", icon="star"),
            Feature(title="Fast Shipping", description="Quick delivery to your doorstep", icon="truck"),
            Feature(title="Satisfaction Guaranteed", description="30-day money-back guarantee", icon="shield"),
        ]

        while len(features) < count and generic_features:
            features.append(generic_features.pop(0))

        return features[:count]

    def _create_fallback_faq(self, language: str) -> list[FAQItem]:
        """Create fallback FAQ when AI fails."""
        if language == "zh":
            return [
                FAQItem(question="发货需要多长时间？", answer="订单通常在1-3个工作日内发货。"),
                FAQItem(question="可以退货吗？", answer="是的，我们提供30天无理由退货服务。"),
                FAQItem(question="如何联系客服？", answer="您可以通过邮件或在线客服联系我们。"),
            ]
        return [
            FAQItem(question="How long does shipping take?", answer="Orders typically ship within 1-3 business days."),
            FAQItem(question="Can I return the product?", answer="Yes, we offer a 30-day money-back guarantee."),
            FAQItem(question="How can I contact support?", answer="You can reach us via email or live chat."),
        ]

    def _truncate(self, text: str, max_length: int) -> str:
        """Truncate text to max length."""
        if len(text) <= max_length:
            return text
        return text[: max_length - 3] + "..."

    def _suggest_icon(self, feature_text: str) -> str:
        """Suggest an icon based on feature text."""
        text_lower = feature_text.lower()

        icon_keywords = {
            "shield": ["protect", "secure", "safe", "guard", "warranty"],
            "clock": ["fast", "quick", "time", "hour", "minute", "speed"],
            "star": ["quality", "premium", "best", "top", "excellent"],
            "heart": ["love", "care", "comfort", "soft", "gentle"],
            "check": ["guarantee", "certified", "verified", "approved"],
            "truck": ["ship", "deliver", "free shipping", "fast delivery"],
            "battery": ["battery", "power", "charge", "long-lasting"],
            "wifi": ["wireless", "bluetooth", "connect", "wifi"],
            "volume": ["sound", "audio", "music", "noise"],
            "zap": ["energy", "powerful", "boost", "performance"],
        }

        for icon, keywords in icon_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return icon

        return "star"  # Default icon

    async def render_html(
        self,
        landing_page_data: dict,
        template: str = "modern",
    ) -> str:
        """Render landing page data as HTML.
        
        Generates a complete HTML page from landing page data structure.
        All CSS and JavaScript are inlined for standalone usage.
        
        Args:
            landing_page_data: Landing page data dict with sections
            template: Template name (modern, minimal, vibrant)
        
        Returns:
            Complete HTML string with inline CSS/JS
        """
        sections = landing_page_data.get("sections", {})
        hero = sections.get("hero", {})
        features = sections.get("features", [])
        reviews = sections.get("reviews", [])
        faq = sections.get("faq", [])
        cta = sections.get("cta", {})
        
        # Get theme config
        theme = self._get_theme_config(template)
        
        # Build HTML
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{landing_page_data.get('title', 'Landing Page')}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: {theme.font_family}, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            line-height: 1.6;
            color: #333;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
        }}
        
        /* Hero Section */
        .hero {{
            background: linear-gradient(135deg, {theme.primary_color} 0%, {theme.secondary_color} 100%);
            color: white;
            padding: 80px 20px;
            text-align: center;
        }}
        
        .hero h1 {{
            font-size: 3rem;
            margin-bottom: 20px;
            font-weight: 700;
        }}
        
        .hero p {{
            font-size: 1.5rem;
            margin-bottom: 30px;
            opacity: 0.95;
        }}
        
        .hero img {{
            max-width: 600px;
            width: 100%;
            height: auto;
            border-radius: 10px;
            margin: 30px 0;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}
        
        .cta-button {{
            display: inline-block;
            background: white;
            color: {theme.primary_color};
            padding: 15px 40px;
            font-size: 1.2rem;
            font-weight: 600;
            text-decoration: none;
            border-radius: 50px;
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        
        .cta-button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        }}
        
        /* Features Section */
        .features {{
            padding: 80px 20px;
            background: #f9fafb;
        }}
        
        .features h2 {{
            text-align: center;
            font-size: 2.5rem;
            margin-bottom: 50px;
            color: {theme.primary_color};
        }}
        
        .features-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 40px;
        }}
        
        .feature-card {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            text-align: center;
        }}
        
        .feature-card h3 {{
            font-size: 1.5rem;
            margin: 20px 0 10px;
            color: {theme.primary_color};
        }}
        
        .feature-card p {{
            color: #666;
        }}
        
        /* Reviews Section */
        .reviews {{
            padding: 80px 20px;
        }}
        
        .reviews h2 {{
            text-align: center;
            font-size: 2.5rem;
            margin-bottom: 50px;
            color: {theme.primary_color};
        }}
        
        .reviews-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 30px;
        }}
        
        .review-card {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        .review-rating {{
            color: #F59E0B;
            font-size: 1.2rem;
            margin-bottom: 10px;
        }}
        
        .review-text {{
            color: #666;
            font-style: italic;
        }}
        
        /* FAQ Section */
        .faq {{
            padding: 80px 20px;
            background: #f9fafb;
        }}
        
        .faq h2 {{
            text-align: center;
            font-size: 2.5rem;
            margin-bottom: 50px;
            color: {theme.primary_color};
        }}
        
        .faq-item {{
            background: white;
            padding: 25px;
            margin-bottom: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .faq-question {{
            font-size: 1.2rem;
            font-weight: 600;
            color: {theme.primary_color};
            margin-bottom: 10px;
        }}
        
        .faq-answer {{
            color: #666;
        }}
        
        /* Final CTA Section */
        .final-cta {{
            background: linear-gradient(135deg, {theme.primary_color} 0%, {theme.secondary_color} 100%);
            color: white;
            padding: 80px 20px;
            text-align: center;
        }}
        
        .final-cta h2 {{
            font-size: 2.5rem;
            margin-bottom: 30px;
        }}
        
        /* Responsive */
        @media (max-width: 768px) {{
            .hero h1 {{
                font-size: 2rem;
            }}
            
            .hero p {{
                font-size: 1.2rem;
            }}
            
            .features h2, .reviews h2, .faq h2, .final-cta h2 {{
                font-size: 2rem;
            }}
        }}
    </style>
</head>
<body>
    <!-- Hero Section -->
    <section class="hero">
        <div class="container">
            <h1>{hero.get('headline', 'Welcome')}</h1>
            <p>{hero.get('subheadline', '')}</p>
            {f'<img src="{hero.get("image")}" alt="Product Image">' if hero.get('image') else ''}
            <a href="#cta" class="cta-button">{hero.get('cta_text', 'Get Started')}</a>
        </div>
    </section>
    
    <!-- Features Section -->
    {self._render_features_section(features, theme) if features else ''}
    
    <!-- Reviews Section -->
    {self._render_reviews_section(reviews, theme) if reviews else ''}
    
    <!-- FAQ Section -->
    {self._render_faq_section(faq, theme) if faq else ''}
    
    <!-- Final CTA Section -->
    <section class="final-cta" id="cta">
        <div class="container">
            <h2>Ready to Get Started?</h2>
            <a href="{cta.get('url', '#')}" class="cta-button">{cta.get('text', 'Buy Now')}</a>
        </div>
    </section>
</body>
</html>"""
        
        return html
    
    def _render_features_section(self, features: list, theme: ThemeConfig) -> str:
        """Render features section HTML."""
        features_html = '<section class="features"><div class="container">'
        features_html += '<h2>Key Features</h2><div class="features-grid">'
        
        for feature in features:
            features_html += f'''
            <div class="feature-card">
                <h3>{feature.get('title', '')}</h3>
                <p>{feature.get('description', '')}</p>
            </div>
            '''
        
        features_html += '</div></div></section>'
        return features_html
    
    def _render_reviews_section(self, reviews: list, theme: ThemeConfig) -> str:
        """Render reviews section HTML."""
        reviews_html = '<section class="reviews"><div class="container">'
        reviews_html += '<h2>What Our Customers Say</h2><div class="reviews-grid">'
        
        for review in reviews:
            rating = review.get('rating', 5)
            stars = '★' * rating + '☆' * (5 - rating)
            reviews_html += f'''
            <div class="review-card">
                <div class="review-rating">{stars}</div>
                <p class="review-text">"{review.get('text', '')}"</p>
            </div>
            '''
        
        reviews_html += '</div></div></section>'
        return reviews_html
    
    def _render_faq_section(self, faq: list, theme: ThemeConfig) -> str:
        """Render FAQ section HTML."""
        faq_html = '<section class="faq"><div class="container">'
        faq_html += '<h2>Frequently Asked Questions</h2>'
        
        for item in faq:
            faq_html += f'''
            <div class="faq-item">
                <div class="faq-question">{item.get('question', '')}</div>
                <div class="faq-answer">{item.get('answer', '')}</div>
            </div>
            '''
        
        faq_html += '</div></section>'
        return faq_html
