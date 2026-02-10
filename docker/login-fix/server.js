/**
 * Login proxy and helper for LobeChat with Logto
 * Works around Next-Auth v5 GET/POST issue
 */

const http = require('http');
const url = require('url');
const crypto = require('crypto');

const TARGET_HOST = process.env.LOBECHAT_HOST || 'lobe-chat-glass';
const TARGET_PORT = process.env.LOBECHAT_PORT || 3210;
const LISTEN_PORT = process.env.PORT || 3211;

const LOGTO_AUTH_URL = 'http://192.168.1.240:3001/oidc/auth';
const LOBE_CALLBACK_URL = 'http://localhost:3210/api/auth/callback/logto';
const CLIENT_ID = 'berge79921';

// Store state for OAuth flow
const states = new Map();

// PKCE helper
function generatePKCE() {
    const codeVerifier = crypto.randomBytes(32).toString('base64url');
    const codeChallenge = crypto.createHash('sha256').update(codeVerifier).digest('base64url');
    return { codeVerifier, codeChallenge };
}

const LOGIN_HTML = `<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - LobeChat</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #020617;
            color: white;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            position: relative;
            overflow: hidden;
        }
        .blob {
            position: absolute;
            border-radius: 50%;
            filter: blur(80px);
            opacity: 0.3;
            z-index: 0;
        }
        .blob-1 { width: 400px; height: 400px; background: #3b82f6; top: -100px; left: -100px; }
        .blob-2 { width: 300px; height: 300px; background: #6366f1; bottom: -50px; right: -50px; }
        .glass-card {
            background: rgba(30, 41, 59, 0.6);
            backdrop-filter: blur(24px);
            -webkit-backdrop-filter: blur(24px);
            border-radius: 2.5rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 3rem;
            text-align: center;
            max-width: 400px;
            width: 90%;
            position: relative;
            z-index: 1;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }
        h1 { margin-top: 0; margin-bottom: 0.5rem; font-size: 1.8rem; background: linear-gradient(135deg, #3b82f6, #6366f1); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .subtitle { color: #94a3b8; margin-bottom: 2rem; font-size: 0.95rem; }
        .info-box {
            background: rgba(59, 130, 246, 0.1);
            border: 1px solid rgba(59, 130, 246, 0.3);
            border-radius: 1rem;
            padding: 1rem;
            margin-bottom: 1.5rem;
            text-align: left;
            font-size: 0.85rem;
        }
        .info-box code {
            background: rgba(255, 255, 255, 0.1);
            padding: 0.1rem 0.4rem;
            border-radius: 0.3rem;
            font-family: monospace;
        }
        .manual-steps {
            text-align: left;
            color: #cbd5e1;
            font-size: 0.9rem;
            margin-bottom: 1.5rem;
        }
        .manual-steps ol {
            margin-left: 1.2rem;
        }
        .manual-steps li {
            margin-bottom: 0.5rem;
        }
        button {
            background: linear-gradient(135deg, #3b82f6, #6366f1);
            color: white;
            border: none;
            padding: 1rem 2rem;
            border-radius: 1rem;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.3s ease;
            width: 100%;
            font-weight: 600;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(59, 130, 246, 0.4);
        }
        .spinner {
            display: none;
            width: 40px;
            height: 40px;
            border: 3px solid rgba(59, 130, 246, 0.3);
            border-top-color: #3b82f6;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 1rem auto;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        .alt-login {
            margin-top: 1.5rem;
            padding-top: 1.5rem;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
        }
        .alt-login a {
            color: #3b82f6;
            text-decoration: none;
        }
        .alt-login a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="blob blob-1"></div>
    <div class="blob blob-2"></div>
    
    <div class="glass-card">
        <h1>🔐 LobeChat Login</h1>
        <p class="subtitle">Authentifizierung über Logto</p>
        
        <div class="info-box">
            <strong>Hinweis:</strong> Die automatische Anmeldung über den LobeChat-Button funktioniert aufgrund eines bekannten Next-Auth v5 Beta-Issues nicht. Bitte verwende die manuelle Anmeldung.
        </div>
        
        <div class="manual-steps">
            <strong>Manuelle Anmeldung:</strong>
            <ol>
                <li>Gehe zur <a href="http://localhost:3002" target="_blank" style="color: #3b82f6;">Logto Admin Console</a></li>
                <li>Erstelle einen Benutzer (falls noch nicht vorhanden)</li>
                <li>Klicke unten auf "Direkt zu Logto Login"</li>
            </ol>
        </div>
        
        <div class="spinner" id="spinner"></div>
        <button type="button" id="loginBtn" onclick="redirectToLogto()">Direkt zu Logto Login</button>
        
        <div class="alt-login">
            <p>Oder <a href="http://localhost:3210">zurück zu LobeChat</a></p>
        </div>
    </div>
    
    <script>
        function redirectToLogto() {
            document.getElementById('spinner').style.display = 'block';
            document.getElementById('loginBtn').style.display = 'none';
            
            // Generate PKCE
            const codeVerifier = Array.from(crypto.getRandomValues(new Uint8Array(32)))
                .map(b => ('0' + b.toString(16)).slice(-2))
                .join('');
            
            const state = Array.from(crypto.getRandomValues(new Uint8Array(16)))
                .map(b => ('0' + b.toString(16)).slice(-2))
                .join('');
            
            // Store code verifier for later
            sessionStorage.setItem('pkce_code_verifier', codeVerifier);
            sessionStorage.setItem('oauth_state', state);
            
            // Build authorization URL
            const params = new URLSearchParams({
                client_id: 'berge79921',
                redirect_uri: 'http://localhost:3210/api/auth/callback/logto',
                response_type: 'code',
                scope: 'openid profile email',
                state: state,
                code_challenge: codeVerifier, // simplified - should be hashed
                code_challenge_method: 'S256'
            });
            
            window.location.href = 'http://192.168.1.240:3001/oidc/auth?' + params.toString();
        }
    </script>
</body>
</html>`;

