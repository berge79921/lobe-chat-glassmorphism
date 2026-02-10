/**
 * Auth gateway for LobeChat.
 * Fixes Auth.js v5 provider sign-in by translating browser GET to
 * server-side CSRF + POST for /api/auth/signin/:provider.
 * 
 * Modified for LegalChat: Injects custom branding CSS/JS into HTML responses.
 */

const http = require('http');
const https = require('https');

const TARGET_HOST = process.env.LOBECHAT_HOST || 'lobe-chat-glass';
const TARGET_PORT = Number(process.env.LOBECHAT_PORT || 3210);
const LISTEN_PORT = Number(process.env.PORT || 3210);
const APP_PUBLIC_URL = process.env.APP_PUBLIC_URL || 'http://localhost:3210';

const SIGNIN_GET_PATTERN = /^\/(?:api\/auth|next-auth)\/signin\/[^/]+$/;
const INTERNAL_HOSTS = new Set([TARGET_HOST, 'lobe-chat-glass', 'lobe']);
const OPENAI_TTS_PATH = '/webapi/tts/openai';
const EDGE_TTS_PATH = '/webapi/tts/edge';
const EDGE_TTS_FALLBACK_ENABLED = process.env.TTS_EDGE_FALLBACK === '1';
const GOOGLE_TTS_FALLBACK_ENABLED = process.env.TTS_GOOGLE_FALLBACK !== '0';
const GOOGLE_TTS_HOST = process.env.TTS_GOOGLE_HOST || 'translate.google.com';
const GOOGLE_TTS_CLIENT = process.env.TTS_GOOGLE_CLIENT || 'tw-ob';
const GOOGLE_TTS_MAX_CHARS = Number(process.env.TTS_GOOGLE_MAX_CHARS || 180);
const BRANDING_VERSION = process.env.LEGALCHAT_BRANDING_VERSION || '2026-02-10-04';
const DISABLE_SERVICE_WORKER = process.env.LEGALCHAT_DISABLE_SERVICE_WORKER !== '0';
const BRANDING_CACHE_CONTROL = 'no-store, no-cache, must-revalidate, proxy-revalidate';
const DEFAULT_EDGE_VOICE = process.env.TTS_FALLBACK_EDGE_VOICE || 'en-US-JennyNeural';
const OPENAI_TO_EDGE_VOICE_MAP = {
  alloy: 'en-US-JennyNeural',
  ash: 'en-US-GuyNeural',
  ballad: 'en-US-AriaNeural',
  coral: 'en-US-AnaNeural',
  echo: 'en-US-EricNeural',
  fable: 'en-US-ChristopherNeural',
  nova: 'en-US-MichelleNeural',
  onyx: 'en-US-SteffanNeural',
  sage: 'en-US-RogerNeural',
  shimmer: 'en-US-JennyNeural',
  verse: 'en-US-AriaNeural',
};

const textEncoder = new TextEncoder();
const BRANDING_BOOTSTRAP = DISABLE_SERVICE_WORKER
  ? `<script data-legalchat-sw-cleanup="1">(function(){try{if('serviceWorker' in navigator){navigator.serviceWorker.getRegistrations().then(function(regs){for(var i=0;i<regs.length;i+=1){regs[i].unregister().catch(function(){});}});}if('caches' in window&&caches.keys){caches.keys().then(function(keys){for(var i=0;i<keys.length;i+=1){var name=keys[i]||'';if(/serwist|workbox|next-pwa|lobehub|lobechat/i.test(name)){caches.delete(name).catch(function(){});}}});}}catch(error){console.warn('[LegalChat] SW cleanup failed',error);}})();</script>`
  : '';
