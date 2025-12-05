import os, time, base64, requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

FONT_PATH = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

def hf_text_to_image(prompt, hf_token, model='stabilityai/stable-diffusion-2'):
    api = f'https://api-inference.huggingface.co/models/{model}'
    headers = {'Authorization': f'Bearer {hf_token}'}
    payload = {'inputs': prompt}
    r = requests.post(api, headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    return r.content

def build_aesthetic_image(background_url=None, title_text='', outfile=None, hf_token=None):
    if not outfile:
        outfile = f'/tmp/pin_{int(time.time())}.jpg'
    if hf_token:
        try:
            prompt = f"Aesthetic vertical photo for a Pinterest pin, 1000x1500, photo background, subject: {title_text}, soft lighting, high detail, muted color palette"
            img_bytes = hf_text_to_image(prompt, hf_token)
            with open(outfile, 'wb') as f:
                f.write(img_bytes)
            return outfile
        except Exception as e:
            print('HF generation failed, falling back to local generator', e)
    try:
        if background_url:
            r = requests.get(background_url, timeout=20)
            img = Image.open(BytesIO(r.content)).convert('RGBA')
            img = img.resize((1000,1500))
        else:
            img = Image.new('RGBA', (1000,1500), (240,240,240,255))
    except Exception:
        img = Image.new('RGBA', (1000,1500), (240,240,240,255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(FONT_PATH, 60)
    except Exception:
        font = ImageFont.load_default()
    text = (title_text or '')[:200]
    words = text.split()
    lines=[]
    line=''
    for w in words:
        if len(line)+len(w)+1>28:
            lines.append(line.strip())
            line = w + ' '
        else:
            line += w + ' '
    if line:
        lines.append(line.strip())
    line_h = font.getsize('A')[1] + 10
    box_h = line_h*len(lines) + 40
    y = img.height - box_h - 60
    draw.rectangle([40, y-10, img.width-40, y+box_h], fill=(0,0,0,150))
    text_y = y + 20
    for ln in lines:
        w,h = draw.textsize(ln, font=font)
        x = (img.width - w)/2
        draw.text((x, text_y), ln, font=font, fill=(255,255,255,255))
        text_y += line_h
    rgb = img.convert('RGB')
    rgb.save(outfile, quality=85)
    return outfile

def upload_image_to_github(path_local, repo=None, branch='gh-pages', dest_path=None, token=None):
    if not token:
        token = os.getenv('GITHUB_TOKEN')
    if not repo:
        repo = os.getenv('GITHUB_REPOSITORY')
    if not token or not repo:
        raise RuntimeError('GITHUB_TOKEN and GITHUB_REPOSITORY required to upload images')
    if not dest_path:
        dest_path = f'images/{int(time.time())}_{os.path.basename(path_local)}'
    owner, repo_name = repo.split('/')
    url = f'https://api.github.com/repos/{owner}/{repo_name}/contents/{dest_path}'
    with open(path_local, 'rb') as f:
        content = f.read()
    b64 = base64.b64encode(content).decode('utf-8')
    payload = {
        'message': f'Add generated image {os.path.basename(dest_path)}',
        'content': b64,
        'branch': branch
    }
    headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github+json'}
    r = requests.put(url, json=payload, headers=headers, timeout=30)
    r.raise_for_status()
    raw_url = f'https://raw.githubusercontent.com/{owner}/{repo_name}/{branch}/{dest_path}'
    return raw_url
