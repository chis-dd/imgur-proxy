# Imgur Proxy

A self-hosted proxy service for accessing Imgur content. This proxy bypasses regional blocks by fetching images from Imgur on your behalf using proper browser headers to avoid rate limiting.

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Start the server:
```bash
python main.py
```

The server will run on `http://localhost:8000`

## Usage

### Web Interface

Open `http://localhost:8000` in your browser and paste any Imgur URL to view the image.

### Browser Extension (Automatic Redirects)

Install the Redirector extension for your browser:
- Chrome: https://chrome.google.com/webstore/detail/redirector/ocgpenflpmgnfapjedencafcfakcekcd
- Firefox: https://addons.mozilla.org/en-US/firefox/addon/redirector/

Add this redirect rule:

```
Description: Imgur Proxy (Regex)
Example URL: https://imgur.com/abc123
Include pattern: ^https?://(i\.)?imgur\.com/(.*)$
Redirect to: http://localhost:8000/proxy?url=https://$1imgur.com/$2
Pattern type: Regular Expression
```

Now all Imgur links will automatically redirect through your proxy.

## Requirements

- Python 3.8+
- FastAPI
- httpx
- uvicorn
- jinja2

See `requirements.txt` for complete list.