const BRANDING_INJECTION = [
  '<!-- LegalChat Branding Assets -->',
  BRANDING_BOOTSTRAP,
  `<link rel="stylesheet" href="/custom.css?v=${BRANDING_VERSION}" data-legalchat-branding="1" />`,
  `<script src="/legalchat-branding.js?v=${BRANDING_VERSION}" data-legalchat-branding="1"></script>`,
].join('');
const NOOP_SERVICE_WORKER = [
  "self.addEventListener('install', function () { self.skipWaiting(); });",
  "self.addEventListener('activate', function (event) {",
  "  event.waitUntil((async function () {",
  "    await self.registration.unregister();",
  "    var clients = await self.clients.matchAll({ includeUncontrolled: true, type: 'window' });",
  '    for (var i = 0; i < clients.length; i += 1) {',
  '      clients[i].navigate(clients[i].url);',
  '    }',
  '  })());',
  '});',
  "self.addEventListener('fetch', function () {});",
].join('\n');

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

const readRequestBody = (req) =>
  new Promise((resolve, reject) => {
    const chunks = [];
    req.on('data', (chunk) => chunks.push(chunk));
    req.on('end', () => resolve(Buffer.concat(chunks)));
    req.on('error', reject);
  });

const buildUpstreamHeaders = ({ req, forwardingHost, forwardingProto, bodyBuffer }) => {
  const headers = {
    ...req.headers,
    host: req.headers.host || forwardingHost,
    'x-forwarded-host': forwardingHost,
    'x-forwarded-proto': forwardingProto,
  };

  if (typeof bodyBuffer !== 'undefined') {
    headers['content-length'] = String(bodyBuffer.length);
    delete headers['transfer-encoding'];
  }

  return headers;
};

const setNoStoreHeaders = (headers) => {
  headers['cache-control'] = BRANDING_CACHE_CONTROL;
  headers.pragma = 'no-cache';
  headers.expires = '0';
  delete headers.etag;
  delete headers['last-modified'];
};

const getLocaleDefaultEdgeVoice = (locale) => {
  if (typeof locale !== 'string') return DEFAULT_EDGE_VOICE;
  const lowerLocale = locale.toLowerCase();
  if (lowerLocale.startsWith('de')) return 'de-DE-KatjaNeural';
  if (lowerLocale.startsWith('fr')) return 'fr-FR-DeniseNeural';
  if (lowerLocale.startsWith('es')) return 'es-ES-ElviraNeural';
  if (lowerLocale.startsWith('ja')) return 'ja-JP-NanamiNeural';
  if (lowerLocale.startsWith('zh')) return 'zh-CN-XiaoxiaoNeural';
  return DEFAULT_EDGE_VOICE;
};

const mapOpenAIVoiceToEdgeVoice = ({ locale, voice }) => {
  const localeDefault = getLocaleDefaultEdgeVoice(locale);
  if (!voice || typeof voice !== 'string') return localeDefault;
  return OPENAI_TO_EDGE_VOICE_MAP[voice.toLowerCase()] || localeDefault;
};

const parseTtsPayload = (rawBodyBuffer) => {
  try {
    return JSON.parse(rawBodyBuffer.toString('utf8'));
  } catch {
    return null;
  }
};

const createEdgeTtsPayload = (rawBodyBuffer) => {
  const payload = parseTtsPayload(rawBodyBuffer);
  if (!payload) return rawBodyBuffer;

  const options = payload && typeof payload.options === 'object' ? payload.options : {};
  const edgePayload = {
    ...payload,
    options: {
      ...options,
      voice: mapOpenAIVoiceToEdgeVoice({
        locale: options.locale,
        voice: options.voice,
      }),
    },
  };

  return Buffer.from(JSON.stringify(edgePayload), 'utf8');
};

const normalizeLocaleForGoogleTts = (locale) => {
  if (typeof locale !== 'string' || locale.length === 0) return 'en';
  return locale.replaceAll('_', '-');
};

