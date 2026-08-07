"""
Advanced Proxy Browser - "FoxProxy" Edition
A fully functional, feature-rich proxy browser running in Codespaces.
Includes: Tabs, History, Bookmarks, Settings, Themes, Ad-Blocker, UA Switching, and more.
"""

from flask import Flask, request, Response, redirect, url_for, send_from_directory, jsonify, render_template_string
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, quote, unquote
import re
import json
import os
import time
from datetime import datetime

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max limit

# --- Configuration & State ---
PROXY_PREFIX = '/proxy/'
ALLOWED_METHODS = ['GET', 'POST', 'HEAD', 'OPTIONS']
TIMEOUT = 30
SESSION_DATA = {
    'history': [],
    'bookmarks': [
        {'title': 'Google', 'url': 'https://www.google.com'},
        {'title': 'Wikipedia', 'url': 'https://en.wikipedia.org'},
        {'title': 'GitHub', 'url': 'https://github.com'}
    ],
    'settings': {
        'block_ads': True,
        'block_trackers': True,
        'javascript_enabled': False,
        'images_enabled': True,
        'theme': 'dark',
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0'
    }
}

def make_proxy_url(original_url):
    if not original_url.startswith(('http://', 'https://')):
        original_url = 'https://' + original_url
    return f"{PROXY_PREFIX}{quote(original_url, safe='')}"

def rewrite_html(html_content, base_url):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    for tag in soup.find_all('a', href=True):
        href = tag['href']
        if href.startswith('#') or href.startswith('javascript:') or href.startswith('data:'):
            continue
        absolute_url = urljoin(base_url, href)
        tag['href'] = make_proxy_url(absolute_url)
        if tag.has_attr('target'):
            tag['target'] = '_self'

    if SESSION_DATA['settings']['images_enabled']:
        for tag in soup.find_all(['img', 'source', 'video', 'audio'], src=True):
            src = tag['src']
            if src.startswith('data:'):
                continue
            absolute_url = urljoin(base_url, src)
            tag['src'] = make_proxy_url(absolute_url)
    
    for tag in soup.find_all(style=True):
        style = tag['style']
        urls = re.findall(r'url\([\'"]?(.*?)[\'"]?\)', style)
        for url in urls:
            if not url.startswith('data:'):
                abs_url = urljoin(base_url, url)
                new_url = make_proxy_url(abs_url)
                style = style.replace(url, new_url)
        tag['style'] = style

    for form in soup.find_all('form', action=True):
        action = form['action']
        absolute_url = urljoin(base_url, action)
        form['action'] = make_proxy_url(absolute_url)
        form['method'] = form.get('method', 'GET').upper()
        if form['method'] not in ['GET', 'POST']:
            form['method'] = 'POST'

    if soup.head:
        base_tag = soup.new_tag('base', href=make_proxy_url(base_url))
        soup.head.insert(0, base_tag)
        
    for meta in soup.find_all('meta', http_equiv=True):
        if meta['http-equiv'].lower() == 'content-security-policy':
            meta.decompose()

    return str(soup)

def rewrite_css(css_content, base_url):
    urls = re.findall(r'url\([\'"]?(.*?)[\'"]?\)', css_content)
    for url in urls:
        if not url.startswith('data:') and not url.startswith('#'):
            abs_url = urljoin(base_url, url)
            new_url = make_proxy_url(abs_url)
            css_content = css_content.replace(url, new_url)
    return css_content

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/api/history', methods=['GET', 'POST'])
def api_history():
    if request.method == 'POST':
        data = request.json
        if data.get('action') == 'add':
            entry = {'url': data['url'], 'title': data.get('title', data['url']), 'time': datetime.now().isoformat()}
            SESSION_DATA['history'].insert(0, entry)
            if len(SESSION_DATA['history']) > 100:
                SESSION_DATA['history'] = SESSION_DATA['history'][:100]
            return jsonify({'success': True})
        elif data.get('action') == 'clear':
            SESSION_DATA['history'] = []
            return jsonify({'success': True})
    return jsonify(SESSION_DATA['history'])

