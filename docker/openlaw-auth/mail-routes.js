'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const LOCAL_MAIL_HTML_PATH = path.join(__dirname, 'mail.html');

const isEnvTruthy = (value) => /^(1|true|yes|on)$/i.test(String(value || '').trim());
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

const MAIL_ENABLED = process.env.MAIL_ENABLED !== '0';
const MAIL_ACCOUNTS_JSON = process.env.MAIL_ACCOUNTS_JSON || '';
const MAIL_ACCOUNT_ACCESS_JSON = process.env.MAIL_ACCOUNT_ACCESS_JSON || '';
const MAIL_CONTACTS_JSON = process.env.MAIL_CONTACTS_JSON || '';
const MAIL_DEFAULT_ACCOUNT = normalizeMailIdentity(process.env.MAIL_DEFAULT_ACCOUNT || '');
const MAIL_USER = String(process.env.MAIL_USER || '').trim().toLowerCase();
const MAIL_PASSWORD = String(process.env.MAIL_PASSWORD || '').trim();
const MAIL_FROM_NAME = String(process.env.MAIL_FROM_NAME || 'OpenLaw').trim() || 'OpenLaw';
const MAIL_IMAP_HOST = String(process.env.MAIL_IMAP_HOST || 'mail.geotracer.cc').trim() || 'mail.geotracer.cc';
const MAIL_IMAP_PORT = Math.max(1, Number(process.env.MAIL_IMAP_PORT || 993));
const MAIL_SMTP_HOST = String(process.env.MAIL_SMTP_HOST || 'mail.geotracer.cc').trim() || 'mail.geotracer.cc';
const MAIL_SMTP_PORT = Math.max(1, Number(process.env.MAIL_SMTP_PORT || 465));
const MAIL_TLS_SERVERNAME = String(process.env.MAIL_TLS_SERVERNAME || 'mail.geotracer.cc').trim();
const MAIL_MAX_JSON_BODY_BYTES = Math.max(
  5 * 1024 * 1024,
  Number(process.env.MAIL_MAX_JSON_BODY_BYTES || 25 * 1024 * 1024),
);
const MAIL_MAX_ATTACHMENTS = Math.max(1, Number(process.env.MAIL_MAX_ATTACHMENTS || 8));
const MAIL_MAX_TOTAL_ATTACHMENT_BYTES = Math.max(
  1 * 1024 * 1024,
  Number(process.env.MAIL_MAX_TOTAL_ATTACHMENT_BYTES || 12 * 1024 * 1024),
);
const MAIL_IMAP_CONNECTION_TIMEOUT_MS = Math.max(
  2_000,
  Number(process.env.MAIL_IMAP_CONNECTION_TIMEOUT_MS || 12_000),
);
const MAIL_IMAP_SOCKET_TIMEOUT_MS = Math.max(
  MAIL_IMAP_CONNECTION_TIMEOUT_MS,
  Number(process.env.MAIL_IMAP_SOCKET_TIMEOUT_MS || 20_000),
);
const MAIL_ACCOUNTS_STATS_TIMEOUT_MS = Math.max(
  2_000,
  Number(process.env.MAIL_ACCOUNTS_STATS_TIMEOUT_MS || 8_000),
);

let _ImapFlow = null;
let _nodemailer = null;
let _simpleParser = null;
let _MailComposer = null;
const lazyRequire = (name, fallback = '') => {
  try {
    return require(name);
  } catch (error) {
    if (fallback) return require(fallback);
    throw error;
  }
};
const _getImapFlow = () => {
  if (!_ImapFlow) _ImapFlow = lazyRequire('imapflow', '/app/node_modules/imapflow');
  return _ImapFlow.ImapFlow;
};
const _getNodemailer = () => {
  if (!_nodemailer) _nodemailer = lazyRequire('nodemailer', '/app/node_modules/nodemailer');
  return _nodemailer;
};
const _getSimpleParser = () => {
  if (!_simpleParser) {
    _simpleParser = lazyRequire('mailparser', '/app/node_modules/mailparser').simpleParser;
  }
  return _simpleParser;
};
const _getMailComposer = () => {
  if (!_MailComposer) {
    _MailComposer = lazyRequire(
      'nodemailer/lib/mail-composer',
      '/app/node_modules/nodemailer/lib/mail-composer',
    );
  }
  return _MailComposer;
};

