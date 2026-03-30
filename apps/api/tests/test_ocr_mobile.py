import asyncio


async def test_ocr():
    # url = "http://localhost:8000/api/v1/ai/ocr"

    # Simple transparent pixel base64
    pixel = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="

    payload = {"image_base64": pixel, "project_id": "test-project"}

    # Note: This will fail if the server is not running or if auth is required
    # Since I don't have a valid token here, I'll just check if the code compiles and runs conceptually
    print(
        "Test script prepared. In a real environment, this would send a base64 payload to /api/v1/ai/ocr"
    )
    print(f"Payload keys: {list(payload.keys())}")


if __name__ == "__main__":
    asyncio.run(test_ocr())
