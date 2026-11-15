// DFM Modern IDM User Interface in Pure Rust
// Authors: Rezanur <rezanurbinshamim@gmail.com>

use crate::bridge::BridgeMessage;
use crate::db::{format_bytes, format_eta, format_speed, sanitize_filename, AppSettings, DownloadItem};
use crate::manager::DownloadManager;
use crate::theme::apply_theme;
use eframe::egui::{self, Color32, RichText, Rounding, Vec2};
use std::collections::HashMap;
use std::process::Command;
use std::sync::mpsc::Receiver;

pub struct DfmApp {
    pub manager: DownloadManager,
    pub settings: AppSettings,
    pub selected_id: Option<String>,
    pub selected_category: String,
    pub search_query: String,

    // Add dialog state
    pub show_add_dialog: bool,
    pub add_url: String,
    pub add_filename: String,
    pub add_save_dir: String,
    pub add_segments: usize,
    pub add_headers: HashMap<String, String>,
    pub add_is_video: bool,
    pub add_probing: bool,
    pub add_probe_error: String,

    // Progress dialog state
    pub show_progress_dialog: bool,
    pub progress_id: Option<String>,

    // Settings dialog state
    pub show_settings_dialog: bool,

    // Background channels
    pub bridge_rx: Receiver<BridgeMessage>,
    pub clipboard_rx: Receiver<String>,
}

impl DfmApp {
    pub fn new(
        settings: AppSettings,
        bridge_rx: Receiver<BridgeMessage>,
        clipboard_rx: Receiver<String>,
    ) -> Self {
        let manager = DownloadManager::new();
        let add_save_dir = settings.default_download_dir.clone();
        let add_segments = settings.default_segments;

        Self {
            manager,
            settings,
            selected_id: None,
            selected_category: "All Downloads".to_string(),
            search_query: String::new(),

            show_add_dialog: false,
            add_url: String::new(),
            add_filename: String::new(),
            add_save_dir,
            add_segments,
            add_headers: HashMap::new(),
            add_is_video: false,
            add_probing: false,
            add_probe_error: String::new(),

            show_progress_dialog: false,
            progress_id: None,

            show_settings_dialog: false,

            bridge_rx,
            clipboard_rx,
        }
    }

    pub fn poll_background_events(&mut self) {
        // 1. Check browser bridge messages
        while let Ok(msg) = self.bridge_rx.try_recv() {
            self.add_url = msg.url.clone();
            self.add_is_video = msg.is_video;
            self.add_headers = msg.headers;
            if let Some(fn_name) = msg.filename {
                self.add_filename = sanitize_filename(&fn_name);
            } else {
                let name = msg.url.split('?').next().unwrap_or("").split('/').last().unwrap_or("download.bin");
                self.add_filename = sanitize_filename(name);
            }
            self.show_add_dialog = true;
            self.add_probing = false;
            self.add_probe_error.clear();
        }

        // 2. Check clipboard messages
        while let Ok(url) = self.clipboard_rx.try_recv() {
            if self.settings.clipboard_listener_enabled && !self.show_add_dialog {
                self.add_url = url.clone();
                let name = url.split('?').next().unwrap_or("").split('/').last().unwrap_or("download.bin");
                self.add_filename = sanitize_filename(name);
                self.add_headers.clear();
                self.add_is_video = false;
                self.show_add_dialog = true;
                self.add_probing = false;
                self.add_probe_error.clear();
            }
        }

        // 3. Sync live download progress updates
        self.manager.sync_updates();
    }

    fn open_file(path: &str) {
        let _ = Command::new("explorer").arg(path).spawn();
    }

    fn open_folder(path: &str) {
        if let Some(parent) = std::path::Path::new(path).parent() {
            let _ = Command::new("explorer").arg(parent).spawn();
        } else {
            let _ = Command::new("explorer").arg(path).spawn();
        }
    }
}

