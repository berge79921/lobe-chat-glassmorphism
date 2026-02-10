(function () {
  'use strict';

  var runtimeConfig = window.__LEGALCHAT_BRANDING_CONFIG__ || {};
  function parsePositiveInt(value, fallback) {
    var n = Number(value);
    if (!Number.isFinite(n) || n <= 0) return fallback;
    return Math.floor(n);
  }

  var APP_NAME = runtimeConfig.appName || 'LegalChat';
  var DEFAULT_AGENT_NAME = runtimeConfig.defaultAgentName || 'George';
  var AVATAR_URL = runtimeConfig.avatarUrl || '/custom-assets/george-avatar.jpg';
  var STT_MAX_RECORDING_MS = parsePositiveInt(runtimeConfig.sttMaxRecordingMs, 90000);
  var STT_SILENCE_STOP_MS = parsePositiveInt(runtimeConfig.sttSilenceStopMs, 3000);
  var ASSISTANT_ROLE_DE = runtimeConfig.assistantRoleDe || 'persönlicher KI-Jurist';
  var ASSISTANT_ROLE_EN = runtimeConfig.assistantRoleEn || 'personal AI legal assistant';
  var WELCOME_PRIMARY_DE =
    runtimeConfig.welcomePrimaryDe ||
    ('Ich bin ' + DEFAULT_AGENT_NAME + ', Ihr ' + ASSISTANT_ROLE_DE + ' bei ' + APP_NAME + '. Wie kann ich Ihnen jetzt helfen?');
  var WELCOME_PRIMARY_EN =
    runtimeConfig.welcomePrimaryEn ||
    ('I am your ' + ASSISTANT_ROLE_EN + ' ' + APP_NAME + '. How can I assist you today?');
  var WELCOME_SECONDARY_DE =
    runtimeConfig.welcomeSecondaryDe ||
    'Wenn Sie einen professionelleren oder maßgeschneiderten Assistenten benötigen, klicken Sie auf +, um einen benutzerdefinierten Assistenten zu erstellen.';
  var WELCOME_SECONDARY_EN =
    runtimeConfig.welcomeSecondaryEn ||
    'If you need a more professional or customized assistant, you can click + to create a custom assistant.';
  var BRAND_PATTERN = /Lobe\s*Hub|Lobe\s*Chat|LobeHub|LobeChat/gi;
  var ROLE_PATTERN_DE = /persönlicher intelligenter Assistent|persönlicher KI-Jurist/gi;
  var ROLE_PATTERN_EN = /personal intelligent assistant|personal ai legal assistant/gi;
  var WELCOME_PRIMARY_DE_PATTERN = /Ich bin Ihr (?:persönlicher intelligenter Assistent|persönlicher KI-Jurist)\s*(?:Lobe\s*Hub|Lobe\s*Chat|LobeHub|LobeChat|LegalChat)?\.?\s*Wie kann ich Ihnen jetzt helfen\?/gi;
  var WELCOME_PRIMARY_EN_PATTERN = /I am your (?:personal intelligent assistant|personal ai legal assistant)\s*(?:Lobe\s*Hub|Lobe\s*Chat|LobeHub|LobeChat|LegalChat)?\.?\s*How can I assist you today\?/gi;
  var WELCOME_SECONDARY_DE_PATTERN = /Wenn Sie einen professionelleren oder maßgeschneiderten Assistenten benötigen,\s*klicken Sie auf\s*\+?\s*,?\s*um einen benutzerdefinierten Assistenten zu erstellen\.?/gi;
  var WELCOME_SECONDARY_EN_PATTERN = /If you need a more professional or customized assistant,\s*you can click\s*\+?\s*to create a custom assistant\.?/gi;
  var DEFAULT_AGENT_PATTERN = /Lass uns plaudern|Just Chat/gi;
  var WORDMARK_SELECTOR = 'svg[viewBox="0 0 940 320"]';

  var scheduled = false;

  function installSpeechRecognitionGuard() {
    if (window.__legalchatSpeechGuardInstalled) return;

    var BaseCtor = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (typeof BaseCtor !== 'function') return;

    window.__legalchatSpeechGuardInstalled = true;
    var knownRecognitions = [];

    function registerRecognition(recognition) {
      if (!recognition) return;
      if (knownRecognitions.indexOf(recognition) === -1) knownRecognitions.push(recognition);
    }

    function stopRecognition(recognition, forceAbort) {
      if (!recognition) return;
      try {
        recognition.stop();
      } catch (_stopError) {}
      if (!forceAbort) return;
      try {
        recognition.abort();
      } catch (_abortError) {}
    }

    function stopAllRecognitions(forceAbort) {
      for (var i = 0; i < knownRecognitions.length; i += 1) {
        stopRecognition(knownRecognitions[i], forceAbort);
      }
    }

    function wrapRecognition(recognition) {
      if (!recognition || recognition.__legalchatSpeechWrapped === '1') return recognition;

      recognition.__legalchatSpeechWrapped = '1';
      registerRecognition(recognition);
      var sessionTimer = 0;
      var silenceTimer = 0;

      function clearTimers() {
        if (sessionTimer) {
          window.clearTimeout(sessionTimer);
          sessionTimer = 0;
        }
        if (silenceTimer) {
          window.clearTimeout(silenceTimer);
          silenceTimer = 0;
        }
      }

      function armSessionTimer() {
        if (STT_MAX_RECORDING_MS <= 0) return;
        if (sessionTimer) window.clearTimeout(sessionTimer);
        sessionTimer = window.setTimeout(function () {
          stopRecognition(recognition, false);
          window.setTimeout(function () {
            stopRecognition(recognition, true);
          }, 900);
        }, STT_MAX_RECORDING_MS);
      }

      function armSilenceTimer() {
        if (STT_SILENCE_STOP_MS <= 0) return;
        if (silenceTimer) window.clearTimeout(silenceTimer);
        silenceTimer = window.setTimeout(function () {
          stopRecognition(recognition, false);
        }, STT_SILENCE_STOP_MS);
      }

      var originalStart = recognition.start && recognition.start.bind(recognition);
      if (originalStart) {
        recognition.start = function () {
          clearTimers();
          armSessionTimer();
          return originalStart();
        };
      }

      var originalStop = recognition.stop && recognition.stop.bind(recognition);
      if (originalStop) {
        recognition.stop = function () {
          clearTimers();
          return originalStop();
        };
      }

      var originalAbort = recognition.abort && recognition.abort.bind(recognition);
      if (originalAbort) {
        recognition.abort = function () {
          clearTimers();
          return originalAbort();
        };
      }

      if (recognition.addEventListener) {
        recognition.addEventListener('start', function () {
          armSessionTimer();
        });
        recognition.addEventListener('speechstart', function () {
          if (silenceTimer) {
            window.clearTimeout(silenceTimer);
            silenceTimer = 0;
          }
        });
        recognition.addEventListener('speechend', armSilenceTimer);
        recognition.addEventListener('soundend', armSilenceTimer);
        recognition.addEventListener('audioend', armSilenceTimer);
        recognition.addEventListener('result', function () {
          if (silenceTimer) {
            window.clearTimeout(silenceTimer);
            silenceTimer = 0;
          }
          armSessionTimer();
        });
        recognition.addEventListener('end', clearTimers);
        recognition.addEventListener('error', clearTimers);
      }

      return recognition;
    }

    function WrappedSpeechRecognition() {
      // eslint-disable-next-line new-cap
      var recognition = new BaseCtor();
      return wrapRecognition(recognition);
    }

    WrappedSpeechRecognition.prototype = BaseCtor.prototype;
    try {
      Object.setPrototypeOf(WrappedSpeechRecognition, BaseCtor);
    } catch (_setPrototypeError) {}

    if (window.SpeechRecognition === BaseCtor) window.SpeechRecognition = WrappedSpeechRecognition;
    if (window.webkitSpeechRecognition === BaseCtor) window.webkitSpeechRecognition = WrappedSpeechRecognition;

    window.__legalchatStopSpeechRecognition = function () {
      stopAllRecognitions(true);
    };

    window.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') stopAllRecognitions(true);
    });

    document.addEventListener('visibilitychange', function () {
      if (document.hidden) stopAllRecognitions(false);
    });
  }

  function rewriteText(value) {
    if (!value) return value;
    return value
      .replace(BRAND_PATTERN, APP_NAME)
      .replace(ROLE_PATTERN_DE, ASSISTANT_ROLE_DE)
      .replace(ROLE_PATTERN_EN, ASSISTANT_ROLE_EN)
      .replace(WELCOME_PRIMARY_DE_PATTERN, WELCOME_PRIMARY_DE)
      .replace(WELCOME_PRIMARY_EN_PATTERN, WELCOME_PRIMARY_EN)
      .replace(WELCOME_SECONDARY_DE_PATTERN, WELCOME_SECONDARY_DE)
      .replace(WELCOME_SECONDARY_EN_PATTERN, WELCOME_SECONDARY_EN)
      .replace(DEFAULT_AGENT_PATTERN, DEFAULT_AGENT_NAME);
  }

  function rewriteTitle() {
    var next = rewriteText(document.title);
    if (next && next !== document.title) {
      document.title = next;
    }
  }

  function rewriteTextNodes(root) {
    if (!root) return;

    var walker = document.createTreeWalker(
      root,
      NodeFilter.SHOW_TEXT,
      {
        acceptNode: function (node) {
          if (!node || !node.nodeValue) return NodeFilter.FILTER_REJECT;
          var parent = node.parentElement;
          if (!parent) return NodeFilter.FILTER_REJECT;
          var tag = parent.tagName;
          if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'NOSCRIPT' || tag === 'TITLE') {
            return NodeFilter.FILTER_REJECT;
          }
          if (!/Lobe\s*Hub|Lobe\s*Chat|LobeHub|LobeChat|persönlicher intelligenter Assistent|persönlicher KI-Jurist|personal intelligent assistant|personal ai legal assistant|professionelleren oder maßgeschneiderten Assistenten|professional or customized assistant|Lass uns plaudern|Just Chat/i.test(node.nodeValue)) {
            return NodeFilter.FILTER_REJECT;
          }
          return NodeFilter.FILTER_ACCEPT;
        },
      },
    );

    var current;
    while ((current = walker.nextNode())) {
      var rewritten = rewriteText(current.nodeValue);
      if (rewritten !== current.nodeValue) {
        current.nodeValue = rewritten;
      }
    }
  }

  function rewriteAttributes() {
    var attrs = ['placeholder', 'title', 'aria-label', 'alt'];
    var candidates = document.querySelectorAll('[placeholder],[title],[aria-label],[alt]');

    for (var i = 0; i < candidates.length; i += 1) {
      var el = candidates[i];
      for (var j = 0; j < attrs.length; j += 1) {
        var attr = attrs[j];
        if (!el.hasAttribute(attr)) continue;
        var current = el.getAttribute(attr);
        var rewritten = rewriteText(current);
        if (rewritten !== current) {
          el.setAttribute(attr, rewritten);
        }
      }
    }
  }

  function rewriteHeadMetadata() {
    var titles = document.querySelectorAll('head title');
    for (var i = 0; i < titles.length; i += 1) {
      var title = titles[i];
      if (!title || !title.textContent) continue;
      var rewrittenTitle = rewriteText(title.textContent);
      if (rewrittenTitle !== title.textContent) title.textContent = rewrittenTitle;
    }
    if (titles.length > 1) {
      for (var titleIndex = titles.length - 1; titleIndex >= 1; titleIndex -= 1) {
        var duplicateTitle = titles[titleIndex];
        if (duplicateTitle && duplicateTitle.parentNode) {
          duplicateTitle.parentNode.removeChild(duplicateTitle);
        }
      }
    }

    var metaSelectors = [
      'meta[name="description"]',
      'meta[name="apple-mobile-web-app-title"]',
      'meta[property="og:title"]',
      'meta[property="og:description"]',
      'meta[property="og:site_name"]',
      'meta[property="og:image:alt"]',
      'meta[name="twitter:title"]',
      'meta[name="twitter:description"]',
    ];

    var metas = document.querySelectorAll(metaSelectors.join(','));
    for (var j = 0; j < metas.length; j += 1) {
      var meta = metas[j];
      var content = meta.getAttribute('content');
      var rewrittenContent = rewriteText(content);
      if (rewrittenContent !== content) {
        meta.setAttribute('content', rewrittenContent);
      }
    }

    var seenMeta = {};
    for (var k = 0; k < metas.length; k += 1) {
      var currentMeta = metas[k];
      if (!currentMeta) continue;

      var name = currentMeta.getAttribute('name');
      var property = currentMeta.getAttribute('property');
      var key = '';
      if (name) key = 'name:' + name.toLowerCase().trim();
      if (!key && property) key = 'property:' + property.toLowerCase().trim();
      if (!key) continue;

      if (seenMeta[key]) {
        if (currentMeta.parentNode) currentMeta.parentNode.removeChild(currentMeta);
        continue;
      }
      seenMeta[key] = true;
    }
  }

  function rewriteWelcomeBlocks() {
    var selectors = [
      'main p',
      'main span',
      'main div',
      '[class*="welcome" i] p',
      '[class*="welcome" i] span',
      '[class*="greet" i] p',
      '[class*="greet" i] span',
    ];
    var nodes = document.querySelectorAll(selectors.join(','));

    for (var i = 0; i < nodes.length; i += 1) {
      var node = nodes[i];
      if (!node || !node.textContent) continue;
      if (node.children && node.children.length > 3) continue;

      var original = node.textContent;
      var normalized = original.replace(/\s+/g, ' ').trim();
      if (!normalized || normalized.length < 24 || normalized.length > 260) continue;

      if (
        /Ich bin Ihr (?:persönlicher intelligenter Assistent|persönlicher KI-Jurist)/i.test(normalized) ||
        /Wie kann ich Ihnen jetzt helfen\?/i.test(normalized)
      ) {
        if (original !== WELCOME_PRIMARY_DE) node.textContent = WELCOME_PRIMARY_DE;
        continue;
      }

      if (
        /I am your (?:personal intelligent assistant|personal ai legal assistant)/i.test(normalized) ||
        /How can I assist you today\?/i.test(normalized)
      ) {
        if (original !== WELCOME_PRIMARY_EN) node.textContent = WELCOME_PRIMARY_EN;
        continue;
      }

      if (/professionelleren oder maßgeschneiderten Assistenten/i.test(normalized)) {
        if (original !== WELCOME_SECONDARY_DE) node.textContent = WELCOME_SECONDARY_DE;
        continue;
      }

      if (/professional or customized assistant/i.test(normalized)) {
        if (original !== WELCOME_SECONDARY_EN) node.textContent = WELCOME_SECONDARY_EN;
      }
    }
  }

  function replaceWordmarkSvg() {
    var svgs = document.querySelectorAll(WORDMARK_SELECTOR);

    for (var i = 0; i < svgs.length; i += 1) {
      var svg = svgs[i];
      if (!svg || svg.dataset.legalchatWordmark === '1') continue;

      var title = svg.querySelector('title');
      var titleText = title ? title.textContent || '' : '';
      var looksLikeBrand = /Lobe|LegalChat/i.test(titleText) || !!svg.closest('[class*="brand" i], [class*="lazdsx" i], [class*="loading" i]');
      if (!looksLikeBrand) continue;

      if (title) title.textContent = APP_NAME;

      var parent = svg.parentElement;
      svg.dataset.legalchatWordmark = '1';
      svg.classList.add('legalchat-hidden-wordmark-svg');

      if (parent && !parent.querySelector('.legalchat-wordmark')) {
        var wordmark = document.createElement('span');
        wordmark.className = 'legalchat-wordmark';
        wordmark.textContent = APP_NAME;
        parent.appendChild(wordmark);
      }
    }
  }

  function setGeorgeAvatar() {
    var isChatRoute = /(?:^|\/)chat(?:\/|$)/i.test(window.location.pathname || '');
    var selectors = [
      'aside img',
      '[class*="session" i] img',
      '[class*="assistant" i] img',
      '[class*="avatar" i] img',
      'img[src*="npmmirror" i]',
      'img[src*="assets-logo" i]',
      'img[alt*="LobeHub" i]',
      'img[alt*="assistant" i]',
      'img[alt*="bot" i]',
      'img[alt*="ai" i]',
    ];

    var avatars = document.querySelectorAll(selectors.join(','));

    for (var i = 0; i < avatars.length; i += 1) {
      var img = avatars[i];
      if (!img) continue;

      var src = img.getAttribute('src') || '';
      if (img.dataset.legalchatAvatar === '1' && src.includes('george-avatar.jpg')) continue;
      var alt = (img.getAttribute('alt') || '').toLowerCase();
      var width = img.width || 0;
      var height = img.height || 0;

      var looksLikeAvatar =
        /avatar|assistant|agent|bot|chat|lobe|fluent-emoji|npmmirror/i.test(src + ' ' + alt) ||
        (width > 0 && width <= 64 && height > 0 && height <= 64);

      if (!looksLikeAvatar) continue;

      if (!src.includes('george-avatar.jpg')) {
        img.src = AVATAR_URL;
        img.setAttribute('src', AVATAR_URL);
        img.setAttribute('srcset', '');
      }

      if (isChatRoute) {
        var rect = img.getBoundingClientRect();
        var isChatWindowAvatar =
          !img.closest('aside') &&
          !img.closest('button,.ant-btn') &&
          rect &&
          rect.x > 220 &&
          rect.y > 30 &&
          rect.width >= 32;
        if (isChatWindowAvatar) {
          img.classList.add('legalchat-chat-avatar');
        } else {
          img.classList.remove('legalchat-chat-avatar');
        }
      } else {
        img.classList.remove('legalchat-chat-avatar');
      }

      img.alt = 'George - KI Jurist';
      img.dataset.legalchatAvatar = '1';
      img.classList.add('legalchat-avatar-img');
    }
  }

  function tuneNavIcons() {
    var iconWrappers = document.querySelectorAll('aside [role="button"] [role="img"], aside a [role="img"]');
    for (var i = 0; i < iconWrappers.length; i += 1) {
      iconWrappers[i].classList.add('legalchat-nav-icon');
    }
  }

  function applyBranding() {
    installSpeechRecognitionGuard();
    rewriteTitle();
    rewriteHeadMetadata();
    rewriteWelcomeBlocks();
    rewriteTextNodes(document.body);
    rewriteAttributes();
    replaceWordmarkSvg();
    setGeorgeAvatar();
    tuneNavIcons();
  }

  function scheduleApply() {
    if (scheduled) return;
    scheduled = true;

    window.setTimeout(function () {
      scheduled = false;
      try {
        applyBranding();
      } catch (error) {
        console.error('[LegalChat] Branding apply failed:', error);
      }
    }, 120);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', scheduleApply, { once: true });
  } else {
    scheduleApply();
  }

  var observer = new MutationObserver(function () {
    scheduleApply();
  });

  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['class', 'title', 'aria-label', 'alt', 'placeholder', 'src', 'srcset'],
    childList: true,
    subtree: true,
  });
})();
