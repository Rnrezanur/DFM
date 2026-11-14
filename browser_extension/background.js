// DFM - High-Speed Video Stream Grabber Background Service Worker
// Intercepts HLS (m3u8), DASH (mpd), MP4, WebM, and media streams from any website.

const tabMedia = new Map();

// Helper to determine media type and quality tag
function parseMediaDetails(url, contentType = "", contentLength = 0) {
  let lowerUrl = url.toLowerCase();
  let type = "Video";
  let ext = "mp4";
  let quality = "HD";

  if (lowerUrl.includes(".m3u8") || contentType.includes("mpegurl")) {
    type = "HLS Stream";
    ext = "m3u8";
  } else if (lowerUrl.includes(".mpd") || contentType.includes("dash+xml")) {
    type = "DASH Stream";
    ext = "mpd";
  } else if (lowerUrl.includes(".webm") || contentType.includes("webm")) {
    type = "WebM Video";
    ext = "webm";
  } else if (lowerUrl.includes(".mp4") || contentType.includes("mp4")) {
    type = "MP4 Video";
    ext = "mp4";
  }

  // Quality heuristic
  if (/2160p?|4k/i.test(lowerUrl)) {
    quality = "4K 2160p";
  } else if (/1440p?|2k/i.test(lowerUrl)) {
    quality = "2K 1440p";
  } else if (/1080p?/i.test(lowerUrl)) {
    quality = "1080p Full HD";
  } else if (/720p?/i.test(lowerUrl)) {
    quality = "720p HD";
  } else if (/480p?/i.test(lowerUrl)) {
    quality = "480p SD";
  } else if (/360p?/i.test(lowerUrl)) {
    quality = "360p";
  } else if (/master\.m3u8/i.test(lowerUrl)) {
    quality = "Adaptive (Master)";
  }

  // Formatted file size string
  let sizeStr = "";
  if (contentLength > 0) {
    if (contentLength > 1024 * 1024 * 1024) {
      sizeStr = (contentLength / (1024 * 1024 * 1024)).toFixed(1) + " GB";
    } else if (contentLength > 1024 * 1024) {
      sizeStr = (contentLength / (1024 * 1024)).toFixed(1) + " MB";
    } else {
      sizeStr = (contentLength / 1024).toFixed(0) + " KB";
    }
  }

  return { type, ext, quality, sizeStr };
}

// Check if request is a video stream or manifest
function isMediaRequest(url, contentType, headers) {
  if (!url || url.startsWith("chrome-extension://") || url.startsWith("blob:")) return false;
  
  let lowerUrl = url.toLowerCase();
  // Filter out tiny segment chunks if master playlist is preferred, but keep m3u8 and mp4
  if (lowerUrl.includes(".m3u8") || lowerUrl.includes(".mpd")) return true;

  if (contentType) {
    let lowerCt = contentType.toLowerCase();
    if (lowerCt.includes("video/") ||
        lowerCt.includes("application/x-mpegurl") ||
        lowerCt.includes("application/vnd.apple.mpegurl") ||
        lowerCt.includes("application/dash+xml")) {
      return true;
    }
  }

  if (/\.(mp4|webm|m4v|flv|mov|mkv)(\?.*)?$/i.test(lowerUrl)) {
    return true;
  }

  return false;
}

// Sniff responses via chrome.webRequest
chrome.webRequest.onHeadersReceived.addListener(
  (details) => {
    if (details.tabId < 0) return;

    let headers = details.responseHeaders || [];
    let contentType = "";
    let contentLength = 0;
    let contentDisposition = "";

    for (let h of headers) {
      let name = h.name.toLowerCase();
      if (name === "content-type") contentType = h.value || "";
      if (name === "content-length") contentLength = parseInt(h.value, 10) || 0;
      if (name === "content-disposition") contentDisposition = h.value || "";
    }

    if (isMediaRequest(details.url, contentType, headers)) {
      // Ignore tiny chunks under 50KB unless it's a playlist (.m3u8 or .mpd)
      let isPlaylist = details.url.includes(".m3u8") || details.url.includes(".mpd");
      if (!isPlaylist && contentLength > 0 && contentLength < 50000) {
        return;
      }

      addMediaToTab(details.tabId, {
        url: details.url,
        initiator: details.initiator || details.documentUrl || "",
        contentType: contentType,
        contentLength: contentLength,
        contentDisposition: contentDisposition,
        method: details.method
      });
    }
  },
  { urls: ["<all_urls>"] },
  ["responseHeaders"]
);

