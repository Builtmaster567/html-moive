# Proxy Browser

A fully functional web proxy browser built with Python Flask that allows you to browse websites through a proxy interface.

## Features

- 🌐 **Full Web Browsing**: Browse any website through the proxy
- 🔒 **Privacy**: Your requests are made from the server, not your local machine
- 🎨 **Modern UI**: Clean, dark-themed browser-like interface
- ⏱️ **Navigation Controls**: Back, forward, and reload buttons
- 📝 **URL Rewriting**: Automatically rewrites links to work through the proxy
- 🖼️ **Resource Loading**: Supports images, CSS, JavaScript, and other assets
- ⚡ **Fast Performance**: Configurable timeouts and content size limits

## Requirements

- Python 3.7+
- Flask
- Requests

## Installation

### Option 1: Using requirements.txt (Recommended)

```bash
pip install -r requirements.txt
```

### Option 2: Manual Installation

```bash
pip install flask requests
```

## Usage

### Running Locally

```bash
python proxy_browser.py
```

The server will start on `http://localhost:5000/`

### Running in GitHub Codespaces

1. **Create a Codespace**: Click the "Code" button on your repository and select "Create codespace on main"
2. **Wait for Setup**: Codespaces will automatically install dependencies from `requirements.txt`
3. **Start the Server**: Run `python proxy_browser.py` in the terminal
4. **Make Port Public**: 
   - Go to the "Ports" tab at the bottom
   - Right-click on port 5000
   - Select "Port Visibility" → "Public"
5. **Access Your Browser**: Click the "Forwarded Address" link that appears

### Direct URL Access

1. Open your web browser
2. Navigate to `http://localhost:5000/`
3. Enter any URL (e.g., `https://example.com`)
4. Click **GO** to browse through the proxy

### Direct URL Access

You can also access specific URLs directly:
```
http://localhost:5000/?url=https://example.com
```

## API Endpoints

- `GET /` - Main proxy browser interface
- `GET /proxy/<url>` - Proxy endpoint for fetching web content
- `GET /health` - Health check endpoint

## Configuration

You can modify these settings in the code:

```python
MAX_CONTENT_SIZE = 10 * 1024 * 1024  # 10MB max content size
TIMEOUT = 30  # Request timeout in seconds
```

## How It Works

1. **User Interface**: The browser provides a clean interface with URL bar and navigation controls
2. **Request Handling**: When you enter a URL, it's sent to the `/proxy/<url>` endpoint
3. **Content Fetching**: The server fetches the target website using the requests library
4. **URL Rewriting**: All links, images, and resources are rewritten to go through the proxy
5. **Content Delivery**: The modified HTML is returned and displayed in an iframe

## Security Notes

⚠️ **Important**: This proxy browser is intended for educational purposes only.

- Respect website terms of service and robots.txt files
- Do not use for malicious activities
- Be aware of legal implications in your jurisdiction
- The server disables SSL verification for proxy functionality (not recommended for production)

## Limitations

- Some modern websites with heavy JavaScript may not work perfectly
- WebSocket connections are not supported
- Some sites may block proxy traffic
- Large files are limited to 10MB by default

## Troubleshooting

**Server won't start:**
- Ensure port 5000 is not in use
- Check if Flask and requests are installed: `pip install flask requests`

**Website doesn't load:**
- Check the server logs for error messages
- Some websites actively block proxy traffic
- Try a different website to verify the proxy is working

**Links don't work:**
- The URL rewriting handles most cases but may miss some dynamic content
- Try clicking links again or use the URL bar directly

## License

This project is provided as-is for educational purposes.
