from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import httpx
import re
from typing import Optional
from urllib.parse import urljoin, urlparse
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
BASE_DOMAIN = os.getenv("BASE_DOMAIN", "http://localhost:8000")
BASE_PATH = os.getenv("BASE_PATH", "")

app = FastAPI(
    title="Imgur Proxy",
    description="Access Imgur content from anywhere",
    root_path=BASE_PATH or None
)

templates = Jinja2Templates(directory="templates")

static_path = f"{BASE_PATH}/static" if BASE_PATH else "/static"
app.mount(static_path, StaticFiles(directory="static"), name="static")

IMGUR_PATTERNS = [
    r'imgur\.com/([a-zA-Z0-9]+)',
    r'i\.imgur\.com/([a-zA-Z0-9]+\.\w+)',
]

# SSRF Protection: Whitelist of allowed domains
ALLOWED_IMGUR_DOMAINS = {
    'imgur.com',
    'i.imgur.com',
    'www.imgur.com',
    'api.imgur.com'
}

def validate_imgur_url(url: str) -> bool:
    """
    Strictly validate that URL is from Imgur to prevent SSRF attacks.
    Returns True only if the URL is from an allowed Imgur domain.
    """
    try:
        parsed = urlparse(url)
        
        if parsed.scheme not in ['http', 'https']:
            logger.warning(f"Invalid scheme in URL: {url}")
            return False
        
        if parsed.netloc not in ALLOWED_IMGUR_DOMAINS:
            logger.warning(f"Domain not in whitelist: {parsed.netloc}")
            return False
        
        if parsed.username or parsed.password:
            logger.warning(f"URL contains credentials: {url}")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error parsing URL {url}: {e}")
        return False

def extract_imgur_id(url: str) -> Optional[tuple[str, str]]:
    """Extract Imgur ID and type from URL"""
    if not validate_imgur_url(url):
        logger.warning(f"URL failed validation: {url}")
        return None
    
    if '/a/' in url:
        album_match = re.search(r'/a/(?:.*-)?([a-zA-Z0-9]{7})(?:[/?#]|$)', url)
        if album_match:
            return ('album', album_match.group(1))
        album_match = re.search(r'/a/([a-zA-Z0-9]{5,7})(?:[/?#]|$)', url)
        if album_match:
            return ('album', album_match.group(1))
    
    if '/gallery/' in url:
        gallery_match = re.search(r'/gallery/(?:.*-)?([a-zA-Z0-9]{7})(?:[/?#]|$)', url)
        if gallery_match:
            return ('album', gallery_match.group(1)) 
        gallery_match = re.search(r'/gallery/([a-zA-Z0-9]{5,7})(?:[/?#]|$)', url)
        if gallery_match:
            return ('album', gallery_match.group(1))
    
    if 'i.imgur.com' in url:
        direct_match = re.search(r'i\.imgur\.com/([a-zA-Z0-9]+\.\w+)', url)
        if direct_match:
            return ('direct', direct_match.group(1))
    
    if 'imgur.com/' in url:
        path_match = re.search(r'imgur\.com/(.+)', url)
        if path_match:
            path = path_match.group(1).split('?')[0].split('#')[0]
            id_match = re.search(r'([a-zA-Z0-9]{5,7})$', path)
            if id_match:
                return ('image', id_match.group(1))
    
    return None

def get_proxy_url(path: str) -> str:
    """Build full proxy URL using BASE_DOMAIN + BASE_PATH"""
    return urljoin(f"{BASE_DOMAIN}{BASE_PATH}/", path.lstrip("/"))

def validate_imgur_id(imgur_id: str) -> bool:
    """
    Validate Imgur ID format to prevent path traversal or malicious input.
    Imgur IDs are alphanumeric, typically 5-7 characters.
    """
    # Allow alphanumeric IDs (7 chars) and filenames with extensions
    if not re.match(r'^[a-zA-Z0-9]{5,8}(\.[a-zA-Z0-9]{3,4})?$', imgur_id):
        logger.warning(f"Invalid Imgur ID format: {imgur_id}")
        return False
    
    # Prevent path traversal attempts
    if '..' in imgur_id or '/' in imgur_id or '\\' in imgur_id:
        logger.warning(f"Path traversal attempt detected: {imgur_id}")
        return False
    
    return True

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Landing page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/proxy")
async def proxy_url(url: str):
    """Proxy an Imgur URL"""
    result = extract_imgur_id(url)
    
    if not result:
        raise HTTPException(status_code=400, detail="Invalid Imgur URL")
    
    content_type, imgur_id = result
    
    logger.info(f"Extracted ID: {imgur_id} from URL: {url}")
    
    if content_type == 'direct':
        redirect_target = get_proxy_url(f"i/{imgur_id}")
    elif content_type == 'album':
        redirect_target = get_proxy_url(f"a/{imgur_id}")
    else:
        redirect_target = get_proxy_url(f"{imgur_id}")

    return RedirectResponse(url=redirect_target)

