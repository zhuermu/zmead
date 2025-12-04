"""Quick verification of video generation tool structure."""

import base64
from app.tools.creative_tools import GenerateVideoTool


def test_tool_metadata():
    """Verify tool metadata and parameters."""
    tool = GenerateVideoTool()
    
    print("Tool Name:", tool.name)
    print("Category:", tool.category)
    print("Credit Cost:", tool.metadata.credit_cost)
    print("\nParameters:")
    for param in tool.metadata.parameters:
        print(f"  - {param.name} ({param.type}): {param.description[:60]}...")
        if param.enum:
            print(f"    Enum: {param.enum}")
    
    print("\n✅ Tool metadata structure is valid")


def test_context_image_extraction():
    """Test image extraction from conversation history."""
    tool = GenerateVideoTool()
    
    # Test with generated images
    fake_image = base64.b64encode(b"test_image").decode()
    context = {
        "conversation_history": [
            {
                "role": "user",
                "content": "Generate an image",
            },
            {
                "role": "assistant",
                "content": "Here's your image",
                "generated_images": [
                    {"data_b64": fake_image, "index": 0}
                ],
            },
        ]
    }
    
    extracted = tool._extract_image_from_context(context, index=0)
    assert extracted == fake_image, "Failed to extract image from context"
    print("✅ Context image extraction works")


def test_prompt_building():
    """Test prompt building methods."""
    tool = GenerateVideoTool()
    
    # Test product prompt
    product_prompt = tool._build_video_prompt(
        {"name": "Test Product", "description": "A great product"},
        "dynamic"
    )
    assert "Test Product" in product_prompt
    assert "fast-paced" in product_prompt or "energetic" in product_prompt
    print("✅ Product prompt building works")
    
    # Test image animation prompt
    animation_prompt = tool._build_image_animation_prompt("calm")
    assert "calm" in animation_prompt.lower() or "smooth" in animation_prompt.lower()
    print("✅ Image animation prompt building works")


if __name__ == "__main__":
    print("=" * 60)
    print("Video Generation Tool Verification")
    print("=" * 60)
    print()
    
    test_tool_metadata()
    print()
    test_context_image_extraction()
    print()
    test_prompt_building()
    print()
    print("=" * 60)
    print("All verifications passed! ✅")
    print("=" * 60)
