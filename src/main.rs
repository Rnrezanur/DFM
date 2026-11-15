// DFM (Download Fast Manager) - 100% Pure Rust Desktop Application
// Authors: Rezanur <rezanurbinshamim@gmail.com>

#![windows_subsystem = "windows"]

mod bridge;
mod clipboard;
mod db;
mod engine;
mod manager;
mod theme;
mod ui;

use bridge::BridgeServer;
use clipboard::ClipboardListener;
use db::Storage;
use eframe::egui::{self, ViewportBuilder};
use std::sync::atomic::AtomicBool;
use std::sync::mpsc;
use std::sync::Arc;
use ui::DfmApp;

fn main() -> eframe::Result<()> {
    // 1. Load configuration
    let storage = Storage::new();
    let settings = storage.load_settings();

    // 2. Setup background channels
    let (bridge_tx, bridge_rx) = mpsc::channel();
    let (clipboard_tx, clipboard_rx) = mpsc::channel();

    // 3. Start Browser Integration Bridge (Port 9666)
    let bridge_server = BridgeServer::new(settings.bridge_port, bridge_tx);
    bridge_server.start();

    // 4. Start Windows Clipboard Sniffer
    let clipboard_enabled = Arc::new(AtomicBool::new(settings.clipboard_listener_enabled));
    let clipboard_listener = ClipboardListener::new(clipboard_tx, Arc::clone(&clipboard_enabled));
    clipboard_listener.start();

    // 5. Try loading app icon
    let icon_data = load_app_icon();

    // 6. Launch eframe native window
    let mut viewport = ViewportBuilder::default()
        .with_title("DFM — Download Fast Manager (100% Rust Pro)")
        .with_inner_size([1020.0, 650.0])
        .with_min_inner_size([800.0, 500.0]);

    if let Some(icon) = icon_data {
        viewport = viewport.with_icon(icon);
    }

    let options = eframe::NativeOptions {
        viewport,
        ..Default::default()
    };

    eframe::run_native(
        "DFM",
        options,
        Box::new(move |_cc| {
            Ok(Box::new(DfmApp::new(settings, bridge_rx, clipboard_rx)))
        }),
    )
}

fn load_app_icon() -> Option<egui::IconData> {
    let icon_bytes = include_bytes!("../assets/dfm_icon.png");
    if let Ok(image) = image::load_from_memory(icon_bytes) {
        let rgba = image.to_rgba8();
        let (width, height) = rgba.dimensions();
        return Some(egui::IconData {
            rgba: rgba.into_raw(),
            width,
            height,
        });
    }
    None
}
