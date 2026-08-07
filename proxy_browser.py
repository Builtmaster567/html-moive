#!/usr/bin/env python3
"""
Proxy Browser Server
A fully functional web proxy that allows browsing websites through a proxy interface.
"""

from flask import Flask, request, Response, render_template_string, jsonify, redirect
import requests
from urllib.parse import urlparse, urljoin, quote
import re
import base64
import ssl

app = Flask(__name__)

# Disable SSL warnings for self-signed certificates
requests.packages.urllib3.disable_warnings()

# Configuration
MAX_CONTENT_SIZE = 10 * 1024 * 1024  # 10MB max content size
TIMEOUT = 30  # Request timeout in seconds

# HTML template for the proxy browser interface
BROWSER_INTERFACE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Proxy Browser</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: #1a1a2e;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        
        .browser-bar {
            background: #16213e;
            padding: 15px 20px;
            display: flex;
            align-items: center;
            gap: 15px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
        }
        
        .nav-buttons {
            display: flex;
            gap: 8px;
        }
        
        .nav-btn {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            border: none;
            background: #0f3460;
            color: #e94560;
            font-size: 18px;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .nav-btn:hover {
            background: #e94560;
            color: white;
            transform: scale(1.1);
        }
        
        .nav-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        
        .url-bar {
            flex: 1;
            display: flex;
            align-items: center;
            background: #0f3460;
            border-radius: 25px;
            padding: 5px 15px;
            gap: 10px;
        }
        
        .url-bar input {
            flex: 1;
            background: transparent;
            border: none;
            color: #fff;
            font-size: 16px;
            padding: 10px;
            outline: none;
        }
        
        .url-bar input::placeholder {
            color: #888;
        }
        
        .go-btn {
            background: #e94560;
            color: white;
            border: none;
            padding: 10px 25px;
            border-radius: 20px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s ease;
        }
        
        .go-btn:hover {
            background: #ff6b6b;
            transform: scale(1.05);
        }
        
        .content-frame {
            flex: 1;
            background: #fff;
            border: none;
            width: 100%;
        }
        
        .loading {
            display: none;
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(0,0,0,0.8);
            color: white;
            padding: 30px 50px;
            border-radius: 10px;
            z-index: 1000;
        }
        
        .loading.active {
            display: block;
        }
        
        .error-message {
            display: none;
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: #e94560;
            color: white;
            padding: 30px 50px;
            border-radius: 10px;
            z-index: 1000;
            max-width: 500px;
            text-align: center;
        }
        
        .error-message.active {
            display: block;
        }
        
        .info-text {
            color: #888;
            font-size: 12px;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="browser-bar">
        <div class="nav-buttons">
            <button class="nav-btn" onclick="goBack()" title="Back">←</button>
            <button class="nav-btn" onclick="goForward()" title="Forward">→</button>
            <button class="nav-btn" onclick="reloadPage()" title="Reload">↻</button>
        </div>
        <div class="url-bar">
            <input type="text" id="urlInput" placeholder="Enter URL (e.g., https://example.com)" 
                   onkeypress="if(event.key==='Enter')navigate()">
            <button class="go-btn" onclick="navigate()">GO</button>
        </div>
    </div>
    
    <iframe id="contentFrame" class="content-frame" sandbox="allow-same-origin allow-scripts allow-forms"></iframe>
    
    <div class="loading" id="loading">Loading...</div>
    <div class="error-message" id="errorMessage"></div>
    
    <script>
        let history = [];
        let historyIndex = -1;
        
        function navigate(url) {
            const input = document.getElementById('urlInput');
            url = url || input.value.trim();
            
            if (!url) {
                showError('Please enter a URL');
                return;
            }
            
            // Add http:// if no protocol specified
            if (!url.startsWith('http://') && !url.startsWith('https://')) {
                url = 'https://' + url;
            }
            
            // Validate URL
            try {
                new URL(url);
            } catch (e) {
                showError('Invalid URL format');
                return;
            }
            
            // Navigate through proxy
            const proxyUrl = '/proxy/' + encodeURIComponent(url);
            
            showLoading();
            
            fetch(proxyUrl)
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Failed to load page: ' + response.status);
                    }
                    return response.text();
                })
                .then(html => {
                    const frame = document.getElementById('contentFrame');
                    frame.srcdoc = html;
                    
                    // Update history
                    if (historyIndex < history.length - 1) {
                        history = history.slice(0, historyIndex + 1);
                    }
                    history.push(url);
                    historyIndex = history.length - 1;
                    
                    input.value = url;
                    hideLoading();
                })
                .catch(error => {
                    hideLoading();
                    showError(error.message);
                });
        }
        
        function goBack() {
            if (historyIndex > 0) {
                historyIndex--;
                navigate(history[historyIndex]);
            }
        }
        
        function goForward() {
            if (historyIndex < history.length - 1) {
                historyIndex++;
                navigate(history[historyIndex]);
            }
        }
        
        function reloadPage() {
            if (historyIndex >= 0) {
                navigate(history[historyIndex]);
            }
        }
        
        function showLoading() {
            document.getElementById('loading').classList.add('active');
            document.getElementById('errorMessage').classList.remove('active');
        }
        
        function hideLoading() {
            document.getElementById('loading').classList.remove('active');
        }
        
        function showError(message) {
            const errorDiv = document.getElementById('errorMessage');
            errorDiv.textContent = message;
            errorDiv.classList.add('active');
            setTimeout(() => {
                errorDiv.classList.remove('active');
            }, 5000);
        }
        
        // Allow direct URL parameter
        const urlParams = new URLSearchParams(window.location.search);
        const initialUrl = urlParams.get('url');
        if (initialUrl) {
            navigate(initialUrl);
        }
    </script>
