import requests
import json
import os
import base64
import time
from PIL import Image
import io
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key from environment variables
API_KEY = os.getenv("BLACKFOREST_API_KEY")

# Debug: Check if API key is loaded
if not API_KEY:
    print("ERROR: BLACKFOREST_API_KEY not found in environment variables")
    exit(1)
else:
    print(f"API Key loaded: {API_KEY[:8]}...{API_KEY[-4:]} (masked for security)")

# IAB sizes with API-compatible dimensions (all are already multiples of 32 and within 256-1440 range)
IAB_SIZES = [
    {"name": "Billboard", "width": 992, "height": 256, "original": "970x250"},
    {"name": "Portrait", "width": 320, "height": 1056, "original": "300x1050"},
    {"name": "Skyscraper", "width": 256, "height": 608, "original": "160x600"},
    {"name": "Medium Rectangle", "width": 320, "height": 256, "original": "300x250"},
]

# BlackForest API configuration
API_BASE_URL = "https://api.us1.bfl.ai/v1"
FLUX_PRO_ENDPOINT = f"{API_BASE_URL}/flux-pro-1.1"

def validate_api_dimensions(width, height):
    """Validate that dimensions meet BlackForest API constraints"""
    if not (256 <= width <= 1440 and 256 <= height <= 1440):
        raise ValueError(f"Dimensions {width}x{height} must be between 256-1440 pixels")
    if width % 32 != 0 or height % 32 != 0:
        raise ValueError(f"Dimensions {width}x{height} must be multiples of 32")
    return True

