/**
 * Auth gateway for LobeChat.
 * Fixes Auth.js v5 provider sign-in by translating browser GET to
 * server-side CSRF + POST for /api/auth/signin/:provider.
 */

const http = require('http');

const TARGET_HOST = process.env.LOBECHAT_HOST || 'lobe-chat-glass';
const TARGET_PORT = Number(process.env.LOBECHAT_PORT || 3210);
const LISTEN_PORT = Number(process.env.PORT || 3210);
const APP_PUBLIC_URL = process.env.APP_PUBLIC_URL || 'http://localhost:3210';

const SIGNIN_GET_PATTERN = /^\/(?:api\/auth|next-auth)\/signin\/[^/]+$/;
const INTERNAL_HOSTS = new Set([TARGET_HOST, 'lobe-chat-glass', 'lobe']);

const textEncoder = new TextEncoder();

const parseCookieHeader = (cookieHeader) => {
  const cookies = new Map();
  if (!cookieHeader) return cookies;

  for (const rawPart of cookieHeader.split(';')) {
    const part = rawPart.trim();
    if (!part) continue;

    const index = part.indexOf('=');
    if (index === -1) continue;

    const name = part.slice(0, index).trim();
    const value = part.slice(index + 1).trim();
    cookies.set(name, value);
  }

  return cookies;
};

const parseSetCookieHeaders = (setCookieHeaders) => {
  const cookies = new Map();
  if (!setCookieHeaders) return cookies;

  const list = Array.isArray(setCookieHeaders) ? setCookieHeaders : [setCookieHeaders];
  for (const raw of list) {
    if (!raw) continue;
    const pair = raw.split(';', 1)[0];
    const index = pair.indexOf('=');
    if (index === -1) continue;

    const name = pair.slice(0, index).trim();
    const value = pair.slice(index + 1).trim();
    cookies.set(name, value);
  }

  return cookies;
};

const serializeCookieHeader = (cookies) =>
  Array.from(cookies.entries())
    .map(([name, value]) => `${name}=${value}`)
    .join('; ');

const mergeCookieMaps = (...maps) => {
  const merged = new Map();
  for (const map of maps) {
    for (const [name, value] of map.entries()) merged.set(name, value);
  }
  return merged;
};

const getForwardedProtocol = (req) => {
  const forwarded = req.headers['x-forwarded-proto'];
  if (typeof forwarded === 'string' && forwarded.length > 0) {
    return forwarded.split(',')[0].trim();
  }
  return 'http';
};

const getPublicHost = (req) => {
  const forwarded = req.headers['x-forwarded-host'];
  if (typeof forwarded === 'string' && forwarded.length > 0) {
    return forwarded.split(',')[0].trim();
  }
  return req.headers.host || `localhost:${LISTEN_PORT}`;
};

const rewriteLocationHeader = (location, req) => {
  if (!location || location.startsWith('/')) return location;

  try {
    const parsed = new URL(location);
    const hostPort = `${parsed.hostname}:${parsed.port || (parsed.protocol === 'https:' ? '443' : '80')}`;
    const targetHostPort = `${TARGET_HOST}:${TARGET_PORT}`;

    const isInternalHost = INTERNAL_HOSTS.has(parsed.hostname) || hostPort === targetHostPort;
    if (!isInternalHost) return location;

    parsed.protocol = `${getForwardedProtocol(req)}:`;
    parsed.host = getPublicHost(req);
    return parsed.toString();
  } catch {
    return location;
  }
};

const requestTarget = ({ method, path, headers = {}, body = '' }) =>
  new Promise((resolve, reject) => {
    const upstreamReq = http.request(
      {
        hostname: TARGET_HOST,
        port: TARGET_PORT,
        method,
        path,
        headers,
      },
      (upstreamRes) => {
        const chunks = [];
        upstreamRes.on('data', (chunk) => chunks.push(chunk));
        upstreamRes.on('end', () => {
          resolve({
            body: Buffer.concat(chunks),
            headers: upstreamRes.headers,
            statusCode: upstreamRes.statusCode || 500,
          });
        });
      },
    );

    upstreamReq.on('error', reject);
    if (body) upstreamReq.write(body);
    upstreamReq.end();
  });

