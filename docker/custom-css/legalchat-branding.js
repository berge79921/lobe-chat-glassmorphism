(function () {
  'use strict';

  var APP_NAME = 'LegalChat';
  var AVATAR_URL = '/custom-assets/george-avatar.jpg';
  var BRAND_PATTERN = /LobeChat|LobeHub/g;
  var WELCOME_PATTERN = /persönlicher intelligenter Assistent/gi;
  var scheduled = false;

  function rewriteText(value) {
    if (!value) return value;
    return value.replace(BRAND_PATTERN, APP_NAME).replace(WELCOME_PATTERN, 'persönlicher KI-Jurist');
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
          if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'NOSCRIPT') {
            return NodeFilter.FILTER_REJECT;
          }
          if (!/LobeChat|LobeHub|persönlicher intelligenter Assistent/i.test(node.nodeValue)) {
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
    var candidates = document.querySelectorAll('[placeholder],[title],[aria-label],[alt]');
    for (var i = 0; i < candidates.length; i += 1) {
      var el = candidates[i];
      var attrs = ['placeholder', 'title', 'aria-label', 'alt'];
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

  function setGeorgeAvatar() {
    var selectors = [
      '[class*="avatar"] img',
      'img[class*="avatar"]',
      'img[alt*="assistant" i]',
      'img[alt*="ai" i]',
      'img[alt*="bot" i]',
    ];
    var avatars = document.querySelectorAll(selectors.join(','));

    for (var i = 0; i < avatars.length; i += 1) {
      var img = avatars[i];
      if (!img || img.dataset.legalchatAvatar === '1') continue;

      var src = img.getAttribute('src') || '';
      if (src.includes('george-avatar.jpg')) {
        img.dataset.legalchatAvatar = '1';
        img.classList.add('legalchat-avatar-img');
        continue;
      }

      img.src = AVATAR_URL;
      img.alt = 'George - KI Jurist';
      img.dataset.legalchatAvatar = '1';
      img.classList.add('legalchat-avatar-img');
    }
  }

  function markWelcomeHeadline() {
    var candidates = document.querySelectorAll('h1,h2,h3,p,span,div');
    for (var i = 0; i < candidates.length; i += 1) {
      var el = candidates[i];
      var text = el.textContent || '';
      if (!text) continue;
      if (text.includes('Guten') || text.includes('Good')) {
        el.classList.add('legalchat-welcome');
      }
      if (text.includes(APP_NAME)) {
        el.classList.add('legalchat-brand-text');
      }
    }
  }

  function applyBranding() {
    rewriteTitle();
    rewriteTextNodes(document.body);
    rewriteAttributes();
    setGeorgeAvatar();
    markWelcomeHeadline();
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
    }, 150);
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
    childList: true,
    subtree: true,
  });
})();
