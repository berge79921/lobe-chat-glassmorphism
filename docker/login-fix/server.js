/**
 * Auth gateway for LegalChat.
 * Fixes Auth.js v5 provider sign-in by translating browser GET to
 * server-side CSRF + POST for /api/auth/signin/:provider.
 * 
 * Modified for LegalChat: Injects custom branding CSS/JS into HTML responses.
 */

const http = require('http');
const https = require('https');
const crypto = require('crypto');

const isEnvTruthy = (value) => /^(1|true|yes|on)$/i.test(String(value || '').trim());
const parseCsvLowerSet = (value) =>
  new Set(
    String(value || '')
      .split(',')
      .map((item) => item.trim().toLowerCase())
      .filter(Boolean),
  );

const TARGET_HOST = process.env.LOBECHAT_HOST || 'lobe-chat-glass';
const TARGET_PORT = Number(process.env.LOBECHAT_PORT || 3210);
const LISTEN_PORT = Number(process.env.PORT || 3210);
const APP_PUBLIC_URL = process.env.APP_PUBLIC_URL || 'http://localhost:3210';
const LEGALCHAT_APP_NAME = process.env.LEGALCHAT_APP_NAME || 'LegalChat';
const LEGALCHAT_DEFAULT_AGENT_NAME = process.env.LEGALCHAT_DEFAULT_AGENT_NAME || 'George';
const LEGALCHAT_AVATAR_URL = process.env.LEGALCHAT_AVATAR_URL || '/custom-assets/legalchat-avatar.jpg';
const LEGALCHAT_FAVICON_URL = process.env.LEGALCHAT_FAVICON_URL || LEGALCHAT_AVATAR_URL;
const LEGALCHAT_TAB_TITLE =
  process.env.LEGALCHAT_TAB_TITLE || `${LEGALCHAT_DEFAULT_AGENT_NAME} · ${LEGALCHAT_APP_NAME}`;
const LEGALCHAT_ASSISTANT_ROLE_DE =
  process.env.LEGALCHAT_ASSISTANT_ROLE_DE || 'persönlicher KI-Jurist';
const LEGALCHAT_ASSISTANT_ROLE_EN =
  process.env.LEGALCHAT_ASSISTANT_ROLE_EN || 'personal AI legal assistant';
const LEGALCHAT_STT_MAX_RECORDING_MS = Number(process.env.LEGALCHAT_STT_MAX_RECORDING_MS || 90000);
const LEGALCHAT_STT_SILENCE_STOP_MS = Number(process.env.LEGALCHAT_STT_SILENCE_STOP_MS || 3000);
const LEGALCHAT_VOICE_MODE = String(process.env.LEGALCHAT_VOICE_MODE || 'guarded')
  .trim()
  .toLowerCase();
const LEGALCHAT_VOICE_OFF =
  LEGALCHAT_VOICE_MODE === 'off' ||
  LEGALCHAT_VOICE_MODE === 'disabled' ||
  LEGALCHAT_VOICE_MODE === 'none' ||
  LEGALCHAT_VOICE_MODE === '0' ||
  process.env.LEGALCHAT_VOICE_OFF === '1';
const LEGALCHAT_WELCOME_PRIMARY_DE =
  process.env.LEGALCHAT_WELCOME_PRIMARY_DE ||
  `Ich bin ${LEGALCHAT_DEFAULT_AGENT_NAME}, Ihr ${LEGALCHAT_ASSISTANT_ROLE_DE} bei ${LEGALCHAT_APP_NAME}. Wie kann ich Ihnen jetzt helfen?`;
const LEGALCHAT_WELCOME_PRIMARY_EN =
  process.env.LEGALCHAT_WELCOME_PRIMARY_EN ||
  `I am your ${LEGALCHAT_ASSISTANT_ROLE_EN} ${LEGALCHAT_APP_NAME}. How can I assist you today?`;
const LEGALCHAT_WELCOME_SECONDARY_DE =
  process.env.LEGALCHAT_WELCOME_SECONDARY_DE ||
  'Wenn Sie einen professionelleren oder maßgeschneiderten Assistenten benötigen, klicken Sie auf +, um einen benutzerdefinierten Assistenten zu erstellen.';
const LEGALCHAT_WELCOME_SECONDARY_EN =
  process.env.LEGALCHAT_WELCOME_SECONDARY_EN ||
  'If you need a more professional or customized assistant, you can click + to create a custom assistant.';
const LEGALCHAT_OCR_ENABLED = process.env.LEGALCHAT_OCR_ENABLED !== '0';
const LEGALCHAT_OCR_MODEL =
  process.env.LEGALCHAT_OCR_MODEL || 'google/gemini-2.5-flash-lite';
const LEGALCHAT_OCR_MAX_IMAGES = Math.max(
  1,
  Number(process.env.LEGALCHAT_OCR_MAX_IMAGES || 6),
);
const LEGALCHAT_OCR_MAX_IMAGE_BYTES = Math.max(
  256 * 1024,
  Number(process.env.LEGALCHAT_OCR_MAX_IMAGE_BYTES || 12 * 1024 * 1024),
);
const LEGALCHAT_OCR_MAX_TEXT_CHARS = Math.max(
  500,
  Number(process.env.LEGALCHAT_OCR_MAX_TEXT_CHARS || 12000),
);
const LEGALCHAT_OCR_TIMEOUT_MS = Math.max(
  2000,
  Number(process.env.LEGALCHAT_OCR_TIMEOUT_MS || 45000),
);
const OPENROUTER_API_KEY = process.env.OPENROUTER_API_KEY || '';
const OPENROUTER_PROXY_URL = (process.env.OPENROUTER_PROXY_URL || 'https://openrouter.ai/api/v1')
  .trim()
  .replace(/\/+$/, '');
const OPENROUTER_CHAT_COMPLETIONS_URL = `${OPENROUTER_PROXY_URL}/chat/completions`;
const LEGALCHAT_OCR_MARKER = 'LEGALCHAT_AUTO_OCR_V1';
const LEGALCHAT_OCR_PROMPT =
  process.env.LEGALCHAT_OCR_PROMPT ||
  'You are an OCR engine. Extract all readable text from this JPEG image in the original language. Return only extracted text. If unreadable, return NO_TEXT.';
const LEGALCHAT_OCR_FILE_CACHE_TTL_MS = Math.max(
  60_000,
  Number(process.env.LEGALCHAT_OCR_FILE_CACHE_TTL_MS || 2 * 60 * 60 * 1000),
);
const LEGALCHAT_OCR_S3_PRESIGN_EXPIRES_SEC = Math.max(
  30,
  Number(process.env.LEGALCHAT_OCR_S3_PRESIGN_EXPIRES_SEC || 300),
);
const S3_ENDPOINT_RAW = (process.env.S3_ENDPOINT || '').trim();
const S3_PUBLIC_DOMAIN_RAW = (process.env.S3_PUBLIC_DOMAIN || '').trim();
const S3_BUCKET = (process.env.S3_BUCKET || '').trim();
const S3_REGION = (process.env.S3_REGION || 'us-east-1').trim();
const S3_ACCESS_KEY_ID = (process.env.S3_ACCESS_KEY_ID || '').trim();
const S3_SECRET_ACCESS_KEY = process.env.S3_SECRET_ACCESS_KEY || '';
const S3_ENABLE_PATH_STYLE = process.env.S3_ENABLE_PATH_STYLE !== '0';
const LEGALCHAT_MCP_INTERNAL_ENABLED = isEnvTruthy(
  process.env.LEGALCHAT_MCP_INTERNAL_ENABLED || '0',
);
const LEGALCHAT_MCP_DEEP_RESEARCH_ENDPOINT = String(
  process.env.LEGALCHAT_MCP_DEEP_RESEARCH_ENDPOINT || '',
)
  .trim()
  .replace(/\/+$/, '');
const LEGALCHAT_MCP_PRUEFUNGSMODUS_ENDPOINT = String(
  process.env.LEGALCHAT_MCP_PRUEFUNGSMODUS_ENDPOINT || '',
)
  .trim()
  .replace(/\/+$/, '');
const LEGALCHAT_MCP_BEARER_TOKEN = String(process.env.LEGALCHAT_MCP_BEARER_TOKEN || '').trim();
const LEGALCHAT_MCP_ADMIN_BEARER_TOKEN = String(
  process.env.LEGALCHAT_MCP_ADMIN_BEARER_TOKEN || '',
).trim();
const LEGALCHAT_MCP_REQUEST_TIMEOUT_MS = Math.max(
  2000,
  Number(
    process.env.LEGALCHAT_MCP_REQUEST_TIMEOUT_MS ||
      Number(process.env.MCP_BRIDGE_REQUEST_TIMEOUT_SEC || 1200) * 1000,
  ),
);
const LEGALCHAT_MCP_STATUS_TIMEOUT_MS = Math.max(
  750,
  Number(process.env.LEGALCHAT_MCP_STATUS_TIMEOUT_MS || 3000),
);
const LEGALCHAT_MCP_API_BASE_PATH = '/api/legalchat/mcp';
const LEGALCHAT_MCP_TOOLS_ROUTE = `${LEGALCHAT_MCP_API_BASE_PATH}/tools`;
const LEGALCHAT_MCP_CALL_ROUTE = `${LEGALCHAT_MCP_API_BASE_PATH}/call`;
const LEGALCHAT_MCP_STATUS_ROUTE = `${LEGALCHAT_MCP_API_BASE_PATH}/status`;
const LEGALCHAT_MCP_DEEP_RESEARCH_ROUTE = `${LEGALCHAT_MCP_API_BASE_PATH}/deep-research`;
const LEGALCHAT_MCP_PRUEFUNGSMODUS_ROUTE = `${LEGALCHAT_MCP_API_BASE_PATH}/pruefungsmodus`;
const LEGALCHAT_MCP_MODE_TOOL_ROUTE_PATTERN =
  /^\/api\/legalchat\/mcp\/(deep-research|pruefungsmodus)\/([^/]+)$/;
const LEGALCHAT_MCP_MODE_ENDPOINTS = {
  'deep-research': LEGALCHAT_MCP_DEEP_RESEARCH_ENDPOINT,
  pruefungsmodus: LEGALCHAT_MCP_PRUEFUNGSMODUS_ENDPOINT,
};
const LEGALCHAT_MCP_ADMIN_EMAILS = parseCsvLowerSet(process.env.LEGALCHAT_MCP_ADMIN_EMAILS || '');
const LEGALCHAT_MCP_ADMIN_ROLES = parseCsvLowerSet(
  process.env.LEGALCHAT_MCP_ADMIN_ROLES || 'admin,owner,superadmin',
);
const LEGALCHAT_MCP_PRIVILEGED_TOOLS_BY_MODE = {
  'deep-research': parseCsvLowerSet(
    process.env.LEGALCHAT_MCP_PRIVILEGED_TOOLS_DEEP_RESEARCH || 'ask_gemini_zivilrecht',
  ),
  pruefungsmodus: parseCsvLowerSet(
    process.env.LEGALCHAT_MCP_PRIVILEGED_TOOLS_PRUEFUNGSMODUS ||
      'run_exam,run_cct,get_validation_dashboard',
  ),
};

const SIGNIN_GET_PATTERN = /^\/(?:api\/auth|next-auth)\/signin\/[^/]+$/;
const INTERNAL_HOSTS = new Set([TARGET_HOST, 'lobe-chat-glass', 'lobe']);
const FILE_CREATE_PATH_PATTERN =
  /(?:^|\/)trpc\/(?:lambda|edge|async|mobile)\/.*(?:^|,)file\.createFile(?:,|$)/;
