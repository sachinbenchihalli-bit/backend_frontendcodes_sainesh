import os
import io
import time
import requests
import logging
import asyncio
import base64
from PIL import Image as PIL_Image
from typing import List, Dict, Any, Optional, AsyncGenerator
from tools.store_s3 import upload_to_s3

# Configure logging
logger = logging.getLogger(__name__)

# Blackforest Labs API settings
BLACKFOREST_API_KEY = os.getenv('BLACKFOREST_API_KEY')
BLACKFOREST_API_BASE_URL = "https://api.us1.bfl.ai/v1"
BLACKFOREST_ENDPOINT = f"{BLACKFOREST_API_BASE_URL}/flux-pro-1.1"

# GetImg AI API settings (kept for backward compatibility)
GETIMG_API_KEY = os.getenv('GETIMGAI_API_KEY')
GETIMG_API_BASE_URL = "https://api.getimg.ai/v1"
GETIMG_MODEL = "flux-schnell"

# IAB standard ad sizes - using API-compatible dimensions (multiples of 32, minimum 256px)
# These dimensions are adjusted to meet Blackforest Labs API constraints while staying as close as possible to IAB standards
IAB_SIZES = [
    {"name": "Billboard", "width": 992, "height": 256, "original": "970x250"},
    {"name": "Portrait", "width": 320, "height": 1056, "original": "300x1050"},
    {"name": "Skyscraper", "width": 256, "height": 608, "original": "160x600"},
    {"name": "Medium Rectangle", "width": 320, "height": 256, "original": "300x250"},
]