const parseMailAccountsConfig = () => {
  const configured = [];
  const byKey = new Map();
  let usesLegacyFallback = false;

  const pushAccount = (rawAccount, fallbackKey = '') => {
    if (!rawAccount || typeof rawAccount !== 'object') return;
    const email = String(rawAccount.email || rawAccount.user || '').trim().toLowerCase();
    const password = String(rawAccount.password || rawAccount.pass || '').trim();
    const key = normalizeMailIdentity(rawAccount.key || email.split('@')[0] || fallbackKey);
    if (!key || !email || !password || byKey.has(key)) return;
    const localPart = email.split('@')[0] || key;
    const label =
      String(rawAccount.label || rawAccount.name || titleCaseMailLabel(localPart)).trim() ||
      titleCaseMailLabel(localPart);
    const fromName =
      String(rawAccount.fromName || rawAccount.from || label || MAIL_FROM_NAME).trim() ||
      MAIL_FROM_NAME;
    const signatureHtml = String(rawAccount.signatureHtml || '').trim();
    const signatureText = String(rawAccount.signatureText || '').trim();
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
      label,
      fromName,
      signatureHtml,
      signatureText,
      aliases,
      matchIdentities: Array.from(matchIdentities),
    };
    configured.push(account);
    byKey.set(key, account);
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

  if (!configured.length && MAIL_USER && MAIL_PASSWORD) {
    usesLegacyFallback = true;
    pushAccount(
      {
        key: MAIL_USER.split('@')[0] || 'primary',
        email: MAIL_USER,
        password: MAIL_PASSWORD,
        fromName: MAIL_FROM_NAME,
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
        .filter((entry) => entry && byKey.has(entry));
      if (!grantedKeys.length) continue;
      for (const identity of getMailIdentityVariants(identityRaw)) {
        const existing = accessMap.get(identity) || new Set();
        for (const grantedKey of grantedKeys) existing.add(grantedKey);
        accessMap.set(identity, existing);
      }
    }
  }

  return {
    accountsByKey: byKey,
    accessMap,
    hasAnyConfiguredAccounts: configured.length > 0,
    orderedAccounts: configured,
    usesLegacyFallback,
  };
};

const MAIL_CONFIG = parseMailAccountsConfig();
const MAIL_PRIMARY_ACCOUNT = MAIL_CONFIG.orderedAccounts[0] || null;

const getSessionMailIdentities = (sessionInfo) => {
  const identities = new Set();
  const values = [
    sessionInfo?.email,
    sessionInfo?.user?.email,
    sessionInfo?.user?.primaryEmail,
  ];
  for (const value of values) {
    for (const variant of getMailIdentityVariants(value)) identities.add(variant);
  }
  return Array.from(identities);
};

const getAccessibleMailAccounts = (sessionInfo) => {
  const identities = getSessionMailIdentities(sessionInfo);
  if (!MAIL_CONFIG.hasAnyConfiguredAccounts) {
    return { accounts: [], defaultAccountKey: '', identities };
  }
  if (MAIL_CONFIG.usesLegacyFallback && MAIL_CONFIG.orderedAccounts.length === 1) {
    return {
      accounts: MAIL_CONFIG.orderedAccounts,
      defaultAccountKey: MAIL_CONFIG.orderedAccounts[0].key,
      identities,
    };
  }

  const grantedKeys = new Set();
  for (const identity of identities) {
    const explicitAccess = MAIL_CONFIG.accessMap.get(identity);
    if (explicitAccess) {
      for (const key of explicitAccess) grantedKeys.add(key);
    }
  }
  for (const account of MAIL_CONFIG.orderedAccounts) {
    if (account.matchIdentities.some((identity) => identities.includes(identity))) {
      grantedKeys.add(account.key);
    }
  }

  const accounts = MAIL_CONFIG.orderedAccounts.filter((account) => grantedKeys.has(account.key));
  let defaultAccountKey = '';
  const directMatch = MAIL_CONFIG.orderedAccounts.find(
    (account) =>
      grantedKeys.has(account.key) &&
      account.matchIdentities.some((identity) => identities.includes(identity)),
  );
  if (directMatch?.key) defaultAccountKey = directMatch.key;
  else if (MAIL_DEFAULT_ACCOUNT && grantedKeys.has(MAIL_DEFAULT_ACCOUNT)) defaultAccountKey = MAIL_DEFAULT_ACCOUNT;
  else defaultAccountKey = accounts[0]?.key || '';

  return { accounts, defaultAccountKey, identities };
};

const resolveMailAccountForSession = (sessionInfo, requestedAccountKey = '') => {
  const access = getAccessibleMailAccounts(sessionInfo);
  if (!MAIL_CONFIG.hasAnyConfiguredAccounts) {
    return { ok: false, code: 'NOT_CONFIGURED', statusCode: 503 };
  }
  if (!access.accounts.length) {
    return { ok: false, code: 'NO_MAIL_ACCESS', statusCode: 403 };
  }
  const key = normalizeMailIdentity(requestedAccountKey) || access.defaultAccountKey;
  const account = access.accounts.find((entry) => entry.key === key);
  if (!account) {
    return { ok: false, code: 'MAIL_ACCOUNT_FORBIDDEN', statusCode: 403 };
  }
  return { ok: true, ...access, account };
};

const MAIL_CONTACT_ADDRESS_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const normalizeMailContactEmail = (value = '') => {
  const email = String(value || '').trim().toLowerCase();
  return MAIL_CONTACT_ADDRESS_RE.test(email) ? email : '';
};
const buildMailPublicContact = (raw = {}, { source = 'configured', favorite = false } = {}) => {
  if (!raw || typeof raw !== 'object') return null;
  const email = normalizeMailContactEmail(raw.email || raw.address || raw.mail || '');
  if (!email) return null;
  const key = normalizeMailIdentity(raw.key || email) || email;
  const label =
    String(raw.label || raw.name || titleCaseMailLabel(email.split('@')[0] || email)).trim() ||
    email;
  const aliases = (Array.isArray(raw.aliases) ? raw.aliases : [])
    .map((entry) => String(entry || '').trim())
    .filter(Boolean);
  return {
    key,
    label,
    email,
    aliases,
    favorite: Boolean(raw.favorite ?? favorite),
    source,
    searchText: [label, email, key].concat(aliases).join(' ').toLowerCase(),
  };
};
const buildMailContactDirectory = (sessionInfo, access = null) => {
  const resolvedAccess = access || getAccessibleMailAccounts(sessionInfo);
  const contactsByEmail = new Map();

  const upsert = (contact, options) => {
    const next = buildMailPublicContact(contact, options);
    if (!next) return;
    const existing = contactsByEmail.get(next.email);
    if (existing) {
      existing.favorite = Boolean(existing.favorite || next.favorite);
      existing.aliases = Array.from(new Set([...(existing.aliases || []), ...(next.aliases || [])]));
      existing.searchText = [existing.label, existing.email, existing.key]
        .concat(existing.aliases)
        .join(' ')
        .toLowerCase();
      return;
    }
    contactsByEmail.set(next.email, next);
  };

  MAIL_CONFIG.orderedAccounts.forEach((account) =>
    upsert(
      {
        key: account.key,
        label: account.label,
        email: account.email,
        aliases: account.aliases,
      },
      { source: 'internal' },
    ),
  );

  const parsed = parseJsonValue(MAIL_CONTACTS_JSON, null);
  if (Array.isArray(parsed)) {
    parsed.forEach((entry) => upsert(entry, { source: 'configured' }));
  } else if (parsed && typeof parsed === 'object') {
    if (Array.isArray(parsed.contacts)) {
      parsed.contacts.forEach((entry) => upsert(entry, { source: 'configured' }));
    } else {
      for (const [key, value] of Object.entries(parsed)) {
        if (value && typeof value === 'object' && !Array.isArray(value)) {
          upsert({ key, ...value }, { source: 'configured' });
        }
      }
    }
  }

  const sessionIdentitySet = new Set(resolvedAccess.identities || []);
  const accessibleAccountKeys = new Set((resolvedAccess.accounts || []).map((account) => account.key));
  const contacts = Array.from(contactsByEmail.values())
    .map((entry) => ({
      ...entry,
      favorite:
        Boolean(entry.favorite) ||
        accessibleAccountKeys.has(entry.key) ||
        sessionIdentitySet.has(entry.email) ||
        sessionIdentitySet.has(entry.key),
    }))
    .sort((left, right) => {
      if (Boolean(left.favorite) !== Boolean(right.favorite)) return left.favorite ? -1 : 1;
      return left.label.localeCompare(right.label, 'de');
    })
    .map(({ searchText, ...entry }) => entry);
  return { contacts, groups: [] };
};

const withTimeout = (promise, timeoutMs, message = 'Operation timed out') => {
  let timer = null;
  const timeoutPromise = new Promise((_, reject) => {
    timer = setTimeout(() => {
      const error = new Error(message);
      error.code = 'TIMEOUT';
      reject(error);
    }, timeoutMs);
  });
  return Promise.race([
    Promise.resolve(promise).finally(() => {
      if (timer) clearTimeout(timer);
    }),
    timeoutPromise,
  ]).finally(() => {
    if (timer) clearTimeout(timer);
  });
};

const _mailImapCache = new Map();
const _mailTransportCache = new Map();
const MAIL_IMAP_TTL = 45_000;

const touchMailImap = (accountKey) => {
  const cached = _mailImapCache.get(accountKey);
  if (cached) cached.ts = Date.now();
};
const resetMailImap = (accountKey = '') => {
  if (accountKey) {
    const cached = _mailImapCache.get(accountKey);
    try {
      if (cached?.client) cached.client.logout().catch(() => {});
    } catch {}
    _mailImapCache.delete(accountKey);
    return;
  }
  for (const [key, cached] of _mailImapCache.entries()) {
    try {
      if (cached?.client) cached.client.logout().catch(() => {});
    } catch {}
    _mailImapCache.delete(key);
  }
};

async function getMailImap(account) {
  if (!account || !account.key) throw new Error('Mail account missing');
  const now = Date.now();
  const cached = _mailImapCache.get(account.key);
  if (cached?.client && cached.client.usable && now - cached.ts < MAIL_IMAP_TTL) {
    cached.ts = now;
    return cached.client;
  }
  if (cached?.client) {
    try {
      await cached.client.logout();
    } catch {}
    _mailImapCache.delete(account.key);
  }
  const client = new (_getImapFlow())({
    host: MAIL_IMAP_HOST,
    port: MAIL_IMAP_PORT,
    secure: true,
    ...(MAIL_TLS_SERVERNAME ? { servername: MAIL_TLS_SERVERNAME } : {}),
    auth: { user: account.email, pass: account.password },
    logger: false,
    connectionTimeout: MAIL_IMAP_CONNECTION_TIMEOUT_MS,
    greetingTimeout: MAIL_IMAP_CONNECTION_TIMEOUT_MS,
    socketTimeout: MAIL_IMAP_SOCKET_TIMEOUT_MS,
    tls: { rejectUnauthorized: true },
  });
  await client.connect();
  _mailImapCache.set(account.key, { client, ts: now });
  return client;
}

function getMailTransport(account) {
  if (!account || !account.key) throw new Error('Mail account missing');
  if (!_mailTransportCache.has(account.key)) {
    _mailTransportCache.set(
      account.key,
      _getNodemailer().createTransport({
        host: MAIL_SMTP_HOST,
        port: MAIL_SMTP_PORT,
        secure: MAIL_SMTP_PORT === 465,
        auth: { user: account.email, pass: account.password },
        tls: {
          rejectUnauthorized: true,
          ...(MAIL_TLS_SERVERNAME ? { servername: MAIL_TLS_SERVERNAME } : {}),
        },
      }),
    );
  }
  return _mailTransportCache.get(account.key);
}

function resolveMailFolder(value) {
  const raw = String(value || 'INBOX').trim().toLowerCase();
  if (!raw || raw === 'inbox') return 'INBOX';
  if (raw === 'sent') return 'Sent';
  if (raw === 'drafts' || raw === 'draft') return 'Drafts';
  if (raw === 'trash') return 'Trash';
  return null;
}

function decodeMailPathSegment(value = '') {
  try {
    return decodeURIComponent(String(value || '').trim());
  } catch {
    return String(value || '').trim();
  }
}

function parseMailLatestRoute(pathname = '') {
  const parts = String(pathname || '')
    .split('/')
    .map((segment) => decodeMailPathSegment(segment))
    .filter(Boolean);
  if (parts.length !== 4) return null;
  if (parts[0] !== 'mail') return null;
  if (String(parts[3] || '').trim().toLowerCase() !== 'latest') return null;
  return {
    accountKey: normalizeMailIdentity(parts[1] || ''),
    folder: resolveMailFolder(parts[2] || ''),
  };
}

function findConfiguredMailAccount(requestedAccountKey = '') {
  const normalized = normalizeMailIdentity(requestedAccountKey);
  if (!normalized) return null;
  return (
    MAIL_CONFIG.accountsByKey.get(normalized) ||
    MAIL_CONFIG.orderedAccounts.find((account) =>
      Array.isArray(account.matchIdentities) && account.matchIdentities.includes(normalized),
    ) ||
    null
  );
}

function safeMailSecretEquals(left = '', right = '') {
  const leftBuffer = Buffer.from(String(left || ''), 'utf8');
  const rightBuffer = Buffer.from(String(right || ''), 'utf8');
  if (leftBuffer.length !== rightBuffer.length) return false;
  return crypto.timingSafeEqual(leftBuffer, rightBuffer);
}

function parseMailBasicAuthCredentials(req) {
  const authorization = String(req?.headers?.authorization || '').trim();
  if (!/^Basic\s+/i.test(authorization)) return null;
  const encoded = authorization.replace(/^Basic\s+/i, '').trim();
  if (!encoded) return null;
  try {
    const decoded = Buffer.from(encoded, 'base64').toString('utf8');
    const separator = decoded.indexOf(':');
    if (separator < 0) return null;
    return {
      username: decoded.slice(0, separator),
      password: decoded.slice(separator + 1),
    };
  } catch {
    return null;
  }
}

function resolveMailPasswordProtectedRoute(req, requestedAccountKey = '') {
  const account = findConfiguredMailAccount(requestedAccountKey);
  if (!account) {
    return { ok: false, code: 'MAIL_ACCOUNT_FORBIDDEN', statusCode: 403 };
  }
  const credentials = parseMailBasicAuthCredentials(req);
  if (!credentials) {
    return { ok: false, code: 'MAIL_PASSWORD_REQUIRED', statusCode: 401 };
  }
  const usernameVariants = new Set(getMailIdentityVariants(credentials.username));
  if (!usernameVariants.size) {
    return { ok: false, code: 'MAIL_PASSWORD_REQUIRED', statusCode: 401 };
  }
  const usernameMatches = account.matchIdentities.some((identity) => usernameVariants.has(identity));
  if (!usernameMatches || !safeMailSecretEquals(credentials.password, account.password)) {
    return { ok: false, code: 'MAIL_PASSWORD_INVALID', statusCode: 401 };
  }
  return { ok: true, account, authMode: 'password' };
}

function sanitizeMailAttachmentName(value) {
  const base = path.basename(String(value || '').replace(/[\0\r\n]+/g, '').trim());
  const safe = base.replace(/[<>:"/\\|?*]+/g, '_').trim();
  return (safe || 'attachment').slice(0, 180);
}

function normalizeOutgoingMailPriority(value = '') {
  const raw = String(value || '').trim().toLowerCase();
  if (raw === 'high' || raw === 'hoch') return 'high';
  if (raw === 'low' || raw === 'niedrig') return 'low';
  return 'normal';
}

function buildOutgoingMailHeaders({ account = null, priority = 'normal' } = {}) {
  const normalizedPriority = normalizeOutgoingMailPriority(priority);
  const headers = {};
  if (normalizedPriority === 'high') {
    headers['X-Priority'] = '1 (Highest)';
    headers.Importance = 'High';
    headers.Priority = 'urgent';
  } else if (normalizedPriority === 'low') {
    headers['X-Priority'] = '5 (Lowest)';
    headers.Importance = 'Low';
    headers.Priority = 'non-urgent';
  }
  if (account?.email) {
    headers['X-OpenLaw-Mailbox'] = account.email;
  }
  return headers;
}

const MAIL_ADDRESS_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function parseMailAddressList(value, fieldName = 'recipient') {
  const rawItems = Array.isArray(value) ? value : [String(value || '')];
  const seen = new Set();
  const addresses = [];
  for (const item of rawItems) {
    const raw = String(item || '').trim();
    const matches = raw.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi) || [];
    if (!matches.length && raw) {
      const error = new Error(`Invalid ${fieldName} address: ${raw}`);
      error.code = `INVALID_${String(fieldName || 'recipient').toUpperCase()}`;
      error.statusCode = 400;
      throw error;
    }
    for (const match of matches) {
      const address = String(match || '').trim().toLowerCase();
      if (!address) continue;
      if (!MAIL_ADDRESS_RE.test(address)) {
        const error = new Error(`Invalid ${fieldName} address: ${address}`);
        error.code = `INVALID_${String(fieldName || 'recipient').toUpperCase()}`;
        error.statusCode = 400;
        throw error;
      }
      if (seen.has(address)) continue;
      seen.add(address);
      addresses.push(address);
    }
  }
  return addresses;
}

function sanitizeOutgoingMailHtml(value = '') {
  let html = String(value || '').trim();
  if (!html) return '';
  html = html.replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, '');
  html = html.replace(/\son[a-z]+\s*=\s*(["'])[\s\S]*?\1/gi, '');
  html = html.replace(/\son[a-z]+\s*=\s*[^\s>]+/gi, '');
  html = html.replace(/\s(href|src)\s*=\s*(["'])\s*javascript:[\s\S]*?\2/gi, ' $1="#"');
  return html.trim();
}

function escapeHtmlForMail(value = '') {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function decodeBasicMailEntities(value = '') {
  return String(value || '')
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/&quot;/gi, '"')
    .replace(/&#39;/gi, "'");
}

function convertOutgoingHtmlToText(value = '') {
  const html = sanitizeOutgoingMailHtml(value);
  if (!html) return '';
  return decodeBasicMailEntities(
    html
      .replace(/<\s*br\s*\/?>/gi, '\n')
      .replace(/<\/p>/gi, '\n\n')
      .replace(/<\/div>/gi, '\n')
      .replace(/<\/li>/gi, '\n')
      .replace(/<li\b[^>]*>/gi, '- ')
      .replace(/<\/blockquote>/gi, '\n\n')
      .replace(/<blockquote\b[^>]*>/gi, '\n> ')
      .replace(/<[^>]+>/g, ' ')
      .replace(/\r/g, '')
      .replace(/\n{3,}/g, '\n\n')
      .replace(/[ \t]+\n/g, '\n')
      .replace(/\n[ \t]+/g, '\n')
      .replace(/[ \t]{2,}/g, ' ')
      .trim(),
  );
}

function convertPlainTextToHtml(value = '') {
  const text = String(value || '').replace(/\r/g, '').trim();
  if (!text) return '';
  return text
    .split(/\n{2,}/)
    .map((paragraph) => `<p>${escapeHtmlForMail(paragraph).replace(/\n/g, '<br>')}</p>`)
    .join('');
}

function appendMailSignatureHtml(html = '', signatureHtml = '') {
  const base = sanitizeOutgoingMailHtml(html);
  const signature = sanitizeOutgoingMailHtml(signatureHtml);
  if (!signature) return base;
  if (!base) return signature;
  return `${base}<hr style="border:none;border-top:1px solid #d7dbe5;margin:18px 0;">${signature}`;
}

function appendMailSignatureText(text = '', signatureText = '') {
  const base = String(text || '').trimEnd();
  const signature = String(signatureText || '').trim();
  if (!signature) return base;
  if (!base) return signature;
  return `${base}\n\n-- \n${signature}`;
}

function hasMeaningfulOutgoingBody({ text = '', html = '' } = {}) {
  if (String(text || '').trim()) return true;
  return Boolean(convertOutgoingHtmlToText(html).trim());
}

function resolveOutgoingMailContent(body = {}, account = null) {
  const rawHtml = sanitizeOutgoingMailHtml(body.html || '');
  const rawText = String(body.text || '');
  const useSignature = body.useSignature !== false;
  const accountSignatureHtml = sanitizeOutgoingMailHtml(account?.signatureHtml || '');
  const accountSignatureText =
    String(account?.signatureText || '').trim() ||
    convertOutgoingHtmlToText(accountSignatureHtml);
  let html = rawHtml;
  let text = rawText;
  if (!html && text.trim()) html = convertPlainTextToHtml(text);
  if (!text.trim() && html) text = convertOutgoingHtmlToText(html);
  if (useSignature) {
    if (accountSignatureHtml) html = appendMailSignatureHtml(html, accountSignatureHtml);
    if (accountSignatureText) text = appendMailSignatureText(text, accountSignatureText);
  }
  return {
    html: sanitizeOutgoingMailHtml(html),
    text: String(text || '').trim(),
  };
}

function normalizeOutgoingMailAttachments(input) {
  const rawAttachments = Array.isArray(input) ? input : [];
  if (!rawAttachments.length) return [];
  const attachments = [];
  for (const entry of rawAttachments) {
    if (!entry || typeof entry !== 'object') {
      const error = new Error('Invalid attachment payload');
      error.code = 'INVALID_ATTACHMENTS';
      error.statusCode = 400;
      throw error;
    }
    const filename = sanitizeMailAttachmentName(entry.name || entry.filename || '');
    const base64 = String(entry.contentBase64 || entry.content || '').trim();
    if (!base64) {
      const error = new Error(`Attachment "${filename}" is empty`);
      error.code = 'INVALID_ATTACHMENTS';
      error.statusCode = 400;
      throw error;
    }
    const buffer = Buffer.from(base64, 'base64');
    if (!buffer.length) {
      const error = new Error(`Attachment "${filename}" is invalid`);
      error.code = 'INVALID_ATTACHMENTS';
      error.statusCode = 400;
      throw error;
    }
    const contentType = String(entry.contentType || entry.type || '').trim();
    attachments.push({
      filename,
      content: buffer,
      ...(contentType ? { contentType } : {}),
    });
  }
  return enforceOutgoingAttachmentLimits(attachments);
}

function enforceOutgoingAttachmentLimits(attachments = []) {
  const normalized = Array.isArray(attachments) ? attachments.filter(Boolean) : [];
  if (!normalized.length) return [];
  if (normalized.length > MAIL_MAX_ATTACHMENTS) {
    const error = new Error(`Too many attachments (max ${MAIL_MAX_ATTACHMENTS})`);
    error.code = 'INVALID_ATTACHMENTS';
    error.statusCode = 400;
    throw error;
  }
  let totalBytes = 0;
  for (const attachment of normalized) {
    const size = Number(
      attachment?.size ||
        (Buffer.isBuffer(attachment?.content) ? attachment.content.length : 0) ||
        0,
    );
    totalBytes += size;
    if (totalBytes > MAIL_MAX_TOTAL_ATTACHMENT_BYTES) {
      const error = new Error(
        `Attachment payload exceeds ${Math.round(MAIL_MAX_TOTAL_ATTACHMENT_BYTES / (1024 * 1024))} MB`,
      );
      error.code = 'ATTACHMENTS_TOO_LARGE';
      error.statusCode = 413;
      throw error;
    }
  }
  return normalized;
}

function extractForwardedMailAttachments(parsedAttachments, requestedIndices) {
  const available = Array.isArray(parsedAttachments) ? parsedAttachments : [];
  if (!available.length) return [];

  let indices = [];
  if (Array.isArray(requestedIndices)) {
    const seen = new Set();
    for (const entry of requestedIndices) {
      const index = Number(entry);
      if (!Number.isInteger(index) || index < 0) {
        const error = new Error('Invalid forwarded attachment selection');
        error.code = 'INVALID_ATTACHMENTS';
        error.statusCode = 400;
        throw error;
      }
      if (seen.has(index)) continue;
      seen.add(index);
      indices.push(index);
    }
  } else {
    indices = available.map((_, index) => index);
  }

  const attachments = [];
  for (const index of indices) {
    const attachment = available[index];
    if (!attachment || !Buffer.isBuffer(attachment.content)) {
      const error = new Error('Forwarded attachment not found');
      error.code = 'INVALID_ATTACHMENTS';
      error.statusCode = 400;
      throw error;
    }
    attachments.push({
      filename: sanitizeMailAttachmentName(attachment.filename || `attachment-${index + 1}`),
      content: Buffer.from(attachment.content),
      ...(attachment.contentType ? { contentType: String(attachment.contentType) } : {}),
    });
  }
  return enforceOutgoingAttachmentLimits(attachments);
}

function summarizeParsedMailAttachments(attachments = []) {
  return (Array.isArray(attachments) ? attachments : []).map((attachment, index) => {
    const filename = sanitizeMailAttachmentName(attachment?.filename || `attachment-${index + 1}`);
    const size = Number(
      attachment?.size ||
        (Buffer.isBuffer(attachment?.content) ? attachment.content.length : 0) ||
        0,
    );
    return {
      filename,
      contentType: String(attachment?.contentType || 'application/octet-stream'),
      size,
    };
  });
}

function buildAttachmentContentDisposition(filename) {
  const safeFilename = sanitizeMailAttachmentName(filename);
  return `attachment; filename="${safeFilename}"; filename*=UTF-8''${encodeURIComponent(safeFilename)}`;
}

function getMailMessageIdDomain(account) {
  const fallback = 'openlaw.cc';
  const domain = String(account?.email || MAIL_PRIMARY_ACCOUNT?.email || '').split('@')[1] || fallback;
  return domain.replace(/[^a-z0-9.-]/gi, '') || fallback;
}

const readRequestBody = (req, maxBytes = 5 * 1024 * 1024) =>
  new Promise((resolve, reject) => {
    let total = 0;
    const chunks = [];
    req.on('data', (chunk) => {
      total += chunk.length;
      if (total > maxBytes) {
        const error = new Error('Request body too large');
        error.code = 'BODY_TOO_LARGE';
        error.statusCode = 413;
        reject(error);
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on('end', () => resolve(Buffer.concat(chunks)));
    req.on('error', reject);
  });

const readJsonRequestBody = async (req, maxBytes = 5 * 1024 * 1024) => {
  const raw = await readRequestBody(req, maxBytes);
  if (!raw || raw.length === 0) return {};
  try {
    return JSON.parse(raw.toString('utf8'));
  } catch {
    const error = new Error('Invalid JSON');
    error.code = 'INVALID_JSON';
    error.statusCode = 400;
    throw error;
  }
};

async function fetchParsedMailboxMessage(account, folder, uid) {
  const client = await getMailImap(account);
  const lock = await client.getMailboxLock(folder);
  try {
    for await (const msg of client.fetch(
      String(uid),
      {
        uid: true,
        envelope: true,
        flags: true,
        source: true,
      },
      { uid: true },
    )) {
      const parsed = await _getSimpleParser()(msg.source);
      touchMailImap(account.key);
      return { msg, parsed };
    }
  } finally {
    lock.release();
  }
  touchMailImap(account.key);
  return null;
}

async function fetchLatestMailboxUid(account, folder) {
  const client = await getMailImap(account);
  const lock = await client.getMailboxLock(folder);
  try {
    let latestUid = 0;
    for await (const msg of client.fetch('1:*', { uid: true }, { uid: true })) {
      if (Number(msg.uid || 0) > latestUid) latestUid = Number(msg.uid || 0);
    }
    touchMailImap(account.key);
    return latestUid || null;
  } finally {
    lock.release();
  }
}

function buildRawMailMessage(mailOpts) {
  return new Promise((resolve, reject) => {
    new (_getMailComposer())(mailOpts).compile().build((error, message) => {
      if (error) reject(error);
      else resolve(message);
    });
  });
}

async function appendMailToFolder(account, folder, mailOpts, { flags = ['\\Seen'] } = {}) {
  const client = await getMailImap(account);
  touchMailImap(account.key);
  try {
    await client.mailboxCreate(folder);
  } catch {}
  const rawMessage = await buildRawMailMessage(mailOpts);
  await client.append(folder, rawMessage, flags, mailOpts.date || new Date());
  touchMailImap(account.key);
}

async function deleteMailMessage(account, folder, uid) {
  const client = await getMailImap(account);
  const lock = await client.getMailboxLock(folder);
  try {
    if (folder === 'Trash' || folder === 'Drafts') {
      await client.messageFlagsAdd({ uid }, ['\\Deleted'], { uid: true });
      await client.messageDelete({ uid }, { uid: true });
      return;
    }
    try {
      await client.messageMove({ uid }, 'Trash', { uid: true });
    } catch {
      await client.messageFlagsAdd({ uid }, ['\\Deleted'], { uid: true });
      await client.messageDelete({ uid }, { uid: true });
    }
  } finally {
    lock.release();
  }
  touchMailImap(account.key);
}

async function getMailInboxStatus(account) {
  const client = await getMailImap(account);
  const lock = await client.getMailboxLock('INBOX');
  try {
    const status = await client.status('INBOX', { messages: true, unseen: true });
    touchMailImap(account.key);
    return {
      total: Number(status.messages || 0),
      unread: Number(status.unseen || 0),
    };
  } finally {
    lock.release();
  }
}

const sendMailJsonError = (res, statusCode, error, code) => {
  res.writeHead(statusCode, { 'content-type': 'application/json' });
  res.end(JSON.stringify({ ok: false, error, code }));
};

const sendMailPasswordAuthChallenge = (res, requestedAccountKey = '') => {
  const realmSuffix = normalizeMailIdentity(requestedAccountKey) || 'mailbox';
  res.writeHead(401, {
    'cache-control': 'no-store',
    'content-type': 'application/json; charset=utf-8',
    'www-authenticate': `Basic realm="OpenLaw Mail ${realmSuffix}", charset="UTF-8"`,
  });
  res.end(
    JSON.stringify({
      ok: false,
      error: 'Mailbox password required',
      code: 'MAIL_PASSWORD_REQUIRED',
    }),
  );
};

const requestPrefersHtmlNavigation = (req) => {
  const accept = String(req?.headers?.accept || '').toLowerCase();
  return accept.includes('text/html');
};

const serveMailHtml = (res) => {
  try {
    const html = fs.readFileSync(LOCAL_MAIL_HTML_PATH, 'utf8');
    res.writeHead(200, { 'cache-control': 'no-cache', 'content-type': 'text/html; charset=utf-8' });
    res.end(html);
  } catch {
    res.writeHead(500, { 'content-type': 'text/plain; charset=utf-8' });
    res.end('mail.html not found');
  }
};

const buildMailMessageResponse = (msg, parsed, accountKey) => ({
  accountKey,
  attachments: summarizeParsedMailAttachments(parsed.attachments),
  bcc: parsed.bcc?.value || [],
  cc: parsed.cc?.value || [],
  date: parsed.date?.toISOString() || msg.envelope?.date?.toISOString() || null,
  from: parsed.from?.value?.[0] || msg.envelope?.from?.[0] || null,
  htmlBody: typeof parsed.html === 'string' ? parsed.html : '',
  messageId: parsed.messageId || '',
  seen: msg.flags.has('\\Seen'),
  subject: parsed.subject || msg.envelope?.subject || '(kein Betreff)',
  textBody: parsed.text || '',
  to: parsed.to?.value || [],
  uid: msg.uid,
});

async function maybeHandleMailRequest(req, res, { publicOrigin, validateSessionViaAuthJs }) {
  if (!MAIL_ENABLED) return false;
  const parsedUrl = new URL(req.url, publicOrigin);
  if (!(parsedUrl.pathname === '/mail' || parsedUrl.pathname.startsWith('/mail/'))) {
    return false;
  }
  const latestRoute = parseMailLatestRoute(parsedUrl.pathname);
  const passwordProtectedRoute = latestRoute
    ? resolveMailPasswordProtectedRoute(req, latestRoute.accountKey)
    : null;
  const sessionInfo = passwordProtectedRoute?.ok ? null : await validateSessionViaAuthJs(req);
  if (!sessionInfo && !passwordProtectedRoute?.ok) {
    if (latestRoute) {
      const hasAuthorizationHeader = Boolean(String(req?.headers?.authorization || '').trim());
      if (passwordProtectedRoute?.code === 'MAIL_ACCOUNT_FORBIDDEN') {
        sendMailJsonError(res, 403, 'Mailbox not allowed for this route', 'MAIL_ACCOUNT_FORBIDDEN');
      } else if (!hasAuthorizationHeader && requestPrefersHtmlNavigation(req)) {
        const callbackUrl = `${publicOrigin}${req.url}`;
        res.writeHead(302, {
          'cache-control': 'no-store',
          location: `/login?callbackUrl=${encodeURIComponent(callbackUrl)}`,
        });
        res.end();
      } else {
        sendMailPasswordAuthChallenge(res, latestRoute.accountKey);
      }
    } else if (parsedUrl.pathname.startsWith('/mail/api/')) {
      sendMailJsonError(res, 401, 'Not authenticated', 'AUTH_REQUIRED');
    } else {
      const callbackUrl = `${publicOrigin}${req.url}`;
      res.writeHead(302, {
        'cache-control': 'no-store',
        location: `/login?callbackUrl=${encodeURIComponent(callbackUrl)}`,
      });
      res.end();
    }
    return true;
  }

  const resolveRequestedMailAccountOrReply = (requestedAccountKey = '') => {
    const resolved = resolveMailAccountForSession(sessionInfo, requestedAccountKey);
    if (resolved.ok) return resolved;
    if (resolved.code === 'NOT_CONFIGURED') {
      sendMailJsonError(res, 503, 'Mail not configured', 'NOT_CONFIGURED');
      return null;
    }
    if (resolved.code === 'NO_MAIL_ACCESS') {
      sendMailJsonError(res, 403, 'No mailbox access for this user', 'NO_MAIL_ACCESS');
      return null;
    }
    sendMailJsonError(res, 403, 'Mailbox not allowed for this user', 'MAIL_ACCOUNT_FORBIDDEN');
    return null;
  };

  if (req.method === 'GET' && latestRoute) {
    if (!latestRoute.accountKey) {
      sendMailJsonError(res, 400, 'Invalid mailbox', 'INVALID_ACCOUNT');
      return true;
    }
    if (!latestRoute.folder) {
      sendMailJsonError(res, 400, 'Invalid folder', 'INVALID_FOLDER');
      return true;
    }
    const account = passwordProtectedRoute?.ok
      ? passwordProtectedRoute.account
      : resolveRequestedMailAccountOrReply(latestRoute.accountKey)?.account;
    if (!account) return true;
    try {
      const latestUid = await fetchLatestMailboxUid(account, latestRoute.folder);
      if (!latestUid) {
        sendMailJsonError(res, 404, 'No message found', 'NOT_FOUND');
        return true;
      }
      const fetched = await fetchParsedMailboxMessage(account, latestRoute.folder, latestUid);
      if (!fetched) {
        sendMailJsonError(res, 404, 'Message not found', 'NOT_FOUND');
        return true;
      }
      res.writeHead(200, {
        'cache-control': 'private, no-store',
        'content-type': 'application/json; charset=utf-8',
      });
      res.end(
        JSON.stringify({
          ok: true,
          data: {
            accessMode: passwordProtectedRoute?.ok ? passwordProtectedRoute.authMode : 'session',
            accountKey: account.key,
            folder: latestRoute.folder,
            message: buildMailMessageResponse(fetched.msg, fetched.parsed, account.key),
          },
        }),
      );
    } catch (error) {
      resetMailImap(account.key);
      sendMailJsonError(res, 500, `IMAP: ${error.message}`, 'IMAP_ERROR');
    }
    return true;
  }

  if (
    req.method === 'GET' &&
    (parsedUrl.pathname === '/mail' ||
      (parsedUrl.pathname.startsWith('/mail/') && !parsedUrl.pathname.startsWith('/mail/api/')))
  ) {
    serveMailHtml(res);
    return true;
  }

  if (req.method === 'GET' && parsedUrl.pathname === '/mail/api/accounts') {
    const access = getAccessibleMailAccounts(sessionInfo);
    if (!MAIL_CONFIG.hasAnyConfiguredAccounts) {
      sendMailJsonError(res, 503, 'Mail not configured', 'NOT_CONFIGURED');
      return true;
    }
    if (!access.accounts.length) {
      sendMailJsonError(res, 403, 'No mailbox access for this user', 'NO_MAIL_ACCESS');
      return true;
    }
    try {
      const summaries = await Promise.all(
        access.accounts.map(async (account) => {
          let inboxTotal = null;
          let unread = null;
          let status = 'ok';
          try {
            const stats = await withTimeout(
              getMailInboxStatus(account),
              MAIL_ACCOUNTS_STATS_TIMEOUT_MS,
              `Mailbox ${account.email} timed out`,
            );
            inboxTotal = stats.total;
            unread = stats.unread;
          } catch (error) {
            status = 'error';
            resetMailImap(account.key);
            console.error(`[mail] inbox status failed for ${account.email}: ${error.message}`);
          }
          return {
            email: account.email,
            fromName: account.fromName,
            hasSignature: Boolean(account.signatureHtml || account.signatureText),
            inboxTotal,
            key: account.key,
            label: account.label,
            status,
            unread,
          };
        }),
      );
      res.writeHead(200, { 'cache-control': 'no-store', 'content-type': 'application/json' });
      res.end(
        JSON.stringify({
          ok: true,
          data: {
            accounts: summaries,
            defaultAccountKey: access.defaultAccountKey,
            limits: {
              maxAttachments: MAIL_MAX_ATTACHMENTS,
              maxJsonBodyBytes: MAIL_MAX_JSON_BODY_BYTES,
              maxTotalAttachmentBytes: MAIL_MAX_TOTAL_ATTACHMENT_BYTES,
            },
          },
        }),
      );
    } catch (error) {
      sendMailJsonError(res, 500, `IMAP: ${error.message}`, 'IMAP_ERROR');
    }
    return true;
  }

  if (req.method === 'GET' && parsedUrl.pathname === '/mail/api/contacts') {
    const access = getAccessibleMailAccounts(sessionInfo);
    if (!MAIL_CONFIG.hasAnyConfiguredAccounts) {
      sendMailJsonError(res, 503, 'Mail not configured', 'NOT_CONFIGURED');
      return true;
    }
    if (!access.accounts.length) {
      sendMailJsonError(res, 403, 'No mailbox access for this user', 'NO_MAIL_ACCESS');
      return true;
    }
    const directory = buildMailContactDirectory(sessionInfo, access);
    res.writeHead(200, { 'cache-control': 'no-store', 'content-type': 'application/json' });
    res.end(JSON.stringify({ ok: true, data: directory }));
    return true;
  }

  if (req.method === 'GET' && parsedUrl.pathname === '/mail/api/list') {
    const folder = resolveMailFolder(parsedUrl.searchParams.get('folder'));
    const limit = Math.max(1, Math.min(100, Number(parsedUrl.searchParams.get('limit') || 50)));
    if (!folder) {
      sendMailJsonError(res, 400, 'Invalid folder', 'INVALID_FOLDER');
      return true;
    }
    const resolved = resolveRequestedMailAccountOrReply(parsedUrl.searchParams.get('account'));
    if (!resolved) return true;
    try {
      const { account } = resolved;
      const client = await getMailImap(account);
      const lock = await client.getMailboxLock(folder);
      let messages = [];
      try {
        for await (const msg of client.fetch(
          '1:*',
          { uid: true, envelope: true, flags: true, size: true },
          { uid: true },
        )) {
          const env = msg.envelope || {};
          messages.push({
            uid: msg.uid,
            subject: env.subject || '(kein Betreff)',
            from: env.from?.[0] || null,
            to: env.to?.[0] || null,
            date: env.date ? env.date.toISOString() : null,
            seen: msg.flags.has('\\Seen'),
            size: msg.size,
          });
        }
      } finally {
        lock.release();
      }
      touchMailImap(account.key);
      messages = messages.sort((a, b) => b.uid - a.uid).slice(0, limit);
      res.writeHead(200, { 'content-type': 'application/json' });
      res.end(JSON.stringify({ ok: true, data: { accountKey: account.key, folder, messages, total: messages.length } }));
    } catch (error) {
      resetMailImap(resolved.account.key);
      sendMailJsonError(res, 500, `IMAP: ${error.message}`, 'IMAP_ERROR');
    }
    return true;
  }

  if (req.method === 'GET' && parsedUrl.pathname === '/mail/api/unread-count') {
    const requestedAccountKey = parsedUrl.searchParams.get('account');
    if (requestedAccountKey) {
      const resolved = resolveRequestedMailAccountOrReply(requestedAccountKey);
      if (!resolved) return true;
      try {
        const stats = await getMailInboxStatus(resolved.account);
        res.writeHead(200, { 'cache-control': 'no-store', 'content-type': 'application/json' });
        res.end(JSON.stringify({ ok: true, data: { accountKey: resolved.account.key, unread: stats.unread } }));
      } catch (error) {
        resetMailImap(resolved.account.key);
        sendMailJsonError(res, 500, `IMAP: ${error.message}`, 'IMAP_ERROR');
      }
      return true;
    }
    const access = getAccessibleMailAccounts(sessionInfo);
    if (!MAIL_CONFIG.hasAnyConfiguredAccounts) {
      sendMailJsonError(res, 503, 'Mail not configured', 'NOT_CONFIGURED');
      return true;
    }
    if (!access.accounts.length) {
      sendMailJsonError(res, 403, 'No mailbox access for this user', 'NO_MAIL_ACCESS');
      return true;
    }
    try {
      const perAccount = {};
      let unread = 0;
      for (const account of access.accounts) {
        try {
          const stats = await getMailInboxStatus(account);
          perAccount[account.key] = stats.unread;
          unread += stats.unread;
        } catch {
          perAccount[account.key] = null;
          resetMailImap(account.key);
        }
      }
      res.writeHead(200, { 'cache-control': 'no-store', 'content-type': 'application/json' });
      res.end(JSON.stringify({ ok: true, data: { unread, perAccount } }));
    } catch (error) {
      sendMailJsonError(res, 500, `IMAP: ${error.message}`, 'IMAP_ERROR');
    }
    return true;
  }

  if (req.method === 'GET' && parsedUrl.pathname === '/mail/api/message') {
    const uid = Number(parsedUrl.searchParams.get('uid'));
    const folder = resolveMailFolder(parsedUrl.searchParams.get('folder'));
    if (!uid) {
      sendMailJsonError(res, 400, 'Missing uid', 'INVALID_PARAM');
      return true;
    }
    if (!folder) {
      sendMailJsonError(res, 400, 'Invalid folder', 'INVALID_FOLDER');
      return true;
    }
    const resolved = resolveRequestedMailAccountOrReply(parsedUrl.searchParams.get('account'));
    if (!resolved) return true;
    try {
      const fetched = await fetchParsedMailboxMessage(resolved.account, folder, uid);
      if (!fetched) {
        sendMailJsonError(res, 404, 'Message not found', 'NOT_FOUND');
        return true;
      }
      res.writeHead(200, { 'content-type': 'application/json' });
      res.end(JSON.stringify({ ok: true, data: buildMailMessageResponse(fetched.msg, fetched.parsed, resolved.account.key) }));
    } catch (error) {
      resetMailImap(resolved.account.key);
      sendMailJsonError(res, 500, `IMAP: ${error.message}`, 'IMAP_ERROR');
    }
    return true;
  }

  if (req.method === 'GET' && parsedUrl.pathname === '/mail/api/attachment') {
    const uid = Number(parsedUrl.searchParams.get('uid'));
    const index = Number(parsedUrl.searchParams.get('index'));
    const folder = resolveMailFolder(parsedUrl.searchParams.get('folder'));
    const inline = isEnvTruthy(parsedUrl.searchParams.get('inline'));
    if (!uid || !Number.isInteger(index) || index < 0) {
      sendMailJsonError(res, 400, 'Invalid attachment request', 'INVALID_PARAM');
      return true;
    }
    if (!folder) {
      sendMailJsonError(res, 400, 'Invalid folder', 'INVALID_FOLDER');
      return true;
    }
    const resolved = resolveRequestedMailAccountOrReply(parsedUrl.searchParams.get('account'));
    if (!resolved) return true;
    try {
      const fetched = await fetchParsedMailboxMessage(resolved.account, folder, uid);
      if (!fetched) {
        sendMailJsonError(res, 404, 'Message not found', 'NOT_FOUND');
        return true;
      }
      const attachment = Array.isArray(fetched.parsed.attachments)
        ? fetched.parsed.attachments[index]
        : null;
      if (!attachment || !Buffer.isBuffer(attachment.content)) {
        sendMailJsonError(res, 404, 'Attachment not found', 'NOT_FOUND');
        return true;
      }
      const filename = sanitizeMailAttachmentName(attachment.filename || `attachment-${index + 1}`);
      res.writeHead(200, {
        'cache-control': 'private, no-store',
        'content-disposition': inline
          ? `inline; filename="${filename}"`
          : buildAttachmentContentDisposition(filename),
        'content-length': attachment.content.length,
        'content-type': String(attachment.contentType || 'application/octet-stream'),
      });
      res.end(attachment.content);
    } catch (error) {
      resetMailImap(resolved.account.key);
      sendMailJsonError(res, 500, `IMAP: ${error.message}`, 'IMAP_ERROR');
    }
    return true;
  }

  if (req.method === 'POST' && parsedUrl.pathname === '/mail/api/send') {
    try {
      const body = await readJsonRequestBody(req, MAIL_MAX_JSON_BODY_BYTES);
      const toList = parseMailAddressList(body.to, 'to');
      const ccList = parseMailAddressList(body.cc, 'cc');
      const bccList = parseMailAddressList(body.bcc, 'bcc');
      const subject = String(body.subject || '').trim();
      const rawText = String(body.text || '');
      const rawHtml = String(body.html || '');
      const priority = normalizeOutgoingMailPriority(body.priority);
      const attachments = normalizeOutgoingMailAttachments(body.attachments);
      if (!toList.length) {
        sendMailJsonError(res, 400, 'Invalid recipient', 'INVALID_TO');
        return true;
      }
      if (!subject) {
        sendMailJsonError(res, 400, 'Missing subject', 'INVALID_SUBJECT');
        return true;
      }
      if (!hasMeaningfulOutgoingBody({ text: rawText, html: rawHtml }) && !attachments.length) {
        sendMailJsonError(res, 400, 'Missing message body or attachments', 'INVALID_BODY');
        return true;
      }
      const resolved = resolveRequestedMailAccountOrReply(body.account);
      if (!resolved) return true;
      const account = resolved.account;
      const content = resolveOutgoingMailContent(body, account);
      const sentAt = new Date();
      const mailOpts = {
        from: `"${account.fromName}" <${account.email}>`,
        to: toList.join(', '),
        ...(ccList.length ? { cc: ccList.join(', ') } : {}),
        ...(bccList.length ? { bcc: bccList.join(', ') } : {}),
        ...(attachments.length ? { attachments } : {}),
        subject,
        text: content.text,
        ...(content.html ? { html: content.html } : {}),
        headers: buildOutgoingMailHeaders({ account, priority }),
        date: sentAt,
        messageId: `<${crypto.randomUUID()}@${getMailMessageIdDomain(account)}>`,
      };
      await getMailTransport(account).sendMail(mailOpts);
      try {
        await appendMailToFolder(account, 'Sent', mailOpts, { flags: ['\\Seen'] });
      } catch (appendError) {
        console.error('[mail] appendMailToFolder failed for Sent:', appendError);
      }
      res.writeHead(200, { 'content-type': 'application/json' });
      res.end(JSON.stringify({ ok: true, data: { accountKey: account.key, message: 'Sent' } }));
    } catch (error) {
      sendMailJsonError(
        res,
        Number(error?.statusCode || 500),
        error?.statusCode ? error.message : `SMTP: ${error.message}`,
        error?.code || 'SMTP_ERROR',
      );
    }
    return true;
  }

  if (req.method === 'POST' && parsedUrl.pathname === '/mail/api/reply') {
    try {
      const body = await readJsonRequestBody(req, MAIL_MAX_JSON_BODY_BYTES);
      const toList = parseMailAddressList(body.to, 'to');
      const ccList = parseMailAddressList(body.cc, 'cc');
      const bccList = parseMailAddressList(body.bcc, 'bcc');
      const subject = String(body.subject || '').trim();
      const rawText = String(body.text || '');
      const rawHtml = String(body.html || '');
      const inReplyTo = String(body.inReplyTo || '').trim();
      const priority = normalizeOutgoingMailPriority(body.priority);
      const attachments = normalizeOutgoingMailAttachments(body.attachments);
      if (!toList.length) {
        sendMailJsonError(res, 400, 'Invalid recipient', 'INVALID_TO');
        return true;
      }
      if (!hasMeaningfulOutgoingBody({ text: rawText, html: rawHtml }) && !attachments.length) {
        sendMailJsonError(res, 400, 'Missing message body or attachments', 'INVALID_BODY');
        return true;
      }
      const resolved = resolveRequestedMailAccountOrReply(body.account);
      if (!resolved) return true;
      const account = resolved.account;
      const content = resolveOutgoingMailContent(body, account);
      const sentAt = new Date();
      const mailOpts = {
        from: `"${account.fromName}" <${account.email}>`,
        to: toList.join(', '),
        ...(ccList.length ? { cc: ccList.join(', ') } : {}),
        ...(bccList.length ? { bcc: bccList.join(', ') } : {}),
        ...(attachments.length ? { attachments } : {}),
        subject: subject.startsWith('Re:') ? subject : `Re: ${subject}`,
        text: content.text,
        ...(content.html ? { html: content.html } : {}),
        headers: buildOutgoingMailHeaders({ account, priority }),
        date: sentAt,
        messageId: `<${crypto.randomUUID()}@${getMailMessageIdDomain(account)}>`,
      };
      if (inReplyTo) mailOpts.inReplyTo = inReplyTo;
      await getMailTransport(account).sendMail(mailOpts);
      try {
        await appendMailToFolder(account, 'Sent', mailOpts, { flags: ['\\Seen'] });
      } catch (appendError) {
        console.error('[mail] appendMailToFolder failed for Sent:', appendError);
      }
      res.writeHead(200, { 'content-type': 'application/json' });
      res.end(JSON.stringify({ ok: true, data: { accountKey: account.key, message: 'Reply sent' } }));
    } catch (error) {
      sendMailJsonError(
        res,
        Number(error?.statusCode || 500),
        error?.statusCode ? error.message : `SMTP: ${error.message}`,
        error?.code || 'SMTP_ERROR',
      );
    }
    return true;
  }

  if (req.method === 'POST' && parsedUrl.pathname === '/mail/api/forward') {
    try {
      const body = await readJsonRequestBody(req, MAIL_MAX_JSON_BODY_BYTES);
      const toList = parseMailAddressList(body.to, 'to');
      const ccList = parseMailAddressList(body.cc, 'cc');
      const bccList = parseMailAddressList(body.bcc, 'bcc');
      const subject = String(body.subject || '').trim();
      const rawText = String(body.text || '');
      const rawHtml = String(body.html || '');
      const priority = normalizeOutgoingMailPriority(body.priority);
      const uploadedAttachments = normalizeOutgoingMailAttachments(body.attachments);
      const forwardSource = body.forwardSource && typeof body.forwardSource === 'object'
        ? body.forwardSource
        : null;
      const sourceUid = Number(forwardSource?.uid || 0);
      const sourceFolder = resolveMailFolder(forwardSource?.folder);
      if (!toList.length) {
        sendMailJsonError(res, 400, 'Invalid recipient', 'INVALID_TO');
        return true;
      }
      if (!subject) {
        sendMailJsonError(res, 400, 'Missing subject', 'INVALID_SUBJECT');
        return true;
      }
      if (!forwardSource || !sourceUid || !sourceFolder) {
        sendMailJsonError(res, 400, 'Missing forward source', 'INVALID_FORWARD_SOURCE');
        return true;
      }
      const resolved = resolveRequestedMailAccountOrReply(body.account);
      if (!resolved) return true;
      const sourceResolved = resolveRequestedMailAccountOrReply(
        forwardSource.account || body.account,
      );
      if (!sourceResolved) return true;
      const fetched = await fetchParsedMailboxMessage(sourceResolved.account, sourceFolder, sourceUid);
      if (!fetched) {
        sendMailJsonError(res, 404, 'Forward source message not found', 'NOT_FOUND');
        return true;
      }
      const forwardedAttachments = extractForwardedMailAttachments(
        fetched.parsed.attachments,
        forwardSource.attachmentIndices,
      );
      const attachments = enforceOutgoingAttachmentLimits([
        ...forwardedAttachments,
        ...uploadedAttachments,
      ]);
      if (!hasMeaningfulOutgoingBody({ text: rawText, html: rawHtml }) && !attachments.length) {
        sendMailJsonError(res, 400, 'Missing message body or attachments', 'INVALID_BODY');
        return true;
      }
      const account = resolved.account;
      const content = resolveOutgoingMailContent(body, account);
      const sentAt = new Date();
      const normalizedSubject = /^(fwd|fw|wg):/i.test(subject) ? subject : `Fwd: ${subject}`;
      const mailOpts = {
        from: `"${account.fromName}" <${account.email}>`,
        to: toList.join(', '),
        ...(ccList.length ? { cc: ccList.join(', ') } : {}),
        ...(bccList.length ? { bcc: bccList.join(', ') } : {}),
        ...(attachments.length ? { attachments } : {}),
        subject: normalizedSubject,
        text: content.text,
        ...(content.html ? { html: content.html } : {}),
        headers: buildOutgoingMailHeaders({ account, priority }),
        date: sentAt,
        messageId: `<${crypto.randomUUID()}@${getMailMessageIdDomain(account)}>`,
      };
      await getMailTransport(account).sendMail(mailOpts);
      try {
        await appendMailToFolder(account, 'Sent', mailOpts, { flags: ['\\Seen'] });
      } catch (appendError) {
        console.error('[mail] appendMailToFolder failed for Sent:', appendError);
      }
      res.writeHead(200, { 'content-type': 'application/json' });
      res.end(JSON.stringify({
        ok: true,
        data: {
          accountKey: account.key,
          forwardedAttachmentCount: forwardedAttachments.length,
          message: 'Forward sent',
        },
      }));
    } catch (error) {
      sendMailJsonError(
        res,
        Number(error?.statusCode || 500),
        error?.statusCode ? error.message : `SMTP: ${error.message}`,
        error?.code || 'SMTP_ERROR',
      );
    }
    return true;
  }

  if (req.method === 'POST' && parsedUrl.pathname === '/mail/api/mark-read') {
    let accountKey = '';
    try {
      const body = await readJsonRequestBody(req, MAIL_MAX_JSON_BODY_BYTES);
      const uid = Number(body.uid);
      const folder = resolveMailFolder(body.folder);
      if (!uid) {
        sendMailJsonError(res, 400, 'Missing uid', 'INVALID_PARAM');
        return true;
      }
      if (!folder) {
        sendMailJsonError(res, 400, 'Invalid folder', 'INVALID_FOLDER');
        return true;
      }
      const resolved = resolveRequestedMailAccountOrReply(body.account);
      if (!resolved) return true;
      accountKey = resolved.account.key;
      const client = await getMailImap(resolved.account);
      const lock = await client.getMailboxLock(folder);
      try {
        await client.messageFlagsAdd({ uid }, ['\\Seen'], { uid: true });
      } finally {
        lock.release();
      }
      touchMailImap(resolved.account.key);
      res.writeHead(200, { 'content-type': 'application/json' });
      res.end(JSON.stringify({ ok: true, data: { accountKey: resolved.account.key, uid } }));
    } catch (error) {
      if (accountKey) resetMailImap(accountKey);
      sendMailJsonError(res, 500, `IMAP: ${error.message}`, 'IMAP_ERROR');
    }
    return true;
  }

  if (req.method === 'POST' && parsedUrl.pathname === '/mail/api/delete') {
    let accountKey = '';
    try {
      const body = await readJsonRequestBody(req, MAIL_MAX_JSON_BODY_BYTES);
      const uid = Number(body.uid);
      const folder = resolveMailFolder(body.folder);
      if (!uid) {
        sendMailJsonError(res, 400, 'Missing uid', 'INVALID_PARAM');
        return true;
      }
      if (!folder) {
        sendMailJsonError(res, 400, 'Invalid folder', 'INVALID_FOLDER');
        return true;
      }
      const resolved = resolveRequestedMailAccountOrReply(body.account);
      if (!resolved) return true;
      accountKey = resolved.account.key;
      await deleteMailMessage(resolved.account, folder, uid);
      res.writeHead(200, { 'content-type': 'application/json' });
      res.end(JSON.stringify({ ok: true, data: { accountKey: resolved.account.key, uid } }));
    } catch (error) {
      if (accountKey) resetMailImap(accountKey);
      sendMailJsonError(res, 500, `IMAP: ${error.message}`, 'IMAP_ERROR');
    }
    return true;
  }

  res.writeHead(404, { 'content-type': 'application/json' });
  res.end(JSON.stringify({ ok: false, error: 'Not found', code: 'NOT_FOUND' }));
  return true;
}

if (MAIL_ENABLED && MAIL_CONFIG.hasAnyConfiguredAccounts) {
  setInterval(() => {
    const now = Date.now();
    for (const [key, cached] of _mailImapCache.entries()) {
      if (cached?.client && now - cached.ts > MAIL_IMAP_TTL) {
        resetMailImap(key);
      }
    }
  }, 30_000);
}

module.exports = {
  maybeHandleMailRequest,
};
