import os, time, base64, requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from requests.exceptions import HTTPError
import replicate


DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0",
}


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
            img = img.resize((1000, 1500))
        else:
            img = Image.new("RGBA", (1000, 1500), (240, 240, 240, 255))
    except Exception as e:
        print(f"[Local Generator] Failed to load background image: {e}")
        img = Image.new("RGBA", (1000, 1500), (240, 240, 240, 255))

    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    text = (title_text or "")[:200]
    words = text.split()
    lines, line = [], ""
    for w in words:
        if len(line) + len(w) + 1 > 28:
            lines.append(line.strip())
            line = w + " "
        else:
            line += w + " "
    if line:
        lines.append(line.strip())

    line_h = font.getbbox("A")[3] + 10
    box_h = line_h * len(lines) + 40
    y = img.height - box_h - 60
    draw.rectangle([40, y - 10, img.width - 40, y + box_h], fill=(0, 0, 0, 150))

    text_y = y + 20
    for ln in lines:
        bbox = draw.textbbox((0, 0), ln, font=font)
        w = bbox[2] - bbox[0]
        x = (img.width - w) / 2
        draw.text((x, text_y), ln, font=font, fill=(255, 255, 255, 255))
        text_y += line_h

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
