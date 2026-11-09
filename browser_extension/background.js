// DFM Extension Background Service Worker

chrome.runtime.onInstalled.addListener(() => {
  // Create context menu item for links
  chrome.contextMenus.create({
    id: "dfm-download-link",
    title: "Download with DFM",
    contexts: ["link", "video", "audio"]
  });

  // Create context menu item for current page
  chrome.contextMenus.create({
    id: "dfm-download-page",
    title: "Download Media on this Page with DFM",
    contexts: ["page"]
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  let targetUrl = info.linkUrl || info.srcUrl || (info.menuItemId === "dfm-download-page" ? tab.url : null);
  if (targetUrl) {
    let cookieString = "";
    try {
      if (chrome.cookies) {
        const cookies = await chrome.cookies.getAll({ url: targetUrl });
        cookieString = cookies.map(c => `${c.name}=${c.value}`).join("; ");
      }
    } catch (e) {
      console.warn("Could not retrieve cookies for target URL:", e);
    }
    sendToDFM(targetUrl, tab.title, cookieString, tab.url);
  }
});

// Intercept browser downloads if user has bridge running
chrome.downloads.onCreated.addListener(async (downloadItem) => {
  // Can optionally capture browser-triggered downloads
});

function sendToDFM(url, pageTitle, cookies = "", referer = "") {
  fetch("http://127.0.0.1:9666/download", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      url: url,
      pageTitle: pageTitle,
      cookies: cookies,
      referer: referer,
      userAgent: navigator.userAgent
    })
  }).then(resp => {
    if (resp.ok) {
      console.log("URL sent to DFM successfully:", url);
    }
  }).catch(err => {
    console.warn("Could not connect to DFM desktop application. Is it running?", err);
  });
}