const buildHelperHtml = () => {
  const callbackUrl = APP_PUBLIC_URL.endsWith('/') ? APP_PUBLIC_URL : `${APP_PUBLIC_URL}/`;
  const loginHref = `/api/auth/signin/logto?callbackUrl=${encodeURIComponent(callbackUrl)}`;

  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>LobeChat Login</title>
  <style>
    body { margin: 0; font-family: Arial, sans-serif; background: #0f172a; color: #e2e8f0; }
    .wrap { min-height: 100vh; display: grid; place-items: center; padding: 24px; }
    .card { width: min(560px, 100%); background: #1e293b; border: 1px solid #334155; border-radius: 16px; padding: 24px; }
    h1 { margin: 0 0 12px; font-size: 22px; }
    p { margin: 0 0 16px; line-height: 1.5; color: #cbd5e1; }
    a.button { display: inline-block; background: #2563eb; color: #fff; text-decoration: none; padding: 10px 16px; border-radius: 10px; font-weight: 600; }
    .muted { margin-top: 14px; font-size: 14px; color: #94a3b8; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1>LobeChat Login Gateway</h1>
      <p>The authentication gateway is active. It converts the broken GET sign-in flow to the required CSRF-protected POST flow automatically.</p>
      <a class="button" href="${loginHref}">Sign in with Logto</a>
      <p class="muted">Main app: <a href="${APP_PUBLIC_URL}" style="color:#93c5fd">${APP_PUBLIC_URL}</a></p>
    </div>
  </div>
</body>
</html>`;
};

const sendLoginHelper = (res) => {
  const html = buildHelperHtml();
  res.writeHead(200, {
    'cache-control': 'no-store',
    'content-length': textEncoder.encode(html).byteLength,
    'content-type': 'text/html; charset=utf-8',
  });
  res.end(html);
};

const handleProviderSigninGet = async (req, res, parsedUrl) => {
  try {
    const incomingCookies = parseCookieHeader(req.headers.cookie);
    const forwardingHost = getPublicHost(req);
    const forwardingProto = getForwardedProtocol(req);

    const csrfResponse = await requestTarget({
      method: 'GET',
      path: '/api/auth/csrf',
      headers: {
        accept: 'application/json',
        cookie: serializeCookieHeader(incomingCookies),
        host: req.headers.host || forwardingHost,
        'user-agent': req.headers['user-agent'] || 'lobe-auth-gateway',
        'x-forwarded-host': forwardingHost,
        'x-forwarded-proto': forwardingProto,
      },
    });

    if (csrfResponse.statusCode < 200 || csrfResponse.statusCode >= 300) {
      throw new Error(`CSRF request failed with status ${csrfResponse.statusCode}`);
    }

    let csrfToken;
    try {
      const payload = JSON.parse(csrfResponse.body.toString('utf8'));
      csrfToken = payload.csrfToken;
    } catch {
      throw new Error('Could not parse CSRF response JSON');
    }

    if (!csrfToken) throw new Error('Missing csrfToken in CSRF response');

    const csrfCookies = parseSetCookieHeaders(csrfResponse.headers['set-cookie']);
    const requestCookies = mergeCookieMaps(incomingCookies, csrfCookies);

    const callbackUrl = parsedUrl.searchParams.get('callbackUrl') || APP_PUBLIC_URL;
    const form = new URLSearchParams();
    form.set('csrfToken', csrfToken);
    form.set('callbackUrl', callbackUrl);

    for (const [key, value] of parsedUrl.searchParams.entries()) {
      if (key === 'csrfToken' || key === 'callbackUrl') continue;
      form.append(key, value);
    }

    const formBody = form.toString();
    const signinResponse = await requestTarget({
      method: 'POST',
      path: req.url,
      headers: {
        accept: req.headers.accept || '*/*',
        'content-length': Buffer.byteLength(formBody),
        'content-type': 'application/x-www-form-urlencoded',
        cookie: serializeCookieHeader(requestCookies),
        host: req.headers.host || forwardingHost,
        origin: `${forwardingProto}://${forwardingHost}`,
        'user-agent': req.headers['user-agent'] || 'lobe-auth-gateway',
        'x-forwarded-host': forwardingHost,
        'x-forwarded-proto': forwardingProto,
      },
      body: formBody,
    });

    const responseHeaders = { ...signinResponse.headers };
    if (responseHeaders.location) {
      responseHeaders.location = rewriteLocationHeader(responseHeaders.location, req);
    }

    res.writeHead(signinResponse.statusCode, responseHeaders);
    res.end(signinResponse.body);
  } catch (error) {
    console.error('Auth gateway signin translation failed:', error);
    res.writeHead(502, { 'content-type': 'text/plain; charset=utf-8' });
    res.end('Auth gateway error');
  }
};

const proxyRequest = (req, res) => {
  const forwardingHost = getPublicHost(req);
  const forwardingProto = getForwardedProtocol(req);
  const headers = {
    ...req.headers,
    host: req.headers.host || forwardingHost,
    'x-forwarded-host': forwardingHost,
    'x-forwarded-proto': forwardingProto,
  };

  const proxyReq = http.request(
    {
      hostname: TARGET_HOST,
      port: TARGET_PORT,
      path: req.url,
      method: req.method,
      headers,
    },
    (proxyRes) => {
      const responseHeaders = { ...proxyRes.headers };
      if (responseHeaders.location) {
        responseHeaders.location = rewriteLocationHeader(responseHeaders.location, req);
      }

      res.writeHead(proxyRes.statusCode || 500, responseHeaders);
      proxyRes.pipe(res);
    },
  );

  proxyReq.on('error', (error) => {
    console.error('Proxy error:', error);
    res.writeHead(502, { 'content-type': 'text/plain; charset=utf-8' });
    res.end('Bad Gateway');
  });

  req.pipe(proxyReq);
};

const shouldShowHelperOnRoot = (req) => {
  const host = getPublicHost(req);
  return host.endsWith(':3211');
};

const server = http.createServer(async (req, res) => {
  const publicOrigin = `${getForwardedProtocol(req)}://${getPublicHost(req)}`;
  const parsedUrl = new URL(req.url, publicOrigin);

  if (req.method === 'GET' && parsedUrl.pathname === '/healthz') {
    res.writeHead(200, { 'content-type': 'text/plain; charset=utf-8' });
    res.end('ok');
    return;
  }

  if (req.method === 'GET' && parsedUrl.pathname === '/login') {
    sendLoginHelper(res);
    return;
  }

  if (req.method === 'GET' && parsedUrl.pathname === '/' && shouldShowHelperOnRoot(req)) {
    res.writeHead(302, { location: '/login' });
    res.end();
    return;
  }

  if (req.method === 'GET' && SIGNIN_GET_PATTERN.test(parsedUrl.pathname)) {
    await handleProviderSigninGet(req, res, parsedUrl);
    return;
  }

  proxyRequest(req, res);
});

server.listen(LISTEN_PORT, () => {
  console.log(`Auth gateway listening on port ${LISTEN_PORT}`);
  console.log(`Target: http://${TARGET_HOST}:${TARGET_PORT}`);
});
