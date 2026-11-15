// DFM Multi-Threaded Download Engine in Pure Rust
// Features: Dynamic Work Stealing, 256KB Direct I/O Buffering, IDM Segment Metrics
// Authors: Rezanur <rezanurbinshamim@gmail.com>

use std::collections::HashMap;
use std::fs::{File, OpenOptions};
use std::io::{Read, Seek, SeekFrom, Write};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};

const READ_BUFFER_SIZE: usize = 256 * 1024; // 256 KB buffer
const MIN_STEAL_SIZE: u64 = 4 * 1024 * 1024; // 4 MB threshold to steal

#[allow(dead_code)]
#[derive(Clone, Debug)]
pub struct SegmentMetric {
    pub id: usize,
    pub start: u64,
    pub current: u64,
    pub end: u64,
    pub active: bool,
}

#[allow(dead_code)]
#[derive(Clone, Debug)]
pub struct EngineProgress {
    pub downloaded: u64,
    pub total: u64,
    pub speed: u64,
    pub eta_secs: u64,
    pub percent: f32,
    pub segments: Vec<SegmentMetric>,
}

#[derive(Clone)]
struct SharedSegment {
    id: usize,
    start: u64,
    end: Arc<AtomicU64>,
    current: Arc<AtomicU64>,
    completed: Arc<AtomicBool>,
    active: Arc<AtomicBool>,
}

#[allow(dead_code)]
pub struct ProbeResult {
    pub total_bytes: u64,
    pub supports_range: bool,
    pub filename: String,
}

pub fn probe_url(url: &str, headers: &HashMap<String, String>) -> Result<ProbeResult, String> {
    let mut req = minreq::get(url).with_timeout(15);
    for (k, v) in headers {
        req = req.with_header(k, v);
    }
    if !headers.contains_key("User-Agent") {
        req = req.with_header("User-Agent", "DFM/2.0 (Windows NT 10.0; Win64; x64) DownloadFastManager");
    }
    req = req.with_header("Range", "bytes=0-0");

    let resp = match req.send() {
        Ok(r) => r,
        Err(e) => return Err(format!("Connection failed: {}", e)),
    };

    let status = resp.status_code;
    if status >= 400 {
        return Err(format!("Server returned HTTP {}", status));
    }

    let mut supports_range = status == 206;
    let mut total_size: u64 = 0;

    if supports_range {
        if let Some(cr) = resp.headers.get("content-range") {
            if let Some(slash_idx) = cr.rfind('/') {
                let total_str = cr[slash_idx + 1..].trim();
                if let Ok(ts) = total_str.parse::<u64>() {
                    total_size = ts;
                }
            }
        }
    } else {
        if let Some(cl) = resp.headers.get("content-length") {
            if let Ok(ts) = cl.parse::<u64>() {
                total_size = ts;
            }
        }
        if let Some(ar) = resp.headers.get("accept-ranges") {
            if ar.to_lowercase().contains("bytes") {
                supports_range = true;
            }
        }
    }

    // Try extracting filename from Content-Disposition header
    let mut extracted_name = String::new();
    if let Some(cd) = resp.headers.get("content-disposition") {
        if let Some(fn_pos) = cd.to_lowercase().find("filename=") {
            let part = &cd[fn_pos + 9..];
            let name = part.trim_matches(|c| c == '"' || c == '\'' || c == ' ');
            let clean = name.split(';').next().unwrap_or("").trim();
            if !clean.is_empty() {
                extracted_name = clean.to_string();
            }
        }
    }

    if extracted_name.is_empty() {
        let path_part = url.split('?').next().unwrap_or("").split('#').next().unwrap_or("");
        let file_part = path_part.split('/').last().unwrap_or("download.bin");
        extracted_name = if file_part.is_empty() { "download.bin".to_string() } else { file_part.to_string() };
    }

    Ok(ProbeResult {
        total_bytes: total_size,
        supports_range,
        filename: extracted_name,
    })
}

