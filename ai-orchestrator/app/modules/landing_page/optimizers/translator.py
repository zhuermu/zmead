"""
Translator for Landing Page module.

Uses Gemini 2.5 Flash to translate landing page content to multiple languages.
Supports English, Spanish, French, and Chinese.

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
"""

import copy
import structlog
from pydantic import BaseModel, Field

from app.services.gemini_client import GeminiClient, GeminiError
from ..models import TranslationResult

logger = structlog.get_logger(__name__)


class TranslatedSection(BaseModel):
    """Translated content for a single section."""

    section_name: str = Field(description="Name of the section")
    original_text: str = Field(description="Original text before translation")
    translated_text: str = Field(description="Translated text")


class TranslationResponse(BaseModel):
    """Structured response from AI for translation."""

    translations: list[TranslatedSection] = Field(
        description="List of translated sections"
    )
    source_language: str = Field(description="Detected or specified source language")
    target_language: str = Field(description="Target language code")


class TranslationError(Exception):
    """Exception raised for translation errors."""

    def __init__(
        self,
        message: str,
        code: str = "TRANSLATION_ERROR",
        retryable: bool = False,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.retryable = retryable


class UnsupportedLanguageError(TranslationError):
    """Exception raised when target language is not supported."""

    def __init__(self, language: str):
        super().__init__(
            message=f"Unsupported language: {language}",
            code="UNSUPPORTED_LANGUAGE",
            retryable=False,
        )
        self.language = language


class Translator:
    """Translator for landing page content.

    Translates landing page content using Gemini 2.5 Flash AI model.
    Supports multiple languages and preserves original structure.

    Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
    """

    # Supported languages with their display names
    SUPPORTED_LANGUAGES = {
        "en": "English",
        "es": "Spanish (Español)",
        "fr": "French (Français)",
        "zh": "Chinese (中文)",
    }

    # Language-specific translation instructions
    LANGUAGE_INSTRUCTIONS = {
        "en": """Translate to English.
- Use clear, professional American English
- Maintain marketing tone and persuasive language
- Keep technical terms where appropriate""",
        "es": """Translate to Spanish (Español).
- Use neutral Latin American Spanish
- Maintain formal 'usted' form for marketing
- Adapt idioms appropriately for Spanish-speaking markets""",
        "fr": """Translate to French (Français).
- Use standard French (France)
- Maintain formal 'vous' form
- Adapt marketing expressions for French market""",
        "zh": """Translate to Chinese (中文).
- Use Simplified Chinese characters
- Adapt marketing language for Chinese market
- Keep brand names in original form with Chinese explanation if needed""",
    }

    def __init__(self, gemini_client: GeminiClient | None = None):
        """Initialize Translator.

        Args:
            gemini_client: Gemini client for AI translation. If None, creates new instance.
        """
        self.gemini_client = gemini_client or GeminiClient()

    def is_language_supported(self, language_code: str) -> bool:
        """Check if a language is supported.

        Args:
            language_code: ISO 639-1 language code (e.g., 'en', 'es', 'fr', 'zh')

        Returns:
            True if language is supported, False otherwise
        """
        return language_code.lower() in self.SUPPORTED_LANGUAGES

    def get_supported_languages(self) -> dict[str, str]:
        """Get dictionary of supported languages.

        Returns:
            Dictionary mapping language codes to display names
        """
        return self.SUPPORTED_LANGUAGES.copy()

    async def translate(
        self,
        content: dict,
        target_language: str,
        sections: list[str] | None = None,
        source_language: str = "en",
    ) -> dict:
        """Translate landing page content.

        Uses Gemini 2.5 Flash to translate the provided content to the target language.
        Preserves original structure and format.

        Args:
            content: Dictionary containing landing page content to translate
            target_language: Target language code (en, es, fr, zh)
            sections: Optional list of sections to translate. If None, translates all.
            source_language: Source language code (default: 'en')

        Returns:
            Dictionary with translated content preserving original structure

        Raises:
            UnsupportedLanguageError: If target language is not supported
            TranslationError: If translation fails

        Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
        """
        log = logger.bind(
            target_language=target_language,
            source_language=source_language,
            sections=sections,
        )

        log.info("translation_start")

        # Normalize language code
        target_language = target_language.lower()
        source_language = source_language.lower()

        # Validate target language
        if not self.is_language_supported(target_language):
            log.warning(
                "translation_unsupported_language",
                language=target_language,
            )
            raise UnsupportedLanguageError(target_language)

        # If source and target are the same, return original content
        if source_language == target_language:
            log.info("translation_same_language_skip")
            return content.copy()

        # Extract text content to translate
        texts_to_translate = self._extract_texts(content, sections)

        if not texts_to_translate:
            log.info("translation_no_content")
            return content.copy()

        try:
            # Build translation prompt
            prompt = self._build_translation_prompt(
                texts=texts_to_translate,
                source_language=source_language,
                target_language=target_language,
            )

            # Call Gemini 2.5 Flash for translation
            result = await self.gemini_client.fast_structured_output(
                messages=[
                    {
                        "role": "system",
                        "content": """You are a professional translator specializing in marketing and e-commerce content.
Your task is to translate landing page content while:
- Preserving the original meaning and tone
- Adapting marketing language for the target culture
- Maintaining persuasive and engaging copy
- Keeping proper nouns and brand names unchanged unless specified""",
                    },
                    {"role": "user", "content": prompt},
                ],
                schema=TranslationResponse,
                temperature=0.3,  # Lower temperature for more consistent translations
            )

            # Apply translations to content
            translated_content = self._apply_translations(
                content=content,
                translations=result.translations,
            )

            log.info(
                "translation_success",
                translated_sections=len(result.translations),
            )

            return translated_content

        except GeminiError as e:
            log.error(
                "translation_gemini_error",
                error=str(e),
                error_code=e.code,
            )
            raise TranslationError(
                message=f"Translation failed: {str(e)}",
                code="AI_TRANSLATION_FAILED",
                retryable=e.retryable,
            )

        except Exception as e:
            log.error(
                "translation_unexpected_error",
                error=str(e),
                exc_info=True,
            )
            raise TranslationError(
                message=f"Translation failed: {str(e)}",
                code="TRANSLATION_ERROR",
                retryable=False,
            )

    def _extract_texts(
        self,
        content: dict,
        sections: list[str] | None = None,
    ) -> list[dict]:
        """Extract text content from landing page structure.

        Args:
            content: Landing page content dictionary
            sections: Optional list of sections to extract

        Returns:
            List of dicts with section_path and text
        """
        texts = []

        # Define extractable fields for each section
        section_fields = {
            "hero": ["headline", "subheadline", "cta_text"],
            "features": ["title", "description"],
            "reviews": ["text"],
            "faq": ["question", "answer"],
            "cta": ["text"],
        }

        # Filter sections if specified
        if sections:
            section_fields = {
                k: v for k, v in section_fields.items() if k in sections
            }

        for section_name, fields in section_fields.items():
            section_content = content.get(section_name)
            if not section_content:
                continue

            if isinstance(section_content, dict):
                # Single section (hero, cta)
                for field in fields:
                    if field in section_content and section_content[field]:
                        texts.append({
                            "section_path": f"{section_name}.{field}",
                            "text": section_content[field],
                        })
            elif isinstance(section_content, list):
                # List sections (features, reviews, faq)
                for idx, item in enumerate(section_content):
                    if isinstance(item, dict):
                        for field in fields:
                            if field in item and item[field]:
                                texts.append({
                                    "section_path": f"{section_name}[{idx}].{field}",
                                    "text": item[field],
                                })

        return texts

    def _build_translation_prompt(
        self,
        texts: list[dict],
        source_language: str,
        target_language: str,
    ) -> str:
        """Build the translation prompt for the AI model.

        Args:
            texts: List of text items to translate
            source_language: Source language code
            target_language: Target language code

        Returns:
            Complete prompt string
        """
        source_name = self.SUPPORTED_LANGUAGES.get(source_language, source_language)
        target_name = self.SUPPORTED_LANGUAGES.get(target_language, target_language)
        language_instruction = self.LANGUAGE_INSTRUCTIONS.get(
            target_language,
            f"Translate to {target_name}.",
        )

        # Format texts for translation
        text_items = "\n".join([
            f"- Section: {t['section_path']}\n  Text: \"{t['text']}\""
            for t in texts
        ])

        return f"""Translate the following landing page content from {source_name} to {target_name}.

{language_instruction}

Content to translate:
{text_items}

For each item, provide:
1. The section_name (use the exact section_path provided)
2. The original_text
3. The translated_text

Maintain the same structure and preserve any HTML tags, URLs, or special formatting."""

    def _apply_translations(
        self,
        content: dict,
        translations: list[TranslatedSection],
    ) -> dict:
        """Apply translations to the content structure.

        Args:
            content: Original content dictionary
            translations: List of translated sections

        Returns:
            Content dictionary with translations applied
        """
        # Create a deep copy to avoid modifying original
        import copy
        translated_content = copy.deepcopy(content)

        # Build a lookup map for translations
        translation_map = {
            t.section_name: t.translated_text for t in translations
        }

        # Apply translations
        for section_path, translated_text in translation_map.items():
            self._set_nested_value(translated_content, section_path, translated_text)

        return translated_content

    def _set_nested_value(self, obj: dict, path: str, value: str) -> None:
        """Set a value in a nested dictionary using dot notation with array indices.

        Args:
            obj: Dictionary to modify
            path: Path like 'hero.headline' or 'features[0].title'
            value: Value to set
        """
        import re

        # Parse path into parts
        parts = []
        for part in path.split("."):
            # Check for array index
            match = re.match(r"(\w+)\[(\d+)\]", part)
            if match:
                parts.append(match.group(1))
                parts.append(int(match.group(2)))
            else:
                parts.append(part)

        # Navigate to the target location
        current = obj
        for i, part in enumerate(parts[:-1]):
            if isinstance(part, int):
                if isinstance(current, list) and part < len(current):
                    current = current[part]
                else:
                    return  # Invalid path
            elif isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return  # Invalid path

        # Set the value
        final_key = parts[-1]
        if isinstance(final_key, int):
            if isinstance(current, list) and final_key < len(current):
                current[final_key] = value
        elif isinstance(current, dict):
            current[final_key] = value

    async def translate_landing_page(
        self,
        landing_page_id: str,
        content: dict,
        target_language: str,
        sections: list[str] | None = None,
        source_language: str = "en",
        user_id: str = "user",
        base_url: str = "https://{user_id}.aae-pages.com",
    ) -> TranslationResult:
        """Translate a complete landing page and generate new language version URL.

        This method translates the landing page content while preserving the original
        structure and format, then generates a new URL for the translated version.

        Args:
            landing_page_id: Original landing page ID
            content: Landing page content dictionary to translate
            target_language: Target language code (en, es, fr, zh)
            sections: Optional list of sections to translate. If None, translates all.
            source_language: Source language code (default: 'en')
            user_id: User ID for URL generation
            base_url: Base URL template for generating the translated page URL

        Returns:
            TranslationResult with translated content, new ID, and URL

        Raises:
            UnsupportedLanguageError: If target language is not supported
            TranslationError: If translation fails

        Requirements: 5.1, 5.2, 5.3
        """
        log = logger.bind(
            landing_page_id=landing_page_id,
            target_language=target_language,
            source_language=source_language,
        )

        log.info("translate_landing_page_start")

        # Normalize language code
        target_language = target_language.lower()
        source_language = source_language.lower()

        # Validate target language
        if not self.is_language_supported(target_language):
            log.warning(
                "translate_landing_page_unsupported_language",
                language=target_language,
            )
            raise UnsupportedLanguageError(target_language)

        # Generate new landing page ID for translated version
        translated_landing_page_id = f"{landing_page_id}_{target_language}"

        # Generate URL for translated version
        # Format: https://{user_id}.aae-pages.com/{landing_page_id}?lang={target_language}
        formatted_base_url = base_url.format(user_id=user_id)
        translated_url = f"{formatted_base_url}/{landing_page_id}?lang={target_language}"

        # If source and target are the same, return original content with new URL
        if source_language == target_language:
            log.info("translate_landing_page_same_language_skip")
            return TranslationResult(
                translated_landing_page_id=translated_landing_page_id,
                url=translated_url,
                translations=copy.deepcopy(content),
                source_language=source_language,
                target_language=target_language,
            )

        # Translate the content (preserves structure)
        translated_content = await self.translate(
            content=content,
            target_language=target_language,
            sections=sections,
            source_language=source_language,
        )

        log.info(
            "translate_landing_page_success",
            translated_landing_page_id=translated_landing_page_id,
            translated_url=translated_url,
        )

        return TranslationResult(
            translated_landing_page_id=translated_landing_page_id,
            url=translated_url,
            translations=translated_content,
            source_language=source_language,
            target_language=target_language,
        )

    def generate_language_url(
        self,
        landing_page_id: str,
        target_language: str,
        user_id: str = "user",
        base_url: str = "https://{user_id}.aae-pages.com",
    ) -> str:
        """Generate URL for a translated landing page version.

        Creates a URL that includes the language parameter for the translated version.

        Args:
            landing_page_id: Original landing page ID
            target_language: Target language code
            user_id: User ID for URL generation
            base_url: Base URL template

        Returns:
            URL string for the translated landing page

        Requirements: 5.3
        """
        formatted_base_url = base_url.format(user_id=user_id)
        return f"{formatted_base_url}/{landing_page_id}?lang={target_language.lower()}"

    def generate_translated_id(
        self,
        landing_page_id: str,
        target_language: str,
    ) -> str:
        """Generate ID for a translated landing page version.

        Creates a unique ID by appending the language code to the original ID.

        Args:
            landing_page_id: Original landing page ID
            target_language: Target language code

        Returns:
            New landing page ID for the translated version

        Requirements: 5.3
        """
        return f"{landing_page_id}_{target_language.lower()}"
