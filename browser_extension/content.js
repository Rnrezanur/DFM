// DFM Content Script - Injected into all web pages & iframes
// Renders the IDM-style floating "Download this video" button over video players

(function() {
  'use strict';

  // Inject sniffer hook into the webpage's DOM
  try {
    const s = document.createElement('script');
    s.src = chrome.runtime.getURL('sniffer_hook.js');
    s.onload = () => s.remove();
    (document.head || document.documentElement).appendChild(s);
  } catch (e) {
    console.debug('DFM hook injection notice:', e);
  }

  // Listen for messages from the injected sniffer hook
  window.addEventListener('message', (event) => {
    if (event.data && event.data.source === 'DFM_SNIFFER' && event.data.action === 'STREAM_FOUND') {
      chrome.runtime.sendMessage({
        action: 'REGISTER_DOM_STREAM',
        url: event.data.url,
        streamType: event.data.streamType
      }).catch(() => {});
    }
  });

  let detectedStreams = [];
  const trackedVideos = new WeakSet();

  // Query background for existing streams on this tab
  chrome.runtime.sendMessage({ action: 'GET_MEDIA' }, (response) => {
    if (response && response.media && response.media.length > 0) {
      detectedStreams = response.media;
      updateAllBars();
    }
  });

  // Listen for media detected events from background
  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.action === 'DFM_MEDIA_DETECTED' && msg.media) {
      if (!detectedStreams.some(m => m.url === msg.media.url)) {
        detectedStreams.unshift(msg.media);
      }
      updateAllBars();
    }
  });

  function findVideoContainer(video) {
    // If the video has a parent player container (e.g. video-js, plyr, html5-video-player)
    let parent = video.parentElement;
    if (!parent) return video;
    
    // Check up to 3 parents for relative or positioned video containers
    let current = parent;
    for (let i = 0; i < 3; i++) {
      if (!current) break;
      let style = window.getComputedStyle(current);
      let rect = current.getBoundingClientRect();
      if (rect.width > 200 && rect.height > 120) {
        if (style.position === 'relative' || style.position === 'absolute') {
          return current;
        }
      }
      current = current.parentElement;
    }

    // Default to direct parent
    let pStyle = window.getComputedStyle(parent);
    if (pStyle.position === 'static') {
      parent.classList.add('dfm-video-container-relative');
    }
    return parent;
  }

  function attachFloatingBar(video) {
    if (trackedVideos.has(video)) return;
    trackedVideos.add(video);

    // Skip tiny icons or audio elements disguised as video
    let rect = video.getBoundingClientRect();
    if (rect.width > 0 && rect.width < 160 && rect.height > 0 && rect.height < 100) {
      return;
    }

    const container = findVideoContainer(video);
    if (container.querySelector('.dfm-floating-bar')) return;

    const bar = document.createElement('div');
    bar.className = 'dfm-floating-bar';
    bar.innerHTML = `
      <button class="dfm-main-btn" title="Download video with DFM">
        <span class="dfm-logo-bolt">⚡</span>
        <span class="dfm-btn-label">Download this video</span>
        <span class="dfm-badge-count" style="display:none;">0</span>
        <span class="dfm-dropdown-arrow">▼</span>
      </button>
      <div class="dfm-dropdown-menu">
        <div class="dfm-dropdown-header">
          <span>Detected Streams</span>
          <span class="dfm-header-site">${window.location.hostname}</span>
        </div>
        <div class="dfm-stream-list"></div>
      </div>
    `;

    container.appendChild(bar);

    const mainBtn = bar.querySelector('.dfm-main-btn');
    const dropdown = bar.querySelector('.dfm-dropdown-menu');
    const streamList = bar.querySelector('.dfm-stream-list');
    const badge = bar.querySelector('.dfm-badge-count');
    const label = bar.querySelector('.dfm-btn-label');

    // Auto-fade timer
    let fadeTimer = null;
    function resetFade() {
      bar.classList.remove('dfm-fade');
      clearTimeout(fadeTimer);
      fadeTimer = setTimeout(() => {
        if (!dropdown.classList.contains('dfm-show')) {
          bar.classList.add('dfm-fade');
        }
      }, 4000);
    }

    container.addEventListener('mousemove', resetFade);
    video.addEventListener('play', resetFade);
    resetFade();

    // Toggle dropdown
    mainBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      e.preventDefault();

      if (detectedStreams.length === 0) {
        // Fallback: download current page / video src directly
        let src = video.currentSrc || video.src || window.location.href;
        triggerDownload({
          url: src,
          quality: 'Original Video',
          type: 'Direct Stream'
        }, mainBtn);
        return;
      }

      // If only 1 stream detected, download directly; if multiple, open menu
      if (detectedStreams.length === 1 && !dropdown.classList.contains('dfm-show')) {
        triggerDownload(detectedStreams[0], mainBtn);
      } else {
        dropdown.classList.toggle('dfm-show');
        renderMenuStreams(streamList, mainBtn);
      }
    });

    // Close dropdown on outside click
    document.addEventListener('click', (e) => {
      if (!bar.contains(e.target)) {
        dropdown.classList.remove('dfm-show');
      }
    });

    // Populate current streams
    renderBarState(bar, mainBtn, badge, label, streamList);
  }

  function renderBarState(bar, mainBtn, badge, label, streamList) {
    if (detectedStreams.length > 0) {
      badge.style.display = 'inline-block';
      badge.textContent = detectedStreams.length;
    }
  }

  function renderMenuStreams(streamList, mainBtn) {
    streamList.innerHTML = '';
    if (detectedStreams.length === 0) {
      streamList.innerHTML = '<div style="padding:10px;font-size:11px;color:#94a3b8;text-align:center;">Detecting streams... play video to capture</div>';
      return;
    }

    detectedStreams.forEach((stream) => {
      const item = document.createElement('div');
      item.className = 'dfm-stream-item';
      item.innerHTML = `
        <div class="dfm-stream-info">
          <div class="dfm-stream-quality">
            <span>⚡</span>
            <span>${stream.quality || 'Standard'}</span>
            <span class="dfm-quality-tag">${stream.ext.toUpperCase()}</span>
          </div>
          <span class="dfm-stream-type">${stream.type}</span>
        </div>
        <div class="dfm-stream-size">${stream.sizeStr || 'Stream'}</div>
      `;

      item.addEventListener('click', (e) => {
        e.stopPropagation();
        triggerDownload(stream, mainBtn);
        item.closest('.dfm-dropdown-menu').classList.remove('dfm-show');
      });

      streamList.appendChild(item);
    });
  }

  function triggerDownload(stream, btn) {
    let originalText = btn.innerHTML;
    btn.innerHTML = '⚡ <b>Connecting to DFM...</b>';
    btn.classList.add('dfm-success-toast');

    chrome.runtime.sendMessage({
      action: 'TRIGGER_DOWNLOAD',
      media: stream,
      tab: {
        url: window.location.href,
        title: document.title
      }
    }, (response) => {
      if (response && response.success) {
        btn.innerHTML = '✓ <b>Sent to DFM!</b>';
      } else {
        btn.innerHTML = '⚡ <b>Queued to DFM</b>';
      }
      setTimeout(() => {
        btn.innerHTML = originalText;
        btn.classList.remove('dfm-success-toast');
      }, 3000);
    });
  }

  function updateAllBars() {
    document.querySelectorAll('.dfm-floating-bar').forEach(bar => {
      const badge = bar.querySelector('.dfm-badge-count');
      const streamList = bar.querySelector('.dfm-stream-list');
      const mainBtn = bar.querySelector('.dfm-main-btn');
      if (badge && detectedStreams.length > 0) {
        badge.style.display = 'inline-block';
        badge.textContent = detectedStreams.length;
      }
      if (streamList && mainBtn && bar.querySelector('.dfm-dropdown-menu.dfm-show')) {
        renderMenuStreams(streamList, mainBtn);
      }
    });
  }

  function scanForVideos() {
    document.querySelectorAll('video').forEach(video => {
      attachFloatingBar(video);
    });
  }

  // Scan immediately and observe DOM mutations
  scanForVideos();
  const observer = new MutationObserver(() => {
    scanForVideos();
  });
  observer.observe(document.body || document.documentElement, {
    childList: true,
    subtree: true
  });

  // Re-scan periodically for lazy-loaded players
  setInterval(scanForVideos, 2000);

})();