#[allow(dead_code)]
pub struct DownloadEngineHandle {
    pub stop_flag: Arc<AtomicBool>,
    pub pause_flag: Arc<AtomicBool>,
}

#[allow(dead_code)]
impl DownloadEngineHandle {
    pub fn cancel(&self) {
        self.stop_flag.store(true, Ordering::SeqCst);
    }

    pub fn pause(&self) {
        self.pause_flag.store(true, Ordering::SeqCst);
    }
}

pub fn run_download<F>(
    url: String,
    save_path: String,
    threads_count: usize,
    headers: HashMap<String, String>,
    stop_flag: Arc<AtomicBool>,
    pause_flag: Arc<AtomicBool>,
    mut on_progress: F,
) -> Result<(), String>
where
    F: FnMut(EngineProgress) + Send + 'static,
{
    // Probe
    let probe = probe_url(&url, &headers)?;
    let total_size = probe.total_bytes;
    let supports_range = probe.supports_range;

    let thread_count = if !supports_range || total_size < 2 * 1024 * 1024 {
        1
    } else {
        threads_count.clamp(1, 32)
    };

    // Open file
    let file = match OpenOptions::new()
        .read(true)
        .write(true)
        .create(true)
        .open(&save_path)
    {
        Ok(f) => f,
        Err(e) => return Err(format!("Cannot open target file: {}", e)),
    };

    if total_size > 0 {
        let _ = file.set_len(total_size);
    }

    let downloaded_atomic = Arc::new(AtomicU64::new(0));
    let has_error = Arc::new(AtomicBool::new(false));
    let is_done = Arc::new(AtomicBool::new(false));

    // Prepare segments
    let part_size = if thread_count > 0 && total_size > 0 {
        total_size / (thread_count as u64)
    } else {
        total_size
    };

    let mut segments: Vec<SharedSegment> = Vec::with_capacity(thread_count);
    for seg_idx in 0..thread_count {
        let start = seg_idx as u64 * part_size;
        let end = if seg_idx == thread_count - 1 {
            total_size.saturating_sub(1)
        } else {
            ((seg_idx as u64 + 1) * part_size).saturating_sub(1)
        };

        segments.push(SharedSegment {
            id: seg_idx,
            start,
            end: Arc::new(AtomicU64::new(end)),
            current: Arc::new(AtomicU64::new(start)),
            completed: Arc::new(AtomicBool::new(false)),
            active: Arc::new(AtomicBool::new(true)),
        });
    }

    let pool = Arc::new(Mutex::new(segments));

    // Progress monitor thread
    let monitor_counter = Arc::clone(&downloaded_atomic);
    let monitor_done = Arc::clone(&is_done);
    let monitor_stop = Arc::clone(&stop_flag);
    let monitor_pause = Arc::clone(&pause_flag);
    let monitor_err = Arc::clone(&has_error);
    let monitor_pool = Arc::clone(&pool);

    let monitor_handle = thread::spawn(move || {
        let mut last_bytes = 0u64;
        let mut last_time = Instant::now();
        let mut smoothed_speed = 0.0f64;
        let alpha = 0.25f64;

        while !monitor_done.load(Ordering::Relaxed)
            && !monitor_stop.load(Ordering::Relaxed)
            && !monitor_pause.load(Ordering::Relaxed)
            && !monitor_err.load(Ordering::Relaxed)
        {
            thread::sleep(Duration::from_millis(150));
            let current = monitor_counter.load(Ordering::Relaxed);
            let now = Instant::now();
            let elapsed = now.duration_since(last_time).as_secs_f64();

            if elapsed >= 0.15 {
                let delta = current.saturating_sub(last_bytes);
                let instant_speed = (delta as f64) / elapsed;

                if smoothed_speed == 0.0 {
                    smoothed_speed = instant_speed;
                } else {
                    smoothed_speed = alpha * instant_speed + (1.0 - alpha) * smoothed_speed;
                }

                last_bytes = current;
                last_time = now;

                let eta = if smoothed_speed > 100.0 && total_size > current {
                    ((total_size - current) as f64 / smoothed_speed) as u64
                } else {
                    0
                };

                let pct = if total_size > 0 {
                    ((current as f32) / (total_size as f32)) * 100.0
                } else {
                    0.0
                };

                // Collect segment metrics
                let mut seg_metrics = Vec::new();
                if let Ok(segs) = monitor_pool.lock() {
                    for s in segs.iter() {
                        seg_metrics.push(SegmentMetric {
                            id: s.id,
                            start: s.start,
                            current: s.current.load(Ordering::Relaxed),
                            end: s.end.load(Ordering::Relaxed),
                            active: s.active.load(Ordering::Relaxed),
                        });
                    }
                }

                on_progress(EngineProgress {
                    downloaded: current,
                    total: total_size,
                    speed: smoothed_speed as u64,
                    eta_secs: eta,
                    percent: pct,
                    segments: seg_metrics,
                });
            }
        }
    });

    // Worker threads
    let mut handles = Vec::new();

    for seg_idx in 0..thread_count {
        let mut file_clone = match file.try_clone() {
            Ok(f) => f,
            Err(e) => return Err(format!("File clone error: {}", e)),
        };

        let url = url.clone();
        let headers = headers.clone();
        let counter = Arc::clone(&downloaded_atomic);
        let err_flag = Arc::clone(&has_error);
        let stop_f = Arc::clone(&stop_flag);
        let pause_f = Arc::clone(&pause_flag);
        let pool_ref = Arc::clone(&pool);

        let h = thread::spawn(move || {
            // Initial segment
            let (init_start, init_end, init_curr, init_done, init_active) = {
                let segs = pool_ref.lock().unwrap();
                let s = &segs[seg_idx];
                (s.start, Arc::clone(&s.end), Arc::clone(&s.current), Arc::clone(&s.completed), Arc::clone(&s.active))
            };

            let ok = download_chunk_stream(
                &url,
                &headers,
                &mut file_clone,
                init_start,
                &init_end,
                &init_curr,
                &counter,
                &err_flag,
                &stop_f,
                &pause_f,
            );

            init_done.store(true, Ordering::SeqCst);
            init_active.store(false, Ordering::SeqCst);

            if !ok || stop_f.load(Ordering::Relaxed) || pause_f.load(Ordering::Relaxed) || err_flag.load(Ordering::Relaxed) {
                return;
            }

            // DYNAMIC WORK STEALING
            loop {
                if stop_f.load(Ordering::Relaxed) || pause_f.load(Ordering::Relaxed) || err_flag.load(Ordering::Relaxed) {
                    break;
                }

                let steal_opt = {
                    let mut segs = pool_ref.lock().unwrap();
                    let mut best_idx = None;
                    let mut max_rem = 0u64;

                    for (i, s) in segs.iter().enumerate() {
                        if !s.completed.load(Ordering::SeqCst) {
                            let cur = s.current.load(Ordering::SeqCst);
                            let end = s.end.load(Ordering::SeqCst);
                            if end > cur {
                                let rem = end - cur;
                                if rem > max_rem && rem >= MIN_STEAL_SIZE {
                                    max_rem = rem;
                                    best_idx = Some(i);
                                }
                            }
                        }
                    }

                    if let Some(target_idx) = best_idx {
                        let target = &mut segs[target_idx];
                        let cur = target.current.load(Ordering::SeqCst);
                        let end = target.end.load(Ordering::SeqCst);
                        let rem = end.saturating_sub(cur);

                        if rem >= MIN_STEAL_SIZE {
                            let mid = cur + rem / 2;
                            let stolen_start = mid + 1;
                            let stolen_end = end;

                            target.end.store(mid, Ordering::SeqCst);

                            let new_id = segs.len();
                            let stolen = SharedSegment {
                                id: new_id,
                                start: stolen_start,
                                end: Arc::new(AtomicU64::new(stolen_end)),
                                current: Arc::new(AtomicU64::new(stolen_start)),
                                completed: Arc::new(AtomicBool::new(false)),
                                active: Arc::new(AtomicBool::new(true)),
                            };
                            let t_end = Arc::clone(&stolen.end);
                            let t_cur = Arc::clone(&stolen.current);
                            let t_done = Arc::clone(&stolen.completed);
                            let t_act = Arc::clone(&stolen.active);
                            segs.push(stolen);

                            Some((stolen_start, t_end, t_cur, t_done, t_act))
                        } else {
                            None
                        }
                    } else {
                        None
                    }
                };

                match steal_opt {
                    Some((stolen_start, s_end, s_cur, s_done, s_act)) => {
                        let success = download_chunk_stream(
                            &url,
                            &headers,
                            &mut file_clone,
                            stolen_start,
                            &s_end,
                            &s_cur,
                            &counter,
                            &err_flag,
                            &stop_f,
                            &pause_f,
                        );
                        s_done.store(true, Ordering::SeqCst);
                        s_act.store(false, Ordering::SeqCst);
                        if !success {
                            break;
                        }
                    }
                    None => break, // Nothing left to steal, thread exits cleanly
                }
            }
        });
        handles.push(h);
    }

    for h in handles {
        let _ = h.join();
    }

    is_done.store(true, Ordering::Relaxed);
    let _ = monitor_handle.join();

    if stop_flag.load(Ordering::Relaxed) {
        return Err("Download canceled by user".to_string());
    }
    if pause_flag.load(Ordering::Relaxed) {
        return Ok(());
    }
    if has_error.load(Ordering::Relaxed) {
        return Err("Network transfer interrupted".to_string());
    }

    let _ = file.sync_all();
    Ok(())
}