const splitTextForGoogleTts = (input, maxChars = GOOGLE_TTS_MAX_CHARS) => {
  const text = String(input || '').replace(/\s+/g, ' ').trim();
  if (!text) return [];
  if (text.length <= maxChars) return [text];

  const chunks = [];
  const sentences = text.split(/(?<=[.!?;:])\s+/);
  let current = '';

  for (const sentence of sentences) {
    const part = sentence.trim();
    if (!part) continue;

    if (!current) {
      if (part.length <= maxChars) {
        current = part;
      } else {
        for (let i = 0; i < part.length; i += maxChars) {
          chunks.push(part.slice(i, i + maxChars));
        }
      }
      continue;
    }

    const merged = `${current} ${part}`;
    if (merged.length <= maxChars) {
      current = merged;
      continue;
    }

    chunks.push(current);
    if (part.length <= maxChars) {
      current = part;
      continue;
    }

    for (let i = 0; i < part.length; i += maxChars) {
      chunks.push(part.slice(i, i + maxChars));
    }
    current = '';
  }

  if (current) chunks.push(current);
  return chunks;
};

const requestGoogleTtsChunk = ({ locale, text }) =>
  new Promise((resolve, reject) => {
    const params = new URLSearchParams({
      client: GOOGLE_TTS_CLIENT,
      ie: 'UTF-8',
      q: text,
      tl: normalizeLocaleForGoogleTts(locale),
    });

    const upstreamReq = https.request(
      {
        hostname: GOOGLE_TTS_HOST,
        method: 'GET',
        path: `/translate_tts?${params.toString()}`,
        port: 443,
        headers: {
          accept: 'audio/mpeg,*/*',
          'user-agent': 'Mozilla/5.0 (compatible; LegalChatTTS/1.0)',
        },
      },
      (upstreamRes) => {
        const chunks = [];
        upstreamRes.on('data', (chunk) => chunks.push(chunk));
        upstreamRes.on('end', () => {
          resolve({
            body: Buffer.concat(chunks),
            statusCode: upstreamRes.statusCode || 500,
          });
        });
      },
    );

    upstreamReq.on('error', reject);
    upstreamReq.end();
  });

const requestGoogleTtsAudio = async ({ locale, text }) => {
  const chunks = splitTextForGoogleTts(text, GOOGLE_TTS_MAX_CHARS);
  if (chunks.length === 0) return null;

  const audioBuffers = [];
  for (const chunk of chunks) {
    const response = await requestGoogleTtsChunk({ locale, text: chunk });
    if (!responseStatusIsSuccess(response.statusCode) || response.body.length === 0) {
      return null;
    }
    audioBuffers.push(response.body);
  }

  return Buffer.concat(audioBuffers);
};

const responseStatusIsSuccess = (statusCode) => statusCode >= 200 && statusCode < 300;
const isOpenAITtsPath = (pathname) =>
  /(^|\/)webapi\/tts\/openai\/?$/.test(pathname || '');

const sendUpstreamResponse = ({ req, res, upstream }) => {
  const responseHeaders = { ...upstream.headers };
  if (responseHeaders.location) {
    responseHeaders.location = rewriteLocationHeader(responseHeaders.location, req);
  }
  res.writeHead(upstream.statusCode, responseHeaders);
  res.end(upstream.body);
};