const OPENAI_TTS_PATH = '/webapi/tts/openai';
const EDGE_TTS_PATH = '/webapi/tts/edge';
const EDGE_TTS_FALLBACK_ENABLED = process.env.TTS_EDGE_FALLBACK === '1';
const GOOGLE_TTS_FALLBACK_ENABLED = process.env.TTS_GOOGLE_FALLBACK !== '0';
const GOOGLE_TTS_HOST = process.env.TTS_GOOGLE_HOST || 'translate.google.com';
const GOOGLE_TTS_CLIENT = process.env.TTS_GOOGLE_CLIENT || 'tw-ob';
const GOOGLE_TTS_MAX_CHARS = Number(process.env.TTS_GOOGLE_MAX_CHARS || 180);
const BRANDING_VERSION = process.env.LEGALCHAT_BRANDING_VERSION || '2026-02-12-05';
const withVersionQuery = (url) => {
  const value = String(url || '').trim();
  if (!value) return value;
  if (!BRANDING_VERSION || /[?&]v=/.test(value)) return value;
  return `${value}${value.includes('?') ? '&' : '?'}v=${encodeURIComponent(BRANDING_VERSION)}`;
};
const LEGALCHAT_AVATAR_VERSIONED_URL = withVersionQuery(LEGALCHAT_AVATAR_URL);
const LEGALCHAT_FAVICON_VERSIONED_URL = withVersionQuery(LEGALCHAT_FAVICON_URL);
const DISABLE_SERVICE_WORKER = process.env.LEGALCHAT_DISABLE_SERVICE_WORKER !== '0';
const BRANDING_CACHE_CONTROL = 'no-store, no-cache, must-revalidate, proxy-revalidate';
const HTML_BRAND_PATTERN = /Lobe\s*Hub|Lobe\s*Chat|LobeHub|LobeChat/gi;
const AUTH_LOGTO_ID = (process.env.AUTH_LOGTO_ID || '').trim();
const LOGTO_END_SESSION_ENDPOINT = (
  process.env.LOGTO_END_SESSION_ENDPOINT || 'https://auth.legalchat.net/oidc/session/end'
).trim();
const LOGTO_POST_LOGOUT_REDIRECT_URL = (
  process.env.LOGTO_POST_LOGOUT_REDIRECT_URL || APP_PUBLIC_URL
).trim();
const LEGALCHAT_LOGOUT_MODE = (process.env.LEGALCHAT_LOGOUT_MODE || 'local')
  .trim()
  .toLowerCase();
const LEGALCHAT_LOCAL_LOGOUT_REDIRECT_URL = (
  process.env.LEGALCHAT_LOCAL_LOGOUT_REDIRECT_URL || '/login?logged_out=1'
).trim();
const LEGALCHAT_FORCE_LOGIN_PROMPT = process.env.LEGALCHAT_FORCE_LOGIN_PROMPT !== '0';
const LOGTO_UPSTREAM_HOST = (process.env.LOGTO_UPSTREAM_HOST || 'logto').trim();
const LOGTO_UPSTREAM_PORT = Number(process.env.LOGTO_UPSTREAM_PORT || 3001);
const LEGALCHAT_LOGTO_BRANDING_ENABLED = process.env.LEGALCHAT_LOGTO_BRANDING !== '0';
const LEGALCHAT_LOGTO_BRANDING_HOSTS = new Set(
  String(process.env.LEGALCHAT_LOGTO_BRANDING_HOSTS || 'auth.legalchat.net')
    .split(',')
    .map((item) => item.trim().toLowerCase())
    .filter(Boolean),
);
const LEGALCHAT_PUBLIC_ASSET_BASE = String(process.env.LEGALCHAT_PUBLIC_ASSET_BASE || APP_PUBLIC_URL)
  .trim()
  .replace(/\/+$/, '');
const LEGALCHAT_LOGTO_LOGO_URL = (
  process.env.LEGALCHAT_LOGTO_LOGO_URL ||
  `${LEGALCHAT_PUBLIC_ASSET_BASE}${
    LEGALCHAT_AVATAR_URL.startsWith('/') ? LEGALCHAT_AVATAR_URL : `/${LEGALCHAT_AVATAR_URL}`
  }`
).trim();
const LEGALCHAT_LOGTO_LOGO_VERSIONED_URL = withVersionQuery(LEGALCHAT_LOGTO_LOGO_URL);
INTERNAL_HOSTS.add(LOGTO_UPSTREAM_HOST);
INTERNAL_HOSTS.add('logto');
const SIGNOUT_PATH_PATTERN = /^\/(?:api\/auth|next-auth)\/signout\/?$/;
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
const LEGALCHAT_LOGTO_CUSTOM_CSS = `
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;700;800&family=Sora:wght@600;700&display=swap');

:root {
  --lc-bg-1: #07133a;
  --lc-bg-2: #0f2360;
  --lc-shell-border: rgba(140, 179, 255, 0.44);
  --lc-shell-top: rgba(22, 43, 104, 0.95);
  --lc-shell-bottom: rgba(10, 21, 54, 0.92);
  --lc-text: #edf4ff;
  --lc-muted: #afc4ee;
  --lc-input: rgba(10, 24, 61, 0.86);
  --lc-input-border: rgba(144, 178, 255, 0.5);
  --lc-primary: #4ea1ff;
  --lc-primary-2: #7f7bff;
}

html,
body {
  min-height: 100%;
  margin: 0;
  font-family: "Manrope", "Segoe UI", "Helvetica Neue", sans-serif !important;
  background: radial-gradient(120% 90% at 50% 0%, #17347f 0%, var(--lc-bg-2) 44%, var(--lc-bg-1) 100%) !important;
}

body {
  position: relative;
}

body::before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  background:
    radial-gradient(42rem 42rem at 12% 18%, rgba(70, 110, 255, 0.22), transparent 65%),
    radial-gradient(30rem 30rem at 85% 8%, rgba(123, 102, 255, 0.2), transparent 72%),
    radial-gradient(28rem 28rem at 84% 84%, rgba(44, 181, 255, 0.14), transparent 70%),
    linear-gradient(rgba(187, 206, 255, 0.06) 1px, transparent 1px),
    linear-gradient(90deg, rgba(187, 206, 255, 0.06) 1px, transparent 1px);
  background-size: auto, auto, auto, 48px 48px, 48px 48px;
  z-index: 0;
}

body.desktop {
  background: transparent !important;
}

#app {
  position: relative;
  min-height: 100vh;
  z-index: 1;
}

/* Root React mount from Logto: keep it full-size, never treat it as the visual card */
#app > * {
  width: 100% !important;
  max-width: none !important;
  min-height: 100vh !important;
  border: 0 !important;
  border-radius: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
  backdrop-filter: none !important;
}

/* Logto page container */
#app > * > * {
  min-height: 100vh !important;
  padding: clamp(16px, 2.2vw, 28px) !important;
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  justify-content: center !important;
}

/* Main auth card */
#app > * > * > *:first-child {
  width: min(760px, 100%) !important;
  min-height: min(86vh, 760px) !important;
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 0 !important;
  border-radius: 30px !important;
  border: 1px solid var(--lc-shell-border) !important;
  background:
    linear-gradient(180deg, var(--lc-shell-top), var(--lc-shell-bottom)) !important;
  box-shadow:
    0 36px 96px rgba(3, 9, 28, 0.72),
    inset 0 1px 0 rgba(255, 255, 255, 0.24) !important;
  padding: clamp(28px, 4.4vw, 52px) !important;
}

/* Hide provider signature strip only (do not hide auth actions like Sign-up) */
#app a[class*="signature"],
#app [class*="signature"],
#app [class*="poweredBy"] {
  display: none !important;
}

#app [class*="logoWrapper"] {
  margin-bottom: clamp(14px, 2.4vw, 22px) !important;
}

#app [class*="logo"] img,
#app img[src*="/custom-assets/" i],
#app img[src*="logo"],
#app img[alt*="logo" i] {
  width: clamp(136px, 14vw, 172px) !important;
  height: clamp(136px, 14vw, 172px) !important;
  object-fit: cover !important;
  border-radius: 999px !important;
  border: 3px solid rgba(132, 175, 255, 0.9) !important;
  box-shadow: 0 14px 38px rgba(73, 136, 255, 0.42) !important;
}

#app h1,
#app h2,
#app [class*="title"] {
  font-family: "Sora", "Manrope", sans-serif !important;
  color: var(--lc-text) !important;
  letter-spacing: -0.02em !important;
  text-align: center !important;
}

body.desktop #app h1,
body.desktop #app h2,
body.desktop #app [class*="title"] {
  font-size: clamp(40px, 3.8vw, 52px) !important;
  line-height: 1.08 !important;
}

#app p,
#app [class*="description"],
#app [class*="subtitle"] {
  color: var(--lc-muted) !important;
  text-align: center !important;
}

body.desktop #app p,
body.desktop #app [class*="description"],
body.desktop #app [class*="subtitle"] {
  font-size: clamp(18px, 1.6vw, 24px) !important;
  line-height: 1.45 !important;
}

#app form,
#app [class*="_form"] {
  width: min(560px, 100%) !important;
  margin-left: auto !important;
  margin-right: auto !important;
}

#app [class*="_form"] > *,
#app form > * {
  width: 100% !important;
}

#app label {
  color: #c2d4fa !important;
  font-weight: 600 !important;
}

#app input,
#app textarea {
  min-height: 58px !important;
  border-radius: 14px !important;
  border: 1px solid var(--lc-input-border) !important;
  background: var(--lc-input) !important;
  color: var(--lc-text) !important;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.12) !important;
  font-size: clamp(16px, 1.2vw, 20px) !important;
  font-weight: 600 !important;
  line-height: 1.25 !important;
  padding: 0 18px !important;
}

#app input::placeholder,
#app textarea::placeholder {
  color: #95addd !important;
}

#app button,
#app [role="button"] {
  min-height: 66px !important;
  border-radius: 16px !important;
  border: 1px solid rgba(177, 208, 255, 0.56) !important;
  font-weight: 800 !important;
  font-size: clamp(28px, 2.2vw, 34px) !important;
}

#app button[type="submit"],
#app button[class*="primary"],
#app [data-type="primary"] {
  background: linear-gradient(130deg, var(--lc-primary), var(--lc-primary-2)) !important;
  color: #ffffff !important;
  box-shadow:
    0 16px 32px rgba(49, 93, 245, 0.44),
    inset 0 1px 0 rgba(255, 255, 255, 0.35) !important;
}

#app button[type="submit"]:hover,
#app button[class*="primary"]:hover {
  filter: brightness(1.05);
}

#app a {
  color: #a9c9ff !important;
}

/* Logto 404/unknown-session Back button */
#app [class*="navBar"],
#app [class*="navButton"],
#app [role="button"][class*="nav" i] {
  position: fixed !important;
  top: 22px !important;
  left: 22px !important;
  z-index: 9999 !important;
}

#app [class*="navButton"],
#app [class*="navBar"] [class*="navButton"],
#app [role="button"][class*="nav" i] {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 10px !important;
  padding: 14px 18px !important;
  border-radius: 16px !important;
  min-height: 56px !important;
  font-size: 22px !important;
  font-weight: 800 !important;
  letter-spacing: -0.01em !important;
  color: var(--lc-text) !important;
  border: 1px solid rgba(177, 208, 255, 0.44) !important;
  background: rgba(10, 24, 61, 0.72) !important;
  box-shadow:
    0 16px 34px rgba(3, 9, 28, 0.55),
    inset 0 1px 0 rgba(255, 255, 255, 0.16) !important;
  backdrop-filter: blur(10px) !important;
}

@media (max-width: 760px) {
  #app > * > * {
    padding: 14px !important;
  }

  #app > * > * > *:first-child {
    width: 100% !important;
    min-height: auto !important;
    border-radius: 22px !important;
    padding: 24px 18px !important;
  }

  #app input,
  #app textarea {
    min-height: 50px !important;
    font-size: 17px !important;
    padding: 0 14px !important;
  }

  #app button,
  #app [role="button"] {
    min-height: 56px !important;
    font-size: 22px !important;
  }
}

@media (prefers-reduced-motion: reduce) {
  #app * {
    transition: none !important;
    animation: none !important;
  }
}
`;

const textEncoder = new TextEncoder();
const BRANDING_RUNTIME_CONFIG = {
  appName: LEGALCHAT_APP_NAME,
  defaultAgentName: LEGALCHAT_DEFAULT_AGENT_NAME,
  avatarUrl: LEGALCHAT_AVATAR_VERSIONED_URL,
  faviconUrl: LEGALCHAT_FAVICON_VERSIONED_URL,
  tabTitle: LEGALCHAT_TAB_TITLE,
  assistantRoleDe: LEGALCHAT_ASSISTANT_ROLE_DE,
  assistantRoleEn: LEGALCHAT_ASSISTANT_ROLE_EN,
  sttMaxRecordingMs: LEGALCHAT_STT_MAX_RECORDING_MS,
  sttSilenceStopMs: LEGALCHAT_STT_SILENCE_STOP_MS,
  brandingVersion: BRANDING_VERSION,
  voiceMode: LEGALCHAT_VOICE_OFF ? 'off' : 'guarded',
  voiceOff: LEGALCHAT_VOICE_OFF,
  welcomePrimaryDe: LEGALCHAT_WELCOME_PRIMARY_DE,
  welcomePrimaryEn: LEGALCHAT_WELCOME_PRIMARY_EN,
  welcomeSecondaryDe: LEGALCHAT_WELCOME_SECONDARY_DE,
  welcomeSecondaryEn: LEGALCHAT_WELCOME_SECONDARY_EN,
  mcp: {
    enabled: LEGALCHAT_MCP_INTERNAL_ENABLED,
    apiBasePath: LEGALCHAT_MCP_API_BASE_PATH,
    deepResearchPath: LEGALCHAT_MCP_DEEP_RESEARCH_ROUTE,
    pruefungsmodusPath: LEGALCHAT_MCP_PRUEFUNGSMODUS_ROUTE,
    genericCallPath: LEGALCHAT_MCP_CALL_ROUTE,
    toolsPath: LEGALCHAT_MCP_TOOLS_ROUTE,
    statusPath: LEGALCHAT_MCP_STATUS_ROUTE,
  },
};
const serializeInlineConfig = (value) =>
  JSON.stringify(value)
    .replace(/</g, '\\u003c')
    .replace(/>/g, '\\u003e')
    .replace(/&/g, '\\u0026')
    .replace(/\u2028/g, '\\u2028')
    .replace(/\u2029/g, '\\u2029');