impl eframe::App for DfmApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        apply_theme(ctx, self.settings.dark_mode);
        self.poll_background_events();
        ctx.request_repaint_after(std::time::Duration::from_millis(150));

        // 1. Top Panel: Toolbar
        egui::TopBottomPanel::top("top_toolbar").show(ctx, |ui| {
            ui.add_space(4.0);
            ui.horizontal(|ui| {
                // Action Buttons matching IDM layout
                let add_btn = ui.button(RichText::new("⚡ + Add URL").strong());
                if add_btn.clicked() {
                    self.show_add_dialog = true;
                    self.add_url.clear();
                    self.add_filename.clear();
                    self.add_headers.clear();
                    self.add_probe_error.clear();
                }

                ui.separator();

                let can_act = self.selected_id.is_some();

                if ui.add_enabled(can_act, egui::Button::new("▶ Resume")).clicked() {
                    if let Some(ref id) = self.selected_id {
                        self.manager.resume_download(id);
                    }
                }

                if ui.add_enabled(can_act, egui::Button::new("⏸ Pause")).clicked() {
                    if let Some(ref id) = self.selected_id {
                        self.manager.pause_download(id);
                    }
                }

                if ui.button("⏹ Stop All").clicked() {
                    self.manager.stop_all();
                }

                if ui.add_enabled(can_act, egui::Button::new("🗑 Delete")).clicked() {
                    if let Some(ref id) = self.selected_id.clone() {
                        self.manager.delete_download(id, false);
                        self.selected_id = None;
                    }
                }

                ui.separator();

                if ui.button("📁 Open Folder").clicked() {
                    let dir = self.settings.default_download_dir.clone();
                    let _ = Command::new("explorer").arg(dir).spawn();
                }

                if ui.button("⚙ Settings").clicked() {
                    self.show_settings_dialog = true;
                }

                let theme_icon = if self.settings.dark_mode { "☀ Light" } else { "🌙 Dark" };
                if ui.button(theme_icon).clicked() {
                    self.settings.dark_mode = !self.settings.dark_mode;
                    self.manager.storage.save_settings(&self.settings);
                }

                // Right-aligned search bar
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    ui.add(egui::TextEdit::singleline(&mut self.search_query).hint_text("🔍 Quick search..."));
                });
            });
            ui.add_space(4.0);
        });

        // 2. Bottom Panel: Status Bar
        egui::TopBottomPanel::bottom("bottom_status_bar").show(ctx, |ui| {
            ui.horizontal(|ui| {
                ui.label(RichText::new("● Engine Active (100% Rust Multi-Threaded)").color(Color32::from_rgb(74, 222, 128)));
                ui.separator();
                ui.label(format!("Port {} • Browser Extension Active", self.settings.bridge_port));
                ui.separator();
                ui.label(format!("Active: {}", self.manager.active_count()));
                ui.separator();
                ui.label(format!("Total Speed: {}", format_speed(self.manager.total_speed())));
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    ui.label(RichText::new("RAM: ~18 MB").color(Color32::from_rgb(56, 189, 248)));
                });
            });
        });

        // 3. Left Panel: Categories Sidebar
        egui::SidePanel::left("left_categories_sidebar")
            .resizable(true)
            .default_width(170.0)
            .width_range(140.0..=240.0)
            .show(ctx, |ui| {
                ui.add_space(8.0);
                ui.label(RichText::new("CATEGORIES").font(egui::FontId::proportional(11.0)).color(Color32::from_rgb(148, 163, 184)));
                ui.add_space(4.0);

                let cats = [
                    ("⚡ All Downloads", self.manager.items.len()),
                    ("⏳ Downloading", self.manager.items.iter().filter(|x| x.status == "downloading").count()),
                    ("✓ Completed", self.manager.items.iter().filter(|x| x.status == "completed").count()),
                    ("⏸ Paused", self.manager.items.iter().filter(|x| x.status == "paused").count()),
                    ("❌ Error", self.manager.items.iter().filter(|x| x.status == "error").count()),
                    ("📦 Compressed", self.manager.items.iter().filter(|x| x.category == "Compressed").count()),
                    ("💻 Programs", self.manager.items.iter().filter(|x| x.category == "Programs").count()),
                    ("🎬 Video & Audio", self.manager.items.iter().filter(|x| x.category == "Video & Audio").count()),
                    ("📄 Documents", self.manager.items.iter().filter(|x| x.category == "Documents").count()),
                    ("📁 Others", self.manager.items.iter().filter(|x| x.category == "Others").count()),
                ];

                for (name, count) in cats {
                    let clean_name = name.split_whitespace().skip(1).collect::<Vec<&str>>().join(" ");
                    let target_key = if name.contains("All") { "All Downloads" } else { &clean_name };
                    let is_sel = self.selected_category == target_key;

                    let label_text = format!("{} ({})", name, count);
                    let resp = ui.selectable_label(is_sel, label_text);
                    if resp.clicked() {
                        self.selected_category = target_key.to_string();
                    }
                }
            });

        // 4. Central Panel: Downloads Table Grid
        egui::CentralPanel::default().show(ctx, |ui| {
            let filtered_items: Vec<DownloadItem> = self.manager.items.iter().filter(|item| {
                // Category match
                let cat_match = match self.selected_category.as_str() {
                    "All Downloads" => true,
                    "Downloading" => item.status == "downloading",
                    "Completed" => item.status == "completed",
                    "Paused" => item.status == "paused",
                    "Error" => item.status == "error",
                    cat => item.category == cat,
                };

                // Search query match
                let search_match = if self.search_query.is_empty() {
                    true
                } else {
                    item.filename.to_lowercase().contains(&self.search_query.to_lowercase())
                        || item.url.to_lowercase().contains(&self.search_query.to_lowercase())
                };

                cat_match && search_match
            }).cloned().collect();

            // Table Header
            ui.add_space(4.0);
            ui.horizontal(|ui| {
                ui.label(RichText::new("FILE NAME").strong().color(Color32::from_rgb(148, 163, 184)));
                ui.allocate_ui_with_layout(Vec2::new(90.0, 18.0), egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    ui.label(RichText::new("SIZE").strong().color(Color32::from_rgb(148, 163, 184)));
                });
                ui.allocate_ui_with_layout(Vec2::new(120.0, 18.0), egui::Layout::centered_and_justified(egui::Direction::LeftToRight), |ui| {
                    ui.label(RichText::new("PROGRESS").strong().color(Color32::from_rgb(148, 163, 184)));
                });
                ui.allocate_ui_with_layout(Vec2::new(90.0, 18.0), egui::Layout::centered_and_justified(egui::Direction::LeftToRight), |ui| {
                    ui.label(RichText::new("STATUS").strong().color(Color32::from_rgb(148, 163, 184)));
                });
                ui.allocate_ui_with_layout(Vec2::new(100.0, 18.0), egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    ui.label(RichText::new("SPEED").strong().color(Color32::from_rgb(148, 163, 184)));
                });
                ui.allocate_ui_with_layout(Vec2::new(80.0, 18.0), egui::Layout::centered_and_justified(egui::Direction::LeftToRight), |ui| {
                    ui.label(RichText::new("TIME LEFT").strong().color(Color32::from_rgb(148, 163, 184)));
                });
                ui.allocate_ui_with_layout(Vec2::new(140.0, 18.0), egui::Layout::centered_and_justified(egui::Direction::LeftToRight), |ui| {
                    ui.label(RichText::new("ADDED").strong().color(Color32::from_rgb(148, 163, 184)));
                });
            });
            ui.separator();

            let mut action_pause: Option<String> = None;
            let mut action_resume: Option<String> = None;
            let mut action_delete: Option<(String, bool)> = None;

            // Table Rows
            egui::ScrollArea::vertical().show(ui, |ui| {
                if filtered_items.is_empty() {
                    ui.add_space(40.0);
                    ui.vertical_centered(|ui| {
                        ui.label(RichText::new("No downloads in this category").color(Color32::from_rgb(148, 163, 184)));
                        ui.label(RichText::new("Click '+ Add URL' or use the Browser Extension to start a download").font(egui::FontId::proportional(12.0)));
                    });
                    return;
                }

                for item in &filtered_items {
                    let is_selected = self.selected_id.as_deref() == Some(&item.id);
                    let row_bg = if is_selected {
                        if self.settings.dark_mode { Color32::from_rgb(37, 99, 235) } else { Color32::from_rgb(219, 234, 254) }
                    } else {
                        Color32::TRANSPARENT
                    };

                    let row_resp = egui::Frame::none()
                        .fill(row_bg)
                        .rounding(Rounding::same(4.0))
                        .show(ui, |ui| {
                            ui.horizontal(|ui| {
                                // Filename with extension badge
                                let ext = item.filename.split('.').last().unwrap_or("FILE").to_uppercase();
                                ui.label(RichText::new(format!("[{}]", ext)).color(Color32::from_rgb(56, 189, 248)).strong());
                                ui.label(RichText::new(&item.filename).strong());

                                // Size
                                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                                    ui.label(&item.added_date);
                                    ui.add_space(10.0);
                                    ui.label(format_eta(item.eta_secs));
                                    ui.add_space(10.0);
                                    ui.label(format_speed(item.speed));
                                    ui.add_space(10.0);

                                    // Status Badge
                                    let (status_text, status_col) = match item.status.as_str() {
                                        "downloading" => ("Downloading", Color32::from_rgb(56, 189, 248)),
                                        "completed" => ("Completed", Color32::from_rgb(74, 222, 128)),
                                        "paused" => ("Paused", Color32::from_rgb(250, 204, 21)),
                                        "error" => ("Error", Color32::from_rgb(248, 113, 113)),
                                        _ => ("Pending", Color32::from_rgb(148, 163, 184)),
                                    };
                                    ui.label(RichText::new(status_text).color(status_col).strong());
                                    ui.add_space(10.0);

                                    // Progress Bar
                                    let prog_ratio = item.progress_ratio();
                                    ui.add(egui::ProgressBar::new(prog_ratio).show_percentage().desired_width(110.0));
                                    ui.add_space(10.0);

                                    ui.label(if item.total_bytes > 0 { format_bytes(item.total_bytes) } else { "--".to_string() });
                                });
                            });
                        });

                    let interact_resp = ui.interact(row_resp.response.rect, ui.id().with(&item.id), egui::Sense::click());
                    if interact_resp.clicked() {
                        self.selected_id = Some(item.id.clone());
                    }
                    if interact_resp.double_clicked() {
                        if item.status == "completed" {
                            Self::open_file(&item.save_path);
                        } else {
                            self.progress_id = Some(item.id.clone());
                            self.show_progress_dialog = true;
                        }
                    }

                    // Context Menu
                    interact_resp.context_menu(|ui| {
                        if item.status == "completed" {
                            if ui.button("Open File").clicked() {
                                Self::open_file(&item.save_path);
                                ui.close_menu();
                            }
                            if ui.button("Open Folder").clicked() {
                                Self::open_folder(&item.save_path);
                                ui.close_menu();
                            }
                        } else if item.status == "downloading" {
                            if ui.button("Pause").clicked() {
                                action_pause = Some(item.id.clone());
                                ui.close_menu();
                            }
                        } else {
                            if ui.button("Resume").clicked() {
                                action_resume = Some(item.id.clone());
                                ui.close_menu();
                            }
                        }
                        if ui.button("Details & Metrics").clicked() {
                            self.progress_id = Some(item.id.clone());
                            self.show_progress_dialog = true;
                            ui.close_menu();
                        }
                        ui.separator();
                        if ui.button("Delete").clicked() {
                            action_delete = Some((item.id.clone(), false));
                            ui.close_menu();
                        }
                        if ui.button("Delete File from Disk").clicked() {
                            action_delete = Some((item.id.clone(), true));
                            ui.close_menu();
                        }
                    });

                    ui.separator();
                }
            });

            if let Some(id) = action_pause {
                self.manager.pause_download(&id);
            }
            if let Some(id) = action_resume {
                self.manager.resume_download(&id);
            }
            if let Some((id, disk)) = action_delete {
                self.manager.delete_download(&id, disk);
            }
        });

        // 5. Modal: Add Download Dialog
        if self.show_add_dialog {
            egui::Window::new("Enter New Download - DFM")
                .collapsible(false)
                .resizable(false)
                .default_width(480.0)
                .anchor(egui::Align2::CENTER_CENTER, [0.0, 0.0])
                .show(ctx, |ui| {
                    ui.label("Download Address (URL):");
                    ui.add(egui::TextEdit::singleline(&mut self.add_url).desired_width(450.0));

                    ui.add_space(6.0);
                    ui.label("Save As (File Name):");
                    ui.add(egui::TextEdit::singleline(&mut self.add_filename).desired_width(450.0));

                    ui.add_space(6.0);
                    ui.label("Save To Folder:");
                    ui.horizontal(|ui| {
                        ui.add(egui::TextEdit::singleline(&mut self.add_save_dir).desired_width(380.0));
                        if ui.button("Browse...").clicked() {
                            // Default to user downloads folder
                        }
                    });

                    ui.add_space(6.0);
                    ui.horizontal(|ui| {
                        ui.label("Segmented Connections (1-32):");
                        ui.add(egui::Slider::new(&mut self.add_segments, 1..=32));
                    });

                    if !self.add_probe_error.is_empty() {
                        ui.label(RichText::new(&self.add_probe_error).color(Color32::from_rgb(248, 113, 113)));
                    }

                    ui.add_space(10.0);
                    ui.horizontal(|ui| {
                        if ui.button(RichText::new("⚡ Start Download").strong()).clicked() {
                            if !self.add_url.is_empty() {
                                let fn_name = if self.add_filename.is_empty() {
                                    let p = self.add_url.split('?').next().unwrap_or("").split('/').last().unwrap_or("download.bin");
                                    sanitize_filename(p)
                                } else {
                                    sanitize_filename(&self.add_filename)
                                };

                                let id = self.manager.add_download(
                                    self.add_url.clone(),
                                    fn_name,
                                    self.add_save_dir.clone(),
                                    self.add_segments,
                                    self.add_is_video,
                                    self.add_headers.clone(),
                                    true,
                                );
                                self.selected_id = Some(id.clone());
                                self.progress_id = Some(id);
                                self.show_progress_dialog = true;
                                self.show_add_dialog = false;
                            }
                        }

                        if ui.button("Download Later").clicked() {
                            if !self.add_url.is_empty() {
                                let fn_name = if self.add_filename.is_empty() {
                                    let p = self.add_url.split('?').next().unwrap_or("").split('/').last().unwrap_or("download.bin");
                                    sanitize_filename(p)
                                } else {
                                    sanitize_filename(&self.add_filename)
                                };

                                self.manager.add_download(
                                    self.add_url.clone(),
                                    fn_name,
                                    self.add_save_dir.clone(),
                                    self.add_segments,
                                    self.add_is_video,
                                    self.add_headers.clone(),
                                    false,
                                );
                                self.show_add_dialog = false;
                            }
                        }

                        if ui.button("Cancel").clicked() {
                            self.show_add_dialog = false;
                        }
                    });
                });
        }

        // 6. Modal: Download Progress Dialog with IDM Connection Visualizer
        if self.show_progress_dialog {
            if let Some(ref target_id) = self.progress_id.clone() {
                if let Some(item) = self.manager.items.iter().find(|x| &x.id == target_id) {
                    let item_clone = item.clone();

                    egui::Window::new("Download Status - DFM")
                        .collapsible(false)
                        .resizable(true)
                        .default_width(520.0)
                        .anchor(egui::Align2::CENTER_CENTER, [0.0, 0.0])
                        .show(ctx, |ui| {
                            ui.label(RichText::new(&item_clone.filename).strong().font(egui::FontId::proportional(15.0)));
                            ui.label(RichText::new(&item_clone.url).color(Color32::from_rgb(148, 163, 184)));

                            ui.add_space(8.0);
                            ui.group(|ui| {
                                ui.label(RichText::new("Transfer Metrics").strong().color(Color32::from_rgb(56, 189, 248)));
                                ui.columns(2, |cols| {
                                    cols[0].label(format!("Status: {}", item_clone.status));
                                    cols[0].label(format!("Downloaded: {}", format_bytes(item_clone.downloaded_bytes)));
                                    cols[0].label("Resume: Supported");

                                    cols[1].label(format!("File Size: {}", format_bytes(item_clone.total_bytes)));
                                    cols[1].label(format!("Transfer Rate: {}", format_speed(item_clone.speed)));
                                    cols[1].label(format!("Time Left: {}", format_eta(item_clone.eta_secs)));
                                });
                            });

                            ui.add_space(8.0);
                            ui.add(egui::ProgressBar::new(item_clone.progress_ratio()).show_percentage().desired_width(500.0));

                            // IDM Segment Connection Visualizer
                            ui.add_space(8.0);
                            ui.label(RichText::new("Segmented Connections (Multi-Threaded Work Stealing):").strong());

                            // Check active task metrics
                            let mut segments_to_render = Vec::new();
                            if let Some(task) = self.manager.active_tasks.get(target_id) {
                                if let Ok(guard) = task.live_progress.lock() {
                                    if let Some(ref p) = *guard {
                                        segments_to_render = p.segments.clone();
                                    }
                                }
                            }

                            if !segments_to_render.is_empty() {
                                egui::Grid::new("seg_vis_grid").num_columns(4).spacing([6.0, 4.0]).show(ui, |ui| {
                                    for (i, seg) in segments_to_render.iter().enumerate() {
                                        let seg_total = seg.end.saturating_sub(seg.start);
                                        let seg_cur = seg.current.saturating_sub(seg.start);
                                        let ratio = if seg_total > 0 { (seg_cur as f32 / seg_total as f32).clamp(0.0, 1.0) } else { 0.0 };
                                        let bar_col = if seg.active { Color32::from_rgb(56, 189, 248) } else { Color32::from_rgb(74, 222, 128) };

                                        ui.horizontal(|ui| {
                                            ui.label(format!("#{:02}", i + 1));
                                            ui.add(egui::ProgressBar::new(ratio).fill(bar_col).desired_width(85.0));
                                        });

                                        if (i + 1) % 4 == 0 {
                                            ui.end_row();
                                        }
                                    }
                                });
                            } else {
                                ui.label(RichText::new(format!("{} connection threads assigned", item_clone.segments_count)).color(Color32::from_rgb(148, 163, 184)));
                            }

                            ui.add_space(10.0);
                            ui.horizontal(|ui| {
                                if item_clone.status == "downloading" {
                                    if ui.button("⏸ Pause").clicked() {
                                        self.manager.pause_download(target_id);
                                    }
                                } else {
                                    if ui.button("▶ Resume").clicked() {
                                        self.manager.resume_download(target_id);
                                    }
                                }

                                if ui.button("Cancel").clicked() {
                                    self.manager.delete_download(target_id, false);
                                    self.show_progress_dialog = false;
                                }

                                if item_clone.status == "completed" {
                                    if ui.button("Open File").clicked() {
                                        Self::open_file(&item_clone.save_path);
                                    }
                                    if ui.button("Open Folder").clicked() {
                                        Self::open_folder(&item_clone.save_path);
                                    }
                                }

                                if ui.button("Hide").clicked() {
                                    self.show_progress_dialog = false;
                                }
                            });
                        });
                } else {
                    self.show_progress_dialog = false;
                }
            }
        }

        // 7. Modal: Settings Dialog
        if self.show_settings_dialog {
            egui::Window::new("Settings - DFM")
                .collapsible(false)
                .resizable(false)
                .default_width(400.0)
                .anchor(egui::Align2::CENTER_CENTER, [0.0, 0.0])
                .show(ctx, |ui| {
                    ui.label("Default Download Directory:");
                    ui.add(egui::TextEdit::singleline(&mut self.settings.default_download_dir).desired_width(380.0));

                    ui.add_space(6.0);
                    ui.horizontal(|ui| {
                        ui.label("Default Connection Segments:");
                        ui.add(egui::Slider::new(&mut self.settings.default_segments, 1..=32));
                    });

                    ui.add_space(6.0);
                    ui.horizontal(|ui| {
                        ui.label("Browser Bridge Port:");
                        ui.add(egui::DragValue::new(&mut self.settings.bridge_port));
                    });

                    ui.add_space(6.0);
                    ui.checkbox(&mut self.settings.clipboard_listener_enabled, "Enable Windows Clipboard URL Sniffer");

                    ui.add_space(12.0);
                    ui.horizontal(|ui| {
                        if ui.button("Save Settings").clicked() {
                            self.manager.storage.save_settings(&self.settings);
                            self.show_settings_dialog = false;
                        }
                        if ui.button("Close").clicked() {
                            self.show_settings_dialog = false;
                        }
                    });
                });
        }
    }
}