</body>
</html>
'''

def get_base_url(url):
    """Extract base URL from full URL"""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"

def rewrite_urls(content, base_url, proxy_prefix='/proxy/'):
    """Rewrite URLs in HTML content to go through proxy"""
    
    # Rewrite href attributes
    def rewrite_href(match):
        attr = match.group(1)
        url = match.group(2)
        if url.startswith(('javascript:', 'data:', '#', 'mailto:', 'tel:')):
            return match.group(0)
        if not url.startswith('http'):
            url = urljoin(base_url, url)
        return f'{attr}="{proxy_prefix}{quote(url)}"'
    
    content = re.sub(r'(href\s*=\s*["\'])([^"\']+?)["\']', rewrite_href, content, flags=re.IGNORECASE)
    
    # Rewrite src attributes
    def rewrite_src(match):
        attr = match.group(1)
        url = match.group(2)
        if url.startswith(('data:', '#')):
            return match.group(0)
        if not url.startswith('http'):
            url = urljoin(base_url, url)
        return f'{attr}="{proxy_prefix}{quote(url)}"'
    
    content = re.sub(r'(src\s*=\s*["\'])([^"\']+?)["\']', rewrite_src, content, flags=re.IGNORECASE)
    
    # Rewrite action attributes in forms
    def rewrite_action(match):
        attr = match.group(1)
        url = match.group(2)
        if not url.startswith('http'):
            url = urljoin(base_url, url)
        return f'{attr}="{proxy_prefix}{quote(url)}"'
    
    content = re.sub(r'(action\s*=\s*["\'])([^"\']*?)["\']', rewrite_action, content, flags=re.IGNORECASE)
    
    # Rewrite CSS url() references
    def rewrite_css_url(match):
        url = match.group(1).strip('"\'')
        if url.startswith(('data:', '#')):
            return match.group(0)
        if not url.startswith('http'):
            url = urljoin(base_url, url)
        return f'url("{proxy_prefix}{quote(url)}")'
    
    content = re.sub(r'url\(\s*["\']?([^)]+?)["\']?\s*\)', rewrite_css_url, content)
    
    # Add base tag to help with relative URLs
    if '<head>' in content.lower():
        content = re.sub(r'(<head[^>]*>)', f'\\1<base href="{base_url}">', content, flags=re.IGNORECASE)
    
    return content

@app.route('/')
def index():
    """Serve the proxy browser interface"""
    return render_template_string(BROWSER_INTERFACE)

# Catch-all route must be defined LAST to avoid capturing /proxy routes
@app.route('/<path:catch_all>')
def catch_all(catch_all=None):
    """Catch all other routes and serve the main interface"""
    return render_template_string(BROWSER_INTERFACE)

@app.route('/proxy/<path:url>')
def proxy(url):
    """Proxy endpoint that fetches and rewrites web content"""
    
    # Decode the URL
    try:
        target_url = requests.utils.unquote(url)
        
        # Handle double encoding
        if target_url.startswith('http'):
            pass
        else:
            # Try to decode again if it looks encoded
            try:
                target_url = requests.utils.unquote(target_url)
            except:
                pass
    except Exception as e:
        return jsonify({'error': f'Invalid URL: {str(e)}'}), 400
    
    # Validate URL
    if not target_url.startswith(('http://', 'https://')):
        target_url = 'https://' + target_url
    
    try:
        parsed = urlparse(target_url)
        if not parsed.netloc:
            return jsonify({'error': 'Invalid URL format'}), 400
    except Exception as e:
        return jsonify({'error': f'URL parsing error: {str(e)}'}), 400
    
    # Fetch the content
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    try:
        response = requests.get(
            target_url,
            headers=headers,
            timeout=TIMEOUT,
            verify=False,  # Disable SSL verification for proxy functionality
            allow_redirects=True,
            stream=True
        )
        
        # Check content size
        content_length = response.headers.get('Content-Length')
        if content_length and int(content_length) > MAX_CONTENT_SIZE:
            return jsonify({'error': 'Content too large'}), 413
        
        # Get content
        content = response.content
        
        # Determine content type
        content_type = response.headers.get('Content-Type', 'text/html')
        
        # Process HTML content
        if 'text/html' in content_type:
            try:
                html_content = content.decode('utf-8', errors='ignore')
                base_url = get_base_url(target_url)
                rewritten_content = rewrite_urls(html_content, base_url)
                
                return Response(
                    rewritten_content,
                    status=response.status_code,
                    headers={
                        'Content-Type': 'text/html; charset=utf-8',
                        'X-Proxied-URL': target_url,
                        'X-Frame-Options': 'SAMEORIGIN',
                    }
                )
            except Exception as e:
                return jsonify({'error': f'HTML processing error: {str(e)}'}), 500
        
        # Return other content types as-is (images, CSS, JS, etc.)
        response_headers = {
            'Content-Type': content_type,
            'X-Proxied-URL': target_url,
        }
        
        # Copy cache headers
        for header in ['Cache-Control', 'ETag', 'Last-Modified']:
            if header in response.headers:
                response_headers[header] = response.headers[header]
        
        return Response(
            content,
            status=response.status_code,
            headers=response_headers
        )
        
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Request timed out'}), 504
    except requests.exceptions.ConnectionError:
        return jsonify({'error': 'Failed to connect to the website'}), 502
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Request error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'proxy-browser'})

if __name__ == '__main__':
    print("=" * 60)
    print("🌐 Proxy Browser Server Starting...")
    print("=" * 60)
    print("\n📍 Access the proxy browser at:")
    print("   http://localhost:5000/")
    print("\n💡 Usage:")
    print("   1. Open http://localhost:5000/ in your browser")
    print("   2. Enter any URL (e.g., https://example.com)")
    print("   3. Click GO to browse through the proxy")
    print("\n⚠️  Note: This is for educational purposes only.")
    print("   Respect website terms of service and robots.txt")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