const BRANDING_CONFIG_INJECTION = `<script data-legalchat-config="1">window.__LEGALCHAT_BRANDING_CONFIG__=${serializeInlineConfig(
  BRANDING_RUNTIME_CONFIG,
)};</script>`;
const BRANDING_PREPAINT_STYLE = `<style data-legalchat-prepaint="1">html[data-legalchat-branding-pending="1"] body{opacity:0!important;visibility:hidden!important;}html[data-legalchat-branding-ready="1"] body{opacity:1!important;visibility:visible!important;transition:opacity .14s ease-out;}</style>`;
const BRANDING_PREPAINT_BOOTSTRAP = `<script data-legalchat-prepaint="1">(function(){try{var root=document.documentElement;if(!root)return;root.setAttribute('data-legalchat-branding-pending','1');var unlock=function(){root.removeAttribute('data-legalchat-branding-pending');root.setAttribute('data-legalchat-branding-ready','1');};window.__legalchatBrandingUnlock=unlock;setTimeout(unlock,2200);}catch(_error){}})();</script>`;
const FAVICON_INJECTION = `<script data-legalchat-favicon="1">(function(){try{var href=${serializeInlineConfig(
  LEGALCHAT_FAVICON_VERSIONED_URL,
)};var head=document.head||document.getElementsByTagName('head')[0];if(!head||!href)return;var iconLinks=head.querySelectorAll('link[rel*="icon" i]');for(var i=0;i<iconLinks.length;i+=1){iconLinks[i].setAttribute('href',href);}var rels=['icon','shortcut icon','apple-touch-icon'];for(var j=0;j<rels.length;j+=1){var rel=rels[j];if(head.querySelector('link[rel=\"'+rel+'\"]'))continue;var link=document.createElement('link');link.setAttribute('rel',rel);link.setAttribute('href',href);head.appendChild(link);}}catch(_error){}})();</script>`;
const BRANDING_BOOTSTRAP = DISABLE_SERVICE_WORKER
  ? `<script data-legalchat-sw-cleanup="1">(function(){try{if('serviceWorker' in navigator){navigator.serviceWorker.getRegistrations().then(function(regs){for(var i=0;i<regs.length;i+=1){regs[i].unregister().catch(function(){});}});}if('caches' in window&&caches.keys){caches.keys().then(function(keys){for(var i=0;i<keys.length;i+=1){var name=keys[i]||'';if(/serwist|workbox|next-pwa|lobehub|lobechat/i.test(name)){caches.delete(name).catch(function(){});}}});}}catch(error){console.warn('[LegalChat] SW cleanup failed',error);}})();</script>`
  : '';
