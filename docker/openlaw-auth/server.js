'use strict';

const http = require('http');
const express = require('express');
const session = require('express-session');

// --- Config ---
const PORT = Number(process.env.PORT || 3210);
const PUBLIC_URL = (process.env.APP_PUBLIC_URL || 'https://www.openlaw.cc').replace(/\/+$/, '');
const SESSION_SECRET = process.env.SESSION_SECRET || process.env.NEXT_AUTH_SECRET || 'openlaw-change-me';
const APP_NAME = process.env.APP_NAME || 'OpenLaw';
const MAIL_ACCOUNTS_JSON = process.env.MAIL_ACCOUNTS_JSON || '';
const MAIL_ACCOUNT_ACCESS_JSON = process.env.MAIL_ACCOUNT_ACCESS_JSON || '';
const MAIL_USER = String(process.env.MAIL_USER || '').trim().toLowerCase();
const MAIL_PASSWORD = String(process.env.MAIL_PASSWORD || '').trim();

// --- Express app ---
const app = express();

app.set('trust proxy', 1);
app.use(express.urlencoded({ extended: false }));

app.use(session({
  name: 'openlaw.sid',
  secret: SESSION_SECRET,
  resave: false,
  saveUninitialized: false,
  cookie: {
    secure: true,
    httpOnly: true,
    sameSite: 'lax',
    maxAge: 7 * 24 * 3600 * 1000,
  },
}));

const parseJsonValue = (value, fallback = null) => {
  const raw = String(value || '').trim();
  if (!raw) return fallback;
  try {
    return JSON.parse(raw);
  } catch {
    return fallback;
  }
};

const normalizeMailIdentity = (value) =>
  String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9@._+-]/g, '');

const getMailIdentityVariants = (value) => {
  const normalized = normalizeMailIdentity(value);
  if (!normalized) return [];
  const variants = new Set([normalized]);
  if (normalized.includes('@')) {
    const localPart = normalized.split('@')[0];
    if (localPart) variants.add(localPart);
  }
  return Array.from(variants).filter(Boolean);
};

const titleCaseMailLabel = (value) => {
  const raw = String(value || '').trim();
  if (!raw) return 'Mailbox';
  return raw
    .replace(/[_-]+/g, ' ')
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
};

const parseMailAccountsConfig = () => {
  const orderedAccounts = [];
  const accountsByKey = new Map();
  let usesLegacyFallback = false;

  const pushAccount = (rawAccount, fallbackKey = '') => {
    if (!rawAccount || typeof rawAccount !== 'object') return;
    const email = String(rawAccount.email || rawAccount.user || '').trim().toLowerCase();
    const password = String(rawAccount.password || rawAccount.pass || '').trim();
    const key = normalizeMailIdentity(rawAccount.key || email.split('@')[0] || fallbackKey);
    if (!key || !email || !password || accountsByKey.has(key)) return;
    const localPart = email.split('@')[0] || key;
    const aliases = Array.isArray(rawAccount.aliases) ? rawAccount.aliases : [];
    const matchIdentities = new Set([
      ...getMailIdentityVariants(key),
      ...getMailIdentityVariants(email),
      ...getMailIdentityVariants(localPart),
    ]);
    for (const alias of aliases) {
      for (const variant of getMailIdentityVariants(alias)) matchIdentities.add(variant);
    }
    const account = {
      key,
      email,
      password,
      label:
        String(rawAccount.label || rawAccount.name || titleCaseMailLabel(localPart)).trim() ||
        titleCaseMailLabel(localPart),
      aliases,
      matchIdentities: Array.from(matchIdentities),
    };
    orderedAccounts.push(account);
    accountsByKey.set(key, account);
  };

  const parsedAccounts = parseJsonValue(MAIL_ACCOUNTS_JSON, null);
  if (Array.isArray(parsedAccounts)) {
    parsedAccounts.forEach((entry, index) => pushAccount(entry, `mail${index + 1}`));
  } else if (parsedAccounts && typeof parsedAccounts === 'object') {
    for (const [key, value] of Object.entries(parsedAccounts)) {
      pushAccount(
        value && typeof value === 'object' && !Array.isArray(value) ? { key, ...value } : null,
        key,
      );
    }
  }

  if (!orderedAccounts.length && MAIL_USER && MAIL_PASSWORD) {
    usesLegacyFallback = true;
    pushAccount(
      {
        key: MAIL_USER.split('@')[0] || 'primary',
        email: MAIL_USER,
        password: MAIL_PASSWORD,
        label: titleCaseMailLabel(MAIL_USER.split('@')[0] || 'primary'),
      },
      'primary',
    );
  }

  const accessMap = new Map();
  const parsedAccess = parseJsonValue(MAIL_ACCOUNT_ACCESS_JSON, null);
  if (parsedAccess && typeof parsedAccess === 'object' && !Array.isArray(parsedAccess)) {
    for (const [identityRaw, grantedRaw] of Object.entries(parsedAccess)) {
      const grantedKeys = (Array.isArray(grantedRaw) ? grantedRaw : [grantedRaw])
        .map((entry) => normalizeMailIdentity(entry))
        .filter((entry) => entry && accountsByKey.has(entry));
      if (!grantedKeys.length) continue;
      for (const identity of getMailIdentityVariants(identityRaw)) {
        const existing = accessMap.get(identity) || new Set();
        for (const grantedKey of grantedKeys) existing.add(grantedKey);
        accessMap.set(identity, existing);
      }
    }
  }

  return { orderedAccounts, accountsByKey, accessMap, usesLegacyFallback };
};

