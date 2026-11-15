// DFM Main-World Stream Sniffer Hook (Supercharged Engine)
// Injected directly into page context to intercept MediaSource, fetch, XHR, and embedded video manifests (.m3u8, .mpd, .mp4)
// Supports all tube sites (Pornhub, Xvideos, YouTube, Spankbang, Vimeo, Dailymotion, anime & streaming players)

(function() {
  'use strict';
  if (window.__DFM_HOOK_INSTALLED__) return;
  window.__DFM_HOOK_INSTALLED__ = true;

  const reportedUrls = new Set();

  function reportMedia(url, type, quality) {
    if (!url || typeof url !== 'string') return;
    if (url.startsWith('chrome-extension://') || url.startsWith('blob:') || url.startsWith('data:')) return;

    // Clean escaped slashes
    url = url.replace(/\\\//g, '/');

    // Ignore duplicates
    if (reportedUrls.has(url)) return;

    let lower = url.toLowerCase();
    const isVideoExtension = lower.includes('.m3u8') || lower.includes('.mpd') || lower.includes('.mp4') || lower.includes('.webm') || lower.includes('.m4v') || lower.includes('.flv');
    const isStreamPath = lower.includes('/manifest') || lower.includes('/playlist') || lower.includes('/hls/') || lower.includes('/dash/') || lower.includes('videoplayback') || lower.includes('googlevideo.com');

    if (isVideoExtension || isStreamPath) {
      reportedUrls.add(url);
      window.postMessage({
        source: 'DFM_SNIFFER',
        action: 'STREAM_FOUND',
        url: url,
        streamType: type || 'video',
        quality: quality || null
      }, '*');
    }
  }

  // 1. Intercept window.fetch
  const originalFetch = window.fetch;
  if (originalFetch) {
    window.fetch = function(...args) {
      try {
        let input = args[0];
        let url = typeof input === 'string' ? input : (input && input.url ? input.url : '');
        reportMedia(url, 'fetch');
      } catch (e) {}
      return originalFetch.apply(this, args);
    };
  }

  // 2. Intercept XMLHttpRequest
  const originalXhrOpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function(method, url, ...rest) {
    try {
      reportMedia(url, 'xhr');
    } catch (e) {}
    return originalXhrOpen.call(this, method, url, ...rest);
  };

  // 3. Intercept HTMLMediaElement.prototype.play
  const originalPlay = HTMLMediaElement.prototype.play;
  HTMLMediaElement.prototype.play = function(...args) {
    try {
      if (this.src && !this.src.startsWith('blob:')) {
        reportMedia(this.src, 'media_src');
      }
      if (this.currentSrc && !this.currentSrc.startsWith('blob:')) {
        reportMedia(this.currentSrc, 'media_currentSrc');
      }
    } catch (e) {}
    return originalPlay.apply(this, args);
  };

  // 4. Intercept HTMLMediaElement.prototype.src setter
  try {
    const originalSrcDesc = Object.getOwnPropertyDescriptor(HTMLMediaElement.prototype, 'src');
    if (originalSrcDesc && originalSrcDesc.set) {
      Object.defineProperty(HTMLMediaElement.prototype, 'src', {
        set: function(val) {
          reportMedia(val, 'media_src_setter');
          return originalSrcDesc.set.call(this, val);
        },
        get: originalSrcDesc.get,
        configurable: true
      });
    }
  } catch (e) {}

  // 5. Intercept HTMLSourceElement.prototype.src setter
  try {
    const originalSourceSrcDesc = Object.getOwnPropertyDescriptor(HTMLSourceElement.prototype, 'src');
    if (originalSourceSrcDesc && originalSourceSrcDesc.set) {
      Object.defineProperty(HTMLSourceElement.prototype, 'src', {
        set: function(val) {
          reportMedia(val, 'source_src_setter');
          return originalSourceSrcDesc.set.call(this, val);
        },
        get: originalSourceSrcDesc.get,
        configurable: true
      });
    }
  } catch (e) {}

  // 6. Sniff adult and tube player global configurations (Pornhub, Xvideos, Spankbang, etc.)
  function scanGlobalConfigs() {
    try {
      // Check Pornhub / MindGeek player variables
      for (let key in window) {
        if (!key) continue;
        if (key.startsWith('flashvars') || key.startsWith('playerObj') || key.startsWith('mgp_') || key.startsWith('player_')) {
          let val = window[key];
          if (val && typeof val === 'object') {
            // Check mediaDefinitions array (Pornhub format)
            if (Array.isArray(val.mediaDefinitions)) {
              val.mediaDefinitions.forEach(m => {
                if (m && m.videoUrl) {
                  let q = m.quality ? (Array.isArray(m.quality) ? m.quality.join('/') : String(m.quality)) : null;
                  reportMedia(m.videoUrl, 'tube_manifest', q ? `${q}p` : null);
                }
              });
            }
            // Check quality properties: quality_1080p, quality_720p, etc.
            ['quality_2160p', 'quality_1440p', 'quality_1080p', 'quality_720p', 'quality_480p', 'quality_360p', 'quality_240p'].forEach(qKey => {
              if (val[qKey] && typeof val[qKey] === 'string') {
                reportMedia(val[qKey], 'tube_direct', qKey.replace('quality_', ''));
              }
            });
          }
        }
      }

      // Check YouTube player response
      if (window.ytInitialPlayerResponse && window.ytInitialPlayerResponse.streamingData) {
        const sd = window.ytInitialPlayerResponse.streamingData;
        if (sd.hlsManifestUrl) {
          reportMedia(sd.hlsManifestUrl, 'youtube_hls', 'Adaptive HD');
        }
        if (Array.isArray(sd.formats)) {
          sd.formats.forEach(f => {
            if (f.url) reportMedia(f.url, 'youtube_fmt', f.qualityLabel || f.quality);
          });
        }
      }
    } catch (e) {}
  }

  // Scan on document load and periodically
  if (document.readyState === 'complete' || document.readyState === 'interactive') {
    scanGlobalConfigs();
  } else {
    window.addEventListener('DOMContentLoaded', scanGlobalConfigs);
    window.addEventListener('load', scanGlobalConfigs);
  }
  setInterval(scanGlobalConfigs, 2000);
})();
