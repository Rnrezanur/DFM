document.addEventListener("DOMContentLoaded", async () => {
  const statusEl = document.getElementById("status");
  const sendBtn = document.getElementById("sendCurrent");

  try {
    const res = await fetch("http://127.0.0.1:9666/status");
    if (res.ok) {
      statusEl.className = "status-badge status-online";
      statusEl.textContent = "● DFM Connected";
    } else {
      throw new Error();
    }
  } catch (e) {
    statusEl.className = "status-badge status-offline";
    statusEl.textContent = "○ DFM Desktop Not Running";
  }

  sendBtn.addEventListener("click", async () => {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab && tab.url) {
      try {
        await fetch("http://127.0.0.1:9666/download", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: tab.url, filename: tab.title })
        });
        sendBtn.textContent = "✓ Sent to DFM!";
        setTimeout(() => window.close(), 1000);
      } catch (err) {
        alert("Could not connect to DFM application. Please ensure DFM is running.");
      }
    }
  });
});
