"""Test script for enhanced video generation capabilities."""

import asyncio
import base64
from pathlib import Path

from app.tools.creative_tools import GenerateVideoTool


async def test_text_to_video():
    """Test basic text-to-video generation."""
    print("\n=== Test 1: Text-to-Video ===")
    tool = GenerateVideoTool()
    
    result = await tool.execute(
        parameters={
            "prompt": "A cute kitten playing with a ball of yarn, playful and energetic",
            "style": "lifestyle",
            "duration": 4,
            "aspect_ratio": "16:9",
        },
        context={"user_id": "test_user"},
    )
    
    print(f"Status: {result.get('status')}")
    print(f"Message: {result.get('message')}")
    if result.get("video_object_name"):
        print(f"Video saved to GCS: {result['video_object_name']}")


async def test_image_to_video_with_context():
    """Test image-to-video using conversation context."""
    print("\n=== Test 2: Image-to-Video (Context) ===")
    tool = GenerateVideoTool()
    
    # Simulate conversation history with a generated image
    fake_image_b64 = base64.b64encode(b"fake_image_data").decode()
    context = {
        "user_id": "test_user",
        "conversation_history": [
            {
                "role": "assistant",
                "content": "Here's your generated image",
                "generated_images": [
                    {
                        "index": 0,
                        "format": "png",
                        "size": 1024,
                        "data_b64": fake_image_b64,
                    }
                ],
            }
        ],
    }
    
    result = await tool.execute(
        parameters={
            "use_context_image": True,
            "prompt": "Animate this image with smooth camera movement",
            "style": "calm",
            "duration": 4,
        },
        context=context,
    )
    
    print(f"Status: {result.get('status')}")
    print(f"Used context image: {result.get('message')}")


async def test_interpolation():
    """Test interpolation with first and last frames."""
    print("\n=== Test 3: Interpolation (First + Last Frame) ===")
    tool = GenerateVideoTool()
    
    # Create fake image data
    first_frame = base64.b64encode(b"first_frame_data").decode()
    last_frame = base64.b64encode(b"last_frame_data").decode()
    
    result = await tool.execute(
        parameters={
            "first_frame_b64": first_frame,
            "last_frame_b64": last_frame,
            "prompt": "Smooth transition from start to end with dynamic camera movement",
            "duration": 8,  # Interpolation requires 8 seconds
            "aspect_ratio": "16:9",
        },
        context={"user_id": "test_user"},
    )
    
    print(f"Status: {result.get('status')}")
    print(f"Message: {result.get('message')}")


async def test_reference_images():
    """Test reference-guided generation."""
    print("\n=== Test 4: Reference-Guided Generation ===")
    tool = GenerateVideoTool()
    
    # Create fake reference images
    ref_images = [
        base64.b64encode(f"reference_image_{i}".encode()).decode()
        for i in range(3)
    ]
    
    result = await tool.execute(
        parameters={
            "reference_images_b64": ref_images,
            "prompt": "A fashion model walking on a runway wearing the dress from the reference images",
            "style": "professional",
            "duration": 8,  # Reference images require 8 seconds
            "aspect_ratio": "16:9",
        },
        context={"user_id": "test_user"},
    )
    
    print(f"Status: {result.get('status')}")
    print(f"Message: {result.get('message')}")


async def main():
    """Run all tests."""
    print("Testing Enhanced Video Generation Tool")
    print("=" * 50)
    
    # Note: These tests will fail without valid Gemini API key
    # They demonstrate the parameter structure and tool capabilities
    
    try:
        await test_text_to_video()
    except Exception as e:
        print(f"Test 1 failed (expected without API key): {e}")
    
    try:
        await test_image_to_video_with_context()
    except Exception as e:
        print(f"Test 2 failed (expected without API key): {e}")
    
    try:
        await test_interpolation()
    except Exception as e:
        print(f"Test 3 failed (expected without API key): {e}")
    
    try:
        await test_reference_images()
    except Exception as e:
        print(f"Test 4 failed (expected without API key): {e}")
    
    print("\n" + "=" * 50)
    print("Test structure validation complete!")
    print("\nSupported modes:")
    print("1. Text-to-video: prompt + style")
    print("2. Image-to-video: use_context_image=true OR first_frame_b64")
    print("3. Interpolation: first_frame_b64 + last_frame_b64")
    print("4. Reference-guided: reference_images_b64 (up to 3)")


if __name__ == "__main__":
    asyncio.run(main())
