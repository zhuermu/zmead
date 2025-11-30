"""
Tests for Translator class.

Tests the translation functionality for landing page content.

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.modules.landing_page.optimizers.translator import (
    Translator,
    TranslationError,
    UnsupportedLanguageError,
    TranslationResponse,
    TranslatedSection,
)
from app.services.gemini_client import GeminiError


@pytest.fixture
def mock_gemini_client():
    """Create a mock Gemini client for testing."""
    return MagicMock()


@pytest.fixture
def translator(mock_gemini_client):
    """Create a Translator instance with mock client."""
    return Translator(gemini_client=mock_gemini_client)


class TestTranslatorInit:
    """Tests for Translator initialization."""

    def test_init_custom_client(self):
        """Test initialization with custom Gemini client."""
        mock_client = MagicMock()
        translator = Translator(gemini_client=mock_client)
        assert translator.gemini_client is mock_client


class TestSupportedLanguages:
    """Tests for language support checking."""

    def test_supported_languages(self, translator):
        """Test that all required languages are supported."""
        # Requirements 5.4: Support English, Spanish, French, Chinese
        assert translator.is_language_supported("en")
        assert translator.is_language_supported("es")
        assert translator.is_language_supported("fr")
        assert translator.is_language_supported("zh")

    def test_unsupported_language(self, translator):
        """Test that unsupported languages return False."""
        assert not translator.is_language_supported("de")
        assert not translator.is_language_supported("ja")
        assert not translator.is_language_supported("invalid")

    def test_case_insensitive_language_check(self, translator):
        """Test that language check is case insensitive."""
        assert translator.is_language_supported("EN")
        assert translator.is_language_supported("Es")
        assert translator.is_language_supported("FR")
        assert translator.is_language_supported("ZH")

    def test_get_supported_languages(self, translator):
        """Test getting the list of supported languages."""
        languages = translator.get_supported_languages()
        
        assert "en" in languages
        assert "es" in languages
        assert "fr" in languages
        assert "zh" in languages
        assert len(languages) == 4


class TestTextExtraction:
    """Tests for text extraction from content."""

    def test_extract_hero_section(self, translator):
        """Test extracting text from hero section."""
        content = {
            "hero": {
                "headline": "Test Headline",
                "subheadline": "Test Subheadline",
                "cta_text": "Buy Now",
            }
        }
        
        texts = translator._extract_texts(content)
        
        assert len(texts) == 3
        paths = [t["section_path"] for t in texts]
        assert "hero.headline" in paths
        assert "hero.subheadline" in paths
        assert "hero.cta_text" in paths

    def test_extract_features_section(self, translator):
        """Test extracting text from features section."""
        content = {
            "features": [
                {"title": "Feature 1", "description": "Description 1"},
                {"title": "Feature 2", "description": "Description 2"},
            ]
        }
        
        texts = translator._extract_texts(content)
        
        assert len(texts) == 4
        paths = [t["section_path"] for t in texts]
        assert "features[0].title" in paths
        assert "features[0].description" in paths
        assert "features[1].title" in paths
        assert "features[1].description" in paths

    def test_extract_specific_sections(self, translator):
        """Test extracting only specific sections."""
        content = {
            "hero": {"headline": "Test Headline"},
            "features": [{"title": "Feature 1", "description": "Desc 1"}],
            "cta": {"text": "Buy Now"},
        }
        
        texts = translator._extract_texts(content, sections=["hero"])
        
        assert len(texts) == 1
        assert texts[0]["section_path"] == "hero.headline"

    def test_extract_empty_content(self, translator):
        """Test extracting from empty content."""
        content = {}
        
        texts = translator._extract_texts(content)
        
        assert len(texts) == 0


class TestApplyTranslations:
    """Tests for applying translations to content."""

    def test_apply_simple_translation(self, translator):
        """Test applying translation to simple field."""
        content = {"hero": {"headline": "Original"}}
        translations = [
            TranslatedSection(
                section_name="hero.headline",
                original_text="Original",
                translated_text="Traducido",
            )
        ]
        
        result = translator._apply_translations(content, translations)
        
        assert result["hero"]["headline"] == "Traducido"

    def test_apply_array_translation(self, translator):
        """Test applying translation to array item."""
        content = {"features": [{"title": "Original"}]}
        translations = [
            TranslatedSection(
                section_name="features[0].title",
                original_text="Original",
                translated_text="Traducido",
            )
        ]
        
        result = translator._apply_translations(content, translations)
        
        assert result["features"][0]["title"] == "Traducido"

    def test_apply_preserves_untranslated(self, translator):
        """Test that untranslated fields are preserved."""
        content = {
            "hero": {"headline": "Original", "image": "https://example.com/img.jpg"},
        }
        translations = [
            TranslatedSection(
                section_name="hero.headline",
                original_text="Original",
                translated_text="Traducido",
            )
        ]
        
        result = translator._apply_translations(content, translations)
        
        assert result["hero"]["headline"] == "Traducido"
        assert result["hero"]["image"] == "https://example.com/img.jpg"


class TestTranslate:
    """Tests for the main translate method."""

    @pytest.mark.asyncio
    async def test_translate_unsupported_language(self, translator):
        """Test that unsupported language raises error."""
        content = {"hero": {"headline": "Test"}}
        
        with pytest.raises(UnsupportedLanguageError) as exc_info:
            await translator.translate(content, target_language="de")
        
        assert exc_info.value.language == "de"
        assert exc_info.value.code == "UNSUPPORTED_LANGUAGE"

    @pytest.mark.asyncio
    async def test_translate_same_language_returns_original(self, translator):
        """Test that translating to same language returns original."""
        content = {"hero": {"headline": "Test"}}
        
        result = await translator.translate(
            content,
            target_language="en",
            source_language="en",
        )
        
        assert result == content

    @pytest.mark.asyncio
    async def test_translate_empty_content(self, translator):
        """Test translating empty content."""
        content = {}
        
        result = await translator.translate(content, target_language="es")
        
        assert result == {}

    @pytest.mark.asyncio
    async def test_translate_success(self):
        """Test successful translation."""
        mock_client = AsyncMock()
        mock_client.fast_structured_output = AsyncMock(
            return_value=TranslationResponse(
                translations=[
                    TranslatedSection(
                        section_name="hero.headline",
                        original_text="Hello World",
                        translated_text="Hola Mundo",
                    )
                ],
                source_language="en",
                target_language="es",
            )
        )
        
        translator = Translator(gemini_client=mock_client)
        content = {"hero": {"headline": "Hello World"}}
        
        result = await translator.translate(content, target_language="es")
        
        assert result["hero"]["headline"] == "Hola Mundo"
        mock_client.fast_structured_output.assert_called_once()

    @pytest.mark.asyncio
    async def test_translate_gemini_error(self):
        """Test that Gemini errors are wrapped in TranslationError."""
        mock_client = AsyncMock()
        mock_client.fast_structured_output = AsyncMock(
            side_effect=GeminiError("API Error", code="API_ERROR", retryable=True)
        )
        
        translator = Translator(gemini_client=mock_client)
        content = {"hero": {"headline": "Test"}}
        
        with pytest.raises(TranslationError) as exc_info:
            await translator.translate(content, target_language="es")
        
        assert exc_info.value.code == "AI_TRANSLATION_FAILED"
        assert exc_info.value.retryable is True

    @pytest.mark.asyncio
    async def test_translate_unexpected_error(self):
        """Test that unexpected errors are wrapped in TranslationError."""
        mock_client = AsyncMock()
        mock_client.fast_structured_output = AsyncMock(
            side_effect=ValueError("Unexpected error")
        )
        
        translator = Translator(gemini_client=mock_client)
        content = {"hero": {"headline": "Test"}}
        
        with pytest.raises(TranslationError) as exc_info:
            await translator.translate(content, target_language="es")
        
        assert exc_info.value.code == "TRANSLATION_ERROR"
        assert exc_info.value.retryable is False


class TestSetNestedValue:
    """Tests for the _set_nested_value helper method."""

    def test_set_simple_path(self, translator):
        """Test setting value with simple path."""
        obj = {"hero": {"headline": "old"}}
        
        translator._set_nested_value(obj, "hero.headline", "new")
        
        assert obj["hero"]["headline"] == "new"

    def test_set_array_path(self, translator):
        """Test setting value with array index in path."""
        obj = {"features": [{"title": "old"}]}
        
        translator._set_nested_value(obj, "features[0].title", "new")
        
        assert obj["features"][0]["title"] == "new"

    def test_set_invalid_path_no_error(self, translator):
        """Test that invalid path doesn't raise error."""
        obj = {"hero": {"headline": "old"}}
        
        # Should not raise, just silently fail
        translator._set_nested_value(obj, "invalid.path", "new")
        
        assert obj == {"hero": {"headline": "old"}}


