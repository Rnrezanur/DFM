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

chrome.contextMenus.onClicked.addListener((info, tab) => {
  let targetUrl = info.linkUrl || info.srcUrl || (info.menuItemId === "dfm-download-page" ? tab.url : null);
  if (targetUrl) {
    sendToDFM(targetUrl, tab.title);
  }
});

// Intercept browser downloads if user has bridge running
chrome.downloads.onCreated.addListener((downloadItem) => {
  // Can optionally prompt or send directly
});

function sendToDFM(url, pageTitle) {
  fetch("http://127.0.0.1:9666/download", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      url: url,
      pageTitle: pageTitle
    })
  }).then(resp => {
    if (resp.ok) {
      console.log("URL sent to DFM successfully:", url);
    }
  }).catch(err => {
    console.warn("Could not connect to DFM desktop application. Is it running?", err);
  });
}
