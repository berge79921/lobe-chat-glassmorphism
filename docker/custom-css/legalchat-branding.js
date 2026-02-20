(function () {
  'use strict';

  var runtimeConfig = window.__LEGALCHAT_BRANDING_CONFIG__ || {};
  function parsePositiveInt(value, fallback) {
    var n = Number(value);
    if (!Number.isFinite(n) || n <= 0) return fallback;
    return Math.floor(n);
  }
  function parseBoolean(value, fallback) {
    if (typeof value === 'boolean') return value;
    if (value == null) return fallback;
    var normalized = String(value).trim().toLowerCase();
    if (!normalized) return fallback;
    if (normalized === '1' || normalized === 'true' || normalized === 'yes' || normalized === 'on') return true;
    if (normalized === '0' || normalized === 'false' || normalized === 'no' || normalized === 'off') return false;
    return fallback;
  }

  var APP_NAME = runtimeConfig.appName || 'LegalChat';
  var DEFAULT_AGENT_NAME = runtimeConfig.defaultAgentName || 'George';
  var RAW_AVATAR_URL = runtimeConfig.avatarUrl || '/custom-assets/legalchat-avatar.jpg';
  var AVATAR_URL = withBrandingVersion(RAW_AVATAR_URL);
  var RAW_FAVICON_URL = runtimeConfig.faviconUrl || RAW_AVATAR_URL;
  var TAB_TITLE = runtimeConfig.tabTitle || (DEFAULT_AGENT_NAME + ' · ' + APP_NAME);
  var STT_MAX_RECORDING_MS = parsePositiveInt(runtimeConfig.sttMaxRecordingMs, 90000);
  var STT_SILENCE_STOP_MS = parsePositiveInt(runtimeConfig.sttSilenceStopMs, 3000);
  var VOICE_MODE = String(runtimeConfig.voiceMode || 'guarded')
    .trim()
    .toLowerCase();
  var VOICE_OFF =
    runtimeConfig.voiceOff === true ||
    String(runtimeConfig.voiceOff || '')
      .trim()
      .toLowerCase() === 'true' ||
    VOICE_MODE === 'off' ||
    VOICE_MODE === 'disabled' ||
    VOICE_MODE === 'none' ||
    VOICE_MODE === '0';
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
  var LEGACY_BRAND_TITLE_PATTERN = /Lobe\s*Hub|Lobe\s*Chat|LobeHub|LobeChat/i;
  var WORDMARK_SELECTOR = 'svg[viewBox="0 0 940 320"]';
  var MCP_CONFIG = runtimeConfig.mcp || {};
  var MCP_ENABLED = parseBoolean(MCP_CONFIG.enabled, false);
  var MCP_API_BASE_PATH = MCP_CONFIG.apiBasePath || '/api/legalchat/mcp';
  var MCP_DEEP_RESEARCH_PATH = MCP_CONFIG.deepResearchPath || MCP_API_BASE_PATH + '/deep-research';
  var MCP_PRUEFUNGSMODUS_PATH = MCP_CONFIG.pruefungsmodusPath || MCP_API_BASE_PATH + '/pruefungsmodus';
  var MCP_GENERIC_CALL_PATH = MCP_CONFIG.genericCallPath || MCP_API_BASE_PATH + '/call';
  var MCP_TOOLS_PATH = MCP_CONFIG.toolsPath || MCP_API_BASE_PATH + '/tools';
  var MCP_STATUS_PATH = MCP_CONFIG.statusPath || MCP_API_BASE_PATH + '/status';

  var scheduled = false;
  window.__legalchatVoiceMode = VOICE_OFF ? 'off' : 'guarded';
  window.__legalchatVoiceOff = VOICE_OFF;

  function withBrandingVersion(url) {
    var value = String(url || '').trim();
    if (!value) return value;
    var version = String(runtimeConfig.brandingVersion || '').trim();
    if (!version) return value;
    if (/[?&]v=/.test(value)) return value;
    return value + (value.indexOf('?') === -1 ? '?' : '&') + 'v=' + encodeURIComponent(version);
  }

  var FAVICON_URL = withBrandingVersion(RAW_FAVICON_URL);
  var AVATAR_URL_NORMALIZED = String(AVATAR_URL || '').toLowerCase();
  var AVATAR_BASENAME = AVATAR_URL_NORMALIZED.split('?')[0].split('#')[0].split('/').pop();

  function hasBrandAvatarSource(src) {
    var value = String(src || '').toLowerCase();
    if (!value) return false;
    if (AVATAR_URL_NORMALIZED && value.indexOf(AVATAR_URL_NORMALIZED) !== -1) return true;
    if (AVATAR_BASENAME && value.indexOf(AVATAR_BASENAME) !== -1) return true;
    return false;
  }

  function createVoiceOffError(message) {
    var text = message || 'Voice input is disabled by LegalChat policy.';
    if (typeof DOMException === 'function') return new DOMException(text, 'NotAllowedError');
    var error = new Error(text);
    error.name = 'NotAllowedError';
    return error;
  }

  function safeUrlString(input) {
    if (!input) return '';
    if (typeof input === 'string') return input;
    if (typeof input.url === 'string') return input.url;
    try {
      return String(input);
    } catch (_stringifyError) {
      return '';
    }
  }

  function looksLikeProtectedTrpcEndpoint(url) {
    if (!url) return false;
    return /(?:^|\/)trpc\/lambda\//i.test(url);
  }

  var authRedirectInProgress = false;
  function redirectToLogin() {
    if (authRedirectInProgress) return;
    if (/\/login(?:\/|$)/i.test(window.location.pathname || '')) return;
    authRedirectInProgress = true;

    var callbackUrl = window.location.href || '/chat';
    var target = '/login?callbackUrl=' + encodeURIComponent(callbackUrl);

    window.setTimeout(function () {
      window.location.assign(target);
    }, 120);
  }

  function installAuth401Guard() {
    if (window.__legalchatAuth401GuardInstalled) return;
    window.__legalchatAuth401GuardInstalled = true;

    if (typeof window.fetch === 'function') {
      var originalFetch = window.fetch.bind(window);
      window.fetch = function (input, init) {
        return originalFetch(input, init).then(function (response) {
          try {
            var inputUrl = safeUrlString(input);
            var responseUrl = response && response.url ? response.url : '';
            var url = inputUrl || responseUrl;
            if (response && response.status === 401 && looksLikeProtectedTrpcEndpoint(url)) {
              redirectToLogin();
            }
          } catch (_fetchGuardError) {}
          return response;
        });
      };
    }

    if (typeof window.XMLHttpRequest === 'function') {
      var OriginalXHR = window.XMLHttpRequest;
      function WrappedXHR() {
        var xhr = new OriginalXHR();
        var trackedUrl = '';
        var originalOpen = xhr.open && xhr.open.bind(xhr);
        if (originalOpen) {
          xhr.open = function (method, url) {
            trackedUrl = safeUrlString(url);
            return originalOpen.apply(xhr, arguments);
          };
        }

        xhr.addEventListener('loadend', function () {
          try {
            if (xhr.status === 401 && looksLikeProtectedTrpcEndpoint(trackedUrl || xhr.responseURL || '')) {
              redirectToLogin();
            }
          } catch (_xhrGuardError) {}
        });
        return xhr;
      }
      WrappedXHR.prototype = OriginalXHR.prototype;
      try {
        Object.setPrototypeOf(WrappedXHR, OriginalXHR);
      } catch (_xhrPrototypeError) {}
      window.XMLHttpRequest = WrappedXHR;
    }
  }

  function createMcpApiError(response, payload) {
    var error = new Error((payload && payload.error) || ('MCP API error (' + response.status + ')'));
    error.status = response.status;
    error.payload = payload;
    return error;
  }

  function requestMcpJson(url, options) {
    if (typeof window.fetch !== 'function') {
      return Promise.reject(new Error('fetch_not_available'));
    }

    var requestOptions = options || {};
    var headers = requestOptions.headers || {};

    return window.fetch(url, {
      method: requestOptions.method || 'GET',
      credentials: 'include',
      headers: headers,
      body: requestOptions.body,
    }).then(function (response) {
      return response
        .text()
        .then(function (rawText) {
          var payload = {};
          if (rawText) {
            try {
              payload = JSON.parse(rawText);
            } catch (_parseError) {
              payload = { ok: false, raw: rawText };
            }
          }
          if (!response.ok) throw createMcpApiError(response, payload);
          return payload;
        });
    });
  }

  function installMcpClient() {
    var existing = window.LegalChatMcp;
    if (existing && typeof existing === 'object') return;

    function callMode(path, name, args) {
      if (!MCP_ENABLED) return Promise.reject(new Error('mcp_disabled'));
      return requestMcpJson(path, {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: String(name || '').trim(),
          arguments: args && typeof args === 'object' && !Array.isArray(args) ? args : {},
        }),
      });
    }

    var api = {
      call: function (mode, name, args) {
        if (!MCP_ENABLED) return Promise.reject(new Error('mcp_disabled'));
        return requestMcpJson(MCP_GENERIC_CALL_PATH, {
          method: 'POST',
          headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            mode: mode,
            name: name,
            arguments: args && typeof args === 'object' && !Array.isArray(args) ? args : {},
          }),
        });
      },
      callDeepResearch: function (name, args) {
        return callMode(MCP_DEEP_RESEARCH_PATH, name, args);
      },
      callPruefungsmodus: function (name, args) {
        return callMode(MCP_PRUEFUNGSMODUS_PATH, name, args);
      },
      deepResearchPath: MCP_DEEP_RESEARCH_PATH,
      enabled: MCP_ENABLED,
      listTools: function (mode) {
        if (!MCP_ENABLED) return Promise.reject(new Error('mcp_disabled'));
        var url = MCP_TOOLS_PATH + '?mode=' + encodeURIComponent(String(mode || '').trim());
        return requestMcpJson(url, {
          method: 'GET',
          headers: { Accept: 'application/json' },
        });
      },
      pruefungsmodusPath: MCP_PRUEFUNGSMODUS_PATH,
      status: function () {
        return requestMcpJson(MCP_STATUS_PATH, {
          method: 'GET',
          headers: { Accept: 'application/json' },
        });
      },
    };

    window.LegalChatMcp = Object.freeze(api);
  }

  function ensureFaviconLinks() {
    var head = document.head || document.getElementsByTagName('head')[0];
    if (!head || !FAVICON_URL) return;

    var rels = ['icon', 'shortcut icon', 'apple-touch-icon'];
    var seen = {};

    var links = head.querySelectorAll('link[rel]');
    for (var i = 0; i < links.length; i += 1) {
      var rel = String(links[i].getAttribute('rel') || '').toLowerCase().trim();
      if (rels.indexOf(rel) === -1) continue;
      links[i].setAttribute('href', FAVICON_URL);
      if (seen[rel]) {
        if (links[i].parentNode) links[i].parentNode.removeChild(links[i]);
        continue;
      }
      seen[rel] = links[i];
    }

    for (var j = 0; j < rels.length; j += 1) {
      var requiredRel = rels[j];
      if (seen[requiredRel]) continue;
      var link = document.createElement('link');
      link.setAttribute('rel', requiredRel);
      link.setAttribute('href', FAVICON_URL);
      head.appendChild(link);
      seen[requiredRel] = link;
    }
  }

  function isVoicePolicyError(error) {
    if (!error) return false;
    var name = String(error.name || '');
    var message = String(error.message || '');
    return (
      name === 'NotAllowedError' &&
      /voice input is disabled by policy|legalchat policy/i.test(message)
    );
  }

  function suppressVoicePolicyRejections() {
    if (!VOICE_OFF || window.__legalchatVoicePolicyRejectionHandlerInstalled) return;
    window.__legalchatVoicePolicyRejectionHandlerInstalled = true;

    window.addEventListener('unhandledrejection', function (event) {
      if (!event) return;
      if (isVoicePolicyError(event.reason)) event.preventDefault();
    });
  }

  function installAudioCaptureGuard() {
    if (window.__legalchatAudioGuardInstalled) return;
    window.__legalchatAudioGuardInstalled = true;

    var activeStreams = [];
    var activeRecorders = [];
    window.__legalchatAudioGuardState = {
      activeStreams: activeStreams,
      activeRecorders: activeRecorders,
    };

    function hasAudioTrack(stream) {
      if (!stream || typeof stream.getAudioTracks !== 'function') return false;
      var tracks = stream.getAudioTracks() || [];
      return tracks.length > 0;
    }

    function removeFromList(list, item) {
      var index = list.indexOf(item);
      if (index !== -1) list.splice(index, 1);
    }

    function stopStream(stream) {
      if (!stream || typeof stream.getTracks !== 'function') return;
      var tracks = stream.getTracks();
      for (var i = 0; i < tracks.length; i += 1) {
        try {
          tracks[i].stop();
        } catch (_trackStopError) {}
      }
    }

    function registerStream(stream) {
      if (!stream || activeStreams.indexOf(stream) !== -1 || !hasAudioTrack(stream)) return stream;
      activeStreams.push(stream);

      var cleanup = function () {
        removeFromList(activeStreams, stream);
      };
      if (stream.addEventListener) stream.addEventListener('inactive', cleanup, { once: true });
      if (stream.addTrack && stream.removeTrack) {
        try {
          var tracks = stream.getTracks ? stream.getTracks() : [];
          for (var i = 0; i < tracks.length; i += 1) {
            if (tracks[i] && tracks[i].addEventListener) {
              tracks[i].addEventListener('ended', cleanup, { once: true });
            }
          }
        } catch (_trackAttachError) {}
      }

      if (STT_MAX_RECORDING_MS > 0) {
        window.setTimeout(function () {
          if (activeStreams.indexOf(stream) !== -1) stopStream(stream);
        }, STT_MAX_RECORDING_MS + 1500);
      }

      return stream;
    }

    function registerRecorder(recorder) {
      if (!recorder || activeRecorders.indexOf(recorder) !== -1) return recorder;
      activeRecorders.push(recorder);

      var recorderTimer = 0;
      function clearRecorderTimer() {
        if (!recorderTimer) return;
        window.clearTimeout(recorderTimer);
        recorderTimer = 0;
      }
      function armRecorderTimer() {
        if (STT_MAX_RECORDING_MS <= 0) return;
        clearRecorderTimer();
        recorderTimer = window.setTimeout(function () {
          try {
            recorder.stop();
          } catch (_recorderStopError) {}
          if (recorder.stream) stopStream(recorder.stream);
        }, STT_MAX_RECORDING_MS);
      }

      if (recorder.addEventListener) {
        recorder.addEventListener('start', armRecorderTimer);
        recorder.addEventListener('pause', clearRecorderTimer);
        recorder.addEventListener('resume', armRecorderTimer);
        recorder.addEventListener('stop', function () {
          clearRecorderTimer();
          removeFromList(activeRecorders, recorder);
        });
        recorder.addEventListener('error', function () {
          clearRecorderTimer();
          removeFromList(activeRecorders, recorder);
        });
      }

      var originalStart = recorder.start && recorder.start.bind(recorder);
      if (originalStart) {
        recorder.start = function () {
          armRecorderTimer();
          return originalStart.apply(recorder, arguments);
        };
      }

      var originalStop = recorder.stop && recorder.stop.bind(recorder);
      if (originalStop) {
        recorder.stop = function () {
          clearRecorderTimer();
          return originalStop.apply(recorder, arguments);
        };
      }

      return recorder;
    }

    function stopAllAudioCapture() {
      for (var i = 0; i < activeRecorders.length; i += 1) {
        var recorder = activeRecorders[i];
        try {
          recorder.stop();
        } catch (_recorderStopError) {}
      }
      for (var j = 0; j < activeStreams.length; j += 1) {
        stopStream(activeStreams[j]);
      }
      activeRecorders.length = 0;
      activeStreams.length = 0;
    }

    function hasActiveAudioCapture() {
      for (var i = 0; i < activeRecorders.length; i += 1) {
        var recorder = activeRecorders[i];
        if (!recorder) continue;
        if (recorder.state && recorder.state !== 'inactive') return true;
      }
      for (var j = 0; j < activeStreams.length; j += 1) {
        var stream = activeStreams[j];
        if (!stream || typeof stream.getAudioTracks !== 'function') continue;
        var audioTracks = stream.getAudioTracks();
        for (var k = 0; k < audioTracks.length; k += 1) {
          if (audioTracks[k] && audioTracks[k].readyState === 'live') return true;
        }
      }
      return false;
    }

    if (navigator.mediaDevices && typeof navigator.mediaDevices.getUserMedia === 'function') {
      var originalGetUserMedia = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
      navigator.mediaDevices.getUserMedia = function (constraints) {
        var wantsAudio =
          constraints &&
          typeof constraints === 'object' &&
          (constraints.audio === true || typeof constraints.audio === 'object');
        if (wantsAudio && VOICE_OFF) {
          return Promise.reject(
            createVoiceOffError('Voice input is disabled by policy. Please contact your LegalChat administrator.'),
          );
        }
        return originalGetUserMedia(constraints).then(function (stream) {
          if (wantsAudio) registerStream(stream);
          return stream;
        });
      };
    }

    if (typeof window.MediaRecorder === 'function') {
      var BaseMediaRecorder = window.MediaRecorder;
      function WrappedMediaRecorder(stream, options) {
        // eslint-disable-next-line new-cap
        var recorder = new BaseMediaRecorder(stream, options);
        registerStream(stream);
        return registerRecorder(recorder);
      }
      WrappedMediaRecorder.prototype = BaseMediaRecorder.prototype;
      try {
        Object.setPrototypeOf(WrappedMediaRecorder, BaseMediaRecorder);
      } catch (_setPrototypeError) {}
      if (typeof BaseMediaRecorder.isTypeSupported === 'function') {
        WrappedMediaRecorder.isTypeSupported = BaseMediaRecorder.isTypeSupported.bind(BaseMediaRecorder);
      }
      window.MediaRecorder = WrappedMediaRecorder;
    }

    window.__legalchatStopAudioCapture = stopAllAudioCapture;
    window.__legalchatHasActiveAudioCapture = hasActiveAudioCapture;

    window.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') forceStopVoiceUiState();
    });

    document.addEventListener('visibilitychange', function () {
      if (document.hidden) forceStopVoiceUiState();
    });
  }

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

    function hasActiveSpeechRecognition() {
      for (var i = 0; i < knownRecognitions.length; i += 1) {
        var recognition = knownRecognitions[i];
        if (recognition && recognition.__legalchatSpeechActive === '1') return true;
      }
      return false;
    }

    function wrapRecognition(recognition) {
      if (!recognition || recognition.__legalchatSpeechWrapped === '1') return recognition;

      recognition.__legalchatSpeechWrapped = '1';
      recognition.__legalchatSpeechActive = '0';
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
          if (VOICE_OFF) {
            clearTimers();
            recognition.__legalchatSpeechActive = '0';
            if (typeof recognition.onerror === 'function') {
              try {
                recognition.onerror({
                  error: 'not-allowed',
                  message: 'Voice input is disabled by policy. Please contact your LegalChat administrator.',
                });
              } catch (_onErrorCallbackError) {}
            }
            if (typeof recognition.onend === 'function') {
              try {
                recognition.onend();
              } catch (_onEndCallbackError) {}
            }
            return;
          }
          clearTimers();
          armSessionTimer();
          recognition.__legalchatSpeechActive = '1';
          return originalStart();
        };
      }

      var originalStop = recognition.stop && recognition.stop.bind(recognition);
      if (originalStop) {
        recognition.stop = function () {
          clearTimers();
          recognition.__legalchatSpeechActive = '0';
          return originalStop();
        };
      }

      var originalAbort = recognition.abort && recognition.abort.bind(recognition);
      if (originalAbort) {
        recognition.abort = function () {
          clearTimers();
          recognition.__legalchatSpeechActive = '0';
          return originalAbort();
        };
      }

      if (recognition.addEventListener) {
        recognition.addEventListener('start', function () {
          recognition.__legalchatSpeechActive = '1';
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
        recognition.addEventListener('end', function () {
          recognition.__legalchatSpeechActive = '0';
          clearTimers();
        });
        recognition.addEventListener('error', function () {
          recognition.__legalchatSpeechActive = '0';
          clearTimers();
        });
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
    window.__legalchatHasActiveSpeechRecognition = hasActiveSpeechRecognition;

    window.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') forceStopVoiceUiState();
    });

    document.addEventListener('visibilitychange', function () {
      if (document.hidden) forceStopVoiceUiState();
    });
  }

  function attachOverlayForceStopButton() {
    if (VOICE_OFF) return;
    var allNodes = document.querySelectorAll('div,section,article');
    for (var i = 0; i < allNodes.length; i += 1) {
      var node = allNodes[i];
      if (!node || !node.textContent) continue;
      if (node.querySelector('.legalchat-stt-force-stop')) continue;

      var text = node.textContent.replace(/\s+/g, ' ').trim();
      if (!/(Spra(?:ch|c)heingabe|Speech input|Voice input)/i.test(text)) continue;
      if (!/\b\d{2}:\d{2}\b/.test(text)) continue;

      var rect = node.getBoundingClientRect ? node.getBoundingClientRect() : null;
      if (!rect || rect.width < 120 || rect.width > 520 || rect.height < 70 || rect.height > 420) continue;

      var computed = window.getComputedStyle(node);
      if (computed && computed.display === 'none') continue;

      var button = document.createElement('button');
      button.type = 'button';
      button.className = 'legalchat-stt-force-stop';
      button.textContent = 'Stop Aufnahme';
      button.addEventListener('click', function (event) {
        event.preventDefault();
        event.stopPropagation();
        forceStopVoiceUiState();
      });
      node.appendChild(button);
      return;
    }
  }

  function parseRgbColor(value) {
    if (!value || typeof value !== 'string') return null;
    var match = value.match(/rgba?\(\s*(\d{1,3})[\s,]+(\d{1,3})[\s,]+(\d{1,3})/i);
    if (!match) return null;
    return {
      r: Number(match[1]),
      g: Number(match[2]),
      b: Number(match[3]),
    };
  }

  function looksOrange(value) {
    var rgb = parseRgbColor(value);
    if (!rgb) return false;
    return rgb.r >= 170 && rgb.g >= 80 && rgb.g <= 190 && rgb.b <= 120;
  }

  function isVisibleElement(el) {
    if (!el || !el.getBoundingClientRect) return false;
    var rect = el.getBoundingClientRect();
    if (!rect || rect.width < 18 || rect.height < 18) return false;
    var style = window.getComputedStyle(el);
    if (!style) return false;
    if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
    return true;
  }

  function findRecordingOverlayNode() {
    var nodes = document.querySelectorAll('div,section,article,aside');
    for (var i = 0; i < nodes.length; i += 1) {
      var node = nodes[i];
      if (!node || !node.textContent) continue;
      if (!isVisibleElement(node)) continue;

      var text = node.textContent.replace(/\s+/g, ' ').trim();
      if (!/(Spra(?:ch|c)heingabe|Speech input|Voice input|Voice recording)/i.test(text)) continue;
      if (!/\b\d{2}:\d{2}\b/.test(text)) continue;

      var rect = node.getBoundingClientRect();
      if (!rect || rect.width < 120 || rect.width > 620 || rect.height < 60 || rect.height > 460) continue;
      return node;
    }
    return null;
  }

  function dispatchReleaseEvents() {
    var names = ['pointerup', 'mouseup', 'touchend', 'keyup'];
    for (var i = 0; i < names.length; i += 1) {
      var name = names[i];
      try {
        window.dispatchEvent(new Event(name, { bubbles: true }));
      } catch (_windowEventError) {}
      try {
        document.dispatchEvent(new Event(name, { bubbles: true }));
      } catch (_documentEventError) {}
    }
  }

  function clickElementSafe(el) {
    if (!el) return;
    try {
      el.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }));
    } catch (_mousedownError) {}
    try {
      el.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true }));
    } catch (_mouseupError) {}
    try {
      el.click();
    } catch (_clickError) {}
  }

  function isLikelyMicPath(pathData) {
    if (!pathData) return false;
    var normalized = String(pathData).replace(/\s+/g, ' ');
    var looksLikeTypeIcon = /M4 7V5|M9 20h6/.test(normalized);
    var hasMicStem = /M12 4v16|M12 3v|M12 5v/.test(normalized);
    var hasMicCapsule = /a3 3 0 0 0-6 0|a3 3 0 0 0 6 0|M19 10v2|a7 7 0 0 1-14 0v-2/.test(normalized);
    return hasMicCapsule || (hasMicStem && !looksLikeTypeIcon);
  }

  function collectMicControls() {
    var controls = [];
    var nodes = document.querySelectorAll('button,div[role="button"],[aria-label],[title]');
    for (var i = 0; i < nodes.length; i += 1) {
      var node = nodes[i];
      if (!node || controls.indexOf(node) !== -1) continue;
      if (!isVisibleElement(node)) continue;

      var rect = node.getBoundingClientRect();
      if (rect.width > 180 || rect.height > 140) continue;

      var text = (node.textContent || '').trim();
      var aria = node.getAttribute('aria-label') || '';
      var title = node.getAttribute('title') || '';
      var cls = String(node.className || '');
      var meta = (text + ' ' + aria + ' ' + title + ' ' + cls).toLowerCase();

      var svg = node.querySelector('svg');
      var svgClass = svg ? String(svg.className && svg.className.baseVal ? svg.className.baseVal : svg.className || '') : '';
      var paths = svg ? svg.querySelectorAll('path') : [];
      var pathData = '';
      for (var j = 0; j < paths.length; j += 1) {
        pathData += ' ' + (paths[j].getAttribute('d') || '');
      }

      var looksLikeMicByText = /mic|micro|voice|speech|record|audio|sprache|aufnahme|diktat|transcribe/.test(meta);
      var looksLikeMicByIcon =
        /mic|microphone|voice|speech/.test(svgClass.toLowerCase()) ||
        /M12 19v3|a7 7 0 0 1-14 0v-2|M19 10v2/.test(pathData) ||
        isLikelyMicPath(pathData);
      var style = window.getComputedStyle(node);
      var looksActive =
        /active|record|listening|speaking/.test(cls.toLowerCase()) ||
        (style && (looksOrange(style.backgroundColor) || looksOrange(style.borderColor) || looksOrange(style.color)));

      var activeWithVoiceHint = looksActive && /mic|micro|voice|speech|record|audio|sprache|aufnahme|diktat/.test(meta);
      var activeMicIconOnly = looksActive && isLikelyMicPath(pathData);
      if (!looksLikeMicByText && !looksLikeMicByIcon && !activeWithVoiceHint && !activeMicIconOnly) continue;
      controls.push(node);
    }
    return controls;
  }

  function markVoiceControlDisabled(node) {
    if (!node) return;
    if (node.classList) node.classList.add('legalchat-voice-off-hidden');
    node.setAttribute('data-legalchat-voice-disabled', '1');
    node.setAttribute('aria-disabled', 'true');
    if (node.tagName === 'BUTTON') {
      try {
        node.disabled = true;
      } catch (_disableError) {}
    }
  }

  function enforceVoiceOffMode() {
    if (!VOICE_OFF) return;
    var htmlEl = document.documentElement;
    if (htmlEl) {
      htmlEl.setAttribute('data-legalchat-voice-mode', 'off');
      htmlEl.setAttribute('data-legalchat-voice-off', '1');
    }

    dispatchReleaseEvents();
    if (typeof window.__legalchatStopSpeechRecognition === 'function') {
      window.__legalchatStopSpeechRecognition();
    }
    if (typeof window.__legalchatStopAudioCapture === 'function') {
      window.__legalchatStopAudioCapture();
    }

    var overlay = findRecordingOverlayNode();
    if (overlay && overlay.parentNode) overlay.parentNode.removeChild(overlay);

    var controls = collectMicControls();
    for (var i = 0; i < controls.length; i += 1) {
      markVoiceControlDisabled(controls[i]);
    }

    var hintControls = document.querySelectorAll(
      '[aria-label*="voice" i],[aria-label*="speech" i],[aria-label*="micro" i],[aria-label*="spra" i],[aria-label*="aufnahme" i],[title*="voice" i],[title*="speech" i],[title*="micro" i],[title*="spra" i],[title*="aufnahme" i],[data-testid*="voice" i],[data-testid*="speech" i],[data-testid*="micro" i]',
    );
    for (var j = 0; j < hintControls.length; j += 1) {
      markVoiceControlDisabled(hintControls[j]);
    }
  }

  function forceStopVoiceUiState() {
    dispatchReleaseEvents();
    if (typeof window.__legalchatStopSpeechRecognition === 'function') {
      window.__legalchatStopSpeechRecognition();
    }
    if (typeof window.__legalchatStopAudioCapture === 'function') {
      window.__legalchatStopAudioCapture();
    }

    if (VOICE_OFF) {
      enforceVoiceOffMode();
      return;
    }

    var controls = collectMicControls();
    var now = Date.now();
    for (var i = 0; i < controls.length; i += 1) {
      var control = controls[i];
      var lastClickAt = Number(control.getAttribute('data-legalchat-force-stop-at') || 0);
      if (lastClickAt && now - lastClickAt < 5000) continue;
      clickElementSafe(control);
      control.setAttribute('data-legalchat-force-stop-at', String(now));
    }
  }

  function installVoiceUiStateWatchdog() {
    if (window.__legalchatVoiceUiWatchdogInstalled) return;
    window.__legalchatVoiceUiWatchdogInstalled = true;

    if (VOICE_OFF) {
      window.setInterval(function () {
        enforceVoiceOffMode();
      }, 700);
      return;
    }

    var staleSince = 0;
    var lastForceAt = 0;

    window.setInterval(function () {
      var overlay = findRecordingOverlayNode();
      var controls = collectMicControls();
      var uiLooksRecording = !!overlay;
      for (var i = 0; i < controls.length; i += 1) {
        var style = window.getComputedStyle(controls[i]);
        if (style && (looksOrange(style.backgroundColor) || looksOrange(style.borderColor) || looksOrange(style.color))) {
          uiLooksRecording = true;
          break;
        }
      }
      if (!uiLooksRecording) {
        staleSince = 0;
        lastForceAt = 0;
        return;
      }

      var hasActiveSpeech =
        typeof window.__legalchatHasActiveSpeechRecognition === 'function' &&
        window.__legalchatHasActiveSpeechRecognition();
      var hasActiveAudio =
        typeof window.__legalchatHasActiveAudioCapture === 'function' &&
        window.__legalchatHasActiveAudioCapture();
      var hasRealCapture = !!(hasActiveSpeech || hasActiveAudio);

      if (!staleSince) staleSince = Date.now();
      var elapsed = Date.now() - staleSince;

      if (!hasRealCapture && elapsed > 900) {
        if (!lastForceAt || Date.now() - lastForceAt > 1800) {
          forceStopVoiceUiState();
          lastForceAt = Date.now();
        }
      }

      if (hasRealCapture && STT_MAX_RECORDING_MS > 0 && elapsed > STT_MAX_RECORDING_MS + 2000) {
        if (!lastForceAt || Date.now() - lastForceAt > 1800) {
          forceStopVoiceUiState();
          lastForceAt = Date.now();
        }
      }

      if (!hasRealCapture && elapsed > 5000 && overlay && overlay.parentNode) {
        overlay.parentNode.removeChild(overlay);
      }
    }, 700);
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
    var originalTitle = String(document.title || '');
    var next = rewriteText(originalTitle);
    if (!originalTitle.trim() || LEGACY_BRAND_TITLE_PATTERN.test(originalTitle)) next = TAB_TITLE;
    if (next && next !== originalTitle) {
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
      var originalTitle = String(title.textContent || '');
      var rewrittenTitle = rewriteText(originalTitle);
      if (!originalTitle.trim() || LEGACY_BRAND_TITLE_PATTERN.test(originalTitle)) rewrittenTitle = TAB_TITLE;
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

  function setBrandAvatar() {
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
      if (img.dataset.legalchatAvatar === '1' && hasBrandAvatarSource(src)) continue;
      var alt = (img.getAttribute('alt') || '').toLowerCase();
      var width = img.width || 0;
      var height = img.height || 0;

      var looksLikeAvatar =
        /avatar|assistant|agent|bot|chat|lobe|fluent-emoji|npmmirror/i.test(src + ' ' + alt) ||
        (width > 0 && width <= 64 && height > 0 && height <= 64);

      if (!looksLikeAvatar) continue;

      if (!hasBrandAvatarSource(src)) {
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

      img.alt = DEFAULT_AGENT_NAME + ' - KI Jurist';
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

  function installLogoutOverride() {
    if (window.__legalchatLogoutOverrideInstalled) return;
    window.__legalchatLogoutOverrideInstalled = true;

    document.addEventListener(
      'click',
      function (event) {
        if (!event) return;
        var rawTarget = event.target;
        if (!rawTarget || !rawTarget.closest) return;

        var trigger = rawTarget.closest('button,a,[role="menuitem"],li,div');
        if (!trigger) return;

        var text = String(trigger.textContent || '')
          .replace(/\s+/g, ' ')
          .trim();
        if (!text) return;

        if (!/\b(Ausloggen|Abmelden|Logout|Log Out|Sign out)\b/i.test(text)) return;

        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
        window.location.assign('/logout');
      },
      true,
    );
  }

  function markBrandingReady() {
    var root = document.documentElement;
    if (!root) return;
    root.removeAttribute('data-legalchat-branding-pending');
    root.setAttribute('data-legalchat-branding-ready', '1');
    if (typeof window.__legalchatBrandingUnlock === 'function') {
      try {
        window.__legalchatBrandingUnlock();
      } catch (_unlockError) {}
    }
  }

  function applyBranding() {
    installAuth401Guard();
    installAudioCaptureGuard();
    installSpeechRecognitionGuard();
    suppressVoicePolicyRejections();
    installVoiceUiStateWatchdog();
    enforceVoiceOffMode();
    attachOverlayForceStopButton();
    rewriteTitle();
    rewriteHeadMetadata();
    ensureFaviconLinks();
    rewriteWelcomeBlocks();
    rewriteTextNodes(document.body);
    rewriteAttributes();
    replaceWordmarkSvg();
    setBrandAvatar();
    tuneNavIcons();
    installLogoutOverride();
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
      } finally {
        markBrandingReady();
      }
    }, 16);
  }

  installAuth401Guard();
  installAudioCaptureGuard();
  installSpeechRecognitionGuard();
  suppressVoicePolicyRejections();
  installLogoutOverride();
  installMcpClient();
  if (VOICE_OFF) enforceVoiceOffMode();
  ensureFaviconLinks();

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
