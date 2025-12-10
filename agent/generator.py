import os, time, base64, requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from requests.exceptions import HTTPError
import replicate


DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0",
}
TARGET_WIDTH = 1000
TARGET_HEIGHT = 1500  # 2:3 Pinterest Aspect Ratio


def generate_image_replicate(prompt, outfile, model_name="prunaai/p-image"):
    """
    Generate an image using Replicate.
    Uses replicate.run() (recommended method) instead of model.predict().
    Raises RuntimeError on failure.
    """
    try:
        # Check available models
        available_models = [m.id for m in replicate.models.list()]
        if model_name not in available_models:
            raise RuntimeError(
                f"[Replicate ERROR] Model '{model_name}' not available for this token.\n"
                f"Available models: {available_models}"
            )

        print(f"[Replicate] Using model '{model_name}' to generate image...")
        output = replicate.run(model_name, input={"prompt": prompt})

        if isinstance(output, list) and len(output) > 0:
            image_url = output[0]
        elif isinstance(output, str):
            image_url = output
        else:
            raise RuntimeError(
                f"[Replicate ERROR] Unexpected output from model: {output}"
            )

        r = requests.get(image_url, timeout=60)
        r.raise_for_status()

        with open(outfile, "wb") as f:
            f.write(r.content)

        print(f"[Replicate] Image saved to {outfile}")
        return outfile

    except Exception as e:
        raise RuntimeError(f"[Replicate ERROR] Generation failed: {e}") from e


def get_wrapped_text(text: str, font, max_width: int):
    """Dynamically wraps text based on font and maximum pixel width."""
    draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))

    words = text.split()
    lines, current_line = [], ""

    for word in words:
        # Check width of line + new word
        test_line = current_line + word + " "
        # Use getbbox for modern Pillow versions
        bbox = draw.textbbox((0, 0), test_line, font=font)
        test_width = bbox[2] - bbox[0]

        if test_width <= max_width:
            current_line = test_line
        else:
            lines.append(current_line.strip())
            current_line = word + " "

    if current_line:
        lines.append(current_line.strip())

    return lines


def build_aesthetic_image(
    background_url=None, title_text="", outfile=None, replicate_model="prunaai/p-image"
):
    """
    Build aesthetic Pinterest-style image.
    Primary: Replicate AI
    Fallback: Local overlay generator
    """
    if not outfile:
        outfile = f"/tmp/pin_{int(time.time())}.jpg"

    replicate_token = os.getenv("REPLICATE_API_TOKEN")

    # PRIMARY: Replicate AI
    if replicate_token:
        prompt = (
            f"Aesthetic vertical Pinterest pin, 1000x1500, soft lighting, "
            f"clean layout, well composed, subject: {title_text}"
        )
        try:
            return generate_image_replicate(prompt, outfile, model_name=replicate_model)
        except RuntimeError as e:
            print(e)
            print(f"[Fallback] Using local image generator for '{title_text}'")

    # FALLBACK: Local image builder
    try:
        if background_url:
            r = requests.get(background_url, headers=DEFAULT_HEADERS, timeout=20)
            img = Image.open(BytesIO(r.content)).convert("RGBA")
            original_w, original_h = img.size

            scale_w = TARGET_WIDTH / original_w
            scale_h = TARGET_HEIGHT / original_h

            scale = min(scale_w, scale_h)

            new_w = int(original_w * scale)
            new_h = int(original_h * scale)

            scaled_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            img = Image.new("RGBA", (TARGET_WIDTH, TARGET_HEIGHT), (0, 0, 0, 255))

            x_offset = (TARGET_WIDTH - new_w) // 2
            y_offset = (TARGET_HEIGHT - new_h) // 2

            img.paste(scaled_img, (x_offset, y_offset))
        else:
            img = Image.new("RGBA", (1000, 1500), (240, 240, 240, 255))
    except Exception as e:
        print(f"[Local Generator] Failed to load background image: {e}")
        img = Image.new("RGBA", (1000, 1500), (240, 240, 240, 255))

    draw = ImageDraw.Draw(img)

    # DYNAMIC FONT SIZING (Using a placeholder font for size)
    FONT_SIZE = 80
    try:
        font = ImageFont.load_default(size=FONT_SIZE)
    except Exception:
        font = ImageFont.load_default()
        FONT_SIZE = 16

    MAX_TEXT_WIDTH = int(img.width * 0.85)
    text_to_use = title_text or ""

    lines = get_wrapped_text(text_to_use, font, MAX_TEXT_WIDTH)

    # CALCULATE BOX AND POSITION
    # Get the bounding box of the entire text block to determine the required box height
    total_text_height = 0
    max_line_width = 0
    for ln in lines:
        bbox = draw.textbbox((0, 0), ln, font=font)
        line_w = bbox[2] - bbox[0]
        line_h = bbox[3] - bbox[1]
        total_text_height += line_h
        if line_w > max_line_width:
            max_line_width = line_w

    LINE_PADDING = 20  # Vertical space between lines
    BOX_PADDING = 40  # Padding around the text box

    total_text_height += LINE_PADDING * (len(lines) - 1)
    box_h = total_text_height + BOX_PADDING * 2

    # Position the box in the bottom quarter of the image
    y = img.height - box_h - 150

    # Draw transparent black rectangle
    draw.rectangle(
        [40, y, img.width - 40, y + box_h],  # Left padding  # Right padding
        fill=(0, 0, 0, 180),  # Darker overlay
    )

    # DRAW TEXT
    text_y = y + BOX_PADDING
    for ln in lines:
        # Recalculate bbox for alignment
        bbox = draw.textbbox((0, 0), ln, font=font)
        w = bbox[2] - bbox[0]

        # Center the text horizontally
        x = (img.width - w) / 2

        draw.text((x, text_y), ln, font=font, fill=(255, 255, 255, 255))

        # Move down for the next line
        text_y += (bbox[3] - bbox[1]) + LINE_PADDING  # Use actual line height + padding

    rgb = img.convert("RGB")
    rgb.save(outfile, quality=85)
    print(f"[Local Generator] Image saved to {outfile}")
    return outfile


def upload_image_to_github(
    path_local, repo=None, branch="gh-pages", dest_path=None, token=None
):
    if not token:
        token = os.getenv("GITHUB_TOKEN")
    if not repo:
        repo = os.getenv("GITHUB_REPOSITORY")
    if not token or not repo:
        raise RuntimeError(
            "GITHUB_TOKEN and GITHUB_REPOSITORY required to upload images"
        )
    if not dest_path:
        dest_path = f"images/{int(time.time())}_{os.path.basename(path_local)}"
    owner, repo_name = repo.split("/")
    url = f"https://api.github.com/repos/{owner}/{repo_name}/contents/{dest_path}"
    with open(path_local, "rb") as f:
        content = f.read()
    b64 = base64.b64encode(content).decode("utf-8")
    payload = {
        "message": f"Add generated image {os.path.basename(dest_path)}",
        "content": b64,
        "branch": branch,
    }
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }
    r = requests.put(url, json=payload, headers=headers, timeout=30)
    r.raise_for_status()
    raw_url = (
        f"https://raw.githubusercontent.com/{owner}/{repo_name}/{branch}/{dest_path}"
    )
    return raw_url
