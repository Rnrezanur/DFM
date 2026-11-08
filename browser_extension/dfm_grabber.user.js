// ==UserScript==
// @name         DFM Web Video Grabber (IDM Alternative)
// @namespace    https://github.com/dfm/dfm
// @version      1.0
// @description  Adds a one-click "Download with DFM" floating button to YouTube and media players
// @author       DFM Team
// @match        *://*.youtube.com/*
// @match        *://*.facebook.com/*
// @match        *://*.twitter.com/*
// @match        *://*.x.com/*
// @match        *://*.tiktok.com/*
// @match        *://*.vimeo.com/*
// @match        *://*.dailymotion.com/*
// @match        *://*.twitch.tv/*
// @grant        GM_xmlhttpRequest
// @connect      127.0.0.1
// ==/UserScript==

(function() {
    'use strict';

    function createDownloadButton() {
        if (document.getElementById('dfm-float-btn')) return;

        const btn = document.createElement('div');
        btn.id = 'dfm-float-btn';
        btn.innerHTML = '⚡ <b>Download with DFM</b>';
        btn.style.position = 'fixed';
        btn.style.bottom = '20px';
        btn.style.right = '20px';
        btn.style.zIndex = '999999';
        btn.style.background = 'linear-gradient(135deg, #3b82f6, #1d4ed8)';
        btn.style.color = '#ffffff';
        btn.style.padding = '10px 16px';
        btn.style.borderRadius = '24px';
        btn.style.boxShadow = '0 4px 15px rgba(0,0,0,0.3)';
        btn.style.cursor = 'pointer';
        btn.style.fontFamily = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
        btn.style.fontSize = '13px';
        btn.style.fontWeight = '600';
        btn.style.transition = 'all 0.2s ease';
        btn.style.display = 'flex';
        btn.style.alignItems = 'center';
        btn.style.gap = '8px';

        btn.onmouseover = () => {
            btn.style.transform = 'translateY(-2px)';
            btn.style.boxShadow = '0 6px 20px rgba(59, 130, 246, 0.4)';
        };
        btn.onmouseout = () => {
            btn.style.transform = 'translateY(0)';
            btn.style.boxShadow = '0 4px 15px rgba(0,0,0,0.3)';
        };

        btn.onclick = () => {
            const currentUrl = window.location.href;
            const title = document.title;
            btn.innerHTML = '⏳ <b>Sending...</b>';

            if (typeof GM_xmlhttpRequest !== 'undefined') {
                GM_xmlhttpRequest({
                    method: 'POST',
                    url: 'http://127.0.0.1:9666/download',
                    headers: { 'Content-Type': 'application/json' },
                    data: JSON.stringify({ url: currentUrl, filename: title, is_video: true }),
                    onload: function() {
                        btn.innerHTML = '✓ <b>Sent to DFM!</b>';
                        setTimeout(() => { btn.innerHTML = '⚡ <b>Download with DFM</b>'; }, 2000);
                    },
                    onerror: function() {
                        btn.innerHTML = '❌ <b>DFM not running</b>';
                        setTimeout(() => { btn.innerHTML = '⚡ <b>Download with DFM</b>'; }, 3000);
                    }
                });
            } else {
                fetch('http://127.0.0.1:9666/download', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: currentUrl, filename: title, is_video: true })
                }).then(() => {
                    btn.innerHTML = '✓ <b>Sent to DFM!</b>';
                    setTimeout(() => { btn.innerHTML = '⚡ <b>Download with DFM</b>'; }, 2000);
                }).catch(() => {
                    btn.innerHTML = '❌ <b>DFM not running</b>';
                    setTimeout(() => { btn.innerHTML = '⚡ <b>Download with DFM</b>'; }, 3000);
                });
            }
        };

        document.body.appendChild(btn);
    }

    window.addEventListener('load', () => setTimeout(createDownloadButton, 1000));
    setInterval(() => {
        if (!document.getElementById('dfm-float-btn')) {
            createDownloadButton();
        }
    }, 3000);
})();
