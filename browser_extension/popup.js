// DFM Extension Popup Logic

document.addEventListener("DOMContentLoaded", async () => {
  const statusBadge = document.getElementById("statusBadge");
  const statusText = document.getElementById("statusText");
  const streamList = document.getElementById("streamList");
  const streamCount = document.getElementById("streamCount");
  const downloadPageBtn = document.getElementById("downloadPageBtn");

  // 1. Check local DFM desktop server connection
  let isDfmOnline = false;
  try {
    const res = await fetch("http://127.0.0.1:9666/status", { method: "GET" });
    if (res.ok) {
      isDfmOnline = true;
      statusBadge.className = "status-badge status-online";
      statusText.textContent = "DFM Connected";
    }
  } catch (e) {
    statusBadge.className = "status-badge status-offline";
    statusText.textContent = "DFM Desktop Offline";
  }

  // 2. Get active tab
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) return;

  // 3. Request detected streams for this tab
  chrome.runtime.sendMessage({ action: "GET_MEDIA", tabId: tab.id }, (response) => {
    let media = (response && response.media) || [];
    renderStreams(media, tab);
  });

  function renderStreams(media, currentTab) {
    streamCount.textContent = `${media.length} found`;

    if (!media || media.length === 0) {
      streamList.innerHTML = `
        <div class="empty-state">
          No streams detected yet.<br>Start video playback on this page to capture manifests and media links.
        </div>
      `;
      return;
    }

    streamList.innerHTML = "";
    media.forEach((item) => {
      const card = document.createElement("div");
      card.className = "stream-card";

      card.innerHTML = `
        <div class="stream-meta">
          <div class="stream-title">
            <span>⚡ ${item.quality || 'Video'}</span>
            <span class="stream-badge">${item.ext.toUpperCase()}</span>
          </div>
          <div class="stream-sub">
            ${item.sizeStr ? item.sizeStr + ' • ' : ''}${item.type}
          </div>
        </div>
        <button class="dl-btn" data-url="${item.url}">
          <span>Download</span>
        </button>
      `;

      const btn = card.querySelector(".dl-btn");
      btn.addEventListener("click", () => {
        btn.textContent = "Sending...";
        chrome.runtime.sendMessage({
          action: "TRIGGER_DOWNLOAD",
          media: item,
          tab: currentTab
        }, (res) => {
          if (res && res.success) {
            btn.textContent = "✓ In DFM";
            btn.style.background = "#16a34a";
          } else {
            btn.textContent = "Queued";
          }
          setTimeout(() => {
            btn.textContent = "Download";
            btn.style.background = "#2563eb";
          }, 2500);
        });
      });

      streamList.appendChild(card);
    });
  }

  // Download entire page / current URL
  downloadPageBtn.addEventListener("click", () => {
    downloadPageBtn.textContent = "Sending to DFM...";
    chrome.runtime.sendMessage({
      action: "TRIGGER_DOWNLOAD",
      media: {
        url: tab.url,
        quality: "Page Video",
        ext: "mp4"
      },
      tab: tab
    }, (res) => {
      downloadPageBtn.textContent = "✓ Sent to DFM!";
      setTimeout(() => {
        downloadPageBtn.textContent = "⚡ Download Current Page / Video";
      }, 2000);
    });
  });
});