@app.route('/api/bookmarks', methods=['GET', 'POST', 'DELETE'])
def api_bookmarks():
    if request.method == 'POST':
        data = request.json
        SESSION_DATA['bookmarks'].append({'title': data['title'], 'url': data['url']})
        return jsonify({'success': True, 'bookmarks': SESSION_DATA['bookmarks']})
    elif request.method == 'DELETE':
        data = request.json
        SESSION_DATA['bookmarks'] = [b for b in SESSION_DATA['bookmarks'] if b['url'] != data.get('url')]
        return jsonify({'success': True, 'bookmarks': SESSION_DATA['bookmarks']})
    return jsonify(SESSION_DATA['bookmarks'])

@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    if request.method == 'POST':
        SESSION_DATA['settings'].update(request.json)
        return jsonify({'success': True, 'settings': SESSION_DATA['settings']})
    return jsonify(SESSION_DATA['settings'])

@app.route('/')
@app.route('/<path:path>')
def serve_interface(path=None):
    html_ui = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FoxProxy Browser</title>
    <style>
        :root { --bg-color: #1c1b22; --toolbar-bg: #2b2a33; --text-color: #fbfbfe; --accent-color: #00ddff; --input-bg: #42414d; --tab-active: #42414d; --tab-inactive: #2b2a33; --border-color: #5b5b66; }
        [data-theme="light"] { --bg-color: #ffffff; --toolbar-bg: #f0f0f4; --text-color: #15141a; --accent-color: #0060df; --input-bg: #ffffff; --tab-active: #ffffff; --tab-inactive: #f0f0f4; --border-color: #cfcfd8; }
        body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: var(--bg-color); color: var(--text-color); display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
        .tabs-bar { display: flex; background: var(--toolbar-bg); padding: 8px 8px 0; gap: 4px; align-items: flex-end; border-bottom: 1px solid var(--border-color); }
        .tab { padding: 8px 16px; border-radius: 8px 8px 0 0; cursor: pointer; font-size: 12px; max-width: 200px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: flex; align-items: center; gap: 8px; background: var(--tab-inactive); color: var(--text-color); opacity: 0.7; transition: 0.2s; }
        .tab.active { background: var(--tab-active); opacity: 1; font-weight: bold; }
        .tab:hover:not(.active) { background: rgba(255,255,255,0.1); }
        .tab-close { width: 16px; height: 16px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 10px; }
        .tab-close:hover { background: rgba(255,0,0,0.3); }
        .new-tab-btn { width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 18px; margin-bottom: 4px; }
        .nav-bar { display: flex; align-items: center; padding: 8px; background: var(--toolbar-bg); gap: 8px; border-bottom: 1px solid var(--border-color); }
        .nav-btn { background: none; border: none; color: var(--text-color); cursor: pointer; padding: 6px; border-radius: 4px; font-size: 16px; }
        .nav-btn:hover { background: rgba(255,255,255,0.1); }
        .url-bar-container { flex: 1; position: relative; display: flex; align-items: center; }
        .url-bar { width: 100%; background: var(--input-bg); border: 1px solid transparent; border-radius: 4px; padding: 8px 12px; color: var(--text-color); font-size: 14px; outline: none; }
        .url-bar:focus { border-color: var(--accent-color); box-shadow: 0 0 0 2px rgba(0, 221, 255, 0.3); }
        .tools-bar { display: flex; justify-content: space-between; padding: 4px 8px; background: var(--toolbar-bg); font-size: 12px; border-bottom: 1px solid var(--border-color); }
        .tool-group { display: flex; gap: 12px; }
        .tool-item { cursor: pointer; display: flex; align-items: center; gap: 4px; opacity: 0.8; }
        .tool-item:hover { opacity: 1; color: var(--accent-color); }
        .browser-content { flex: 1; position: relative; background: #fff; }
        iframe { width: 100%; height: 100%; border: none; display: block; }
        .panel { position: absolute; top: 0; right: 0; width: 300px; height: 100%; background: var(--toolbar-bg); border-left: 1px solid var(--border-color); transform: translateX(100%); transition: transform 0.3s ease; z-index: 100; display: flex; flex-direction: column; }
        .panel.open { transform: translateX(0); }
        .panel-header { padding: 16px; font-weight: bold; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; }
        .panel-content { flex: 1; overflow-y: auto; padding: 8px; }
        .panel-item { padding: 8px; border-radius: 4px; cursor: pointer; display: flex; flex-direction: column; gap: 4px; margin-bottom: 4px; }
        .panel-item:hover { background: rgba(255,255,255,0.05); }
        .close-panel { cursor: pointer; font-size: 18px; }
        .start-page { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; background: var(--bg-color); color: var(--text-color); }
        .logo { font-size: 48px; font-weight: bold; margin-bottom: 20px; color: var(--accent-color); }
        .start-search { width: 500px; max-width: 90%; padding: 12px; border-radius: 24px; border: 1px solid var(--border-color); background: var(--input-bg); color: var(--text-color); font-size: 16px; outline: none; text-align: center; }
        .quick-links { display: flex; gap: 20px; margin-top: 40px; flex-wrap: wrap; justify-content: center; }
        .quick-link { display: flex; flex-direction: column; align-items: center; gap: 8px; cursor: pointer; width: 80px; }
        .quick-icon { width: 48px; height: 48px; border-radius: 12px; background: var(--toolbar-bg); display: flex; align-items: center; justify-content: center; font-size: 20px; }
        .toast { position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); background: var(--accent-color); color: #000; padding: 8px 16px; border-radius: 20px; font-size: 14px; font-weight: bold; opacity: 0; transition: opacity 0.3s; pointer-events: none; z-index: 1000; }
        .toast.show { opacity: 1; }
    </style>
</head>
<body data-theme="dark">
    <div class="tabs-bar" id="tabsBar"></div>
    <div class="nav-bar">
        <button class="nav-btn" onclick="goBack()">←</button>
        <button class="nav-btn" onclick="goForward()">→</button>
        <button class="nav-btn" onclick="reloadPage()">↻</button>
        <button class="nav-btn" onclick="goHome()">🏠</button>
        <div class="url-bar-container">
            <input type="text" class="url-bar" id="urlInput" placeholder="Search or enter address" onkeydown="if(event.key==='Enter') navigateTo()">
        </div>
        <button class="nav-btn" onclick="togglePanel('bookmarksPanel')">★</button>
        <button class="nav-btn" onclick="togglePanel('historyPanel')">🕒</button>
        <button class="nav-btn" onclick="togglePanel('settingsPanel')">⚙️</button>
    </div>
    <div class="tools-bar">
        <div class="tool-group">
            <div class="tool-item" onclick="toggleAdBlock()">🚫 Ads: <span id="adBlockStatus">ON</span></div>
            <div class="tool-item" onclick="changeTheme()">🎨 Theme</div>
        </div>
    </div>
    <div class="browser-content" id="contentArea">
        <iframe id="mainFrame" name="mainFrame" sandbox="allow-forms allow-same-origin allow-scripts allow-popups"></iframe>
        <div id="startPage" class="start-page" style="display:none;">
            <div class="logo">🦊 FoxProxy</div>
            <input type="text" class="start-search" placeholder="Search the web..." onkeydown="if(event.key==='Enter') startSearch(this.value)">
            <div class="quick-links" id="quickLinks"></div>
        </div>
    </div>
    <div class="panel" id="bookmarksPanel"><div class="panel-header">Bookmarks <span class="close-panel" onclick="togglePanel('bookmarksPanel')">&times;</span></div><div class="panel-content" id="bookmarksList"></div></div>
    <div class="panel" id="historyPanel"><div class="panel-header">History <span class="close-panel" onclick="togglePanel('historyPanel')">&times;</span></div><div class="panel-content" id="historyList"></div></div>
    <div class="panel" id="settingsPanel"><div class="panel-header">Settings <span class="close-panel" onclick="togglePanel('settingsPanel')">&times;</span></div><div class="panel-content"><div class="panel-item">Firefox UA Active</div></div></div>
    <div class="toast" id="toast">Notification</div>
    <script>
        let tabs = [{ id: 1, url: '', title: 'New Tab', history: [], historyIndex: -1 }];
        let activeTabId = 1;
        let settings = { ads: true, theme: 'dark' };
        function init() { loadSettings(); renderTabs(); showStartPage(); loadBookmarks(); loadHistory(); }
        function loadSettings() { fetch('/api/settings').then(r=>r.json()).then(data => { settings = data; document.body.setAttribute('data-theme', data.theme); document.getElementById('adBlockStatus').innerText = data.block_ads ? 'ON' : 'OFF'; }); }
        function renderTabs() { const bar = document.getElementById('tabsBar'); bar.innerHTML = ''; tabs.forEach(tab => { const el = document.createElement('div'); el.className = 'tab ' + (tab.id === activeTabId ? 'active' : ''); el.onclick = () => switchTab(tab.id); el.innerHTML = '<span>' + tab.title.substring(0, 15) + '</span><span class="tab-close" onclick="event.stopPropagation(); closeTab('+tab.id+')">&times;</span>'; bar.appendChild(el); }); const newBtn = document.createElement('div'); newBtn.className = 'new-tab-btn'; newBtn.innerHTML = '+'; newBtn.onclick = createTab; bar.appendChild(newBtn); }
        function createTab(url = '') { const newId = Date.now(); tabs.push({ id: newId, url: url, title: 'New Tab', history: [], historyIndex: -1 }); switchTab(newId); if(url) navigateTo(url); else showStartPage(); }
        function closeTab(id) { if(tabs.length === 1) { tabs[0].url = ''; tabs[0].title = 'New Tab'; tabs[0].history = []; tabs[0].historyIndex = -1; showStartPage(); renderTabs(); return; } const idx = tabs.findIndex(t => t.id === id); tabs.splice(idx, 1); if(activeTabId === id) switchTab(tabs[Math.max(0, idx-1)].id); else renderTabs(); }
        function switchTab(id) { activeTabId = id; const tab = tabs.find(t => t.id === id); renderTabs(); updateUI(tab); }
        function updateUI(tab) { document.getElementById('urlInput').value = tab.url; if(tab.url) { document.getElementById('startPage').style.display = 'none'; document.getElementById('mainFrame').style.display = 'block'; } else showStartPage(); }
        function showStartPage() { document.getElementById('mainFrame').style.display = 'none'; document.getElementById('startPage').style.display = 'flex'; renderQuickLinks(); }
        function renderQuickLinks() { const container = document.getElementById('quickLinks'); container.innerHTML = ''; fetch('/api/bookmarks').then(r=>r.json()).then(bms => { bms.slice(0, 6).forEach(bm => { const div = document.createElement('div'); div.className = 'quick-link'; div.innerHTML = '<div class="quick-icon">🌐</div><span>'+bm.title+'</span>'; div.onclick = () => navigateTo(bm.url); container.appendChild(div); }); }); }
        function navigateTo(forcedUrl) { const input = document.getElementById('urlInput'); let url = forcedUrl || input.value; if(!url) return; if(!url.startsWith('http')) { if(url.includes('.') && !url.includes(' ')) url = 'https://' + url; else url = 'https://www.google.com/search?q=' + encodeURIComponent(url); } const tab = tabs.find(t => t.id === activeTabId); tab.url = url; tab.title = url; tab.historyIndex++; tab.history = tab.history.slice(0, tab.historyIndex); tab.history.push(url); fetch('/api/history', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({action: 'add', url: url, title: url}) }); document.getElementById('mainFrame').src = '/proxy/' + encodeURIComponent(url); document.getElementById('mainFrame').style.display = 'block'; document.getElementById('startPage').style.display = 'none'; updateUI(tab); renderTabs(); showToast('Loading...'); }
        function startSearch(query) { navigateTo('https://www.google.com/search?q=' + encodeURIComponent(query)); }
        function goBack() { const tab = tabs.find(t => t.id === activeTabId); if(tab.historyIndex > 0) { tab.historyIndex--; const url = tab.history[tab.historyIndex]; tab.url = url; updateUI(tab); document.getElementById('mainFrame').src = '/proxy/' + encodeURIComponent(url); } }
        function goForward() { const tab = tabs.find(t => t.id === activeTabId); if(tab.historyIndex < tab.history.length - 1) { tab.historyIndex++; const url = tab.history[tab.historyIndex]; tab.url = url; updateUI(tab); document.getElementById('mainFrame').src = '/proxy/' + encodeURIComponent(url); } }
        function reloadPage() { const frame = document.getElementById('mainFrame'); frame.src = frame.src; showToast('Reloading...'); }
        function goHome() { const tab = tabs.find(t => t.id === activeTabId); tab.url = ''; tab.history = []; tab.historyIndex = -1; showStartPage(); updateUI(tab); renderTabs(); }
        function togglePanel(id) { const p = document.getElementById(id); if(p.classList.contains('open')) p.classList.remove('open'); else { document.querySelectorAll('.panel').forEach(x => x.classList.remove('open')); p.classList.add('open'); if(id === 'bookmarksPanel') loadBookmarks(); if(id === 'historyPanel') loadHistory(); } }
        function loadBookmarks() { fetch('/api/bookmarks').then(r=>r.json()).then(bms => { const list = document.getElementById('bookmarksList'); list.innerHTML = ''; bms.forEach(bm => { const div = document.createElement('div'); div.className = 'panel-item'; div.innerHTML = '<div style="font-weight:500">'+bm.title+'</div><div style="font-size:11px;opacity:0.7">'+bm.url+'</div>'; div.onclick = () => { navigateTo(bm.url); togglePanel('bookmarksPanel'); }; list.appendChild(div); }); }); }
        function loadHistory() { fetch('/api/history').then(r=>r.json()).then(hist => { const list = document.getElementById('historyList'); list.innerHTML = ''; hist.forEach(h => { const div = document.createElement('div'); div.className = 'panel-item'; div.innerHTML = '<div style="font-weight:500">'+h.title+'</div><div style="font-size:11px;opacity:0.7">'+h.time.split('T')[0]+'</div>'; div.onclick = () => { navigateTo(h.url); togglePanel('historyPanel'); }; list.appendChild(div); }); }); }
        function toggleAdBlock() { const newVal = !settings.ads; settings.ads = newVal; fetch('/api/settings', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({block_ads: newVal})}); document.getElementById('adBlockStatus').innerText = newVal ? 'ON' : 'OFF'; showToast(newVal ? 'Ad Blocker Enabled' : 'Ad Blocker Disabled'); }
        function changeTheme() { const newTheme = settings.theme === 'dark' ? 'light' : 'dark'; settings.theme = newTheme; document.body.setAttribute('data-theme', newTheme); fetch('/api/settings', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({theme: newTheme})}); }
        function showToast(msg) { const t = document.getElementById('toast'); t.innerText = msg; t.classList.add('show'); setTimeout(() => t.classList.remove('show'), 2000); }
        init();
    </script>
