// DFM Engine - Ultra-Fast Multi-Threaded Download Core with Dynamic Work Stealing
// Authors: Rezanur <rezanurbinshamim@gmail.com>

use std::collections::HashMap;
use std::env;
use std::fs::{File, OpenOptions};
use std::io::{Read, Seek, SeekFrom, Write};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};

const READ_BUFFER_SIZE: usize = 256 * 1024; // 256 KB high-throughput buffer
const MIN_STEAL_SIZE: u64 = 4 * 1024 * 1024; // 4 MB minimum size required to steal work

struct DownloadConfig {
    url: String,
    out_path: String,
    threads: usize,
    headers: HashMap<String, String>,
    json_mode: bool,
}

#[derive(Clone)]
struct SharedSegment {
    _id: usize,
    start: u64,
    end: Arc<AtomicU64>,
    current: Arc<AtomicU64>,
    completed: Arc<AtomicBool>,
}

fn emit_event(
    ev_type: &str,
    downloaded: u64,
    total: u64,
    speed: u64,
    eta_secs: u64,
    percent: f64,
    threads: usize,
    message: Option<&str>,
    json_mode: bool,
) {
    if json_mode {
        let msg_str = match message {
            Some(m) => format!("\"{}\"", m.replace('\\', "\\\\").replace('"', "\\\"")),
            None => "null".to_string(),
        };
        println!(
            r#"{{"type":"{}","downloaded":{},"total":{},"speed":{},"eta_secs":{},"percent":{:.1},"active_threads":{},"message":{}}}"#,
            ev_type, downloaded, total, speed, eta_secs, percent, threads, msg_str
        );
    } else {
        match ev_type {
            "init" => {
                println!(
                    "[DFM Core] Accelerated download: total {} MB across {} connection threads",
                    total / 1_048_576,
                    threads
                );
            }
            "progress" => {
                let speed_mb = (speed as f64) / 1_048_576.0;
                print!(
                    "\r[DFM Core] {:>5.1}% | {:>6.2} MB/s | ETA: {:>3}s | {} / {} MB",
                    percent,
                    speed_mb,
                    eta_secs,
                    downloaded / 1_048_576,
                    total / 1_048_576
                );
                let _ = std::io::stdout().flush();
            }
            "completed" => {
                println!("\n[DFM Core] Download complete: {}", message.unwrap_or("Done"));
            }
            "error" => {
                eprintln!("\n[DFM Core ERROR] {}", message.unwrap_or("Unknown error"));
            }
            _ => {}
        }
    }
}

fn parse_args() -> Result<DownloadConfig, String> {
    let args: Vec<String> = env::args().collect();
    let mut url = String::new();
    let mut out_path = String::new();
    let mut threads = 16usize; // Default 16 aggressive threads for maximum speed
    let mut headers = HashMap::new();
    let mut json_mode = false;

    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--url" | "-u" => {
                if i + 1 < args.len() {
                    url = args[i + 1].clone();
                    i += 1;
                }
            }
            "--out" | "-o" => {
                if i + 1 < args.len() {
                    out_path = args[i + 1].clone();
                    i += 1;
                }
            }
            "--threads" | "-t" => {
                if i + 1 < args.len() {
                    if let Ok(t) = args[i + 1].parse::<usize>() {
                        threads = t.clamp(1, 32);
                    }
                    i += 1;
                }
            }
            "--header" | "-H" => {
                if i + 1 < args.len() {
                    let h = &args[i + 1];
                    if let Some(pos) = h.find(':') {
                        let key = h[..pos].trim().to_string();
                        let val = h[pos + 1..].trim().to_string();
                        headers.insert(key, val);
                    }
                    i += 1;
                }
            }
            "--json" => {
                json_mode = true;
            }
            _ => {}
        }
        i += 1;
    }

    if url.is_empty() {
        return Err("Missing required argument: --url <URL>".to_string());
    }
    if out_path.is_empty() {
        let file_part = url.split('?').next().unwrap_or("").split('/').last().unwrap_or("download.bin");
        out_path = if file_part.is_empty() { "download.bin".to_string() } else { file_part.to_string() };
    }

    Ok(DownloadConfig {
        url,
        out_path,
        threads,
        headers,
        json_mode,
    })
}