const BRANDING_INJECTION = [
  '<!-- LegalChat Branding Assets -->',
  BRANDING_PREPAINT_STYLE,
  BRANDING_PREPAINT_BOOTSTRAP,
  BRANDING_BOOTSTRAP,
  BRANDING_CONFIG_INJECTION,
  FAVICON_INJECTION,
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
const OCR_FILE_URL_CACHE = new Map();

const ensureUrlProtocol = (value, defaultProtocol = 'http') => {
  const normalized = String(value || '').trim();
  if (!normalized) return '';
  if (/^[a-zA-Z][a-zA-Z0-9+.-]*:\/\//.test(normalized)) return normalized;
  return `${defaultProtocol}://${normalized}`;
};

const tryParseUrl = (value, defaultProtocol = 'http') => {
  try {
    const normalized = ensureUrlProtocol(value, defaultProtocol);
    if (!normalized) return null;
    return new URL(normalized);
  } catch {
    return null;
  }
};

const S3_ENDPOINT_URL = tryParseUrl(S3_ENDPOINT_RAW);
const S3_PUBLIC_DOMAIN_URL = tryParseUrl(S3_PUBLIC_DOMAIN_RAW);
const S3_SIGNING_READY = Boolean(
  S3_ENDPOINT_URL && S3_BUCKET && S3_ACCESS_KEY_ID && S3_SECRET_ACCESS_KEY,
);

const pruneOcrFileUrlCache = () => {
  const now = Date.now();
  for (const [fileId, entry] of OCR_FILE_URL_CACHE.entries()) {
    if (!entry || now - entry.updatedAt > LEGALCHAT_OCR_FILE_CACHE_TTL_MS) {
      OCR_FILE_URL_CACHE.delete(fileId);
    }
  }
};

const getCachedFileEntry = (fileId) => {
  const entry = OCR_FILE_URL_CACHE.get(fileId);
  if (!entry) return null;
  if (Date.now() - entry.updatedAt > LEGALCHAT_OCR_FILE_CACHE_TTL_MS) {
    OCR_FILE_URL_CACHE.delete(fileId);
    return null;
  }
  return entry;
};

const putCachedFileEntry = (fileId, value) => {
  if (!fileId || typeof fileId !== 'string') return;
  pruneOcrFileUrlCache();
  OCR_FILE_URL_CACHE.set(fileId, {
    ...value,
    updatedAt: Date.now(),
  });
};

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

const buildExpiredCookie = (name) =>
  `${name}=; Path=/; Max-Age=0; Expires=Thu, 01 Jan 1970 00:00:00 GMT; HttpOnly; Secure; SameSite=Lax`;

const buildLogoutCookieHeaders = () => {
  const baseNames = [
    '__Host-authjs.csrf-token',
    '__Secure-authjs.callback-url',
    '__Secure-authjs.pkce.code_verifier',
    '__Secure-authjs.state',
    '__Secure-authjs.nonce',
    'authjs.session-token',
    '__Secure-authjs.session-token',
    'next-auth.session-token',
    '__Secure-next-auth.session-token',
  ];

  const headers = baseNames.map(buildExpiredCookie);
  const chunkedPrefixes = [
    'authjs.session-token.',
    '__Secure-authjs.session-token.',
    'next-auth.session-token.',
    '__Secure-next-auth.session-token.',
  ];

  // Clear likely chunked cookie segments (Auth.js splits long values).
  for (const prefix of chunkedPrefixes) {
    for (let index = 0; index < 12; index += 1) {
      headers.push(buildExpiredCookie(`${prefix}${index}`));
    }
  }

  return headers;
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

const normalizeHost = (value) =>
  String(value || '')
    .trim()
    .toLowerCase()
    .replace(/:\d+$/, '');

const isLogtoBrandingHost = (req) => {
  if (!LEGALCHAT_LOGTO_BRANDING_ENABLED) return false;
  const host = normalizeHost(getPublicHost(req));
  return LEGALCHAT_LOGTO_BRANDING_HOSTS.has(host);
};

const rewriteLocationHeader = (location, req) => {
  if (!location || location.startsWith('/')) return location;

  try {
    const parsed = new URL(location);
    const hostPort = `${parsed.hostname}:${parsed.port || (parsed.protocol === 'https:' ? '443' : '80')}`;
    const targetHostPort = `${TARGET_HOST}:${TARGET_PORT}`;
    const logtoHostPort = `${LOGTO_UPSTREAM_HOST}:${LOGTO_UPSTREAM_PORT}`;

    const isInternalHost =
      INTERNAL_HOSTS.has(parsed.hostname) ||
      hostPort === targetHostPort ||
      hostPort === logtoHostPort;
    if (!isInternalHost) return location;

    parsed.protocol = `${getForwardedProtocol(req)}:`;
    parsed.host = getPublicHost(req);
    return parsed.toString();
  } catch {
    return location;
  }
};

const requestTarget = ({ method, path, headers = {}, body = '', timeoutMs = 0 }) =>
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

    if (timeoutMs > 0) {
      upstreamReq.setTimeout(timeoutMs, () => {
        upstreamReq.destroy(new Error(`upstream_timeout:${timeoutMs}`));
      });
    }

    upstreamReq.on('error', reject);
    if (body) upstreamReq.write(body);
    upstreamReq.end();
  });

const readRequestBody = (req, maxBytes = 5 * 1024 * 1024) =>
  new Promise((resolve, reject) => {
    const chunks = [];
    let currentLength = 0;
    req.on('data', (chunk) => {
      currentLength += chunk.length;
      if (currentLength > maxBytes) {
        req.destroy();
        const error = new Error('Payload Too Large');
        error.code = 'PAYLOAD_TOO_LARGE';
        error.statusCode = 413;
        reject(error);
      } else {
        chunks.push(chunk);
      }
    });
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

const findLogtoSsrJsonRange = (html) => {
  const marker = 'window.logtoSsr = Object.freeze(';
  const markerStart = html.indexOf(marker);
  if (markerStart === -1) return null;

  let i = markerStart + marker.length;
  while (i < html.length && /\s/.test(html[i])) i += 1;
  if (html[i] !== '{') return null;

  const jsonStart = i;
  let depth = 0;
  let inString = false;
  let escaped = false;

  for (; i < html.length; i += 1) {
    const ch = html[i];
    if (inString) {
      if (escaped) {
        escaped = false;
        continue;
      }
      if (ch === '\\') {
        escaped = true;
        continue;
      }
      if (ch === '"') {
        inString = false;
        continue;
      }
      continue;
    }

    if (ch === '"') {
      inString = true;
      continue;
    }
    if (ch === '{') {
      depth += 1;
      continue;
    }
    if (ch === '}') {
      depth -= 1;
      if (depth === 0) {
        return { jsonStart, jsonEnd: i + 1 };
      }
    }
  }

  return null;
};

const injectLogtoBrandingExperience = (html, pathname = '') => {
  const range = findLogtoSsrJsonRange(html);
  if (!range) return html;

  let ssrPayload;
  try {
    ssrPayload = JSON.parse(html.slice(range.jsonStart, range.jsonEnd));
  } catch {
    return html;
  }

  const experience = ssrPayload?.signInExperience?.data;
  if (!experience || typeof experience !== 'object') return html;

  ssrPayload.signInExperience.data = {
    ...experience,
    color: {
      ...(experience.color || {}),
      primaryColor: '#4EA1FF',
      darkPrimaryColor: '#7F7BFF',
      isDarkModeEnabled: true,
    },
    branding: {
      ...(experience.branding || {}),
      logoUrl: LEGALCHAT_LOGTO_LOGO_VERSIONED_URL,
      darkLogoUrl: LEGALCHAT_LOGTO_LOGO_VERSIONED_URL,
    },
    hideLogtoBranding: true,
    customCss: LEGALCHAT_LOGTO_CUSTOM_CSS,
  };

  // Logto returns signInMode=SignIn even for /register; the SPA then pushes to /sign-in.
  // Force the expected mode on the register route so account creation stays on the sign-up UI.
  if (/^\/register(?:\/|$)/i.test(pathname)) {
    ssrPayload.signInExperience.data.signInMode = 'SignUp';
  }

  const serialized = JSON.stringify(ssrPayload)
    .replace(/</g, '\\u003c')
    .replace(/>/g, '\\u003e')
    .replace(/&/g, '\\u0026')
    .replace(/\u2028/g, '\\u2028')
    .replace(/\u2029/g, '\\u2029');

  let rewritten =
    html.slice(0, range.jsonStart) + serialized + html.slice(range.jsonEnd);
  rewritten = rewritten.replace(
    /<title>\s*<\/title>/i,
    `<title>${escapeHtml(LEGALCHAT_APP_NAME)} Anmeldung</title>`,
  );
  return rewritten;
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
const isAnyTtsPath = (pathname) => /(^|\/)webapi\/tts(?:\/|$)/.test(pathname || '');

const sendVoiceDisabledResponse = (res) => {
  const body = JSON.stringify({
    error: 'VOICE_DISABLED',
    message: 'Voice service is disabled by LegalChat policy.',
  });

  res.writeHead(403, {
    'cache-control': 'no-store',
    'content-length': Buffer.byteLength(body),
    'content-type': 'application/json; charset=utf-8',
    'x-legalchat-voice-mode': 'off',
  });
  res.end(body);
};

const sendUpstreamResponse = ({ req, res, upstream }) => {
  const responseHeaders = { ...upstream.headers };
  if (responseHeaders.location) {
    responseHeaders.location = rewriteLocationHeader(responseHeaders.location, req);
  }
  res.writeHead(upstream.statusCode, responseHeaders);
  res.end(upstream.body);
};

const isAiChatSendMessagePath = (pathname) =>
  /(?:^|\/)trpc\/(?:lambda|edge|async|mobile)\/.*aiChat\.sendMessageInServer(?:,|$)/.test(
    pathname || '',
  );

const isFileCreatePath = (pathname) => FILE_CREATE_PATH_PATTERN.test(pathname || '');

const fetchWithTimeout = async (url, options = {}, timeoutMs = LEGALCHAT_OCR_TIMEOUT_MS) => {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timeout);
  }
};

const sendJsonResponse = (res, statusCode, payload, extraHeaders = {}) => {
  const body = Buffer.from(JSON.stringify(payload), 'utf8');
  res.writeHead(statusCode, {
    'cache-control': 'no-store',
    'content-length': String(body.length),
    'content-type': 'application/json; charset=utf-8',
    ...extraHeaders,
  });
  res.end(body);
};

const extractBearerToken = (authorizationHeader) => {
  const value = String(authorizationHeader || '').trim();
  if (!/^Bearer\s+/i.test(value)) return '';
  return value.replace(/^Bearer\s+/i, '').trim();
};

const timingSafeEquals = (left, right) => {
  const leftBuffer = Buffer.from(String(left || ''), 'utf8');
  const rightBuffer = Buffer.from(String(right || ''), 'utf8');
  if (leftBuffer.length === 0 || leftBuffer.length !== rightBuffer.length) return false;
  try {
    return crypto.timingSafeEqual(leftBuffer, rightBuffer);
  } catch {
    return false;
  }
};

const normalizeMcpMode = (value) => {
  const normalized = String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[ _]+/g, '-')
    .replace(/ä/g, 'ae')
    .replace(/ö/g, 'oe')
    .replace(/ü/g, 'ue')
    .replace(/ß/g, 'ss');
  if (!normalized) return '';
  if (normalized === 'deepresearch') return 'deep-research';
  if (normalized === 'deep-research') return 'deep-research';
  if (normalized === 'pruefungs-modus') return 'pruefungsmodus';
  if (normalized === 'pruefungsmodus') return 'pruefungsmodus';
  return '';
};

const getMcpEndpointForMode = (mode) => LEGALCHAT_MCP_MODE_ENDPOINTS[normalizeMcpMode(mode)] || '';

const extractSessionRoles = (user) => {
  const roles = new Set();
  if (!user || typeof user !== 'object') return roles;
  const candidates = [
    user.role,
    user.roles,
    user.permissions,
    user.scope,
    user.scopes,
    user.customData?.role,
    user.customData?.roles,
    user.profile?.role,
    user.profile?.roles,
  ];
  for (const candidate of candidates) {
    if (typeof candidate === 'string') {
      for (const part of candidate.split(/[,\s]+/)) {
        const value = part.trim().toLowerCase();
        if (value) roles.add(value);
      }
      continue;
    }
    if (Array.isArray(candidate)) {
      for (const item of candidate) {
        const value = String(item || '').trim().toLowerCase();
        if (value) roles.add(value);
      }
    }
  }
  return roles;
};

const validateSessionViaAuthJs = async (req) => {
  const cookieHeader = String(req.headers.cookie || '').trim();
  if (!cookieHeader) return null;
  if (!hasSessionCookie(req)) return null;

  try {
    const forwardingHost = getPublicHost(req);
    const forwardingProto = getForwardedProtocol(req);
    const sessionResponse = await requestTarget({
      method: 'GET',
      path: '/api/auth/session',
      headers: {
        accept: 'application/json',
        cookie: cookieHeader,
        host: forwardingHost,
        'user-agent': req.headers['user-agent'] || 'legalchat-mcp-auth-check',
        'x-forwarded-host': forwardingHost,
        'x-forwarded-proto': forwardingProto,
      },
      timeoutMs: 3000,
    });

    if (!responseStatusIsSuccess(sessionResponse.statusCode)) return null;
    const payload = JSON.parse(sessionResponse.body.toString('utf8') || '{}');
    if (!payload || typeof payload !== 'object') return null;
    if (!payload.user || typeof payload.user !== 'object') return null;
    if (typeof payload.expires !== 'string' || !payload.expires) return null;
    const user = payload.user;
    const email = String(user.email || user.primaryEmail || '')
      .trim()
      .toLowerCase();
    return {
      email,
      roles: extractSessionRoles(user),
      user,
    };
  } catch {
    return null;
  }
};

const isPrivilegedMcpTool = (mode, toolName) => {
  const modeKey = normalizeMcpMode(mode);
  const toolKey = String(toolName || '').trim().toLowerCase();
  if (!modeKey || !toolKey) return false;
  return LEGALCHAT_MCP_PRIVILEGED_TOOLS_BY_MODE[modeKey]?.has(toolKey) === true;
};

const isSessionAdmin = (sessionInfo) => {
  if (!sessionInfo || typeof sessionInfo !== 'object') return false;
  if (sessionInfo.email && LEGALCHAT_MCP_ADMIN_EMAILS.has(sessionInfo.email)) return true;
  for (const role of sessionInfo.roles || []) {
    if (LEGALCHAT_MCP_ADMIN_ROLES.has(role)) return true;
  }
  return false;
};

const authorizeMcpToolCall = ({ access, mode, toolName }) => {
  if (!isPrivilegedMcpTool(mode, toolName)) return { ok: true };
  if (access?.authType === 'bearer' && access?.bearerRole === 'admin') return { ok: true };
  if (isSessionAdmin(access?.session)) return { ok: true };
  return {
    error:
      'Forbidden. Missing role or permission for this MCP tool. Ask an administrator for access.',
    ok: false,
    statusCode: 403,
  };
};

const canAccessMcpLane = async (req) => {
  if (!LEGALCHAT_MCP_INTERNAL_ENABLED) {
    return {
      error: 'MCP lane is disabled.',
      ok: false,
      statusCode: 503,
    };
  }

  const requestToken = extractBearerToken(req.headers.authorization);
  if (requestToken) {
    if (
      LEGALCHAT_MCP_ADMIN_BEARER_TOKEN &&
      timingSafeEquals(requestToken, LEGALCHAT_MCP_ADMIN_BEARER_TOKEN)
    ) {
      return { authType: 'bearer', bearerRole: 'admin', ok: true };
    }
    if (LEGALCHAT_MCP_BEARER_TOKEN && timingSafeEquals(requestToken, LEGALCHAT_MCP_BEARER_TOKEN)) {
      return { authType: 'bearer', bearerRole: 'standard', ok: true };
    }
  }

  const sessionInfo = await validateSessionViaAuthJs(req);
  if (sessionInfo) {
    return { authType: 'session', ok: true, session: sessionInfo };
  }

  return {
    error: 'Unauthorized. Sign in or provide a valid bearer token.',
    ok: false,
    statusCode: 401,
  };
};

const readJsonRequestBody = async (req) => {
  const raw = await readRequestBody(req);
  if (!raw || raw.length === 0) return {};
  try {
    return JSON.parse(raw.toString('utf8'));
  } catch {
    const error = new Error('invalid_json');
    error.code = 'INVALID_JSON';
    throw error;
  }
};

const callMcpBridge = async ({
  mode,
  path,
  payload,
  timeoutMs = LEGALCHAT_MCP_REQUEST_TIMEOUT_MS,
}) => {
  const normalizedMode = normalizeMcpMode(mode);
  const endpoint = getMcpEndpointForMode(normalizedMode);
  if (!endpoint) {
    return {
      ok: false,
      payload: {
        error: `MCP endpoint for mode "${normalizedMode || mode || 'unknown'}" is not configured.`,
        ok: false,
      },
      statusCode: 500,
    };
  }

  const url = `${endpoint}${path}`;
  let response;
  try {
    response = await fetchWithTimeout(
      url,
      {
        body: typeof payload === 'undefined' ? undefined : JSON.stringify(payload),
        headers:
          typeof payload === 'undefined'
            ? { Accept: 'application/json' }
            : {
                Accept: 'application/json',
                'Content-Type': 'application/json',
              },
        method: typeof payload === 'undefined' ? 'GET' : 'POST',
      },
      timeoutMs,
    );
  } catch (error) {
    return {
      ok: false,
      payload: {
        details: error?.message || String(error),
        error: `MCP bridge "${normalizedMode}" is unreachable.`,
        ok: false,
      },
      statusCode: 502,
    };
  }

  const rawText = await response.text().catch(() => '');
  let parsedPayload = null;
  if (rawText) {
    try {
      parsedPayload = JSON.parse(rawText);
    } catch {
      parsedPayload = null;
    }
  }

  if (!response.ok) {
    return {
      ok: false,
      payload: {
        bridgeResponse: parsedPayload || rawText.slice(0, 600),
        bridgeStatus: response.status,
        error: `MCP bridge request failed for mode "${normalizedMode}".`,
        ok: false,
      },
      statusCode: response.status === 404 ? 502 : response.status,
    };
  }

  return {
    ok: true,
    payload: parsedPayload ?? { ok: true, result: rawText },
    statusCode: 200,
  };
};

const normalizeToolCallPayload = ({ body, modeFromPath, toolNameFromPath }) => {
  const bodyObject = body && typeof body === 'object' && !Array.isArray(body) ? body : {};
  const mode = normalizeMcpMode(modeFromPath || bodyObject.mode);
  if (!mode) return { error: 'Missing or invalid mode.' };

  const toolNameRaw = toolNameFromPath || bodyObject.name;
  const toolName = String(toolNameRaw || '').trim();
  if (!toolName) return { error: 'Missing tool name.' };

  if (
    typeof bodyObject.arguments === 'object' &&
    bodyObject.arguments !== null &&
    !Array.isArray(bodyObject.arguments)
  ) {
    return {
      arguments: bodyObject.arguments,
      mode,
      name: toolName,
    };
  }

  const fallbackArgs = { ...bodyObject };
  delete fallbackArgs.mode;
  delete fallbackArgs.name;
  return {
    arguments: fallbackArgs,
    mode,
    name: toolName,
  };
};

const handleMcpStatusRequest = async (req, res) => {
  const access = await canAccessMcpLane(req);
  if (!access.ok) {
    sendJsonResponse(res, access.statusCode, { error: access.error, ok: false });
    return;
  }

  const modes = ['deep-research', 'pruefungsmodus'];
  const modeStatus = await Promise.all(
    modes.map(async (mode) => {
      const endpoint = getMcpEndpointForMode(mode);
      if (!endpoint) {
        return { configured: false, healthy: false, mode };
      }

      const probe = await callMcpBridge({
        mode,
        path: '/health',
        payload: undefined,
        timeoutMs: LEGALCHAT_MCP_STATUS_TIMEOUT_MS,
      });

      if (!probe.ok) {
        return {
          configured: true,
          error: probe.payload?.error || 'Bridge probe failed.',
          healthy: false,
          mode,
        };
      }

      return {
        configured: true,
        healthy: Boolean(probe.payload?.ok),
        mode,
      };
    }),
  );

  sendJsonResponse(res, 200, {
    authType: access.authType || 'unknown',
    bearerRole: access.bearerRole || null,
    enabled: LEGALCHAT_MCP_INTERNAL_ENABLED,
    modes: modeStatus,
    ok: true,
  });
};

const handleMcpToolsListRequest = async (req, res, parsedUrl) => {
  const access = await canAccessMcpLane(req);
  if (!access.ok) {
    sendJsonResponse(res, access.statusCode, { error: access.error, ok: false });
    return;
  }

  const mode = normalizeMcpMode(parsedUrl.searchParams.get('mode'));
  if (!mode) {
    sendJsonResponse(res, 400, {
      error: 'Missing or invalid mode. Use "deep-research" or "pruefungsmodus".',
      ok: false,
    });
    return;
  }

  const bridgeResponse = await callMcpBridge({
    mode,
    path: '/tools',
    payload: undefined,
    timeoutMs: LEGALCHAT_MCP_STATUS_TIMEOUT_MS,
  });
  if (!bridgeResponse.ok) {
    sendJsonResponse(res, bridgeResponse.statusCode, bridgeResponse.payload);
    return;
  }

  sendJsonResponse(res, 200, {
    mode,
    ok: true,
    result: bridgeResponse.payload?.result ?? bridgeResponse.payload,
  });
};

const handleMcpToolCallRequest = async (req, res, { modeFromPath = '', toolNameFromPath = '' } = {}) => {
  const access = await canAccessMcpLane(req);
  if (!access.ok) {
    sendJsonResponse(res, access.statusCode, { error: access.error, ok: false });
    return;
  }

  let body;
  try {
    body = await readJsonRequestBody(req);
  } catch {
    sendJsonResponse(res, 400, { error: 'Invalid JSON body.', ok: false });
    return;
  }

  const parsed = normalizeToolCallPayload({ body, modeFromPath, toolNameFromPath });
  if (parsed.error) {
    sendJsonResponse(res, 400, { error: parsed.error, ok: false });
    return;
  }

  const authorization = authorizeMcpToolCall({
    access,
    mode: parsed.mode,
    toolName: parsed.name,
  });
  if (!authorization.ok) {
    console.warn(
      `[LegalChat MCP] denied tool call mode=${parsed.mode} tool=${parsed.name} auth=${access.authType || 'unknown'}`,
    );
    sendJsonResponse(res, authorization.statusCode, {
      error: authorization.error,
      mode: parsed.mode,
      ok: false,
      tool: parsed.name,
    });
    return;
  }

  const bridgeResponse = await callMcpBridge({
    mode: parsed.mode,
    path: '/tools/call',
    payload: {
      arguments: parsed.arguments,
      name: parsed.name,
    },
  });

  if (!bridgeResponse.ok) {
    sendJsonResponse(res, bridgeResponse.statusCode, {
      ...bridgeResponse.payload,
      mode: parsed.mode,
      tool: parsed.name,
    });
    return;
  }

  sendJsonResponse(res, 200, {
    mode: parsed.mode,
    ok: true,
    result: bridgeResponse.payload?.result ?? bridgeResponse.payload,
    tool: parsed.name,
  });
};

const extractFirstAssistantText = (payload) => {
  const content = payload?.choices?.[0]?.message?.content;
  if (typeof content === 'string') return content;
  if (Array.isArray(content)) {
    return content
      .map((part) => {
        if (typeof part === 'string') return part;
        if (part && typeof part.text === 'string') return part.text;
        return '';
      })
      .join('\n')
      .trim();
  }
  return '';
};

const findSendMessagePayloads = (root) => {
  const matches = [];
  const visited = new Set();

  const walk = (node) => {
    if (!node || typeof node !== 'object') return;
    if (visited.has(node)) return;
    visited.add(node);

    if (
      node.newUserMessage &&
      typeof node.newUserMessage === 'object' &&
      typeof node.newUserMessage.content === 'string' &&
      node.newAssistantMessage &&
      typeof node.newAssistantMessage === 'object'
    ) {
      matches.push(node);
    }

    if (Array.isArray(node)) {
      for (const item of node) walk(item);
      return;
    }

    for (const value of Object.values(node)) walk(value);
  };

  walk(root);
  return matches;
};

const isJpegMimeType = (mimeType) => /image\/(?:jpeg|jpg)/i.test(String(mimeType || ''));
const isLikelyJpegBuffer = (buffer) =>
  Buffer.isBuffer(buffer) &&
  buffer.length > 3 &&
  buffer[0] === 0xff &&
  buffer[1] === 0xd8 &&
  buffer[2] === 0xff;

const encodeRfc3986 = (value) =>
  encodeURIComponent(String(value))
    .replace(/[!'()*]/g, (char) => `%${char.charCodeAt(0).toString(16).toUpperCase()}`);

const encodePathSegments = (path) =>
  String(path)
    .split('/')
    .filter((segment) => segment.length > 0)
    .map((segment) => encodeRfc3986(segment))
    .join('/');

const sha256Hex = (value) =>
  crypto.createHash('sha256').update(value).digest('hex');

const hmacSha256 = (key, value, output = 'buffer') =>
  crypto.createHmac('sha256', key).update(value).digest(output);

const normalizeStorageKey = (rawStorageUrl) => {
  const value = String(rawStorageUrl || '').trim();
  if (!value) return null;
  if (/^https?:\/\//i.test(value)) return { directUrl: value, key: null };

  if (/^s3:\/\//i.test(value)) {
    const parsed = tryParseUrl(value, 's3');
    if (parsed) {
      const host = parsed.hostname || '';
      let key = parsed.pathname.replace(/^\/+/, '');
      if (host && host !== S3_BUCKET) {
        key = `${host}/${key}`.replace(/^\/+/, '');
      }
      return { directUrl: null, key: key || null };
    }
  }

  let key = value.replace(/^\/+/, '');
  if (S3_BUCKET && key.startsWith(`${S3_BUCKET}/`)) {
    key = key.slice(S3_BUCKET.length + 1);
  }

  return { directUrl: null, key: key || null };
};

const isLikelyStorageUrl = (value) => {
  const raw = String(value || '').trim();
  if (!raw) return false;
  if (/^s3:\/\//i.test(raw)) return true;
  if (/^(?:\/)?files\//i.test(raw)) return true;
  if (/^https?:\/\/[^?#]+\/(?:[^?#]+\/)?files\//i.test(raw)) return true;
  return false;
};

const buildS3PresignedGetUrl = (storageKey) => {
  if (!S3_SIGNING_READY || !storageKey) return null;
  const key = String(storageKey).replace(/^\/+/, '');
  if (!key) return null;

  const now = new Date();
  const amzDate = now.toISOString().replace(/[:-]|\.\d{3}/g, '');
  const dateStamp = amzDate.slice(0, 8);
  const credentialScope = `${dateStamp}/${S3_REGION}/s3/aws4_request`;
  const algorithm = 'AWS4-HMAC-SHA256';

  const endpoint = S3_ENDPOINT_URL;
  const endpointPathPrefix = endpoint.pathname.replace(/^\/+|\/+$/g, '');
  const host = S3_ENABLE_PATH_STYLE ? endpoint.host : `${S3_BUCKET}.${endpoint.host}`;
  const uriParts = [endpointPathPrefix];
  if (S3_ENABLE_PATH_STYLE) uriParts.push(S3_BUCKET);
  uriParts.push(key);
  const canonicalUri = `/${encodePathSegments(uriParts.filter(Boolean).join('/'))}`;

  const queryParams = {
    'X-Amz-Algorithm': algorithm,
    'X-Amz-Credential': `${S3_ACCESS_KEY_ID}/${credentialScope}`,
    'X-Amz-Date': amzDate,
    'X-Amz-Expires': String(LEGALCHAT_OCR_S3_PRESIGN_EXPIRES_SEC),
    'X-Amz-SignedHeaders': 'host',
  };

  const canonicalQueryString = Object.entries(queryParams)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([k, v]) => `${encodeRfc3986(k)}=${encodeRfc3986(v)}`)
    .join('&');

  const canonicalRequest = [
    'GET',
    canonicalUri,
    canonicalQueryString,
    `host:${host}`,
    '',
    'host',
    'UNSIGNED-PAYLOAD',
  ].join('\n');

  const stringToSign = [
    algorithm,
    amzDate,
    credentialScope,
    sha256Hex(canonicalRequest),
  ].join('\n');

  const signingKeyDate = hmacSha256(`AWS4${S3_SECRET_ACCESS_KEY}`, dateStamp);
  const signingKeyRegion = hmacSha256(signingKeyDate, S3_REGION);
  const signingKeyService = hmacSha256(signingKeyRegion, 's3');
  const signingKey = hmacSha256(signingKeyService, 'aws4_request');
  const signature = hmacSha256(signingKey, stringToSign, 'hex');

  return `${endpoint.protocol}//${host}${canonicalUri}?${canonicalQueryString}&X-Amz-Signature=${signature}`;
};

const buildS3PublicDomainUrl = (storageKey) => {
  if (!S3_PUBLIC_DOMAIN_URL || !S3_BUCKET || !storageKey) return null;
  const key = String(storageKey).replace(/^\/+/, '');
  if (!key) return null;

  const basePath = S3_PUBLIC_DOMAIN_URL.pathname.replace(/^\/+|\/+$/g, '');
  const encodedPath = encodePathSegments([basePath, S3_BUCKET, key].filter(Boolean).join('/'));
  return `${S3_PUBLIC_DOMAIN_URL.protocol}//${S3_PUBLIC_DOMAIN_URL.host}/${encodedPath}`;
};

const normalizeExtractedText = (text) => {
  const normalized = String(text || '').trim();
  if (!normalized) return '';
  if (normalized.toUpperCase() === 'NO_TEXT') return '';
  return normalized.length > LEGALCHAT_OCR_MAX_TEXT_CHARS
    ? normalized.slice(0, LEGALCHAT_OCR_MAX_TEXT_CHARS)
    : normalized;
};

const extractFileCreateInputs = (root) => {
  const inputs = [];
  const visited = new Set();

  const walk = (node) => {
    if (!node || typeof node !== 'object') return;
    if (visited.has(node)) return;
    visited.add(node);

    if (Array.isArray(node)) {
      for (const item of node) walk(item);
      return;
    }

    if (
      typeof node.url === 'string' &&
      (typeof node.hash === 'string' ||
        typeof node.fileType === 'string' ||
        typeof node.name === 'string' ||
        typeof node.size === 'number')
    ) {
      inputs.push({
        fileType: typeof node.fileType === 'string' ? node.fileType : '',
        storageUrl: node.url,
      });
    }

    for (const value of Object.values(node)) walk(value);
  };

  walk(root);
  return inputs;
};

const extractFileCreateOutputs = (root) => {
  const outputs = [];
  const visited = new Set();

  const walk = (node) => {
    if (!node || typeof node !== 'object') return;
    if (visited.has(node)) return;
    visited.add(node);

    if (Array.isArray(node)) {
      for (const item of node) walk(item);
      return;
    }

    if (typeof node.id === 'string' && (typeof node.url === 'string' || node.id.startsWith('file_'))) {
      outputs.push({
        fileId: node.id,
        url: typeof node.url === 'string' ? node.url : '',
      });
    }

    for (const value of Object.values(node)) walk(value);
  };

  walk(root);
  return outputs;
};

const rememberFileCreateMappings = ({ requestPayload, responsePayload }) => {
  if (!requestPayload || !responsePayload) return 0;

  const inputs = extractFileCreateInputs(requestPayload);
  const outputs = extractFileCreateOutputs(responsePayload);
  if (outputs.length === 0) return 0;

  let stored = 0;
  for (let index = 0; index < outputs.length; index += 1) {
    const output = outputs[index];
    const input = inputs[index] || (inputs.length === 1 ? inputs[0] : null);
    if (!output?.fileId) continue;

    const responseUrl = typeof output.url === 'string' ? output.url : '';
    const storageUrl = typeof input?.storageUrl === 'string' ? input.storageUrl : '';

    putCachedFileEntry(output.fileId, {
      fileType: typeof input?.fileType === 'string' ? input.fileType : '',
      responseUrl,
      storageUrl,
    });
    stored += 1;
  }

  return stored;
};

const toAbsoluteUpstreamUrl = (value) => {
  const input = String(value || '').trim();
  if (!input) return '';
  if (/^https?:\/\//i.test(input)) return input;
  if (input.startsWith('/')) return `http://${TARGET_HOST}:${TARGET_PORT}${input}`;
  return `http://${TARGET_HOST}:${TARGET_PORT}/${input}`;
};

const extractFileItemFromTrpcPayload = (root, fileId) => {
  const visited = new Set();
  let matched = null;

  const walk = (node) => {
    if (matched || !node || typeof node !== 'object') return;
    if (visited.has(node)) return;
    visited.add(node);

    if (
      typeof node.id === 'string' &&
      node.id === fileId &&
      typeof node.url === 'string'
    ) {
      matched = {
        fileType: typeof node.fileType === 'string' ? node.fileType : '',
        id: node.id,
        url: node.url,
      };
      return;
    }

    if (Array.isArray(node)) {
      for (const item of node) walk(item);
      return;
    }

    for (const value of Object.values(node)) walk(value);
  };

  walk(root);
  return matched;
};

const fetchFileItemViaTrpc = async (fileId, requestHeaders = {}) => {
  const cookie = typeof requestHeaders.cookie === 'string' ? requestHeaders.cookie : '';
  const authorization =
    typeof requestHeaders.authorization === 'string' ? requestHeaders.authorization : '';
  if (!cookie && !authorization) return null;

  const input = encodeURIComponent(JSON.stringify({ 0: { id: fileId } }));
  const path = `/trpc/lambda/file.getFileItemById?batch=1&input=${input}`;
  const headers = {
    accept: 'application/json',
  };

  if (cookie) headers.cookie = cookie;
  if (authorization) headers.authorization = authorization;

  const response = await requestTarget({
    headers,
    method: 'GET',
    path,
  });

  if (!responseStatusIsSuccess(response.statusCode)) return null;

  let payload;
  try {
    payload = JSON.parse(response.body.toString('utf8'));
  } catch {
    return null;
  }

  return extractFileItemFromTrpcPayload(payload, fileId);
};

const downloadJpegFromUrl = async ({ fileId, source, url }) => {
  if (!url) return null;

  const response = await fetchWithTimeout(
    url,
    {
      method: 'GET',
      redirect: 'follow',
      headers: {
        accept: 'image/jpeg,image/jpg,image/*;q=0.8,*/*;q=0.2',
      },
    },
    LEGALCHAT_OCR_TIMEOUT_MS,
  );

  if (!response.ok) return null;

  const contentType = String(response.headers.get('content-type') || '')
    .split(';')[0]
    .trim()
    .toLowerCase();

  const arrayBuffer = await response.arrayBuffer();
  const buffer = Buffer.from(arrayBuffer);
  if (!buffer.length) return null;
  if (buffer.length > LEGALCHAT_OCR_MAX_IMAGE_BYTES) return null;

  const jpegByType = isJpegMimeType(contentType);
  const jpegByBuffer = isLikelyJpegBuffer(buffer);
  const jpegByPath = /\.jpe?g(?:$|\?)/i.test(url);
  if (!jpegByType && !jpegByBuffer && !jpegByPath) return null;

  return {
    base64: buffer.toString('base64'),
    fileId,
    mimeType: jpegByType ? contentType : 'image/jpeg',
    size: buffer.length,
    source,
  };
};

const buildOcrDownloadCandidates = (fileId) => {
  const candidates = [];
  const seen = new Set();
  const addCandidate = (source, url) => {
    const value = String(url || '').trim();
    if (!value) return;
    if (seen.has(value)) return;
    seen.add(value);
    candidates.push({ source, url: value });
  };

  addCandidate('file-proxy', toAbsoluteUpstreamUrl(`/f/${encodeURIComponent(fileId)}`));
  addCandidate('api-file', toAbsoluteUpstreamUrl(`/api/file/${encodeURIComponent(fileId)}`));

  const cached = getCachedFileEntry(fileId);
  if (!cached) return candidates;

  addCandidate('cache-response-url', toAbsoluteUpstreamUrl(cached.responseUrl));

  const normalizedStorage = normalizeStorageKey(cached.storageUrl);
  if (!normalizedStorage) return candidates;

  if (normalizedStorage.directUrl) {
    addCandidate('cache-storage-direct', normalizedStorage.directUrl);
    return candidates;
  }

  if (!normalizedStorage.key) return candidates;

  const presignedUrl = buildS3PresignedGetUrl(normalizedStorage.key);
  addCandidate('cache-s3-presigned', presignedUrl);

  const publicDomainUrl = buildS3PublicDomainUrl(normalizedStorage.key);
  addCandidate('cache-s3-public', publicDomainUrl);

  return candidates;
};

const downloadJpegForOcr = async (fileId, requestHeaders = null) => {
  const cached = getCachedFileEntry(fileId);
  if (!cached && requestHeaders) {
    try {
      const fileItem = await fetchFileItemViaTrpc(fileId, requestHeaders);
      if (fileItem && fileItem.url) {
        putCachedFileEntry(fileId, {
          fileType: fileItem.fileType || '',
          responseUrl: fileItem.url,
          storageUrl: isLikelyStorageUrl(fileItem.url) ? fileItem.url : '',
        });
      }
    } catch (error) {
      console.warn(
        `[LegalChat OCR] file.getFileItemById fallback failed for ${fileId}:`,
        error?.message || error,
      );
    }
  }

  const candidates = buildOcrDownloadCandidates(fileId);

  for (const candidate of candidates) {
    try {
      const downloaded = await downloadJpegFromUrl({
        fileId,
        source: candidate.source,
        url: candidate.url,
      });
      if (!downloaded) continue;
      return downloaded;
    } catch (error) {
      console.warn(
        `[LegalChat OCR] Download candidate failed (${candidate.source}) for ${fileId}:`,
        error?.message || error,
      );
    }
  }

  return null;
};

const requestOcrTextFromOpenRouter = async ({ imageBase64, mimeType }) => {
  const requestPayload = {
    messages: [
      {
        role: 'user',
        content: [
          { type: 'text', text: LEGALCHAT_OCR_PROMPT },
          {
            type: 'image_url',
            image_url: { url: `data:${mimeType};base64,${imageBase64}` },
          },
        ],
      },
    ],
    model: LEGALCHAT_OCR_MODEL,
    temperature: 0,
  };

  const response = await fetchWithTimeout(
    OPENROUTER_CHAT_COMPLETIONS_URL,
    {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${OPENROUTER_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestPayload),
    },
    LEGALCHAT_OCR_TIMEOUT_MS,
  );

  if (!response.ok) {
    const errorBody = await response.text().catch(() => '');
    throw new Error(`OCR model request failed (${response.status}): ${errorBody.slice(0, 300)}`);
  }

  const payload = await response.json();
  if (payload?.error) {
    throw new Error(`OCR model error: ${JSON.stringify(payload.error)}`);
  }

  return normalizeExtractedText(extractFirstAssistantText(payload));
};

const buildAutoOcrBlock = (ocrResults) => {
  const sections = ocrResults.map(
    (item, index) =>
      `[JPEG ${index + 1} | ${item.fileId}]\n${item.text}`,
  );

  return (
    `[${LEGALCHAT_OCR_MARKER}]\n` +
    `Automatisch extrahierter OCR-Text (Gemini 2.5 Flash Lite) aus JPEG-Anhaengen:\n\n` +
    `${sections.join('\n\n---\n\n')}\n` +
    `[/${LEGALCHAT_OCR_MARKER}]`
  );
};

const injectJpegOcrIntoTrpcBody = async (bodyBuffer, requestHeaders = null) => {
  if (!LEGALCHAT_OCR_ENABLED) return { bodyBuffer, injected: false, reason: 'disabled' };
  if (!OPENROUTER_API_KEY) return { bodyBuffer, injected: false, reason: 'missing_api_key' };
  if (!bodyBuffer || bodyBuffer.length === 0) return { bodyBuffer, injected: false, reason: 'empty' };

  let parsed;
  try {
    parsed = JSON.parse(bodyBuffer.toString('utf8'));
  } catch {
    return { bodyBuffer, injected: false, reason: 'not_json' };
  }

  const sendPayloads = findSendMessagePayloads(parsed);
  if (sendPayloads.length === 0) return { bodyBuffer, injected: false, reason: 'no_send_payload' };

  let injected = false;
  let totalOcrItems = 0;

  for (const payload of sendPayloads) {
    const message = payload.newUserMessage;
    if (!message || typeof message.content !== 'string') continue;
    if (message.content.includes(`[${LEGALCHAT_OCR_MARKER}]`)) continue;

    const fileIds = Array.isArray(message.files)
      ? message.files.filter((id) => typeof id === 'string' && id.length > 0)
      : [];
    if (fileIds.length === 0) continue;

    const limitedFileIds = fileIds.slice(0, LEGALCHAT_OCR_MAX_IMAGES);
    const ocrResults = [];

    for (const fileId of limitedFileIds) {
      try {
        const downloaded = await downloadJpegForOcr(fileId, requestHeaders);
        if (!downloaded) continue;

        const text = await requestOcrTextFromOpenRouter({
          imageBase64: downloaded.base64,
          mimeType: downloaded.mimeType,
        });
        if (!text) continue;

        ocrResults.push({ fileId, text });
      } catch (error) {
        console.warn(`[LegalChat OCR] ${fileId} failed:`, error?.message || error);
      }
    }

    if (ocrResults.length === 0) continue;

    const suffix = buildAutoOcrBlock(ocrResults);
    payload.newUserMessage.content = `${message.content}\n\n${suffix}`;
    injected = true;
    totalOcrItems += ocrResults.length;
  }

  if (!injected) return { bodyBuffer, injected: false, reason: 'no_jpeg_or_no_text' };

  return {
    bodyBuffer: Buffer.from(JSON.stringify(parsed), 'utf8'),
    injected: true,
    ocrItems: totalOcrItems,
    reason: 'ok',
  };
};

const handleAiChatSendMessageWithAutoOcr = async (req, res) => {
  try {
    const forwardingHost = getPublicHost(req);
    const forwardingProto = getForwardedProtocol(req);
    const originalBody = await readRequestBody(req);
    const ocrResult = await injectJpegOcrIntoTrpcBody(originalBody, req.headers || null);
    const bodyToForward = ocrResult.bodyBuffer || originalBody;

    if (ocrResult.injected) {
      console.log(
        `[LegalChat OCR] Injected OCR text for ${ocrResult.ocrItems} JPEG file(s) via ${LEGALCHAT_OCR_MODEL}`,
      );
    } else {
      console.log(`[LegalChat OCR] Bypass: ${ocrResult.reason}`);
    }

    const headers = buildUpstreamHeaders({
      req,
      bodyBuffer: bodyToForward,
      forwardingHost,
      forwardingProto,
    });

    const upstream = await requestTarget({
      body: bodyToForward,
      headers,
      method: req.method,
      path: req.url,
    });

    sendUpstreamResponse({ req, res, upstream });
  } catch (error) {
    console.error('Auto OCR proxy failed:', error);
    res.writeHead(502, { 'content-type': 'text/plain; charset=utf-8' });
    res.end('Auto OCR proxy error');
  }
};

const tryParseJsonBuffer = (buffer) => {
  try {
    if (!buffer || buffer.length === 0) return null;
    return JSON.parse(buffer.toString('utf8'));
  } catch {
    return null;
  }
};

const handleFileCreateWithCache = async (req, res) => {
  try {
    const forwardingHost = getPublicHost(req);
    const forwardingProto = getForwardedProtocol(req);
    const requestBody = await readRequestBody(req);

    const headers = buildUpstreamHeaders({
      req,
      bodyBuffer: requestBody,
      forwardingHost,
      forwardingProto,
    });

    const upstream = await requestTarget({
      body: requestBody,
      headers,
      method: req.method,
      path: req.url,
    });

    const requestPayload = tryParseJsonBuffer(requestBody);
    const responsePayload = tryParseJsonBuffer(upstream.body);
    const storedMappings = rememberFileCreateMappings({
      requestPayload,
      responsePayload,
    });

    if (storedMappings > 0) {
      console.log(`[LegalChat OCR] Cached ${storedMappings} file.createFile mapping(s)`);
    }

    sendUpstreamResponse({ req, res, upstream });
  } catch (error) {
    console.error('File create cache proxy failed:', error);
    res.writeHead(502, { 'content-type': 'text/plain; charset=utf-8' });
    res.end('File cache proxy error');
  }
};

const escapeHtml = (value) =>
  String(value == null ? '' : value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');

const isTruthyFlag = (value) => /^(1|true|yes|on)$/i.test(String(value || '').trim());

const buildProviderSigninUrl = (callbackUrl, options = {}) => {
  const params = new URLSearchParams();
  params.set('callbackUrl', callbackUrl || APP_PUBLIC_URL);
  const forcePrompt =
    typeof options.forcePrompt === 'boolean'
      ? options.forcePrompt
      : LEGALCHAT_FORCE_LOGIN_PROMPT;
  if (forcePrompt) {
    params.set('prompt', 'login');
    params.set('max_age', '0');
  }
  if (options.firstScreen) {
    params.set('first_screen', options.firstScreen);
  }
  if (options.identifier) {
    params.set('identifier', options.identifier);
  }
  if (options.directSignIn) {
    params.set('direct_sign_in', options.directSignIn);
  }
  return `/api/auth/signin/logto?${params.toString()}`;
};

const normalizeCallbackUrl = (input, fallbackOrigin) => {
  const fallback = `${fallbackOrigin.replace(/\/+$/, '')}/chat`;
  const raw = String(input || '').trim();
  if (!raw) return fallback;
  try {
    const parsed = new URL(raw, fallbackOrigin);
    const fallbackUrl = new URL(fallback);
    if (parsed.origin !== fallbackUrl.origin) return fallback;
    return parsed.toString();
  } catch {
    return fallback;
  }
};

const buildHelperHtml = ({ loggedOut = false, callbackUrl } = {}) => {
  const callback = normalizeCallbackUrl(callbackUrl, APP_PUBLIC_URL);
  const loginHref = buildProviderSigninUrl(callback);
  // Important: Always start from the app's OIDC entrypoint (not /sign-up directly),
  // otherwise Logto may show unknown-session 404.
  const signUpHref = buildProviderSigninUrl(callback, {
    forcePrompt: false,
    firstScreen: 'register',
  });
  const appName = escapeHtml(LEGALCHAT_APP_NAME);
  const avatarUrl = escapeHtml(LEGALCHAT_AVATAR_VERSIONED_URL);
  const assistantRole = escapeHtml(LEGALCHAT_ASSISTANT_ROLE_DE);
  const statusHtml = loggedOut
    ? `
      <div class="status" role="status" aria-live="polite">
        <span class="statusDot" aria-hidden="true"></span>
        Sie wurden sicher abgemeldet.
      </div>
    `
    : '';

  return `<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>${appName} Anmeldung</title>
  <meta name="theme-color" content="#0b1635" />
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;700;800&family=Sora:wght@600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #08112b;
      --bg-2: #0f1f45;
      --line: rgba(163, 184, 255, 0.26);
      --text: #ebf1ff;
      --muted: #aebfdf;
      --accent-a: #4ea1ff;
      --accent-b: #7f7bff;
      --ok: #46d39b;
    }
    * { box-sizing: border-box; }
    html, body { height: 100%; }
    body {
      margin: 0;
      color: var(--text);
      font-family: "Manrope", "Segoe UI", "Helvetica Neue", sans-serif;
      background: radial-gradient(120% 90% at 50% 0%, #122b65 0%, #0b1738 42%, #060f27 100%);
      overflow: hidden;
    }
    .wrap {
      position: relative;
      min-height: 100%;
      display: grid;
      place-items: center;
      padding: 24px;
      isolation: isolate;
    }
    .mesh {
      position: absolute;
      inset: 0;
      background:
        radial-gradient(42rem 42rem at 12% 18%, rgba(70, 110, 255, 0.22), transparent 65%),
        radial-gradient(30rem 30rem at 85% 8%, rgba(123, 102, 255, 0.20), transparent 72%),
        radial-gradient(28rem 28rem at 84% 84%, rgba(44, 181, 255, 0.14), transparent 70%);
      z-index: -2;
    }
    .mesh::after {
      content: "";
      position: absolute;
      inset: 0;
      background-image: linear-gradient(rgba(187, 206, 255, 0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(187, 206, 255, 0.06) 1px, transparent 1px);
      background-size: 48px 48px;
      mask-image: radial-gradient(circle at center, black 22%, transparent 88%);
      pointer-events: none;
    }
    .shell {
      position: relative;
      width: min(640px, 100%);
      border-radius: 28px;
      padding: 1px;
      background: linear-gradient(140deg, rgba(107, 151, 255, 0.55), rgba(123, 102, 255, 0.36), rgba(99, 220, 255, 0.28));
      box-shadow:
        0 36px 90px rgba(3, 8, 24, 0.7),
        inset 0 1px 0 rgba(255, 255, 255, 0.25);
      animation: panelFloat 7.5s ease-in-out infinite;
    }
    .card {
      border-radius: 27px;
      backdrop-filter: blur(12px);
      background:
        linear-gradient(180deg, rgba(16, 30, 67, 0.92), rgba(10, 20, 49, 0.9)),
        linear-gradient(120deg, rgba(255, 255, 255, 0.06), rgba(255, 255, 255, 0));
      padding: clamp(28px, 5vw, 44px);
      text-align: center;
      border: 1px solid rgba(177, 202, 255, 0.2);
    }
    .eyebrow {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-size: 11px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      color: #bed1ff;
      border: 1px solid rgba(156, 183, 255, 0.32);
      border-radius: 999px;
      padding: 7px 12px;
      background: rgba(20, 44, 95, 0.54);
      margin-bottom: 20px;
    }
    .avatarHalo {
      width: 148px;
      height: 148px;
      margin: 0 auto 18px;
      border-radius: 50%;
      display: grid;
      place-items: center;
      background: conic-gradient(from 40deg, rgba(81, 162, 255, 0.95), rgba(126, 109, 255, 0.9), rgba(78, 161, 255, 0.95));
      animation: spin 16s linear infinite;
      box-shadow: 0 10px 36px rgba(71, 131, 255, 0.42);
    }
    .avatarFrame {
      width: 140px;
      height: 140px;
      border-radius: 50%;
      padding: 3px;
      background: linear-gradient(180deg, rgba(255, 255, 255, 0.45), rgba(255, 255, 255, 0.1));
    }
    .avatar {
      display: block;
      width: 100%;
      height: 100%;
      object-fit: cover;
      border-radius: 50%;
      border: 1px solid rgba(195, 214, 255, 0.52);
    }
    h1 {
      margin: 0;
      font-family: "Sora", "Manrope", sans-serif;
      font-size: clamp(34px, 5vw, 48px);
      letter-spacing: -0.03em;
      color: #f4f7ff;
      text-shadow: 0 8px 26px rgba(63, 126, 255, 0.35);
    }
    .subline {
      margin: 10px 0 0;
      font-size: clamp(17px, 2.4vw, 21px);
      color: #b4c7ee;
      font-weight: 500;
    }
    .status {
      margin: 18px auto 0;
      width: fit-content;
      max-width: 100%;
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 9px 14px;
      border-radius: 999px;
      border: 1px solid rgba(98, 228, 168, 0.52);
      background: rgba(28, 78, 64, 0.35);
      color: #d6ffe6;
      font-size: 14px;
      font-weight: 600;
    }
    .statusDot {
      width: 9px;
      height: 9px;
      border-radius: 50%;
      background: var(--ok);
      box-shadow: 0 0 0 6px rgba(70, 211, 155, 0.16);
    }
    .ctaWrap {
      margin-top: 28px;
      display: flex;
      justify-content: center;
      gap: 10px;
      flex-wrap: wrap;
    }
    .button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 216px;
      padding: 14px 26px;
      border-radius: 14px;
      text-decoration: none;
      font-size: 18px;
      font-weight: 800;
      letter-spacing: 0.01em;
      color: #fff;
      background: linear-gradient(130deg, var(--accent-a), var(--accent-b));
      border: 1px solid rgba(182, 209, 255, 0.55);
      box-shadow:
        0 14px 26px rgba(52, 102, 241, 0.44),
        inset 0 1px 0 rgba(255, 255, 255, 0.35);
      transition: transform 180ms ease, box-shadow 180ms ease, filter 180ms ease;
    }
    .button:hover { transform: translateY(-2px); filter: brightness(1.06); box-shadow: 0 18px 34px rgba(52, 102, 241, 0.52), inset 0 1px 0 rgba(255, 255, 255, 0.45); }
    .button:active { transform: translateY(0); }
    .button.secondary {
      background: rgba(17, 35, 82, 0.72);
      border: 1px solid rgba(171, 201, 255, 0.46);
      box-shadow: none;
      color: #dbe9ff;
    }
    .button.secondary:hover {
      box-shadow: 0 10px 18px rgba(8, 20, 52, 0.44);
    }
    .hint {
      margin: 16px auto 0;
      color: var(--muted);
      font-size: 14px;
      max-width: 46ch;
      line-height: 1.5;
    }
    .footer {
      margin-top: 16px;
      font-size: 12px;
      letter-spacing: 0.09em;
      text-transform: uppercase;
      color: rgba(173, 195, 236, 0.72);
    }
    @keyframes spin { to { transform: rotate(1turn); } }
    @keyframes panelFloat {
      0%, 100% { transform: translateY(0); }
      50% { transform: translateY(-5px); }
    }
    @media (max-width: 640px) {
      .wrap { padding: 16px; }
      .card { border-radius: 22px; }
      .shell { border-radius: 23px; }
      .button { width: 100%; min-width: 0; }
      .avatarHalo { width: 128px; height: 128px; }
      .avatarFrame { width: 120px; height: 120px; }
      .hint { font-size: 13px; }
    }
    @media (prefers-reduced-motion: reduce) {
      .shell, .avatarHalo { animation: none; }
      .button { transition: none; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="mesh" aria-hidden="true"></div>
    <div class="shell">
      <div class="card">
      <div class="eyebrow">Sichere Anmeldung</div>
      <div class="avatarHalo" aria-hidden="true">
        <div class="avatarFrame">
          <img src="${avatarUrl}" alt="${escapeHtml(LEGALCHAT_DEFAULT_AGENT_NAME)}" class="avatar" />
        </div>
      </div>
      <h1>${appName} ⚖</h1>
      <p class="subline">Ihr ${assistantRole}</p>
      ${statusHtml}
      <div class="ctaWrap">
      <a class="button" href="${loginHref}">Anmelden</a>
      <a class="button secondary" href="${escapeHtml(signUpHref)}">Konto erstellen</a>
      </div>
      <p class="hint">Anmeldung ist möglich via Apple, Google, Facebook oder GitHub (falls in Logto aktiviert) sowie optional mit Passwort. Danach werden Sie direkt zurück in Ihren Workspace geleitet.</p>
      <div class="footer">LegalChat Security Layer</div>
      </div>
    </div>
  </div>
</body>
</html>`;
};

const sendLoginHelper = (res, options = {}) => {
  const html = buildHelperHtml(options);
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

const normalizeLocalLogoutLocation = (input, fallbackOrigin) => {
  const fallback = LEGALCHAT_LOCAL_LOGOUT_REDIRECT_URL || '/login?logged_out=1';
  const raw = String(input || '').trim();
  if (!raw) return fallback;
  try {
    const parsed = new URL(raw, fallbackOrigin);
    const fallbackUrl = new URL(APP_PUBLIC_URL);
    if (parsed.origin !== fallbackUrl.origin) return fallback;
    return `${parsed.pathname}${parsed.search}${parsed.hash}`;
  } catch {
    return fallback;
  }
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

const rewriteHeadBrandingMetadata = (html) => {
  const headOpen = html.indexOf('<head');
  const headClose = html.indexOf('</head>');
  if (headOpen === -1 || headClose === -1 || headClose <= headOpen) return html;

  const headHtml = html.slice(headOpen, headClose);
  let rewrittenHead = headHtml;

  rewrittenHead = rewrittenHead.replace(
    /<title[^>]*>[\s\S]*?<\/title>/gi,
    (tag) => tag.replace(HTML_BRAND_PATTERN, LEGALCHAT_APP_NAME),
  );

  rewrittenHead = rewrittenHead.replace(
    /<meta\b[^>]*(?:name|property)=["'](?:description|apple-mobile-web-app-title|og:title|og:description|og:site_name|og:image:alt|twitter:title|twitter:description)["'][^>]*>/gi,
    (tag) => tag.replace(HTML_BRAND_PATTERN, LEGALCHAT_APP_NAME),
  );

  rewrittenHead = rewrittenHead.replace(
    /<link\b[^>]*rel=["'](?:shortcut icon|icon|apple-touch-icon)["'][^>]*>/gi,
    (tag) =>
      /href\s*=/.test(tag)
        ? tag.replace(/href=["'][^"']*["']/i, `href="${LEGALCHAT_FAVICON_VERSIONED_URL}"`)
        : tag.replace(/\/?>$/, ` href="${LEGALCHAT_FAVICON_VERSIONED_URL}"$&`),
  );

  return html.slice(0, headOpen) + rewrittenHead + html.slice(headClose);
};

// Inject branding into HTML responses
const injectBrandingIntoHTML = (body) => {
  let html = body.toString('utf8');
  html = rewriteHeadBrandingMetadata(html);
  html = html
    .replace(/Anmelden bei\s+(?:LobeHub|LobeChat)/gi, `Anmelden bei ${LEGALCHAT_APP_NAME}`)
    .replace(/Sign in to\s+(?:LobeHub|LobeChat)/gi, `Sign in to ${LEGALCHAT_APP_NAME}`)
    .replace(/Powered by\s+(?:LobeHub|LobeChat)/gi, `Powered by ${LEGALCHAT_APP_NAME}`)
    .replace(/Powered by Logto/gi, `Powered by ${LEGALCHAT_APP_NAME}`)
    .replace(/>\s*Logto\s*</g, '>Anmelden<');
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
  const isUiPath =
    pathname === '/' ||
    /(?:^|\/)(chat|welcome|settings)(?:\/|$)/i.test(pathname) ||
    /^\/next-auth\/(?:signin|error)(?:\/|$)/i.test(pathname);
  const isPageRequest =
    (req.method === 'GET' || req.method === 'HEAD') && isUiPath;
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

const proxyLogtoBrandedRequest = async (req, res) => {
  const parsedUrl = new URL(req.url, `${getForwardedProtocol(req)}://${getPublicHost(req)}`);
  const pathname = parsedUrl.pathname;
  const isPageRequest =
    (req.method === 'GET' || req.method === 'HEAD') &&
    (/^\/(?:sign-in|sign-up|signup|sign_in|register|create-account|unknown-session|reset-password|forgot-password|oidc\/auth)/.test(
      pathname,
    ) ||
      pathname === '/');

  const forwardingHost = getPublicHost(req);
  const forwardingProto = getForwardedProtocol(req);
  const headers = {
    ...req.headers,
    host: req.headers.host || forwardingHost,
    ...(isPageRequest ? { 'accept-encoding': 'identity' } : {}),
    'x-forwarded-host': forwardingHost,
    'x-forwarded-proto': forwardingProto,
  };

  try {
    const proxyRes = await new Promise((resolve, reject) => {
      const proxyReq = http.request(
        {
          hostname: LOGTO_UPSTREAM_HOST,
          port: LOGTO_UPSTREAM_PORT,
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
    if (isPageRequest) {
      setNoStoreHeaders(responseHeaders);
    }

    let body = proxyRes.body;
    const contentType = proxyRes.headers['content-type'] || '';
    if (req.method === 'GET' && isPageRequest && contentType.includes('text/html')) {
      body = Buffer.from(injectLogtoBrandingExperience(body.toString('utf8'), pathname), 'utf8');
      delete responseHeaders['content-encoding'];
      delete responseHeaders['transfer-encoding'];
      responseHeaders['content-length'] = body.length;
      console.log('[LegalChat] Logto branding injected');
    }

    res.writeHead(proxyRes.statusCode || 500, responseHeaders);
    res.end(body);
  } catch (error) {
    console.error('Logto proxy error:', error);
    res.writeHead(502, { 'content-type': 'text/plain; charset=utf-8' });
    res.end('Bad Gateway');
  }
};

const shouldShowHelperOnRoot = (req) => {
  const host = getPublicHost(req);
  return host.endsWith(':3211');
};

const SESSION_COOKIE_NAMES = new Set([
  'authjs.session-token',
  '__Secure-authjs.session-token',
  'next-auth.session-token',
  '__Secure-next-auth.session-token',
]);

const isUiRoutePath = (pathname) =>
  pathname === '/' || /(?:^|\/)(chat|welcome|settings)(?:\/|$)/i.test(pathname);

const hasSessionCookie = (req) => {
  const cookies = parseCookieHeader(req.headers.cookie);
  for (const name of cookies.keys()) {
    if (SESSION_COOKIE_NAMES.has(name)) return true;
    if (
      /^(__Secure-)?authjs\.session-token\.\d+$/.test(name) ||
      /^(__Secure-)?next-auth\.session-token\.\d+$/.test(name)
    ) {
      return true;
    }
  }
  return false;
};

const shouldEnforceLogin = (req, parsedUrl) => {
  if (req.method !== 'GET') return false;
  if (!isUiRoutePath(parsedUrl.pathname)) return false;
  if (parsedUrl.pathname === '/login') return false;
  if (shouldShowHelperOnRoot(req)) return false;
  return !hasSessionCookie(req);
};

const server = http.createServer(async (req, res) => {
  const publicOrigin = `${getForwardedProtocol(req)}://${getPublicHost(req)}`;
  const parsedUrl = new URL(req.url, publicOrigin);

  if (req.method === 'GET' && parsedUrl.pathname === '/healthz') {
    res.writeHead(200, { 'content-type': 'text/plain; charset=utf-8' });
    res.end('ok');
    return;
  }

  if (req.method === 'GET' && parsedUrl.pathname === LEGALCHAT_MCP_STATUS_ROUTE) {
    await handleMcpStatusRequest(req, res);
    return;
  }

  if (req.method === 'GET' && parsedUrl.pathname === LEGALCHAT_MCP_TOOLS_ROUTE) {
    await handleMcpToolsListRequest(req, res, parsedUrl);
    return;
  }

  if (req.method === 'POST' && parsedUrl.pathname === LEGALCHAT_MCP_CALL_ROUTE) {
    await handleMcpToolCallRequest(req, res);
    return;
  }

  if (req.method === 'POST' && parsedUrl.pathname === LEGALCHAT_MCP_DEEP_RESEARCH_ROUTE) {
    await handleMcpToolCallRequest(req, res, { modeFromPath: 'deep-research' });
    return;
  }

  if (req.method === 'POST' && parsedUrl.pathname === LEGALCHAT_MCP_PRUEFUNGSMODUS_ROUTE) {
    await handleMcpToolCallRequest(req, res, { modeFromPath: 'pruefungsmodus' });
    return;
  }

  if (req.method === 'POST') {
    const modeToolMatch = parsedUrl.pathname.match(LEGALCHAT_MCP_MODE_TOOL_ROUTE_PATTERN);
    if (modeToolMatch) {
      await handleMcpToolCallRequest(req, res, {
        modeFromPath: modeToolMatch[1],
        toolNameFromPath: decodeURIComponent(modeToolMatch[2] || ''),
      });
      return;
    }
  }

  if (isLogtoBrandingHost(req)) {
    if (req.method === 'GET') {
      // Guardrail: Auth.js/NextAuth endpoints exist on the app origin (legalchat.net),
      // not on the IdP host (auth.legalchat.net). If we ever land here with /api/auth
      // or /next-auth paths, redirect back to the app to avoid 404s and redirect loops.
      if (/^\/(?:api\/auth|next-auth)(?:\/|$)/.test(parsedUrl.pathname)) {
        const appOrigin = new URL(APP_PUBLIC_URL).origin;
        const location = `${appOrigin}${req.url}`;
        res.writeHead(302, { 'cache-control': 'no-store', location });
        res.end();
        return;
      }

      const hasInteractionContext =
        parsedUrl.searchParams.has('interaction') ||
        parsedUrl.searchParams.has('interaction_id') ||
        parsedUrl.searchParams.has('flow') ||
        parsedUrl.searchParams.has('ticket');

      // Do not restart OIDC from inside Logto pages. Logto's /sign-in and /register are
      // first-party interaction pages that rely on interaction cookies. Redirecting
      // them back to /api/auth/signin breaks login/sign-up.
      if (!hasInteractionContext && /^\/sign-up\/?$/.test(parsedUrl.pathname)) {
        // Normalize legacy /sign-up -> /register (Logto canonical).
        const appId = parsedUrl.searchParams.get('app_id') || AUTH_LOGTO_ID;
        const target = new URL('/register', publicOrigin);
        for (const [k, v] of parsedUrl.searchParams.entries()) target.searchParams.set(k, v);
        if (appId && !target.searchParams.has('app_id')) target.searchParams.set('app_id', appId);
        res.writeHead(302, { 'cache-control': 'no-store', location: target.pathname + target.search });
        res.end();
        return;
      }

      const isUnknownSession =
        parsedUrl.pathname === '/' ||
        parsedUrl.pathname === '/login' ||
        /^\/unknown-session(?:\/|$)/.test(parsedUrl.pathname);

      if (isUnknownSession) {
        const appId = parsedUrl.searchParams.get('app_id') || AUTH_LOGTO_ID;
        const location = appId ? `/sign-in?app_id=${encodeURIComponent(appId)}` : '/sign-in';
        res.writeHead(302, { 'cache-control': 'no-store', location });
        res.end();
        return;
      }
    }

    await proxyLogtoBrandedRequest(req, res);
    return;
  }

  if (
    req.method === 'GET' &&
    (parsedUrl.pathname === '/logout' || parsedUrl.pathname === '/signout')
  ) {
    const requestedPostLogoutRedirectUrl = parsedUrl.searchParams.get('post_logout_redirect_uri');
    const postLogoutRedirectUrl =
      requestedPostLogoutRedirectUrl || LOGTO_POST_LOGOUT_REDIRECT_URL || APP_PUBLIC_URL;
    const useOidcLogout = LEGALCHAT_LOGOUT_MODE === 'oidc';
    const location = useOidcLogout
      ? (() => {
          const logoutUrl = new URL(LOGTO_END_SESSION_ENDPOINT);
          logoutUrl.searchParams.set('post_logout_redirect_uri', postLogoutRedirectUrl);
          if (AUTH_LOGTO_ID) logoutUrl.searchParams.set('client_id', AUTH_LOGTO_ID);
          return logoutUrl.toString();
        })()
      : normalizeLocalLogoutLocation(
          requestedPostLogoutRedirectUrl || LEGALCHAT_LOCAL_LOGOUT_REDIRECT_URL,
          publicOrigin,
        );

    res.writeHead(302, {
      'cache-control': 'no-store',
      location,
      'set-cookie': buildLogoutCookieHeaders(),
    });
    res.end();
    return;
  }

  // Force all built-in signout flows through /logout to ensure IdP session ends too.
  if (
    SIGNOUT_PATH_PATTERN.test(parsedUrl.pathname) &&
    (req.method === 'GET' || req.method === 'POST')
  ) {
    const callbackUrl = parsedUrl.searchParams.get('callbackUrl');
    const logoutLocation =
      LEGALCHAT_LOGOUT_MODE === 'oidc'
        ? callbackUrl
          ? `/logout?post_logout_redirect_uri=${encodeURIComponent(callbackUrl)}`
          : '/logout'
        : normalizeLocalLogoutLocation(LEGALCHAT_LOCAL_LOGOUT_REDIRECT_URL, publicOrigin);

    if (
      req.method === 'POST' ||
      req.headers['x-auth-return-redirect'] === '1' ||
      String(req.headers.accept || '').includes('application/json')
    ) {
      const payload = JSON.stringify({ url: logoutLocation });
      res.writeHead(200, {
        'cache-control': 'no-store',
        'content-type': 'application/json; charset=utf-8',
        'content-length': Buffer.byteLength(payload),
        'set-cookie': buildLogoutCookieHeaders(),
      });
      res.end(payload);
      return;
    }

    res.writeHead(302, {
      'cache-control': 'no-store',
      location: logoutLocation,
      'set-cookie': buildLogoutCookieHeaders(),
    });
    res.end();
    return;
  }

  // Skip built-in /next-auth/signin screen and go straight to Logto.
  if (req.method === 'GET' && parsedUrl.pathname === '/next-auth/signin') {
    const callbackUrl = parsedUrl.searchParams.get('callbackUrl') || `${publicOrigin}/chat`;
    const location = `/login?callbackUrl=${encodeURIComponent(callbackUrl)}`;
    res.writeHead(302, { 'cache-control': 'no-store', location });
    res.end();
    return;
  }

  if (req.method === 'GET' && parsedUrl.pathname === '/login') {
    sendLoginHelper(res, {
      loggedOut: isTruthyFlag(parsedUrl.searchParams.get('logged_out')),
      callbackUrl: parsedUrl.searchParams.get('callbackUrl'),
    });
    return;
  }

  if (shouldEnforceLogin(req, parsedUrl)) {
    const callbackUrl = `${publicOrigin}${req.url}`;
    const location = `/login?callbackUrl=${encodeURIComponent(callbackUrl)}`;
    res.writeHead(302, { 'cache-control': 'no-store', location });
    res.end();
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

  if (req.method === 'POST' && isFileCreatePath(parsedUrl.pathname)) {
    await handleFileCreateWithCache(req, res);
    return;
  }

  if (req.method === 'POST' && isAiChatSendMessagePath(parsedUrl.pathname)) {
    await handleAiChatSendMessageWithAutoOcr(req, res);
    return;
  }

  if (LEGALCHAT_VOICE_OFF && isAnyTtsPath(parsedUrl.pathname)) {
    sendVoiceDisabledResponse(res);
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
  console.log(`Voice mode: ${LEGALCHAT_VOICE_OFF ? 'off (microphone blocked)' : 'guarded'}`);
  console.log(
    `Auto OCR mode: ${
      LEGALCHAT_OCR_ENABLED && OPENROUTER_API_KEY
        ? `on (model=${LEGALCHAT_OCR_MODEL}, jpeg-only)`
        : 'off'
    }`,
  );
  console.log(
    `Auto OCR file fetch: ${
      S3_SIGNING_READY ? `s3-signing-ready (cache ttl=${LEGALCHAT_OCR_FILE_CACHE_TTL_MS}ms)` : 'limited'
    }`,
  );
  console.log(`George is ready! ⚖️`);
});