class TestGenerateLanguageUrl:
    """Tests for URL generation for translated landing pages.
    
    Requirements: 5.3
    """

    def test_generate_language_url_basic(self, translator):
        """Test basic URL generation with language parameter."""
        url = translator.generate_language_url(
            landing_page_id="lp_123",
            target_language="es",
            user_id="user123",
        )
        
        assert url == "https://user123.aae-pages.com/lp_123?lang=es"

    def test_generate_language_url_normalizes_language(self, translator):
        """Test that language code is normalized to lowercase."""
        url = translator.generate_language_url(
            landing_page_id="lp_123",
            target_language="ES",
            user_id="user123",
        )
        
        assert url == "https://user123.aae-pages.com/lp_123?lang=es"

    def test_generate_language_url_custom_base(self, translator):
        """Test URL generation with custom base URL."""
        url = translator.generate_language_url(
            landing_page_id="lp_456",
            target_language="fr",
            user_id="testuser",
            base_url="https://{user_id}.custom-domain.com",
        )
        
        assert url == "https://testuser.custom-domain.com/lp_456?lang=fr"


class TestGenerateTranslatedId:
    """Tests for translated landing page ID generation.
    
    Requirements: 5.3
    """

    def test_generate_translated_id_basic(self, translator):
        """Test basic translated ID generation."""
        translated_id = translator.generate_translated_id(
            landing_page_id="lp_123",
            target_language="es",
        )
        
        assert translated_id == "lp_123_es"

    def test_generate_translated_id_normalizes_language(self, translator):
        """Test that language code is normalized to lowercase."""
        translated_id = translator.generate_translated_id(
            landing_page_id="lp_123",
            target_language="ZH",
        )
        
        assert translated_id == "lp_123_zh"


