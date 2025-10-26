# mirrgr

A self-hosted proxy service for accessing Imgur content. This proxy bypasses regional blocks by fetching images from Imgur on your behalf using proper browser headers to avoid rate limiting.

## Installation

1. **Clone or download this repository**

2. **Create a virtual environment:**
```bash
python -m venv .venv
```

3. **Activate the virtual environment:**

   On Linux/Mac:
   ```bash
   source .venv/bin/activate
   ```
   
   On Windows:
   ```bash
   .venv\Scripts\activate
   ```

4. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

5. **Configure environment variables:**

   Create a `.env` file in the project root:
   ```bash
   cp .env.example .env
   ```
   
   Or manually create `.env` with the following content:
   ```env
   HOST=0.0.0.0
   PORT=8000
   BASE_DOMAIN=http://localhost:8000
   BASE_PATH=
   ```

   **Configuration options:**
   - `HOST`: Server bind address (default: `0.0.0.0`)
   - `PORT`: Server port (default: `8000`)
   - `BASE_DOMAIN`: Your proxy's public URL (e.g., `https://imgur-proxy.example.com`)
   - `BASE_PATH`: Optional base path if running behind a reverse proxy (e.g., `/imgur-proxy`)

6. **Start the server:**
```bash
python main.py
```

The server will run on `http://localhost:8000` (or your configured HOST:PORT)

## Usage

### Web Interface

Open `http://localhost:8000` in your browser and paste any Imgur URL to view the image.

### Browser Extension (Automatic Redirects)

Install the Redirector extension for your browser:
- **Chrome**: https://chrome.google.com/webstore/detail/redirector/ocgpenflpmgnfapjedencafcfakcekcd
- **Firefox**: https://addons.mozilla.org/en-US/firefox/addon/redirector/

Add this redirect rule:

```
Description: Imgur Proxy (Regex)
Example URL: https://imgur.com/abc123
Include pattern: ^https?://(i\.)?imgur\.com/(.*)$
Redirect to: http://localhost:8000/proxy?url=https://$1imgur.com/$2
Pattern type: Regular Expression
```

**Note:** If you changed `BASE_DOMAIN` or `BASE_PATH`, update the redirect URL accordingly.

Now all Imgur links will automatically redirect through your proxy.

## Production Deployment

For production use with a custom domain:

1. Update `.env`:
   ```env
   HOST=0.0.0.0
   PORT=8000
   BASE_DOMAIN=https://your-domain.com
   BASE_PATH=
   ```

2. Update your browser extension redirect rule to use your domain:
   ```
   Redirect to: https://your-domain.com/proxy?url=https://$1imgur.com/$2
   ```

3. (Optional) Run with a process manager like systemd or supervisor for auto-restart.

## Requirements

- Python 3.8+
- FastAPI
- httpx
- uvicorn
- jinja2
- python-dotenv

See `requirements.txt` for complete list.

## Troubleshooting

**Issue: "Module not found" errors**
- Make sure your virtual environment is activated
- Run `pip install -r requirements.txt` again

**Issue: Images not loading**
- Check your `.env` configuration matches your deployment
- Verify `BASE_DOMAIN` is accessible from your browser
- Check server logs for errors

**Issue: Browser extension not working**
- Ensure the redirect URL matches your `BASE_DOMAIN` configuration
- Test the proxy manually first by visiting the web interface

## TODO
- Create docker image for quick deployment