// Download a specific range [range_start .. range_end] into the file
fn download_range(
    url: &str,
    headers: &HashMap<String, String>,
    file: &mut File,
    range_start: u64,
    range_end_atomic: &Arc<AtomicU64>,
    current_atomic: &Arc<AtomicU64>,
    global_counter: &Arc<AtomicU64>,
    err_flag: &Arc<AtomicBool>,
) -> bool {
    let initial_end = range_end_atomic.load(Ordering::SeqCst);
    if range_start > initial_end {
        return true;
    }

    let mut req = minreq::get(url).with_timeout(30);
    for (k, v) in headers {
        req = req.with_header(k, v);
    }
    if !headers.contains_key("User-Agent") {
        req = req.with_header("User-Agent", "DFM/2.0 (Windows NT 10.0; Win64; x64) DownloadFastManager");
    }
    req = req.with_header("Range", format!("bytes={}-{}", range_start, initial_end));

    let mut resp = match req.send_lazy() {
        Ok(r) => r,
        Err(_) => {
            err_flag.store(true, Ordering::Relaxed);
            return false;
        }
    };

    if file.seek(SeekFrom::Start(range_start)).is_err() {
        err_flag.store(true, Ordering::Relaxed);
        return false;
    }

    let mut pos = range_start;
    let mut buf = vec![0u8; READ_BUFFER_SIZE];

    loop {
        let current_target_end = range_end_atomic.load(Ordering::SeqCst);
        if pos > current_target_end {
            break; // Finished this portion or was stolen
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
                current_atomic.store(pos, Ordering::SeqCst);
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

fn main() {
    let cfg = match parse_args() {
        Ok(c) => c,
        Err(e) => {
            eprintln!("{}", e);
            eprintln!("Usage: dfm-engine --url <URL> --out <FILE> [--threads 16] [--header \"K: V\"] [--json]");
            std::process::exit(1);
        }
    };

    // 1. Probe URL with Range 0-0
    let mut probe_req = minreq::get(&cfg.url).with_timeout(15);
    for (k, v) in &cfg.headers {
        probe_req = probe_req.with_header(k, v);
    }
    if !cfg.headers.contains_key("User-Agent") {
        probe_req = probe_req.with_header("User-Agent", "DFM/2.0 (Windows NT 10.0; Win64; x64) DownloadFastManager");
    }
    probe_req = probe_req.with_header("Range", "bytes=0-0");

    let probe_resp = match probe_req.send() {
        Ok(r) => r,
        Err(e) => {
            emit_event("error", 0, 0, 0, 0, 0.0, 0, Some(&format!("Connection failed: {}", e)), cfg.json_mode);
            std::process::exit(1);
        }
    };

    let status = probe_resp.status_code;
    if status >= 400 {
        emit_event("error", 0, 0, 0, 0, 0.0, 0, Some(&format!("HTTP Error {}", status)), cfg.json_mode);
        std::process::exit(1);
    }

    let mut supports_range = status == 206;
    let mut total_size: u64 = 0;

    if supports_range {
        if let Some(cr) = probe_resp.headers.get("content-range") {
            if let Some(slash_idx) = cr.rfind('/') {
                let total_str = cr[slash_idx + 1..].trim();
                if let Ok(ts) = total_str.parse::<u64>() {
                    total_size = ts;
                }
            }
        }
    } else {
        if let Some(cl) = probe_resp.headers.get("content-length") {
            if let Ok(ts) = cl.parse::<u64>() {
                total_size = ts;
            }
        }
        if let Some(ar) = probe_resp.headers.get("accept-ranges") {
            if ar.to_lowercase().contains("bytes") {
                supports_range = true;
            }
        }
    }

    drop(probe_resp);

    // Thread count selection
    let thread_count = if !supports_range || total_size < 2 * 1024 * 1024 {
        1
    } else {
        cfg.threads
    };

    // 2. Open and pre-allocate target file
    let file = match OpenOptions::new()
        .read(true)
        .write(true)
        .create(true)
        .truncate(true)
        .open(&cfg.out_path)
    {
        Ok(f) => f,
        Err(e) => {
            emit_event("error", 0, total_size, 0, 0, 0.0, 0, Some(&format!("Cannot open output file: {}", e)), cfg.json_mode);
            std::process::exit(1);
        }
    };

    if total_size > 0 {
        let _ = file.set_len(total_size);
    }

    emit_event("init", 0, total_size, 0, 0, 0.0, thread_count, None, cfg.json_mode);

    let downloaded_atomic = Arc::new(AtomicU64::new(0));
    let is_done = Arc::new(AtomicBool::new(false));
    let has_error = Arc::new(AtomicBool::new(false));

    // 3. Monitor thread with Exponential Moving Average (EMA) rate smoothing
    let monitor_downloaded = Arc::clone(&downloaded_atomic);
    let monitor_done = Arc::clone(&is_done);
    let monitor_error = Arc::clone(&has_error);
    let json_mode = cfg.json_mode;

    let monitor_handle = thread::spawn(move || {
        let mut last_bytes = 0u64;
        let mut last_time = Instant::now();
        let mut smoothed_speed = 0.0f64;
        let alpha = 0.25f64;

        while !monitor_done.load(Ordering::Relaxed) && !monitor_error.load(Ordering::Relaxed) {
            thread::sleep(Duration::from_millis(200));
            let current = monitor_downloaded.load(Ordering::Relaxed);
            let now = Instant::now();
            let elapsed = now.duration_since(last_time).as_secs_f64();

            if elapsed >= 0.2 {
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
                    ((current as f64) / (total_size as f64)) * 100.0
                } else {
                    0.0
                };

                emit_event(
                    "progress",
                    current,
                    total_size,
                    smoothed_speed as u64,
                    eta,
                    (pct * 10.0).round() / 10.0,
                    thread_count,
                    None,
                    json_mode,
                );
            }
        }
    });

    let start_instant = Instant::now();
    let mut handles = Vec::new();

    if thread_count == 1 || total_size == 0 {
        // Single connection stream
        let mut file_clone = file.try_clone().expect("Failed to clone file handle");
        let url = cfg.url.clone();
        let headers = cfg.headers.clone();
        let counter = Arc::clone(&downloaded_atomic);
        let err_flag = Arc::clone(&has_error);

        let h = thread::spawn(move || {
            let mut req = minreq::get(&url).with_timeout(30);
            for (k, v) in &headers {
                req = req.with_header(k, v);
            }
            if !headers.contains_key("User-Agent") {
                req = req.with_header("User-Agent", "DFM/2.0 (Windows NT 10.0; Win64; x64) DownloadFastManager");
            }

            match req.send_lazy() {
                Ok(mut reader) => {
                    let mut buf = vec![0u8; READ_BUFFER_SIZE];
                    loop {
                        match reader.read(&mut buf) {
                            Ok(0) => break,
                            Ok(n) => {
                                if file_clone.write_all(&buf[..n]).is_err() {
                                    err_flag.store(true, Ordering::Relaxed);
                                    break;
                                }
                                counter.fetch_add(n as u64, Ordering::Relaxed);
                            }
                            Err(_) => {
                                err_flag.store(true, Ordering::Relaxed);
                                break;
                            }
                        }
                    }
                }
                Err(_) => {
                    err_flag.store(true, Ordering::Relaxed);
                }
            }
        });
        handles.push(h);
    } else {
        // Multi-connection segmented downloading WITH DYNAMIC WORK STEALING
        let part_size = total_size / (thread_count as u64);
        let mut segments: Vec<SharedSegment> = Vec::with_capacity(thread_count);

        for seg_idx in 0..thread_count {
            let start = seg_idx as u64 * part_size;
            let end = if seg_idx == thread_count - 1 {
                total_size - 1
            } else {
                (seg_idx as u64 + 1) * part_size - 1
            };

            segments.push(SharedSegment {
                _id: seg_idx,
                start,
                end: Arc::new(AtomicU64::new(end)),
                current: Arc::new(AtomicU64::new(start)),
                completed: Arc::new(AtomicBool::new(false)),
            });
        }

        let all_segments = Arc::new(Mutex::new(segments));

        for seg_idx in 0..thread_count {
            let mut file_clone = file.try_clone().expect("Failed to clone file handle");
            let url = cfg.url.clone();
            let headers = cfg.headers.clone();
            let counter = Arc::clone(&downloaded_atomic);
            let err_flag = Arc::clone(&has_error);
            let pool = Arc::clone(&all_segments);

            let h = thread::spawn(move || {
                // 1. Download initial assigned segment
                let (initial_start, initial_end, initial_curr, initial_done) = {
                    let segs = pool.lock().unwrap();
                    let s = &segs[seg_idx];
                    (s.start, Arc::clone(&s.end), Arc::clone(&s.current), Arc::clone(&s.completed))
                };

                let success = download_range(
                    &url,
                    &headers,
                    &mut file_clone,
                    initial_start,
                    &initial_end,
                    &initial_curr,
                    &counter,
                    &err_flag,
                );

                initial_done.store(true, Ordering::SeqCst);

                if !success || err_flag.load(Ordering::Relaxed) {
                    return;
                }

                // 2. WORK STEALING LOOP: Keep thread alive and steal from slowest/largest remaining segment
                loop {
                    if err_flag.load(Ordering::Relaxed) {
                        break;
                    }

                    // Find segment with largest remaining bytes
                    let steal_task = {
                        let mut segs = pool.lock().unwrap();
                        let mut best_idx = None;
                        let mut max_remaining = 0u64;

                        for (i, s) in segs.iter().enumerate() {
                            if !s.completed.load(Ordering::SeqCst) {
                                let cur = s.current.load(Ordering::SeqCst);
                                let end = s.end.load(Ordering::SeqCst);
                                if end > cur {
                                    let rem = end - cur;
                                    if rem > max_remaining && rem >= MIN_STEAL_SIZE {
                                        max_remaining = rem;
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

                                // Truncate original segment to mid
                                target.end.store(mid, Ordering::SeqCst);

                                // Add new stolen segment to pool
                                let new_id = segs.len();
                                let stolen_seg = SharedSegment {
                                    _id: new_id,
                                    start: stolen_start,
                                    end: Arc::new(AtomicU64::new(stolen_end)),
                                    current: Arc::new(AtomicU64::new(stolen_start)),
                                    completed: Arc::new(AtomicBool::new(false)),
                                };
                                let task_end = Arc::clone(&stolen_seg.end);
                                let task_curr = Arc::clone(&stolen_seg.current);
                                let task_done = Arc::clone(&stolen_seg.completed);
                                segs.push(stolen_seg);

                                Some((stolen_start, task_end, task_curr, task_done))
                            } else {
                                None
                            }
                        } else {
                            None
                        }
                    };

                    match steal_task {
                        Some((stolen_start, stolen_end_atomic, stolen_curr_atomic, stolen_done_atomic)) => {
                            let ok = download_range(
                                &url,
                                &headers,
                                &mut file_clone,
                                stolen_start,
                                &stolen_end_atomic,
                                &stolen_curr_atomic,
                                &counter,
                                &err_flag,
                            );
                            stolen_done_atomic.store(true, Ordering::SeqCst);
                            if !ok {
                                break;
                            }
                        }
                        None => {
                            // No segments left to steal; thread can cleanly exit
                            break;
                        }
                    }
                }
            });
            handles.push(h);
        }
    }

    for h in handles {
        let _ = h.join();
    }

    is_done.store(true, Ordering::Relaxed);
    let _ = monitor_handle.join();

    let total_elapsed = start_instant.elapsed();
    let final_downloaded = downloaded_atomic.load(Ordering::Relaxed);

    if has_error.load(Ordering::Relaxed) {
        emit_event(
            "error",
            final_downloaded,
            total_size,
            0,
            0,
            0.0,
            0,
            Some("Stream interrupted or connection reset"),
            cfg.json_mode,
        );
        std::process::exit(1);
    }

    let _ = file.sync_all();

    emit_event(
        "completed",
        final_downloaded,
        if total_size > 0 { total_size } else { final_downloaded },
        if total_elapsed.as_secs_f64() > 0.0 {
            (final_downloaded as f64 / total_elapsed.as_secs_f64()) as u64
        } else {
            0
        },
        0,
        100.0,
        0,
        Some(&format!("{:.2}s ({})", total_elapsed.as_secs_f64(), &cfg.out_path)),
        cfg.json_mode,
    );
}
