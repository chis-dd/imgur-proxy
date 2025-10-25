# Imgur Proxy 🖼️

A FastAPI-based proxy service to access Imgur content from anywhere, even in regions where Imgur is blocked.

## Features

- ✅ Proxy any Imgur image URL
- ✅ Support for direct images (i.imgur.com)
- ✅ Support for regular Imgur links (imgur.com/abc123)
- ✅ Simple, clean web interface
- ✅ Fast async image fetching
- ✅ Automatic extension detection
- ✅ Caching headers for better performance

## Quick Start

### Local Development

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Run the server:**
```bash
python main.py
```

3. **Open in browser:**
```
http://localhost:8000
```

### Using the Proxy

**Method 1: Web Interface**
- Go to the homepage
- Paste an Imgur URL
- Click "View Image"

**Method 2: Direct URL replacement**
Replace `imgur.com` or `i.imgur.com` with your proxy domain:

```
Before: https://imgur.com/abc123
After:  https://yourproxy.com/abc123

Before: https://i.imgur.com/abc123.jpg
After:  https://yourproxy.com/i/abc123.jpg
```

## Deployment Options

### Option 1: Railway (Recommended)

1. Create a Railway account at https://railway.app
2. Click "New Project" → "Deploy from GitHub repo"
3. Connect your repo
4. Railway will auto-detect Python and deploy
5. Get your public URL

### Option 2: Render

1. Create account at https://render.com
2. Click "New" → "Web Service"
3. Connect your GitHub repo
4. Set:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Deploy

### Option 3: Fly.io

1. Install flyctl: https://fly.io/docs/hands-on/install-flyctl/
2. Create Fly account and login:
```bash
fly auth login
```

3. Create `fly.toml`:
```toml
app = "your-imgur-proxy"

[build]
  builder = "paketobuildpacks/builder:base"

[env]
  PORT = "8000"

[[services]]
  http_checks = []
  internal_port = 8000
  processes = ["app"]
  protocol = "tcp"

  [services.concurrency]
    hard_limit = 25
    soft_limit = 20

  [[services.ports]]
    force_https = true
    handlers = ["http"]
    port = 80

  [[services.ports]]
    handlers = ["tls", "http"]
    port = 443

  [[services.tcp_checks]]
    grace_period = "1s"
    interval = "15s"
    restart_limit = 0
    timeout = "2s"
```

4. Deploy:
```bash
fly launch
fly deploy
```

### Option 4: DigitalOcean App Platform

1. Create account at https://www.digitalocean.com
2. Go to App Platform → Create App
3. Connect GitHub repo
4. Choose region OUTSIDE UK
5. DigitalOcean will auto-detect Python
6. Deploy

### Option 5: VPS (Most Control)

Deploy on a VPS outside the UK (DigitalOcean, Vultr, Linode, etc.):

```bash
# Install Python 3.10+
sudo apt update
sudo apt install python3 python3-pip

# Clone your repo
git clone your-repo-url
cd imgur-proxy

# Install dependencies
pip3 install -r requirements.txt

# Run with Gunicorn (production)
pip3 install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Or use systemd service (recommended)
# Create /etc/systemd/system/imgur-proxy.service
```

Example systemd service:
```ini
[Unit]
Description=Imgur Proxy Service
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/imgur-proxy
ExecStart=/usr/local/bin/gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable imgur-proxy
sudo systemctl start imgur-proxy
```

## Add Nginx Reverse Proxy (VPS)

```nginx
server {
    listen 80;
    server_name yourproxy.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

Then get SSL with Certbot:
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourproxy.com
```

## Environment Variables (Optional)

You can add these for production:

```bash
export MAX_CACHE_SIZE=1000  # Number of images to cache
export REQUEST_TIMEOUT=30   # Timeout in seconds
export LOG_LEVEL=INFO       # DEBUG, INFO, WARNING, ERROR
```

## API Endpoints

- `GET /` - Landing page
- `GET /proxy?url={imgur_url}` - Proxy an Imgur URL
- `GET /{imgur_id}` - Serve image by ID (tries multiple extensions)
- `GET /i/{filename}` - Serve direct image from i.imgur.com
- `GET /health` - Health check

## Performance Tips

1. **Add Redis caching** for frequently accessed images:
```bash
pip install redis
```

2. **Use a CDN** like Cloudflare in front of your proxy

3. **Increase workers** in production:
```bash
gunicorn main:app -w 8 -k uvicorn.workers.UvicornWorker
```

## Legal Considerations

- This proxy simply fetches public Imgur content and serves it
- No content is modified or stored permanently
- Respect Imgur's Terms of Service
- Use responsibly

## Future Enhancements

- [ ] Add Redis caching
- [ ] Support for Imgur albums/galleries
- [ ] Rate limiting per IP
- [ ] Image optimization/compression
- [ ] Browser extension for automatic redirects
- [ ] Support for other blocked image hosts

## Contributing

Pull requests welcome! Please ensure:
- Code follows PEP 8
- Add tests for new features
- Update documentation

## License

MIT License - feel free to use and modify!

---

Made with ❤️ to help access content freely