const MAIL_CONFIG = parseMailAccountsConfig();

const authenticateDirectLogin = (identifierRaw, passwordRaw) => {
  const password = String(passwordRaw || '').trim();
  if (!password) return null;

  const identityVariants = getMailIdentityVariants(identifierRaw);
  if (!identityVariants.length) return null;

  for (const account of MAIL_CONFIG.orderedAccounts) {
    const matchesIdentity = account.matchIdentities.some((identity) => identityVariants.includes(identity));
    if (matchesIdentity && account.password === password) {
      return {
        email: account.email,
        primaryEmail: account.email,
        name: account.label,
        accountKey: account.key,
      };
    }
  }

  for (const identity of identityVariants) {
    const grantedKeys = MAIL_CONFIG.accessMap.get(identity);
    if (!grantedKeys) continue;
    for (const grantedKey of grantedKeys) {
      const account = MAIL_CONFIG.accountsByKey.get(grantedKey);
      if (!account || account.password !== password) continue;
      return {
        email: normalizeMailIdentity(identifierRaw),
        primaryEmail: normalizeMailIdentity(identifierRaw),
        name: account.label,
        accountKey: account.key,
      };
    }
  }

  return null;
};

const renderLoginPage = ({ callbackUrl = '/mail', loggedOut = false, error = '' } = {}) => {
  const safeCallback = String(callbackUrl || '/mail');
  const errorHtml = error
    ? `<p class="error">${error}</p>`
    : '';
  const loggedOutHtml = loggedOut ? '<p class="logged-out">Erfolgreich abgemeldet.</p>' : '';

  return `<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${APP_NAME} — Anmeldung</title>
<style>
*{box-sizing:border-box;margin:0}
html,body{height:100%}
body{
  background:linear-gradient(135deg,#f6f0e7 0%,#efe7da 100%);
  font-family:"Avenir Next","Segoe UI",system-ui,sans-serif;
  color:#26190f;display:flex;align-items:center;justify-content:center;
}
.card{
  background:rgba(255,255,255,.88);backdrop-filter:blur(20px);
  border-radius:24px;padding:48px 40px;max-width:420px;width:100%;
  box-shadow:0 24px 48px rgba(61,37,18,.10);
}
h1{font-family:Georgia,serif;font-size:28px;margin-bottom:6px;text-align:center}
.sub{color:#685242;margin-bottom:28px;font-size:15px;text-align:center}
form{display:grid;gap:14px}
label{font-size:14px;color:#6d5849}
input{
  width:100%;padding:13px 14px;border:1px solid #d8c8b8;border-radius:12px;
  font-size:16px;background:#fff;color:#26190f;
}
button{
  display:block;width:100%;padding:14px;border:none;border-radius:12px;
  background:#8a3b12;color:#fff;font-size:16px;font-weight:600;cursor:pointer;
}
button:hover{background:#a04814}
.note{margin-top:18px;font-size:13px;color:#907965;text-align:center}
.logged-out{color:#215f4a;margin-bottom:16px;font-size:14px;text-align:center}
.error{color:#9b1c1c;background:#fff1f1;border:1px solid #f1c4c4;border-radius:12px;padding:12px 14px;font-size:14px}
</style>
</head>
<body>
<div class="card">
  <h1>${APP_NAME} ⚖</h1>
  <p class="sub">Direkter Mail-Login</p>
  ${loggedOutHtml}
  ${errorHtml}
  <form method="post" action="/login">
    <input type="hidden" name="callbackUrl" value="${safeCallback}">
    <div>
      <label for="email">E-Mail</label>
      <input id="email" name="email" type="email" autocomplete="username" required>
    </div>
    <div>
      <label for="password">Passwort</label>
      <input id="password" name="password" type="password" autocomplete="current-password" required>
    </div>
    <button type="submit">Anmelden</button>
  </form>
  <p class="note">Kein Logto, keine externe Weiterleitung.</p>
</div>
</body>
</html>`;
};