class BlackforestIABGenerator:
    """
    Class to generate images in IAB standard sizes using Blackforest Labs API.
    Supports both text-to-image and image-to-image generation.
    """

    def __init__(self):
        """Initialize the Blackforest IAB Size Generator."""
        self.api_key = BLACKFOREST_API_KEY
        self.api_base_url = BLACKFOREST_API_BASE_URL
        self.endpoint = BLACKFOREST_ENDPOINT
        self.iab_sizes = IAB_SIZES

        if not self.api_key:
            logger.warning("BLACKFOREST_API_KEY not found in environment variables")

    def validate_api_dimensions(self, width: int, height: int) -> bool:
        """Validate that dimensions meet Blackforest Labs API constraints"""
        if not (256 <= width <= 1440 and 256 <= height <= 1440):
            raise ValueError(f"Dimensions {width}x{height} must be between 256-1440 pixels")
        if width % 32 != 0 or height % 32 != 0:
            raise ValueError(f"Dimensions {width}x{height} must be multiples of 32")
        return True

    def calculate_api_compatible_dimensions(self, width: int, height: int) -> tuple[int, int]:
        """
        Calculate API-compatible dimensions that meet Blackforest Labs constraints.

        Args:
            width (int): Original width
            height (int): Original height

        Returns:
            tuple[int, int]: API-compatible (width, height) that are multiples of 32 and >= 256px
        """
        # Ensure minimum dimensions
        width = max(width, 256)
        height = max(height, 256)

        # Ensure maximum dimensions
        width = min(width, 1440)
        height = min(height, 1440)

        # Round to nearest multiple of 32 (round up to preserve or increase size)
        width = ((width + 31) // 32) * 32  # Round up to nearest 32
        height = ((height + 31) // 32) * 32  # Round up to nearest 32

        return width, height

    def preprocess_reference_image(self, reference_image: PIL_Image.Image) -> PIL_Image.Image:
        """
        Preprocess reference image to meet Blackforest Labs API requirements.

        Args:
            reference_image (PIL_Image.Image): Original reference image

        Returns:
            PIL_Image.Image: Preprocessed image that meets API constraints

        Raises:
            ValueError: If image cannot be processed
        """
        try:
            # Get original dimensions
            orig_width, orig_height = reference_image.size
            logger.info(f"Original reference image dimensions: {orig_width}x{orig_height}")

            # Check if image is too small or needs resizing
            if orig_width < 256 or orig_height < 256:
                logger.info(f"Reference image is smaller than minimum 256x256, will be scaled up")

                # Calculate scale factor to meet minimum requirements while preserving aspect ratio
                scale_factor = max(256 / orig_width, 256 / orig_height)
                new_width = int(orig_width * scale_factor)
                new_height = int(orig_height * scale_factor)

                logger.info(f"Scaling up by factor {scale_factor:.2f} to {new_width}x{new_height}")

            elif orig_width > 1440 or orig_height > 1440:
                logger.info(f"Reference image is larger than maximum 1440x1440, will be scaled down")

                # Calculate scale factor to fit within maximum dimensions while preserving aspect ratio
                scale_factor = min(1440 / orig_width, 1440 / orig_height)
                new_width = int(orig_width * scale_factor)
                new_height = int(orig_height * scale_factor)

                logger.info(f"Scaling down by factor {scale_factor:.2f} to {new_width}x{new_height}")

            else:
                # Image is within acceptable range, but may need adjustment for multiples of 32
                new_width = orig_width
                new_height = orig_height

            # Ensure dimensions are multiples of 32
            api_width, api_height = self.calculate_api_compatible_dimensions(new_width, new_height)

            if api_width != orig_width or api_height != orig_height:
                logger.info(f"Resizing reference image from {orig_width}x{orig_height} to {api_width}x{api_height}")

                # Use high-quality resampling to maintain image quality
                processed_image = reference_image.resize(
                    (api_width, api_height),
                    PIL_Image.Resampling.LANCZOS
                )

                # Ensure image is in RGB mode for JPEG conversion
                if processed_image.mode != 'RGB':
                    processed_image = processed_image.convert('RGB')

                return processed_image
            else:
                logger.info("Reference image dimensions are already API-compatible")
                # Ensure image is in RGB mode for JPEG conversion
                if reference_image.mode != 'RGB':
                    return reference_image.convert('RGB')
                return reference_image

        except Exception as e:
            logger.error(f"Error preprocessing reference image: {str(e)}")
            raise ValueError(f"Failed to preprocess reference image: {str(e)}")

    def pil_image_to_base64(self, pil_image: PIL_Image.Image, format='JPEG', quality=95) -> str:
        """Convert PIL Image to base64 string"""
        buffer = io.BytesIO()
        pil_image.save(buffer, format=format, quality=quality)
        buffer.seek(0)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')

    def generate_image_text_to_image(self, prompt: str, width: int, height: int) -> Dict[str, Any]:
        """
        Generate an image using Blackforest Labs API (text-to-image)

        Args:
            prompt (str): The text prompt for image generation
            width (int): Target width
            height (int): Target height

        Returns:
            dict: Result containing success status and image data or error
        """
        if not self.api_key:
            return {"error": "BLACKFOREST_API_KEY not configured"}

        # Validate dimensions meet API constraints
        try:
            self.validate_api_dimensions(width, height)
        except ValueError as e:
            return {"error": str(e)}

        headers = {
            "Content-Type": "application/json",
            "X-Key": self.api_key
        }

        payload = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "steps": 40,
            "guidance": 2.5,
            "safety_tolerance": 2,
            "output_format": "jpeg"
        }

        try:
            logger.info(f"Making Blackforest API request for text-to-image: {width}x{height}")
            response = requests.post(self.endpoint, headers=headers, json=payload, timeout=30)

            if response.status_code == 200:
                result = response.json()
                if "polling_url" in result:
                    return self.poll_blackforest_result(result['polling_url'])
                else:
                    return {"error": "Unexpected response format from Blackforest API"}
            else:
                # Use improved error parsing
                error_message = self.parse_api_error(response)
                logger.error(f"Blackforest API error: {response.status_code} - {error_message}")
                return {"error": error_message}

        except Exception as e:
            logger.error(f"Error calling Blackforest API: {str(e)}")
            return {"error": f"Failed to generate image: {str(e)}"}

    def parse_api_error(self, response: requests.Response) -> str:
        """
        Parse API error response and return user-friendly error message.

        Args:
            response (requests.Response): The failed API response

        Returns:
            str: User-friendly error message
        """
        try:
            error_data = response.json()

            # Handle specific Blackforest Labs API errors
            if response.status_code == 422:
                if "detail" in error_data:
                    detail = error_data["detail"]
                    if isinstance(detail, list) and len(detail) > 0:
                        # Extract the first error message
                        first_error = detail[0]
                        if isinstance(first_error, dict) and "msg" in first_error:
                            error_msg = first_error["msg"]
                            if "Image_prompt dimensions must be at least 256x256 pixels" in error_msg:
                                return "Reference image is too small. Please upload an image that is at least 256x256 pixels, or let us automatically resize it for you."
                            elif "dimensions" in error_msg.lower():
                                return f"Image dimension error: {error_msg}. The image will be automatically resized to meet API requirements."
                            else:
                                return f"Validation error: {error_msg}"
                    elif isinstance(detail, str):
                        if "Image_prompt dimensions must be at least 256x256 pixels" in detail:
                            return "Reference image is too small. Please upload an image that is at least 256x256 pixels, or let us automatically resize it for you."
                        else:
                            return f"Validation error: {detail}"

                return "Image validation failed. Please check your image format and dimensions."

            elif response.status_code == 400:
                return "Invalid request. Please check your image format and try again."

            elif response.status_code == 401:
                return "API authentication failed. Please check your API key configuration."

            elif response.status_code == 429:
                return "API rate limit exceeded. Please wait a moment and try again."

            elif response.status_code >= 500:
                return "API server error. Please try again later."

            else:
                # Try to extract any error message from the response
                if "error" in error_data:
                    return f"API error: {error_data['error']}"
                elif "message" in error_data:
                    return f"API error: {error_data['message']}"
                else:
                    return f"API request failed with status {response.status_code}"

        except (ValueError, KeyError):
            # If we can't parse the JSON or extract error details
            return f"API request failed with status {response.status_code}: {response.text[:200]}"

    def generate_image_with_reference(self, prompt: str, reference_image: PIL_Image.Image, width: int, height: int) -> Dict[str, Any]:
        """
        Generate an image using Blackforest Labs API with reference image (image-to-image)

        Args:
            prompt (str): The text prompt for image generation
            reference_image (PIL_Image.Image): Reference image for image-to-image generation
            width (int): Target width
            height (int): Target height

        Returns:
            dict: Result containing success status and image data or error
        """
        if not self.api_key:
            return {"error": "BLACKFOREST_API_KEY not configured"}

        # Validate target dimensions meet API constraints
        try:
            self.validate_api_dimensions(width, height)
        except ValueError as e:
            return {"error": str(e)}

        try:
            # Convert reference image to base64 (image is already preprocessed)
            reference_b64 = self.pil_image_to_base64(reference_image)

            headers = {
                "Content-Type": "application/json",
                "X-Key": self.api_key
            }

            payload = {
                "prompt": f"Create a high-quality {width}x{height} image based on the provided reference image. {prompt}",
                "image_prompt": reference_b64,
                "width": width,
                "height": height,
                "steps": 40,
                "guidance": 2.5,
                "safety_tolerance": 2,
                "output_format": "jpeg"
            }

            logger.info(f"Making Blackforest API request for image-to-image: {width}x{height}")
            response = requests.post(self.endpoint, headers=headers, json=payload, timeout=30)

            if response.status_code == 200:
                result = response.json()
                if "polling_url" in result:
                    return self.poll_blackforest_result(result['polling_url'])
                else:
                    return {"error": "Unexpected response format from Blackforest API"}
            else:
                # Use improved error parsing
                error_message = self.parse_api_error(response)
                logger.error(f"Blackforest API error: {response.status_code} - {error_message}")
                return {"error": error_message}

        except Exception as e:
            logger.error(f"Error calling Blackforest API with reference: {str(e)}")
            return {"error": f"Failed to generate image: {str(e)}"}

    def poll_blackforest_result(self, polling_url: str) -> Dict[str, Any]:
        """
        Poll the Blackforest API for results with improved error handling.

        Args:
            polling_url (str): The polling URL returned by the API

        Returns:
            dict: Result containing success status and image data or error
        """
        max_attempts = 30
        attempt = 0

        while attempt < max_attempts:
            attempt += 1
            logger.debug(f"Polling Blackforest API attempt {attempt}/{max_attempts}...")

            try:
                poll_response = requests.get(polling_url, headers={"X-Key": self.api_key}, timeout=30)

                if poll_response.status_code == 200:
                    poll_result = poll_response.json()

                    if "result" in poll_result and poll_result["result"] is not None:
                        if "sample" in poll_result["result"]:
                            sample_url = poll_result["result"]["sample"]
                            logger.info(f"Blackforest generation completed, downloading from: {sample_url}")

                            # Download the generated image with retry logic
                            try:
                                img_response = requests.get(sample_url, timeout=30)
                                if img_response.status_code == 200:
                                    # Validate that we received image data
                                    if len(img_response.content) == 0:
                                        return {"error": "Generated image file is empty"}

                                    # Convert to PIL Image with error handling
                                    try:
                                        image = PIL_Image.open(io.BytesIO(img_response.content))
                                        # Verify the image can be loaded
                                        image.verify()
                                        # Reopen for actual use (verify() closes the image)
                                        image = PIL_Image.open(io.BytesIO(img_response.content))
                                        return {"success": True, "image": image}
                                    except Exception as img_error:
                                        logger.error(f"Failed to process generated image: {img_error}")
                                        return {"error": f"Generated image is corrupted or invalid: {str(img_error)}"}
                                else:
                                    return {"error": f"Failed to download generated image (HTTP {img_response.status_code})"}
                            except requests.exceptions.RequestException as download_error:
                                logger.error(f"Error downloading generated image: {download_error}")
                                return {"error": f"Failed to download generated image: {str(download_error)}"}
                        else:
                            return {"error": "Generation completed but no image was produced"}
                    else:
                        # Check if there's an error in the result
                        if "error" in poll_result:
                            return {"error": f"Generation failed: {poll_result['error']}"}

                        logger.debug("Blackforest job still processing, waiting...")
                        time.sleep(5)

                elif poll_response.status_code == 404:
                    return {"error": "Generation job not found - it may have expired"}
                elif poll_response.status_code == 401:
                    return {"error": "Authentication failed while polling for results"}
                else:
                    # Try to parse error from polling response
                    try:
                        error_data = poll_response.json()
                        if "error" in error_data:
                            return {"error": f"Polling failed: {error_data['error']}"}
                        else:
                            return {"error": f"Polling failed with status {poll_response.status_code}"}
                    except:
                        return {"error": f"Polling failed with status {poll_response.status_code}"}

            except requests.exceptions.Timeout:
                logger.warning(f"Polling attempt {attempt} timed out, retrying...")
                if attempt == max_attempts:
                    return {"error": "Polling timed out - generation may still be in progress"}
                time.sleep(2)
                continue

            except Exception as e:
                logger.error(f"Polling error on attempt {attempt}: {e}")
                if attempt == max_attempts:
                    return {"error": f"Polling failed after {max_attempts} attempts: {str(e)}"}
                time.sleep(2)
                continue

        return {"error": "Generation timed out - please try again with a simpler prompt"}

    def get_aspect_ratio_from_dimensions(self, width: int, height: int) -> str:
        """Calculate aspect ratio from dimensions"""
        # For IAB sizes, use descriptive names based on API-compatible dimensions
        if width == 992 and height == 256:
            return "Billboard"
        elif width == 320 and height == 1056:
            return "Portrait"
        elif width == 256 and height == 608:
            return "Skyscraper"
        elif width == 320 and height == 256:
            return "Medium Rectangle"
        else:
            # Calculate ratio for other dimensions
            from math import gcd
            ratio_gcd = gcd(width, height)
            return f"{width//ratio_gcd}:{height//ratio_gcd}"

    async def generate_iab_size(self, size_info: Dict[str, Any], prompt: str, image_title: str, reference_image: Optional[PIL_Image.Image] = None) -> Dict[str, Any]:
        """
        Generate an image for a specific IAB size using Blackforest Labs API

        Args:
            size_info (dict): Dictionary containing name, width, height, and original size
            prompt (str): The prompt to generate the image
            image_title (str): The title for the generated image
            reference_image (PIL_Image.Image, optional): Reference image for image-to-image generation

        Returns:
            dict: Result containing success status, image URL, and metadata
        """
        name = size_info["name"]
        width = size_info["width"]
        height = size_info["height"]
        original = size_info["original"]

        logger.info(f"Generating image for {name} ({width}x{height}) - Original: {original}...")

        # Create a prompt that mentions the ad size
        enhanced_prompt = f"{prompt} Create this as a professional advertisement suitable for a {name.split(' ')[0]} ad format."

        # Choose generation method based on whether reference image is provided
        if reference_image:
            logger.info(f"Using image-to-image generation for {name}")
            # Note: reference_image is already preprocessed at this point
            result = self.generate_image_with_reference(enhanced_prompt, reference_image, width, height)
        else:
            logger.info(f"Using text-to-image generation for {name}")
            result = self.generate_image_text_to_image(enhanced_prompt, width, height)

        if "error" in result:
            return {
                "success": False,
                "size_info": size_info,
                "error": result["error"],
                "image_path": None
            }

        if result.get("success") and "image" in result:
            image = result["image"]

            # Convert the image to bytes for S3 upload
            byte_io = io.BytesIO()
            image.save(byte_io, "PNG")
            byte_io.seek(0)

            # Upload to S3
            try:
                uploaded_result = upload_to_s3(byte_io.getvalue())
                s3_key = uploaded_result["key"]

                # Calculate aspect ratio for display
                aspect_ratio = self.get_aspect_ratio_from_dimensions(width, height)

                return {
                    "success": True,
                    "size_info": size_info,
                    "S3Key": s3_key,
                    "Title": f"{image_title} ({name})",
                    "AspectRatio": aspect_ratio,
                    "Dimensions": f"{width}x{height}",
                    "OriginalSize": original,
                    "APICompatibleSize": f"{width}x{height}",
                    "actual_dimensions": image.size
                }
            except Exception as e:
                logger.error(f"Error uploading image to S3: {e}")
                return {
                    "success": False,
                    "size_info": size_info,
                    "error": f"Failed to upload image to S3: {str(e)}",
                    "image_path": None
                }
        else:
            return {
                "success": False,
                "size_info": size_info,
                "error": "Failed to generate image",
                "image_path": None
            }

    async def generate_all_iab_sizes(self, prompt: str, image_title: str, specific_sizes: List[str] = None, reference_image: Optional[PIL_Image.Image] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate images for IAB standard sizes using Blackforest Labs API

        Args:
            prompt (str): The prompt to generate the images
            image_title (str): The title for the generated images
            specific_sizes (List[str], optional): List of specific IAB sizes to generate (e.g., ["970x250", "300x250"])
            reference_image (PIL_Image.Image, optional): Reference image for image-to-image generation

        Yields:
            dict: Status updates and results for each generated image
        """
        logger.info("Starting Blackforest IAB Size Generation")

        # Filter sizes if specific ones are requested
        sizes_to_generate = self.iab_sizes
        if specific_sizes:
            sizes_to_generate = [size for size in self.iab_sizes if size["original"] in specific_sizes]
            logger.info(f"Generating only specific IAB sizes: {specific_sizes}")
            if not sizes_to_generate:
                logger.warning(f"None of the requested sizes {specific_sizes} match available IAB sizes. Using all sizes.")
                sizes_to_generate = self.iab_sizes

        # Preprocess reference image if provided and give user feedback
        preprocessed_reference = None
        if reference_image:
            try:
                yield {"status": "preprocessing", "message": "Preprocessing your reference image to meet API requirements..."}

                orig_width, orig_height = reference_image.size
                preprocessed_reference = self.preprocess_reference_image(reference_image)
                new_width, new_height = preprocessed_reference.size

                if orig_width != new_width or orig_height != new_height:
                    yield {
                        "status": "preprocessing_complete",
                        "message": f"Reference image automatically resized from {orig_width}x{orig_height} to {new_width}x{new_height} to meet API requirements."
                    }
                else:
                    yield {
                        "status": "preprocessing_complete",
                        "message": "Reference image is already compatible with API requirements."
                    }

            except ValueError as e:
                yield {"status": "error", "message": f"Failed to preprocess reference image: {str(e)}"}
                return

        # Initial status update
        generation_mode = "image-to-image" if reference_image else "text-to-image"
        if specific_sizes:
            yield {"status": "resize_to_iab", "message": f"Preparing to generate {len(sizes_to_generate)} selected IAB standard ad sizes using {generation_mode}..."}
        else:
            yield {"status": "resize_to_iab", "message": f"Preparing to generate all IAB standard ad sizes using {generation_mode}..."}

        results = []
        total_sizes = len(sizes_to_generate)

        for i, size_info in enumerate(sizes_to_generate):
            try:
                # Update status
                yield {
                    "status": "generating_variant",
                    "message": f"Generating image {i+1} of {total_sizes}: {size_info['name']} ({size_info['original']})"
                }

                # Generate the image using preprocessed reference if available
                result = await self.generate_iab_size(size_info, prompt, image_title, preprocessed_reference)

                if result["success"]:
                    results.append(result)
                    logger.info(f"Successfully generated {size_info['name']}")

                    # Stream each image as it's generated
                    # Create markdown with S3 key for database storage
                    markdown_with_s3_key = f"\n\n **{result['Title']}:**\n![{result['Title']}]({result['S3Key']})\n\n"

                    # Convert S3 key to URL for frontend display
                    from tools.store_s3 import process_s3_keys_to_urls
                    markdown_with_url = process_s3_keys_to_urls(markdown_with_s3_key, expires_in=7200)

                    partial_result = {
                        "S3Key": result["S3Key"],
                        "Title": result["Title"],
                        "AspectRatio": result["AspectRatio"],
                        "Dimensions": result["Dimensions"],
                        "OriginalSize": result["OriginalSize"],
                        "APICompatibleSize": result["APICompatibleSize"],
                        "MarkdownOutput": markdown_with_s3_key  # Store S3 key version for database
                    }

                    # Create frontend version with URL
                    frontend_partial_result = partial_result.copy()
                    frontend_partial_result["MarkdownOutput"] = markdown_with_url

                    # Yield the partial result immediately
                    await asyncio.sleep(0)  # Allow event loop to process
                    yield {"status": "partial_result", "message": f"Generated {size_info['name']}", "result": frontend_partial_result, "index": i, "total": total_sizes}
                else:
                    logger.error(f"Failed to generate {size_info['name']}: {result.get('error', 'Unknown error')}")
                    yield {"status": "warning", "message": f"Could not generate {size_info['name']}: {result.get('error', 'Unknown error')}"}

            except Exception as e:
                logger.error(f"Error generating image for {size_info['name']}: {str(e)}")
                yield {"status": "error", "message": f"Error generating {size_info['name']}: {str(e)}"}

        # Prepare the final result with all generated images
        if results:
            # Log the completion of the IAB size generation
            logger.info(f"Blackforest IAB size generation completed with {len(results)} images")

            # Send a completion status with a flag indicating this is an IAB generate result
            # But don't include the full result with all images again
            yield {
                "status": "complete",
                "message": f"Successfully generated {len(results)} IAB standard ad sizes using Blackforest Labs!",
                "is_resize_to_iab": True
            }
        else:
            logger.error("Blackforest IAB size generation failed: No images were generated")
            yield {"status": "error", "message": "Failed to generate any IAB standard ad sizes"}

class IABSizeGenerator:
    """
    Class to generate images in IAB standard sizes using GetImg AI API.
    """

    def __init__(self):
        """Initialize the IAB Size Generator."""
        self.api_key = GETIMG_API_KEY
        self.api_base_url = GETIMG_API_BASE_URL
        self.model = GETIMG_MODEL
        self.iab_sizes = IAB_SIZES

    def generate_image(self, prompt: str, width: int, height: int) -> Dict[str, Any]:
        """
        Generate an image using GetImg AI API with specified dimensions

        Args:
            prompt (str): The prompt to generate the image
            width (int): Width of the image
            height (int): Height of the image

        Returns:
            dict: API response containing the image URL or error
        """
        # Truncate prompt if too long
        max_prompt_length = 2048
        if len(prompt) > max_prompt_length:
            prompt = prompt[:max_prompt_length]

        url = f"{self.api_base_url}/{self.model}/text-to-image"

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "prompt": prompt,
            "response_format": "url",
            "output_format": "png",
            "width": width,
            "height": height,
            "steps": 4
        }

        try:
            response = requests.post(url, headers=headers, json=payload)

            # Handle HTTP errors without raising exceptions
            if response.status_code != 200:
                error_msg = f"API request failed with status code {response.status_code}"
                try:
                    error_details = response.json()
                    error_msg += f": {error_details.get('error', 'Unknown error')}"
                except:
                    error_msg += f": {response.text[:100]}"

                logger.error(error_msg)
                return {"error": error_msg}

            # Parse the JSON response
            try:
                result = response.json()
            except Exception as e:
                logger.error(f"Failed to parse API response as JSON: {e}")
                return {"error": f"Invalid API response format: {str(e)}"}

            # Check if URL is in the response
            if "url" not in result:
                logger.error(f"API Response did not return expected image URL: {result}")
                return {"error": "Image URL not found in response"}

            return {"id": "direct", "url": result["url"]}
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making request: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status code: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text}")
            return {"error": f"API request failed: {str(e)}"}

    def poll_for_result(self, request_id: str, max_attempts: int = 60, delay: int = 1) -> Dict[str, Any]:
        """
        For GetImg API, we don't need to poll as it returns the URL directly.
        This method is kept for compatibility with the existing code.

        Args:
            request_id (str): The ID of the request or "direct" if URL is already available
            max_attempts (int): Not used
            delay (int): Not used

        Returns:
            dict: API response containing the result or error
        """
        # If we have a direct URL (from generate_image), return it immediately
        if request_id == "direct" and "url" in request_id:
            return {"status": "Ready", "result": {"sample": request_id["url"]}}

        # Otherwise, this is an error case
        return {"error": "Invalid request ID format for GetImg API"}

    def download_image(self, url: str) -> Optional[PIL_Image.Image]:
        """
        Download an image from a URL

        Args:
            url (str): URL of the image to download

        Returns:
            PIL.Image or None: The downloaded image or None if download failed
        """
        try:
            # Set a timeout to prevent hanging on slow connections
            response = requests.get(url, timeout=30)

            # Handle HTTP errors without raising exceptions
            if response.status_code != 200:
                logger.error(f"Failed to download image: HTTP status {response.status_code}")
                return None

            # Check if the content is actually an image
            content_type = response.headers.get('Content-Type', '')
            if not content_type.startswith('image/'):
                logger.error(f"Downloaded content is not an image: {content_type}")
                return None

            # Try to open the image
            try:
                return PIL_Image.open(io.BytesIO(response.content))
            except Exception as e:
                logger.error(f"Failed to open downloaded image: {e}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading image: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading image: {e}")
            return None

    def get_aspect_ratio_from_dimensions(self, width: int, height: int) -> str:
        """
        Calculate the aspect ratio from width and height.

        Args:
            width: Width in pixels
            height: Height in pixels

        Returns:
            String representation of the aspect ratio (e.g., "16:9")
        """
        import math
        gcd = math.gcd(width, height)
        return f"{width//gcd}:{height//gcd}"

    async def generate_iab_size(self, size_info: Dict[str, Any], prompt: str, image_title: str) -> Dict[str, Any]:
        """
        Generate an image for a specific IAB size

        Args:
            size_info (dict): Dictionary containing name, width, height, and original size
            prompt (str): The prompt to generate the image
            image_title (str): The title for the generated image

        Returns:
            dict: Result containing success status, image URL, and metadata
        """
        name = size_info["name"]
        width = size_info["width"]
        height = size_info["height"]
        original = size_info["original"]

        logger.info(f"Generating image for {name} ({width}x{height}) - Original: {original}...")

        # Create a prompt that mentions the ad size
        enhanced_prompt = f"{prompt} Create this as a professional advertisement suitable for a {name.split(' ')[0]} ad format."

        # Generate the image
        request = self.generate_image(enhanced_prompt, width, height)

        if "error" in request:
            return {
                "success": False,
                "size_info": size_info,
                "error": request["error"],
                "image_path": None
            }

        # For GetImg API, we get the URL directly
        if "url" in request:
            image_url = request["url"]
            logger.debug(f"Image URL: {image_url}")

            # Download the image
            image = self.download_image(image_url)

            if image is None:
                return {
                    "success": False,
                    "size_info": size_info,
                    "error": "Failed to download image",
                    "image_path": None
                }

            # Convert the image to bytes for S3 upload
            byte_io = io.BytesIO()
            image.save(byte_io, "PNG")
            byte_io.seek(0)

            # Upload to S3
            try:
                uploaded_result = upload_to_s3(byte_io.getvalue())
                s3_key = uploaded_result["key"]

                # Calculate aspect ratio for display
                aspect_ratio = self.get_aspect_ratio_from_dimensions(width, height)

                return {
                    "success": True,
                    "size_info": size_info,
                    "S3Key": s3_key,
                    "Title": f"{image_title} ({name})",
                    "AspectRatio": aspect_ratio,
                    "Dimensions": f"{width}x{height}",
                    "OriginalSize": original,
                    "actual_dimensions": image.size
                }
            except Exception as e:
                logger.error(f"Error uploading image to S3: {e}")
                return {
                    "success": False,
                    "size_info": size_info,
                    "error": f"Failed to upload image to S3: {str(e)}",
                    "image_path": None
                }

        # If we have a request ID, we need to poll for the result (should not happen with GetImg API)
        elif "id" in request:
            logger.warning("Unexpected flow: GetImg API returned a request ID instead of direct URL")
            return {
                "success": False,
                "size_info": size_info,
                "error": "Unexpected API response format",
                "image_path": None
            }

        return {
            "success": False,
            "size_info": size_info,
            "error": "Unknown error in image generation",
            "image_path": None
        }

    async def generate_all_iab_sizes(self, prompt: str, image_title: str, specific_sizes: List[str] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate images for IAB standard sizes

        Args:
            prompt (str): The prompt to generate the images
            image_title (str): The title for the generated images
            specific_sizes (List[str], optional): List of specific IAB sizes to generate (e.g., ["970x250", "300x250"])
                                                If None, all IAB sizes will be generated

        Yields:
            dict: Status updates and results for each generated image
        """
        logger.info("Starting IAB Size Generation")

        # Filter sizes if specific ones are requested
        sizes_to_generate = self.iab_sizes
        if specific_sizes:
            sizes_to_generate = [size for size in self.iab_sizes if size["original"] in specific_sizes]
            logger.info(f"Generating only specific IAB sizes: {specific_sizes}")
            if not sizes_to_generate:
                logger.warning(f"None of the requested sizes {specific_sizes} match available IAB sizes. Using all sizes.")
                sizes_to_generate = self.iab_sizes

        # Initial status update
        if specific_sizes:
            yield {"status": "resize_to_iab", "message": f"Preparing to generate {len(sizes_to_generate)} selected IAB standard ad sizes..."}
        else:
            yield {"status": "resize_to_iab", "message": "Preparing to generate all IAB standard ad sizes..."}

        results = []
        total_sizes = len(sizes_to_generate)

        for i, size_info in enumerate(sizes_to_generate):
            try:
                # Update status
                yield {
                    "status": "generating_variant",
                    "message": f"Generating image {i+1} of {total_sizes}: {size_info['name']} ({size_info['original']})"
                }

                # Generate the image
                result = await self.generate_iab_size(size_info, prompt, image_title)

                if result["success"]:
                    results.append(result)

                    # Create a partial result to stream immediately
                    # Create markdown with S3 key for database storage
                    markdown_with_s3_key = f" {result['Title']}\n\n![{result['Title']}]({result['S3Key']})"

                    # Convert S3 key to URL for frontend display
                    from tools.store_s3 import process_s3_keys_to_urls
                    markdown_with_url = process_s3_keys_to_urls(markdown_with_s3_key, expires_in=7200)

                    partial_result = {
                        "S3Key": result["S3Key"],
                        "Title": result["Title"],
                        "AspectRatio": result["AspectRatio"],
                        "Dimensions": result["Dimensions"],
                        "OriginalSize": result["OriginalSize"],
                        "MarkdownOutput": markdown_with_s3_key  # Store S3 key version for database
                    }

                    # Create frontend version with URL
                    frontend_partial_result = partial_result.copy()
                    frontend_partial_result["MarkdownOutput"] = markdown_with_url

                    # Yield the partial result immediately
                    await asyncio.sleep(0)  # Allow event loop to process before continuing
                    yield {
                        "status": "partial_result",
                        "message": f"Generated {size_info['name']} variant",
                        "result": frontend_partial_result,
                        "index": i,
                        "total": total_sizes
                    }
                else:
                    logger.error(f"Failed to generate image for {size_info['name']}: {result['error']}")
                    yield {
                        "status": "error",
                        "message": f"Failed to generate {size_info['name']} variant: {result['error']}"
                    }

            except Exception as e:
                logger.error(f"Error generating image for {size_info['name']}: {str(e)}")
                yield {
                    "status": "error",
                    "message": f"Error generating {size_info['name']} variant: {str(e)}"
                }

        # Prepare the final result with all generated images
        if results:
            # Log the completion of the IAB size generation
            logger.info(f"IAB size generation completed with {len(results)} images")

            # Send a completion status with a flag indicating this is an IAB generate result
            # But don't include the full result with all images again
            yield {
                "status": "complete",
                "message": f"Successfully generated {len(results)} IAB standard ad sizes!",
                "is_resize_to_iab": True
            }
        else:
            logger.error("IAB size generation failed: No images were generated")
            yield {"status": "error", "message": "Failed to generate any IAB standard ad sizes"}


