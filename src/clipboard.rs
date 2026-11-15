// DFM Windows Clipboard URL Sniffer in Pure Rust
// Authors: Rezanur <rezanurbinshamim@gmail.com>

use arboard::Clipboard;
use std::collections::HashSet;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::mpsc::Sender;
use std::sync::Arc;
use std::thread;
use std::time::Duration;

pub struct ClipboardListener {
    tx: Sender<String>,
    enabled: Arc<AtomicBool>,
}

impl ClipboardListener {
    pub fn new(tx: Sender<String>, enabled: Arc<AtomicBool>) -> Self {
        Self { tx, enabled }
    }

    pub fn start(self) {
        thread::spawn(move || {
            let mut seen_urls: HashSet<String> = HashSet::new();

            loop {
                thread::sleep(Duration::from_millis(800));

                if !self.enabled.load(Ordering::Relaxed) {
                    continue;
                }

                if let Ok(mut cb) = Clipboard::new() {
                    if let Ok(text) = cb.get_text() {
                        let trimmed = text.trim();
                        if (trimmed.starts_with("http://") || trimmed.starts_with("https://"))
                            && !seen_urls.contains(trimmed)
                        {
                            if is_downloadable_url(trimmed) {
                                seen_urls.insert(trimmed.to_string());
                                let _ = self.tx.send(trimmed.to_string());
                            }
                        }
                    }
                }
            }
        });
    }
}

fn is_downloadable_url(url: &str) -> bool {
    let lower = url.to_lowercase();
    let path = lower.split('?').next().unwrap_or("");

    // Check extensions
    let exts = [
        ".zip", ".rar", ".7z", ".tar", ".gz", ".iso", ".exe", ".msi", ".apk",
        ".mp4", ".mkv", ".mp3", ".webm", ".avi", ".mov", ".flv", ".pdf", ".epub",
        ".m3u8", ".mpd",
    ];
    if exts.iter().any(|ext| path.ends_with(ext)) {
        return true;
    }

    // Check video domains
    let video_domains = [
        "youtube.com", "youtu.be", "tiktok.com", "twitter.com", "x.com",
        "facebook.com", "instagram.com", "vimeo.com", "twitch.tv", "pornhub.com",
        "xvideos.com", "spankbang.com", "dailymotion.com",
    ];
    if video_domains.iter().any(|dom| lower.contains(dom)) {
        return true;
    }

    false
}