// --- Auth routes ---

// Login page
app.get('/login', (req, res) => {
  if (req.session.user && !req.query.logged_out) {
    return res.redirect(req.query.callbackUrl || '/mail');
  }
  const callbackUrl = req.query.callbackUrl || '/mail';
  res.setHeader('Content-Type', 'text/html; charset=utf-8');
  res.setHeader('Cache-Control', 'no-store');
  res.send(
    renderLoginPage({
      callbackUrl,
      loggedOut: req.query.logged_out === '1',
      error: req.query.error === 'invalid_credentials' ? 'E-Mail oder Passwort ist falsch.' : '',
    }),
  );
});

app.post('/login', (req, res) => {
  const callbackUrl = String(req.body?.callbackUrl || '/mail');
  const email = String(req.body?.email || '');
  const password = String(req.body?.password || '');
  const user = authenticateDirectLogin(email, password);
  if (!user) {
    const location = `/login?callbackUrl=${encodeURIComponent(callbackUrl)}&error=invalid_credentials`;
    res.redirect(location);
    return;
  }

  req.session.user = user;
  console.log(`Direct login OK: ${user.primaryEmail || user.email}`);
  res.redirect(callbackUrl || '/mail');
});

// Session check endpoint (for mail-routes.js compatibility)
app.get('/api/auth/session', (req, res) => {
  if (req.session.user) {
    res.json({ user: req.session.user });
  } else {
    res.json({});
  }
});

// Logout
app.get('/logout', (req, res) => {
  req.session.destroy(() => {
    res.redirect('/login?logged_out=1');
  });
});
app.get('/signout', (req, res) => res.redirect('/logout'));

app.get('/api/auth/signin/logto', (req, res) => {
  const callbackUrl = req.query.callbackUrl || '/mail';
  res.redirect(`/login?callbackUrl=${encodeURIComponent(callbackUrl)}`);
});

// --- Mailbox alias ---
app.all('/mailbox', (req, res) => res.redirect(301, req.url.replace('/mailbox', '/mail')));
app.all('/mailbox/*', (req, res) => res.redirect(301, req.url.replace('/mailbox', '/mail')));

// --- Mail routes ---
const { maybeHandleMailRequest } = require('./mail-routes');

const validateSession = async (req) => {
  return req.session?.user || null;
};

app.use(async (req, res, next) => {
  try {
    const handled = await maybeHandleMailRequest(req, res, {
      publicOrigin: PUBLIC_URL,
      validateSessionViaAuthJs: validateSession,
    });
    if (!handled) next();
  } catch (err) {
    console.error('Mail route error:', err.message);
    if (!res.headersSent) res.status(500).json({ ok: false, error: 'Internal error' });
  }
});

// --- Fallback ---
app.use((req, res) => {
  res.redirect('/login');
});

// --- Start ---
const server = http.createServer(app);
server.listen(PORT, () => {
  console.log(`${APP_NAME} auth server listening on :${PORT}`);
  console.log(`Public URL: ${PUBLIC_URL}`);
});