function addMediaToTab(tabId, item) {
  if (!tabMedia.has(tabId)) {
    tabMedia.set(tabId, []);
  }

  let list = tabMedia.get(tabId);
  // Dedup identical URLs
  if (list.some(m => m.url === item.url)) return;

  let details = parseMediaDetails(item.url, item.contentType, item.contentLength);

  let mediaEntry = {
    id: "media_" + Math.random().toString(36).substr(2, 9),
    url: item.url,
    initiator: item.initiator,
    type: details.type,
    ext: details.ext,
    quality: details.quality,
    sizeStr: details.sizeStr,
    contentLength: item.contentLength,
    timestamp: Date.now()
  };

  list.unshift(mediaEntry);
  if (list.length > 50) list.pop(); // Keep top 50

  // Update badge count
  chrome.action.setBadgeText({ tabId: tabId, text: String(list.length) });
  chrome.action.setBadgeBackgroundColor({ tabId: tabId, color: "#2563eb" });

  // Store in storage for popup
  chrome.storage.local.set({ ["media_" + tabId]: list });

  // Notify tab's content script to show IDM floating player bar
  chrome.tabs.sendMessage(tabId, {
    action: "DFM_MEDIA_DETECTED",
    media: mediaEntry,
    totalCount: list.length
  }).catch(() => {});
}

// Clean up when tab navigates or closes
chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
  if (changeInfo.status === "loading" && changeInfo.url) {
    tabMedia.delete(tabId);
    chrome.action.setBadgeText({ tabId: tabId, text: "" });
    chrome.storage.local.remove("media_" + tabId);
  }
});

chrome.tabs.onRemoved.addListener((tabId) => {
  tabMedia.delete(tabId);
  chrome.storage.local.remove("media_" + tabId);
});

// Context Menus
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "dfm-download-link",
    title: "Download with DFM",
    contexts: ["link", "video", "audio"]
  });

  chrome.contextMenus.create({
    id: "dfm-download-page",
    title: "Grab All Media on This Page with DFM",
    contexts: ["page"]
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  let targetUrl = info.linkUrl || info.srcUrl || (info.menuItemId === "dfm-download-page" ? tab.url : null);
  if (targetUrl) {
    await sendToDFM({
      url: targetUrl,
      filename: tab.title || "Video Download",
      referer: tab.url,
      is_video: true
    });
  }
});

// Listen for messages from content.js or popup.js
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === "GET_MEDIA") {
    let tabId = msg.tabId || (sender.tab && sender.tab.id);
    let list = tabMedia.get(tabId) || [];
    sendResponse({ media: list });
    return true;
  }

  if (msg.action === "TRIGGER_DOWNLOAD") {
    let item = msg.media;
    let tab = sender.tab || msg.tab;
    let pageUrl = tab ? tab.url : (item.initiator || item.url);
    let pageTitle = tab ? tab.title : (item.quality || "DFM Video");

    sendToDFM({
      url: item.url,
      filename: pageTitle,
      referer: pageUrl,
      is_video: true,
      quality: item.quality
    }).then(res => {
      sendResponse({ success: res });
    });
    return true;
  }

  if (msg.action === "REGISTER_DOM_STREAM") {
    let tabId = sender.tab && sender.tab.id;
    if (tabId) {
      addMediaToTab(tabId, {
        url: msg.url,
        initiator: sender.tab.url,
        contentType: msg.contentType || "video/mp4",
        contentLength: msg.contentLength || 0
      });
    }
  }
});

// Send request to local DFM desktop server
async function sendToDFM(options) {
  let cookieString = "";
  try {
    if (chrome.cookies && options.url) {
      const cookies = await chrome.cookies.getAll({ url: options.url });
      cookieString = cookies.map(c => `${c.name}=${c.value}`).join("; ");
    }
  } catch (e) {
    console.warn("Could not retrieve cookies for target URL:", e);
  }

  let headers = {
    "Referer": options.referer || options.url,
    "Origin": options.referer ? new URL(options.referer).origin : ""
  };
  if (cookieString) {
    headers["Cookie"] = cookieString;
  }

  try {
    let response = await fetch("http://127.0.0.1:9666/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: options.url,
        filename: options.filename,
        is_video: Boolean(options.is_video),
        cookies: cookieString,
        referer: options.referer,
        headers: headers,
        userAgent: navigator.userAgent
      })
    });
    return response.ok;
  } catch (err) {
    console.warn("Could not send download to DFM desktop application:", err);
    return false;
  }
}