fn download_chunk_stream(
    url: &str,
    headers: &HashMap<String, String>,
    file: &mut File,
    start: u64,
    end_atomic: &Arc<AtomicU64>,
    cur_atomic: &Arc<AtomicU64>,
    global_counter: &Arc<AtomicU64>,
    err_flag: &Arc<AtomicBool>,
    stop_flag: &Arc<AtomicBool>,
    pause_flag: &Arc<AtomicBool>,
) -> bool {
    let initial_end = end_atomic.load(Ordering::SeqCst);
    if start > initial_end {
        return true;
    }

    let mut req = minreq::get(url).with_timeout(30);
    for (k, v) in headers {
        req = req.with_header(k, v);
    }
    if !headers.contains_key("User-Agent") {
        req = req.with_header("User-Agent", "DFM/2.0 (Windows NT 10.0; Win64; x64) DownloadFastManager");
    }
    req = req.with_header("Range", format!("bytes={}-{}", start, initial_end));

    let mut resp = match req.send_lazy() {
        Ok(r) => r,
        Err(_) => {
            err_flag.store(true, Ordering::Relaxed);
            return false;
        }
    };

    if file.seek(SeekFrom::Start(start)).is_err() {
        err_flag.store(true, Ordering::Relaxed);
        return false;
    }

    let mut pos = start;
    let mut buf = vec![0u8; READ_BUFFER_SIZE];

    loop {
        if stop_flag.load(Ordering::Relaxed) || pause_flag.load(Ordering::Relaxed) {
            return false;
        }

        let current_target_end = end_atomic.load(Ordering::SeqCst);
        if pos > current_target_end {
            break;
        }

        let max_to_read = ((current_target_end - pos + 1) as usize).min(buf.len());
        if max_to_read == 0 {
            break;
        }

        match resp.read(&mut buf[..max_to_read]) {
            Ok(0) => break,
            Ok(n) => {
                if file.write_all(&buf[..n]).is_err() {
                    err_flag.store(true, Ordering::Relaxed);
                    return false;
                }
                pos += n as u64;
                cur_atomic.store(pos, Ordering::SeqCst);
                global_counter.fetch_add(n as u64, Ordering::Relaxed);
            }
            Err(_) => {
                err_flag.store(true, Ordering::Relaxed);
                return false;
            }
        }
    }

    true
}