def image_to_base64(image_path):
    """Convert image file to base64 string"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def pil_image_to_base64(pil_image, format='JPEG', quality=95):
    """Convert PIL Image to base64 string"""
    buffer = io.BytesIO()
    pil_image.save(buffer, format=format, quality=quality)
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode('utf-8')

def smart_preprocess_image(image_input, target_width, target_height):
    """
    Smart preprocessing: resize input image to target dimensions

    Args:
        image_input: Either file path (str) or base64 string
        target_width: Target width (must be API-compatible)
        target_height: Target height (must be API-compatible)

    Returns:
        base64 encoded image string
    """
    validate_api_dimensions(target_width, target_height)

    # Handle different input types
    if isinstance(image_input, str) and os.path.exists(image_input):
        # File path input
        with Image.open(image_input) as img:
            print(f"Original dimensions: {img.size[0]}x{img.size[1]}")
            print(f"Target dimensions: {target_width}x{target_height}")

            # Resize with high-quality resampling
            resized_img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
            return pil_image_to_base64(resized_img)

    elif isinstance(image_input, str):
        # Assume base64 string input
        try:
            image_data = base64.b64decode(image_input)
            with Image.open(io.BytesIO(image_data)) as img:
                print(f"Original dimensions: {img.size[0]}x{img.size[1]}")
                print(f"Target dimensions: {target_width}x{target_height}")

                # Resize with high-quality resampling
                resized_img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
                return pil_image_to_base64(resized_img)
        except Exception as e:
            raise ValueError(f"Invalid base64 image data: {e}")

    else:
        raise ValueError("image_input must be a file path or base64 string")

def generate_image_with_blackforest(image_prompt_b64, target_width, target_height, name, output_dir):
    """
    Generate image using BlackForest Labs flux-pro-1.1 API

    Args:
        image_prompt_b64: Base64 encoded image to use as prompt
        target_width: Target width for final image
        target_height: Target height for final image
        name: Name for output file
        output_dir: Directory to save output

    Returns:
        Path to saved image or None if failed
    """
    validate_api_dimensions(target_width, target_height)

    # Prepare headers
    headers = {
        "Content-Type": "application/json",
        "X-Key": API_KEY
    }

    # Prepare payload for flux-pro-1.1
    payload = {
        "prompt": f"Create a high-quality {target_width}x{target_height} image based on the provided image prompt. Maintain the original content while optimizing for clarity, sharpness, and visual appeal.",
        "image_prompt": image_prompt_b64,
        "width": target_width,
        "height": target_height,
        "steps": 40,
        "guidance": 2.5,
        "safety_tolerance": 2,
        "output_format": "jpeg"
    }

    print(f"Making API request to generate {target_width}x{target_height} image...")

    try:
        response = requests.post(FLUX_PRO_ENDPOINT, headers=headers, json=payload, timeout=30)
        print(f"API response status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()

            if "polling_url" in result:
                print("Polling for generation result...")
                return poll_and_save_result(result['polling_url'], target_width, target_height, name, output_dir)
            else:
                print("Unexpected response format")
                print(f"Response: {result}")
                return None
        else:
            print(f"API error: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        print(f"API request failed: {e}")
        return None

def poll_and_save_result(polling_url, width, height, name, output_dir):
    """Poll the API for results and save the generated image"""

    max_attempts = 30
    attempt = 0

    while attempt < max_attempts:
        attempt += 1
        print(f"Polling attempt {attempt}/{max_attempts}...")

        try:
            poll_response = requests.get(polling_url, headers={"X-Key": API_KEY}, timeout=30)

            if poll_response.status_code == 200:
                poll_result = poll_response.json()

                if "result" in poll_result and poll_result["result"] is not None:
                    if "sample" in poll_result["result"]:
                        sample_url = poll_result["result"]["sample"]
                        print(f"Downloading generated image from: {sample_url}")

                        # Download the generated image
                        img_response = requests.get(sample_url, timeout=30)
                        if img_response.status_code == 200:
                            # Create output directory if it doesn't exist
                            os.makedirs(output_dir, exist_ok=True)

                            # Save generated image
                            output_path = os.path.join(output_dir, f"{name}_{width}x{height}_generated.jpg")
                            with open(output_path, "wb") as f:
                                f.write(img_response.content)

                            print(f"Successfully generated and saved image as {output_path}")
                            return output_path
                        else:
                            print(f"Failed to download generated image: {img_response.status_code}")
                            return None
                    else:
                        print("Result found but no sample image")
                        return None
                else:
                    print("Job still processing, waiting 5 seconds...")
                    time.sleep(5)
            else:
                print(f"Polling failed: {poll_response.status_code}")
                return None

        except Exception as e:
            print(f"Polling error: {e}")
            return None

    print("Polling timeout - generation took too long")
    return None

def process_image_to_iab_size(image_input, target_width, target_height, name, output_dir):
    """
    Main streamlined function: Process image to IAB size using BlackForest API

    Args:
        image_input: Either file path (str) or base64 string
        target_width: Target IAB width
        target_height: Target IAB height
        name: Name for output file
        output_dir: Directory to save output

    Returns:
        Path to saved image or None if failed
    """
    print(f"Processing image to {target_width}x{target_height} ({name})")

    try:
        # Step 1: Smart preprocessing - resize input to target dimensions
        print("Step 1: Smart preprocessing...")
        preprocessed_b64 = smart_preprocess_image(image_input, target_width, target_height)

        # Step 2: Generate final image using BlackForest API
        print("Step 2: Generating with BlackForest API...")
        result_path = generate_image_with_blackforest(
            preprocessed_b64, target_width, target_height, name, output_dir
        )

        if result_path:
            print(f"Successfully processed image: {result_path}")
            return result_path
        else:
            print("Failed to generate image")
            return None

    except Exception as e:
        print(f"Error processing image: {e}")
        return None

def main():
    # Path to the input image
    input_image = "Headphones.jpg"

    # Output directory for processed images
    output_dir = "resized_images"

    # Test with one size first using new streamlined approach
    print("Testing streamlined approach: Medium Rectangle (320x256)")
    result = process_image_to_iab_size(
        input_image,
        320,
        256,
        "Medium_Rectangle_Streamlined",
        output_dir
    )

    if result:
        print(f"✅ Test successful: {result}")
    else:
        print("❌ Test failed")
        return

    # Process all IAB sizes with streamlined approach
    print("\nProcessing all IAB sizes with streamlined approach...")
    for size in IAB_SIZES:
        print(f"\n{'='*50}")
        print(f"Processing {size['name']} ({size['width']}x{size['height']})...")
        print(f"Original size: {size['original']}")

        result = process_image_to_iab_size(
            input_image,
            size["width"],
            size["height"],
            size["name"],
            output_dir
        )

        if result:
            print(f"✅ {size['name']} completed: {result}")
        else:
            print(f"❌ {size['name']} failed")

# Convenience function for external use
def resize_image_to_iab(image_input, iab_size_name, output_dir="resized_images"):
    """
    Convenience function to resize image to a specific IAB size by name

    Args:
        image_input: File path or base64 string
        iab_size_name: Name of IAB size ("Billboard", "Portrait", "Skyscraper", "Medium Rectangle")
        output_dir: Output directory

    Returns:
        Path to generated image or None if failed
    """
    # Find the IAB size configuration
    iab_config = None
    for size in IAB_SIZES:
        if size["name"] == iab_size_name:
            iab_config = size
            break

    if not iab_config:
        print(f"Error: Unknown IAB size '{iab_size_name}'")
        print(f"Available sizes: {[s['name'] for s in IAB_SIZES]}")
        return None

    return process_image_to_iab_size(
        image_input,
        iab_config["width"],
        iab_config["height"],
        iab_config["name"],
        output_dir
    )

if __name__ == "__main__":
    main()