// DFM Main-World Stream Sniffer Hook
// Injected into page context to intercept MediaSource, fetch, and XHR requests for video manifests (.m3u8, .mpd)

(function() {
  'use strict';
  if (window.__DFM_HOOK_INSTALLED__) return;
  window.__DFM_HOOK_INSTALLED__ = true;

  function reportMedia(url, type) {
    if (!url || typeof url !== 'string') return;
    if (url.startsWith('chrome-extension://') || url.startsWith('blob:')) return;

    let lower = url.toLowerCase();
    if (lower.includes('.m3u8') || lower.includes('.mpd') || lower.includes('.mp4') || lower.includes('.webm') || lower.includes('.ts') || lower.includes('/manifest')) {
      window.postMessage({
        source: 'DFM_SNIFFER',
        action: 'STREAM_FOUND',
        url: url,
        streamType: type || 'video'
      }, '*');
    }
  }

  // Intercept window.fetch
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

  // Intercept XMLHttpRequest
  const originalXhrOpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function(method, url, ...rest) {
    try {
      reportMedia(url, 'xhr');
    } catch (e) {}
    return originalXhrOpen.call(this, method, url, ...rest);
  };

  // Intercept HTMLMediaElement.prototype.play and src setter
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
})();