@app.get("/a/{album_id}", response_class=HTMLResponse)
async def serve_album(album_id: str, request: Request):
    """Serve Imgur album as a gallery"""
    logger.info(f"Attempting to serve album with ID: {album_id}")
    
    if not validate_imgur_id(album_id):
        raise HTTPException(status_code=400, detail="Invalid album ID format")
    
    api_url = f"https://api.imgur.com/post/v1/albums/{album_id}"
    params = {
        'client_id': 'cf37933da20ab71',
        'include': 'media'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0',
        'Accept': '*/*',
        'Accept-Language': 'en-GB,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://imgur.com/',
        'Origin': 'https://imgur.com',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            response = await client.get(api_url, params=params)
            response.raise_for_status()
            
            album_data = response.json()
            
            images = []
            for media in album_data.get('media', []):
                image_id = media['id']
                
                metadata = media.get('metadata', {})
                description = metadata.get('description', '') or metadata.get('title', '') or media.get('name', '')
                
                images.append({
                    'id': image_id,
                    'url': get_proxy_url(f"i/{image_id}.{media['ext']}"),
                    'width': media.get('width', 0),
                    'height': media.get('height', 0),
                    'name': description,
                    'description': description,
                    'mime_type': media.get('mime_type', 'image/jpeg')
                })
            
            if not images:
                raise HTTPException(status_code=404, detail="Album is empty or not found")
            
            return templates.TemplateResponse("album.html", {
                "request": request,
                "album_id": album_id,
                "title": album_data.get('title', 'Imgur Album'),
                "description": album_data.get('description', ''),
                "image_count": len(images),
                "images": images
            })
            
    except httpx.HTTPError as e:
        logger.error(f"Error fetching album {album_id}: {e}")
        raise HTTPException(status_code=404, detail="Album not found")
    except Exception as e:
        logger.error(f"Error processing album {album_id}: {e}")
        raise HTTPException(status_code=500, detail="Error processing album")

@app.get("/i/{filename}")
async def serve_direct_image(filename: str):
    """Serve images from i.imgur.com directly"""
    if not validate_imgur_id(filename):
        raise HTTPException(status_code=400, detail="Invalid filename format")
    
    imgur_url = f"https://i.imgur.com/{filename}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0',
        'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://imgur.com/',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'image',
        'Sec-Fetch-Mode': 'no-cors',
        'Sec-Fetch-Site': 'cross-site',
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0, headers=headers, follow_redirects=True) as client:
            response = await client.get(imgur_url)
            response.raise_for_status()
            
            content_type = response.headers.get("content-type", "image/jpeg")
            
            return StreamingResponse(
                iter([response.content]),
                media_type=content_type,
                headers={
                    "Cache-Control": "public, max-age=86400",
                    "Access-Control-Allow-Origin": "*"
                }
            )
    except httpx.HTTPError as e:
        logger.error(f"Error fetching {imgur_url}: {e}")
        raise HTTPException(status_code=404, detail="Image not found")

@app.get("/{imgur_id}", response_class=HTMLResponse)
async def serve_image(imgur_id: str, request: Request):
    """Serve Imgur images by ID in image viewer"""
    logger.info(f"Attempting to serve image with ID: {imgur_id}")
    
    if not validate_imgur_id(imgur_id):
        raise HTTPException(status_code=400, detail="Invalid Imgur ID format")
    
    api_url = f"https://api.imgur.com/post/v1/media/{imgur_id}"
    params = {
        'client_id': 'cf37933da20ab71',
        'include': 'media'
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0',
        'Accept': '*/*',
        'Accept-Language': 'en-GB,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://imgur.com/',
        'Origin': 'https://imgur.com',
    }

    try:
        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            response = await client.get(api_url, params=params)
            response.raise_for_status()
            media_data = response.json()

            media_list = media_data.get("media", [])
            if not media_list:
                raise HTTPException(status_code=404, detail="No media found in response")

            m = media_list[0]

            image_id = m["id"]
            ext = m.get("ext", "jpg")
            mime_type = m.get("mime_type", "image/jpeg")
            width = m.get("width", 0)
            height = m.get("height", 0)
            metadata = m.get("metadata", {})
            title = metadata.get("title", "") or m.get("name", "") or f"{image_id}.{ext}"
            description = metadata.get("description", "") or ""

            image_url = get_proxy_url(f"i/{image_id}.{ext}")

            return templates.TemplateResponse("image.html", {
                "request": request,
                "image_id": f"{image_id}.{ext}",
                "image_url": image_url,
                "title": title,
                "description": description,
                "width": width,
                "height": height,
                "mime_type": mime_type
            })

    except httpx.HTTPError as e:
        logger.error(f"Error fetching image {imgur_id}: {e}")
        raise HTTPException(status_code=404, detail="Image not found")
    except Exception as e:
        logger.error(f"Error processing image {imgur_id}: {e}")
        raise HTTPException(status_code=500, detail="Error processing image")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting server on {HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT)