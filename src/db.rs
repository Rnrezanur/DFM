// DFM Database & Settings Persistence in Pure Rust
// Authors: Rezanur <rezanurbinshamim@gmail.com>

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::env;
use std::fs;
use std::path::PathBuf;

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct DownloadItem {
    pub id: String,
    pub url: String,
    pub filename: String,
    pub save_path: String,
    pub category: String,
    pub total_bytes: u64,
    pub downloaded_bytes: u64,
    pub status: String, // "pending", "downloading", "paused", "completed", "error"
    pub speed: u64,
    pub eta_secs: u64,
    pub segments_count: usize,
    pub added_date: String,
    pub error_message: String,
    pub is_video: bool,
    #[serde(default)]
    pub headers: HashMap<String, String>,
}

impl DownloadItem {
    pub fn progress_ratio(&self) -> f32 {
        if self.total_bytes > 0 {
            (self.downloaded_bytes as f32 / self.total_bytes as f32).clamp(0.0, 1.0)
        } else {
            0.0
        }
    }

    #[allow(dead_code)]
    pub fn progress_percent(&self) -> f32 {
        self.progress_ratio() * 100.0
    }
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct AppSettings {
    pub default_download_dir: String,
    pub default_segments: usize,
    pub max_concurrent_downloads: usize,
    pub dark_mode: bool,
    pub bridge_port: u16,
    pub clipboard_listener_enabled: bool,
}

impl Default for AppSettings {
    fn default() -> Self {
        let download_dir = if let Some(user_profile) = env::var_os("USERPROFILE") {
            let p = PathBuf::from(user_profile).join("Downloads");
            p.to_string_lossy().to_string()
        } else {
            "C:\\Downloads".to_string()
        };

        Self {
            default_download_dir: download_dir,
            default_segments: 16,
            max_concurrent_downloads: 5,
            dark_mode: true,
            bridge_port: 9666,
            clipboard_listener_enabled: true,
        }
    }
}

pub struct Storage {
    app_dir: PathBuf,
}

impl Storage {
    pub fn new() -> Self {
        let app_dir = if let Some(appdata) = env::var_os("APPDATA") {
            PathBuf::from(appdata).join("DFM")
        } else {
            PathBuf::from(".dfm")
        };
        let _ = fs::create_dir_all(&app_dir);
        Self { app_dir }
    }

    pub fn load_settings(&self) -> AppSettings {
        let path = self.app_dir.join("settings.json");
        if path.exists() {
            if let Ok(content) = fs::read_to_string(&path) {
                if let Ok(settings) = serde_json::from_str::<AppSettings>(&content) {
                    return settings;
                }
            }
        }
        let default_settings = AppSettings::default();
        self.save_settings(&default_settings);
        default_settings
    }

    pub fn save_settings(&self, settings: &AppSettings) {
        let path = self.app_dir.join("settings.json");
        if let Ok(json) = serde_json::to_string_pretty(settings) {
            let _ = fs::write(path, json);
        }
    }

    pub fn load_downloads(&self) -> Vec<DownloadItem> {
        let path = self.app_dir.join("downloads.json");
        if path.exists() {
            if let Ok(content) = fs::read_to_string(&path) {
                if let Ok(items) = serde_json::from_str::<Vec<DownloadItem>>(&content) {
                    return items;
                }
            }
        }
        Vec::new()
    }

    pub fn save_downloads(&self, items: &[DownloadItem]) {
        let path = self.app_dir.join("downloads.json");
        if let Ok(json) = serde_json::to_string_pretty(items) {
            let _ = fs::write(path, json);
        }
    }
}

// Helpers
pub fn determine_category(filename: &str) -> &'static str {
    let lower = filename.to_lowercase();
    let ext = lower.split('.').last().unwrap_or("");
    match ext {
        "zip" | "rar" | "7z" | "tar" | "gz" | "bz2" | "xz" | "iso" => "Compressed",
        "exe" | "msi" | "apk" | "bat" | "cmd" | "appx" => "Programs",
        "mp4" | "mkv" | "avi" | "mov" | "wmv" | "flv" | "webm" | "m4v" | "mp3" | "wav" | "flac" | "aac" | "ogg" | "m4a" => "Video & Audio",
        "pdf" | "doc" | "docx" | "xls" | "xlsx" | "ppt" | "pptx" | "txt" | "epub" => "Documents",
        _ => "Others",
    }
}

pub fn format_bytes(bytes: u64) -> String {
    if bytes == 0 {
        return "0 B".to_string();
    }
    const KB: f64 = 1024.0;
    const MB: f64 = 1024.0 * 1024.0;
    const GB: f64 = 1024.0 * 1024.0 * 1024.0;
    let b = bytes as f64;

    if b >= GB {
        format!("{:.2} GB", b / GB)
    } else if b >= MB {
        format!("{:.1} MB", b / MB)
    } else if b >= KB {
        format!("{:.1} KB", b / KB)
    } else {
        format!("{} B", bytes)
    }
}

pub fn format_speed(bytes_per_sec: u64) -> String {
    if bytes_per_sec == 0 {
        return "0 B/s".to_string();
    }
    format!("{}/s", format_bytes(bytes_per_sec))
}

pub fn format_eta(eta_secs: u64) -> String {
    if eta_secs == 0 {
        return "--:--:--".to_string();
    }
    let hours = eta_secs / 3600;
    let minutes = (eta_secs % 3600) / 60;
    let seconds = eta_secs % 60;
    if hours > 0 {
        format!("{:02}:{:02}:{:02}", hours, minutes, seconds)
    } else {
        format!("{:02}:{:02}", minutes, seconds)
    }
}

pub fn sanitize_filename(name: &str) -> String {
    let invalid = ['\\', '/', ':', '*', '?', '"', '<', '>', '|'];
    let sanitized: String = name.chars().map(|c| if invalid.contains(&c) { '_' } else { c }).collect();
    if sanitized.trim().is_empty() {
        "download.bin".to_string()
    } else {
        sanitized.trim().to_string()
    }
}