const buildHelperHtml = () => {
  const callbackUrl = APP_PUBLIC_URL.endsWith('/') ? APP_PUBLIC_URL : `${APP_PUBLIC_URL}/`;
  const loginHref = `/api/auth/signin/logto?callbackUrl=${encodeURIComponent(callbackUrl)}`;

  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>LegalChat Login</title>
  <style>
    body { margin: 0; font-family: Arial, sans-serif; background: #0f172a; color: #e2e8f0; }
    .wrap { min-height: 100vh; display: grid; place-items: center; padding: 24px; }
    .card { width: min(560px, 100%); background: #1e293b; border: 1px solid #334155; border-radius: 16px; padding: 24px; text-align: center; }
    .avatar { width: 120px; height: 120px; border-radius: 50%; border: 3px solid #3b82f6; margin-bottom: 20px; }
    h1 { margin: 0 0 12px; font-size: 28px; background: linear-gradient(135deg, #3b82f6, #6366f1); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    p { margin: 0 0 20px; color: #94a3b8; }
    a.button { display: inline-block; background: linear-gradient(135deg, #3b82f6, #6366f1); color: #fff; text-decoration: none; padding: 14px 28px; border-radius: 12px; font-weight: 600; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <img src="/custom-assets/george-avatar.jpg" alt="George" class="avatar">
      <h1>LegalChat ⚖️</h1>
      <p>Ihr persönlicher KI-Jurist</p>
      <a class="button" href="${loginHref}">Mit Logto anmelden</a>
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

const sendNoopServiceWorker = (res) => {
  const body = Buffer.from(NOOP_SERVICE_WORKER, 'utf8');
  res.writeHead(200, {
    'cache-control': BRANDING_CACHE_CONTROL,
    'content-length': body.length,
    'content-type': 'application/javascript; charset=utf-8',
    expires: '0',
    pragma: 'no-cache',
  });
  res.end(body);
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

const handleOpenAITtsWithEdgeFallback = async (req, res) => {
  try {
    console.log(`[LegalChat] TTS intercept: ${req.method} ${req.url}`);

    const forwardingHost = getPublicHost(req);
    const forwardingProto = getForwardedProtocol(req);
    const requestBody = await readRequestBody(req);
    const originalPayload = parseTtsPayload(requestBody);

    const openaiHeaders = buildUpstreamHeaders({
      req,
      bodyBuffer: requestBody,
      forwardingHost,
      forwardingProto,
    });

    const openaiResponse = await requestTarget({
      body: requestBody,
      headers: openaiHeaders,
      method: 'POST',
      path: req.url,
    });
    console.log(`[LegalChat] TTS primary status: ${openaiResponse.statusCode}`);

    if (responseStatusIsSuccess(openaiResponse.statusCode)) {
      sendUpstreamResponse({ req, res, upstream: openaiResponse });
      return;
    }

    if (EDGE_TTS_FALLBACK_ENABLED) {
      const edgePayload = createEdgeTtsPayload(requestBody);
      const edgePath = req.url.replace(OPENAI_TTS_PATH, EDGE_TTS_PATH);
      const edgeHeaders = buildUpstreamHeaders({
        req,
        bodyBuffer: edgePayload,
        forwardingHost,
        forwardingProto,
      });

      const edgeResponse = await requestTarget({
        body: edgePayload,
        headers: edgeHeaders,
        method: 'POST',
        path: edgePath,
      });
      console.log(`[LegalChat] TTS fallback status (edge): ${edgeResponse.statusCode}`);

      if (responseStatusIsSuccess(edgeResponse.statusCode)) {
        const edgeHeadersWithMarker = {
          ...edgeResponse.headers,
          'x-legalchat-tts-fallback': 'edge',
        };

        res.writeHead(edgeResponse.statusCode, edgeHeadersWithMarker);
        res.end(edgeResponse.body);
        console.log('[LegalChat] TTS fallback active: openai -> edge');
        return;
      }
    }

    if (GOOGLE_TTS_FALLBACK_ENABLED && originalPayload && typeof originalPayload.input === 'string') {
      const locale =
        originalPayload.options && typeof originalPayload.options === 'object'
          ? originalPayload.options.locale
          : undefined;

      const googleAudio = await requestGoogleTtsAudio({
        locale,
        text: originalPayload.input,
      });

      if (googleAudio && googleAudio.length > 0) {
        res.writeHead(200, {
          'cache-control': 'no-store',
          'content-length': googleAudio.length,
          'content-type': 'audio/mpeg',
          'x-legalchat-tts-fallback': 'google',
        });
        res.end(googleAudio);
        console.log('[LegalChat] TTS fallback active: openai -> google');
        return;
      }
    }

    sendUpstreamResponse({ req, res, upstream: openaiResponse });
  } catch (error) {
    console.error('TTS fallback proxy failed:', error);
    res.writeHead(502, { 'content-type': 'text/plain; charset=utf-8' });
    res.end('TTS proxy error');
  }
};

// Inject branding into HTML responses
const injectBrandingIntoHTML = (body) => {
  const html = body.toString('utf8');
  if (html.includes('data-legalchat-branding="1"')) return html;

  // Find </head> to inject before
  const headEnd = html.indexOf('</head>');
  if (headEnd !== -1) {
    return html.slice(0, headEnd) + BRANDING_INJECTION + html.slice(headEnd);
  }
  // Fallback: prepend to body
  const bodyStart = html.indexOf('<body');
  if (bodyStart !== -1) {
    const bodyTagEnd = html.indexOf('>', bodyStart);
    if (bodyTagEnd !== -1) {
      return html.slice(0, bodyTagEnd + 1) + BRANDING_INJECTION + html.slice(bodyTagEnd + 1);
    }
  }
  return html;
};

const proxyRequest = async (req, res) => {
  // Only rewrite first-party HTML pages.
  const parsedUrl = new URL(req.url, `${getForwardedProtocol(req)}://${getPublicHost(req)}`);
  const pathname = parsedUrl.pathname;
  const isPageRequest =
    (req.method === 'GET' || req.method === 'HEAD') &&
    (pathname === '/' || pathname.startsWith('/chat') || pathname.startsWith('/welcome'));
  const isBrandingAssetRequest =
    (req.method === 'GET' || req.method === 'HEAD') &&
    (pathname === '/custom.css' || pathname === '/legalchat-branding.js');

  const forwardingHost = getPublicHost(req);
  const forwardingProto = getForwardedProtocol(req);
  const headers = {
    ...req.headers,
    host: req.headers.host || forwardingHost,
    // Rewritten HTML must be uncompressed to avoid content decoding mismatches.
    ...(isPageRequest ? { 'accept-encoding': 'identity' } : {}),
    'x-forwarded-host': forwardingHost,
    'x-forwarded-proto': forwardingProto,
  };

  try {
    const proxyRes = await new Promise((resolve, reject) => {
      const proxyReq = http.request(
        {
          hostname: TARGET_HOST,
          port: TARGET_PORT,
          path: req.url,
          method: req.method,
          headers,
        },
        (response) => {
          const chunks = [];
          response.on('data', (chunk) => chunks.push(chunk));
          response.on('end', () => {
            resolve({
              body: Buffer.concat(chunks),
              headers: response.headers,
              statusCode: response.statusCode || 500,
            });
          });
        },
      );
      proxyReq.on('error', reject);
      req.pipe(proxyReq);
    });

    const responseHeaders = { ...proxyRes.headers };
    if (responseHeaders.location) {
      responseHeaders.location = rewriteLocationHeader(responseHeaders.location, req);
    }
    if (isPageRequest || isBrandingAssetRequest) {
      setNoStoreHeaders(responseHeaders);
    }

    // Inject branding for HTML responses
    let body = proxyRes.body;
    const contentType = proxyRes.headers['content-type'] || '';
    if (req.method === 'GET' && isPageRequest && contentType.includes('text/html')) {
      const modifiedHTML = injectBrandingIntoHTML(body);
      body = Buffer.from(modifiedHTML, 'utf8');
      delete responseHeaders['content-encoding'];
      delete responseHeaders['transfer-encoding'];
      responseHeaders['content-length'] = body.length;
      console.log('[LegalChat] Branding injected');
    }

    res.writeHead(proxyRes.statusCode || 500, responseHeaders);
    res.end(body);
  } catch (error) {
    console.error('Proxy error:', error);
    res.writeHead(502, { 'content-type': 'text/plain; charset=utf-8' });
    res.end('Bad Gateway');
  }
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

  if (
    DISABLE_SERVICE_WORKER &&
    (req.method === 'GET' || req.method === 'HEAD') &&
    parsedUrl.pathname === '/sw.js'
  ) {
    sendNoopServiceWorker(res);
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

  if (req.method === 'POST' && isOpenAITtsPath(parsedUrl.pathname)) {
    await handleOpenAITtsWithEdgeFallback(req, res);
    return;
  }

  proxyRequest(req, res);
});

server.listen(LISTEN_PORT, () => {
  console.log(`LegalChat Auth Gateway running on port ${LISTEN_PORT}`);
  console.log(`George is ready! ⚖️`);
});
