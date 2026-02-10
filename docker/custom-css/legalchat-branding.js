(function () {
  'use strict';

  var APP_NAME = 'LegalChat';
  var DEFAULT_AGENT_NAME = 'George';
  var AVATAR_URL = '/custom-assets/george-avatar.jpg';
  var BRAND_PATTERN = /Lobe\s*Hub|Lobe\s*Chat|LobeHub|LobeChat/gi;
  var WELCOME_PATTERN = /persönlicher intelligenter Assistent|personal intelligent assistant/gi;
  var DEFAULT_AGENT_PATTERN = /Lass uns plaudern|Just Chat/gi;
  var WORDMARK_SELECTOR = 'svg[viewBox="0 0 940 320"]';

  var scheduled = false;

  function rewriteText(value) {
    if (!value) return value;
    return value
      .replace(BRAND_PATTERN, APP_NAME)
      .replace(WELCOME_PATTERN, 'persönlicher KI-Jurist')
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
          if (!/Lobe\s*Hub|Lobe\s*Chat|LobeHub|LobeChat|persönlicher intelligenter Assistent|personal intelligent assistant|Lass uns plaudern|Just Chat/i.test(node.nodeValue)) {
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
    rewriteTitle();
    rewriteHeadMetadata();
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
