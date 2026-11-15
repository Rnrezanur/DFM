// DFM Download Manager & Task Queue Orchestrator in Pure Rust
// Authors: Rezanur <rezanurbinshamim@gmail.com>

use crate::db::{determine_category, DownloadItem, Storage};
use crate::engine::{run_download, DownloadEngineHandle, EngineProgress};
use chrono::Local;
use std::collections::HashMap;
use std::fs;
use std::sync::atomic::AtomicBool;
use std::sync::{Arc, Mutex};
use std::thread;

pub struct ActiveTask {
    pub handle: DownloadEngineHandle,
    pub live_progress: Arc<Mutex<Option<EngineProgress>>>,
}

pub struct DownloadManager {
    pub items: Vec<DownloadItem>,
    pub active_tasks: HashMap<String, ActiveTask>,
    pub storage: Storage,
}

impl DownloadManager {
    pub fn new() -> Self {
        let storage = Storage::new();
        let items = storage.load_downloads();
        Self {
            items,
            active_tasks: HashMap::new(),
            storage,
        }
    }

    pub fn save(&self) {
        self.storage.save_downloads(&self.items);
    }

    pub fn add_download(
        &mut self,
        url: String,
        filename: String,
        save_dir: String,
        segments_count: usize,
        is_video: bool,
        headers: HashMap<String, String>,
        auto_start: bool,
    ) -> String {
        let id = uuid::Uuid::new_v4().to_string();
        let save_path = format!("{}\\{}", save_dir.trim_end_matches('\\'), filename);
        let category = if is_video {
            "Video & Audio".to_string()
        } else {
            determine_category(&filename).to_string()
        };
        let now = Local::now().format("%Y-%m-%d %H:%M:%S").to_string();

        let item = DownloadItem {
            id: id.clone(),
            url,
            filename,
            save_path,
            category,
            total_bytes: 0,
            downloaded_bytes: 0,
            status: "pending".to_string(),
            speed: 0,
            eta_secs: 0,
            segments_count,
            added_date: now,
            error_message: String::new(),
            is_video,
            headers,
        };

        self.items.insert(0, item);
        self.save();

        if auto_start {
            self.start_download(&id);
        }

        id
    }

    pub fn start_download(&mut self, id: &str) {
        // If already active, skip
        if self.active_tasks.contains_key(id) {
            return;
        }

        let item_idx = match self.items.iter().position(|x| x.id == id) {
            Some(i) => i,
            None => return,
        };

        let item = &mut self.items[item_idx];
        item.status = "downloading".to_string();
        item.error_message.clear();

        let url = item.url.clone();
        let save_path = item.save_path.clone();
        let threads_count = item.segments_count;
        let headers = item.headers.clone();

        let stop_flag = Arc::new(AtomicBool::new(false));
        let pause_flag = Arc::new(AtomicBool::new(false));

        let live_progress = Arc::new(Mutex::new(None));
        let progress_writer = Arc::clone(&live_progress);

        let handle = DownloadEngineHandle {
            stop_flag: Arc::clone(&stop_flag),
            pause_flag: Arc::clone(&pause_flag),
        };

        self.active_tasks.insert(
            id.to_string(),
            ActiveTask {
                handle,
                live_progress,
            },
        );

        self.save();

        let _task_id = id.to_string();
        thread::spawn(move || {
            let _res = run_download(
                url,
                save_path,
                threads_count,
                headers,
                stop_flag,
                pause_flag,
                move |prog| {
                    if let Ok(mut lock) = progress_writer.lock() {
                        *lock = Some(prog);
                    }
                },
            );

            // Completion / Error handling
            // Managed in periodic sync_updates
        });
    }

    pub fn pause_download(&mut self, id: &str) {
        if let Some(task) = self.active_tasks.remove(id) {
            task.handle.pause();
        }
        if let Some(item) = self.items.iter_mut().find(|x| x.id == id) {
            item.status = "paused".to_string();
            item.speed = 0;
            item.eta_secs = 0;
        }
        self.save();
    }

    pub fn resume_download(&mut self, id: &str) {
        self.start_download(id);
    }

    pub fn stop_all(&mut self) {
        let ids: Vec<String> = self.active_tasks.keys().cloned().collect();
        for id in ids {
            self.pause_download(&id);
        }
    }

    pub fn delete_download(&mut self, id: &str, delete_file: bool) {
        self.pause_download(id);
        if let Some(pos) = self.items.iter().position(|x| x.id == id) {
            let item = self.items.remove(pos);
            if delete_file {
                let _ = fs::remove_file(&item.save_path);
            }
            self.save();
        }
    }

    pub fn sync_updates(&mut self) {
        let mut completed_or_stopped = Vec::new();

        for (id, task) in &self.active_tasks {
            if let Some(item) = self.items.iter_mut().find(|x| &x.id == id) {
                if let Ok(guard) = task.live_progress.lock() {
                    if let Some(ref prog) = *guard {
                        item.downloaded_bytes = prog.downloaded;
                        if prog.total > 0 {
                            item.total_bytes = prog.total;
                        }
                        item.speed = prog.speed;
                        item.eta_secs = prog.eta_secs;

                        if prog.total > 0 && prog.downloaded >= prog.total {
                            item.status = "completed".to_string();
                            item.speed = 0;
                            item.eta_secs = 0;
                            completed_or_stopped.push(id.clone());
                        }
                    }
                }
            }
        }

        for id in completed_or_stopped {
            self.active_tasks.remove(&id);
            self.save();
        }
    }

    pub fn total_speed(&self) -> u64 {
        self.items
            .iter()
            .filter(|x| x.status == "downloading")
            .map(|x| x.speed)
            .sum()
    }

    pub fn active_count(&self) -> usize {
        self.items.iter().filter(|x| x.status == "downloading").count()
    }
}
