from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx
import re
from typing import Optional
from urllib.parse import urlparse
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Imgur Proxy", description="Access Imgur content from anywhere")

templates = Jinja2Templates(directory="templates")

IMGUR_PATTERNS = [
    r'imgur\.com/([a-zA-Z0-9]+)',
    r'i\.imgur\.com/([a-zA-Z0-9]+\.\w+)',
]

def extract_imgur_id(url: str) -> Optional[tuple[str, str]]:
    """Extract Imgur ID and type from URL"""
    if 'imgur.com/' in url and '/gallery/' not in url and '/a/' not in url and 'i.imgur.com' not in url:
        path_match = re.search(r'imgur\.com/(.+)', url)
        if path_match:
            path = path_match.group(1)
            path = path.split('?')[0].split('#')[0]
            id_match = re.search(r'([a-zA-Z0-9]{7})$', path)
            if id_match:
                return ('image', id_match.group(1))
    
    for pattern in IMGUR_PATTERNS:
        match = re.search(pattern, url)
        if match:
            imgur_id = match.group(1)
            if '/a/' in url:
                return ('album', imgur_id)
            elif '/gallery/' in url:
                return ('gallery', imgur_id)
            elif '.' in imgur_id:
                return ('direct', imgur_id)
            else:
                return ('image', imgur_id)
    return None

def get_imgur_url(content_type: str, imgur_id: str) -> str:
    """Construct the appropriate Imgur URL"""
    if content_type == 'direct':
        return f"https://i.imgur.com/{imgur_id}"
    else:
        return f"https://i.imgur.com/{imgur_id}.jpg"

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
        return RedirectResponse(url=f"/i/{imgur_id}")
    else:
        return RedirectResponse(url=f"/{imgur_id}")

@app.get("/i/{filename}")
async def serve_direct_image(filename: str):
    """Serve images from i.imgur.com directly"""
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

@app.get("/{imgur_id}")
async def serve_image(imgur_id: str):
    """Serve Imgur images by ID - tries multiple extensions"""
    logger.info(f"Attempting to serve image with ID: {imgur_id}")
    
    extensions = ['jpg', 'png', 'gif', 'jpeg', 'webp']
    
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
    
    for ext in extensions:
        imgur_url = f"https://i.imgur.com/{imgur_id}.{ext}"
        logger.info(f"Trying: {imgur_url}")
        
        try:
            async with httpx.AsyncClient(timeout=30.0, headers=headers, follow_redirects=True) as client:
                response = await client.get(imgur_url)
                logger.info(f"Response status for {imgur_url}: {response.status_code}")
                
                if response.status_code == 200:
                    content_type = response.headers.get("content-type", f"image/{ext}")
                    
                    return StreamingResponse(
                        iter([response.content]),
                        media_type=content_type,
                        headers={
                            "Cache-Control": "public, max-age=86400",
                            "Access-Control-Allow-Origin": "*"
                        }
                    )
        except httpx.HTTPError as e:
            logger.error(f"Error trying {imgur_url}: {e}")
            continue
    
    logger.error(f"Image not found with ID {imgur_id} after trying all extensions")
    raise HTTPException(status_code=404, detail="Image not found with any common extension")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)