class TestTranslateLandingPage:
    """Tests for the translate_landing_page method.
    
    Requirements: 5.1, 5.2, 5.3
    """

    @pytest.mark.asyncio
    async def test_translate_landing_page_success(self):
        """Test successful landing page translation with URL generation."""
        mock_client = AsyncMock()
        mock_client.fast_structured_output = AsyncMock(
            return_value=TranslationResponse(
                translations=[
                    TranslatedSection(
                        section_name="hero.headline",
                        original_text="Hello World",
                        translated_text="Hola Mundo",
                    ),
                    TranslatedSection(
                        section_name="hero.subheadline",
                        original_text="Welcome",
                        translated_text="Bienvenido",
                    ),
                ],
                source_language="en",
                target_language="es",
            )
        )
        
        translator = Translator(gemini_client=mock_client)
        content = {
            "hero": {
                "headline": "Hello World",
                "subheadline": "Welcome",
                "image": "https://example.com/img.jpg",
            }
        }
        
        result = await translator.translate_landing_page(
            landing_page_id="lp_123",
            content=content,
            target_language="es",
            user_id="user123",
        )
        
        # Verify TranslationResult structure
        assert result.translated_landing_page_id == "lp_123_es"
        assert "lang=es" in str(result.url)
        assert result.source_language == "en"
        assert result.target_language == "es"
        
        # Verify translations preserve structure
        assert result.translations["hero"]["headline"] == "Hola Mundo"
        assert result.translations["hero"]["subheadline"] == "Bienvenido"
        # Non-text fields should be preserved
        assert result.translations["hero"]["image"] == "https://example.com/img.jpg"

    @pytest.mark.asyncio
    async def test_translate_landing_page_same_language(self, translator):
        """Test that same language returns original content with new URL."""
        content = {"hero": {"headline": "Test"}}
        
        result = await translator.translate_landing_page(
            landing_page_id="lp_123",
            content=content,
            target_language="en",
            source_language="en",
            user_id="user123",
        )
        
        assert result.translated_landing_page_id == "lp_123_en"
        assert "lang=en" in str(result.url)
        assert result.translations == content

    @pytest.mark.asyncio
    async def test_translate_landing_page_unsupported_language(self, translator):
        """Test that unsupported language raises error."""
        content = {"hero": {"headline": "Test"}}
        
        with pytest.raises(UnsupportedLanguageError) as exc_info:
            await translator.translate_landing_page(
                landing_page_id="lp_123",
                content=content,
                target_language="de",
            )
        
        assert exc_info.value.language == "de"

    @pytest.mark.asyncio
    async def test_translate_landing_page_preserves_structure(self):
        """Test that translation preserves original structure and format.
        
        Requirements: 5.2 - Maintain original format during translation
        """
        mock_client = AsyncMock()
        mock_client.fast_structured_output = AsyncMock(
            return_value=TranslationResponse(
                translations=[
                    TranslatedSection(
                        section_name="hero.headline",
                        original_text="Buy Now",
                        translated_text="Comprar Ahora",
                    ),
                    TranslatedSection(
                        section_name="features[0].title",
                        original_text="Feature 1",
                        translated_text="Característica 1",
                    ),
                    TranslatedSection(
                        section_name="features[0].description",
                        original_text="Description 1",
                        translated_text="Descripción 1",
                    ),
                ],
                source_language="en",
                target_language="es",
            )
        )
        
        translator = Translator(gemini_client=mock_client)
        content = {
            "hero": {
                "headline": "Buy Now",
                "image": "https://example.com/hero.jpg",
                "cta_text": "Shop",
            },
            "features": [
                {
                    "title": "Feature 1",
                    "description": "Description 1",
                    "icon": "star",
                }
            ],
            "theme": {
                "primary_color": "#FF0000",
            },
        }
        
        result = await translator.translate_landing_page(
            landing_page_id="lp_456",
            content=content,
            target_language="es",
            sections=["hero", "features"],
        )
        
        # Verify structure is preserved
        assert "hero" in result.translations
        assert "features" in result.translations
        assert "theme" in result.translations
        
        # Verify non-text fields are preserved
        assert result.translations["hero"]["image"] == "https://example.com/hero.jpg"
        assert result.translations["features"][0]["icon"] == "star"
        assert result.translations["theme"]["primary_color"] == "#FF0000"
        
        # Verify text fields are translated
        assert result.translations["hero"]["headline"] == "Comprar Ahora"
        assert result.translations["features"][0]["title"] == "Característica 1"

    @pytest.mark.asyncio
    async def test_translate_landing_page_url_format(self):
        """Test that generated URL follows correct format.
        
        Requirements: 5.3 - Generate new language version URL
        """
        mock_client = AsyncMock()
        mock_client.fast_structured_output = AsyncMock(
            return_value=TranslationResponse(
                translations=[],
                source_language="en",
                target_language="zh",
            )
        )
        
        translator = Translator(gemini_client=mock_client)
        
        result = await translator.translate_landing_page(
            landing_page_id="lp_789",
            content={},
            target_language="zh",
            user_id="testuser",
        )
        
        # URL should include user_id, landing_page_id, and lang parameter
        url_str = str(result.url)
        assert "testuser" in url_str
        assert "lp_789" in url_str
        assert "lang=zh" in url_str
