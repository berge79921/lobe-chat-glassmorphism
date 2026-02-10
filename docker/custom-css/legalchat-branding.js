/**
 * LegalChat Branding Customization
 * Replaces LobeChat branding with LegalChat and sets George as avatar
 */

(function() {
  'use strict';

  const CONFIG = {
    appName: 'LegalChat',
    avatarUrl: '/custom-assets/george-avatar.jpg',
    subtitle: 'Ihr intelligenter KI-Jurist'
  };

  // Replace text content
  function replaceText(node) {
    if (node.nodeType === Node.TEXT_NODE) {
      if (node.textContent.includes('LobeChat')) {
        node.textContent = node.textContent.replace(/LobeChat/g, CONFIG.appName);
      }
      return;
    }
    
    if (node.nodeType === Node.ELEMENT_NODE) {
      // Skip script and style elements
      if (node.tagName === 'SCRIPT' || node.tagName === 'STYLE') return;
      
      // Check for placeholder attributes
      if (node.placeholder && node.placeholder.includes('LobeChat')) {
        node.placeholder = node.placeholder.replace(/LobeChat/g, CONFIG.appName);
      }
      
      // Check title and alt attributes
      if (node.title && node.title.includes('LobeChat')) {
        node.title = node.title.replace(/LobeChat/g, CONFIG.appName);
      }
      if (node.alt && node.alt.includes('LobeChat')) {
        node.alt = node.alt.replace(/LobeChat/g, CONFIG.appName);
      }
    }
  }

  // Walk DOM and replace text
  function walkDOM(node) {
    replaceText(node);
    node.childNodes.forEach(walkDOM);
  }

  // Set George avatar for assistant/user
  function setGeorgeAvatar() {
    // Find avatar images and replace with George
    const avatarSelectors = [
      'img[alt*="assistant"]',
      'img[alt*="AI"]',
      '.assistant-avatar',
      '[class*="avatar"] img',
      '.message-assistant img',
      '.chat-assistant-avatar'
    ];

    document.querySelectorAll(avatarSelectors.join(', ')).forEach(img => {
      img.src = CONFIG.avatarUrl;
      img.alt = 'George - KI Jurist';
    });
  }

  // Update page title
  function updatePageTitle() {
    if (document.title.includes('LobeChat')) {
      document.title = document.title.replace(/LobeChat/g, CONFIG.appName);
    }
  }

  // Update meta tags
  function updateMetaTags() {
    const metaDescription = document.querySelector('meta[name="description"]');
    if (metaDescription && metaDescription.content.includes('LobeChat')) {
      metaDescription.content = metaDescription.content.replace(/LobeChat/g, CONFIG.appName);
    }
  }

  // Main branding function
  function applyBranding() {
    walkDOM(document.body);
    updatePageTitle();
    updateMetaTags();
    setGeorgeAvatar();
  }

  // Run on load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', applyBranding);
  } else {
    applyBranding();
  }

  // Re-apply on dynamic content changes (React app)
  const observer = new MutationObserver((mutations) => {
    let shouldUpdate = false;
    mutations.forEach(mutation => {
      if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
        shouldUpdate = true;
      }
    });
    if (shouldUpdate) {
      applyBranding();
    }
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true
  });

  // Periodic check for avatars (React re-renders)
  setInterval(setGeorgeAvatar, 1000);

  console.log('[LegalChat] Branding applied - George is ready!');
})();