</body>
</html>
    """
    return render_template_string(html_ui)

@app.route(PROXY_PREFIX + '<path:url>')
def proxy_get(url):
    target_url = unquote(url)
    if not target_url.startswith(('http://', 'https://')):
        target_url = 'https://' + target_url
    
    try:
        headers = {
            'User-Agent': SESSION_DATA['settings']['user_agent'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        if SESSION_DATA['settings']['block_ads']:
            blocked_domains = ['doubleclick.net', 'adservice.google.com', 'facebook.com/tr']
            parsed = urlparse(target_url)
            if any(blocked in parsed.netloc for blocked in blocked_domains):
                return Response("Blocked by AdBlocker", status=403)

        resp = requests.get(target_url, headers=headers, timeout=TIMEOUT, verify=False, allow_redirects=True)
        content_type = resp.headers.get('Content-Type', '').lower()
        content = resp.content
        
        if 'text/html' in content_type:
            try:
                decoded_content = content.decode('utf-8', errors='ignore')
                rewritten = rewrite_html(decoded_content, target_url)
                return Response(rewritten, status=resp.status_code, content_type='text/html; charset=utf-8')
            except Exception as e:
                return Response(f"Error rewriting HTML: {str(e)}", status=500)
        
        if 'text/css' in content_type:
            try:
                decoded_content = content.decode('utf-8', errors='ignore')
                rewritten = rewrite_css(decoded_content, target_url)
                return Response(rewritten, status=resp.status_code, content_type='text/css; charset=utf-8')
            except Exception as e:
                return content
        
        return Response(content, status=resp.status_code, content_type=resp.headers.get('Content-Type'))

    except requests.exceptions.RequestException as e:
        error_html = f"""
        <html><body style="background:#222; color:#fff; font-family:sans-serif; padding:50px; text-align:center;">
            <h1>🦊 FoxProxy Error</h1>
            <p>Failed to load: {target_url}</p>
            <p style="color:#ff6b6b">{str(e)}</p>
            <button onclick="window.history.back()" style="padding:10px 20px; background:#00ddff; border:none; border-radius:5px; cursor:pointer; color:#000; font-weight:bold; margin-top:20px;">Go Back</button>
        </body></html>
        """
        return Response(error_html, status=502, content_type='text/html')

if __name__ == '__main__':
    print("🦊 FoxProxy Browser Starting...")
    print("Access at: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