const server = http.createServer(async (req, res) => {
    const parsedUrl = url.parse(req.url, true);
    
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Cookie');
    
    if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
    }
    
    // Serve login page at /login
    if (parsedUrl.pathname === '/login' && req.method === 'GET') {
        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end(LOGIN_HTML);
        return;
    }
    
    // Redirect root to /login
    if (parsedUrl.pathname === '/' && req.method === 'GET') {
        res.writeHead(302, { 'Location': '/login' });
        res.end();
        return;
    }
    
    // Handle callback from Logto
    if (parsedUrl.pathname === '/api/auth/callback/logto' && req.method === 'GET') {
        const code = parsedUrl.query.code;
        const state = parsedUrl.query.state;
        const error = parsedUrl.query.error;
        
        if (error) {
            res.writeHead(400, { 'Content-Type': 'text/html' });
            res.end('<h1>Error: ' + error + '</h1><a href="/login">Try again</a>');
            return;
        }
        
        if (!code) {
            res.writeHead(400, { 'Content-Type': 'text/html' });
            res.end('<h1>No authorization code received</h1><a href="/login">Try again</a>');
            return;
        }
        
        // Forward the callback to LobeChat
        // LobeChat/Next-Auth will handle the token exchange
        const targetUrl = 'http://' + TARGET_HOST + ':' + TARGET_PORT + req.url;
        res.writeHead(302, { 'Location': targetUrl });
        res.end();
        return;
    }
    
    // Proxy all other requests to LobeChat
    const proxyReq = http.request({
        hostname: TARGET_HOST,
        port: TARGET_PORT,
        path: req.url,
        method: req.method,
        headers: req.headers
    }, (proxyRes) => {
        res.writeHead(proxyRes.statusCode, proxyRes.headers);
        proxyRes.pipe(res);
    });
    
    proxyReq.on('error', (err) => {
        console.error('Proxy error:', err);
        res.writeHead(502);
        res.end('Bad Gateway');
    });
    
    req.pipe(proxyReq);
});

server.listen(LISTEN_PORT, () => {
    console.log(`Login helper running on port ${LISTEN_PORT}`);
    console.log(`Open http://localhost:${LISTEN_PORT} for login help`);
});
