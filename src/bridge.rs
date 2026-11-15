// DFM Local Browser Extension Bridge Server in Pure Rust
// Listens on 127.0.0.1:9666 for download requests from Chrome, Edge, and userscripts
// Authors: Rezanur <rezanurbinshamim@gmail.com>

use serde::Deserialize;
use std::collections::HashMap;
use std::sync::mpsc::Sender;
use std::thread;
use tiny_http::{Header, Method, Response, Server};

#[derive(Clone, Debug)]
pub struct BridgeMessage {
    pub url: String,
    pub filename: Option<String>,
    pub is_video: bool,
    pub headers: HashMap<String, String>,
}

#[derive(Deserialize)]
struct BridgeRequestPayload {
    url: Option<String>,
    filename: Option<String>,
    is_video: Option<bool>,
    cookies: Option<String>,
    referer: Option<String>,
    #[serde(default)]
    headers: HashMap<String, String>,
}

pub struct BridgeServer {
    port: u16,
    tx: Sender<BridgeMessage>,
}

impl BridgeServer {
    pub fn new(port: u16, tx: Sender<BridgeMessage>) -> Self {
        Self { port, tx }
    }

    pub fn start(self) {
        let addr = format!("127.0.0.1:{}", self.port);
        thread::spawn(move || {
            let server = match Server::http(&addr) {
                Ok(s) => s,
                Err(e) => {
                    eprintln!("[DFM Bridge] Failed to bind HTTP server to {}: {}", addr, e);
                    return;
                }
            };

            for mut req in server.incoming_requests() {
                let cors_origin = Header::from_bytes(&b"Access-Control-Allow-Origin"[..], &b"*"[..]).unwrap();
                let cors_methods = Header::from_bytes(&b"Access-Control-Allow-Methods"[..], &b"GET, POST, OPTIONS"[..]).unwrap();
                let cors_headers = Header::from_bytes(&b"Access-Control-Allow-Headers"[..], &b"Content-Type, Authorization"[..]).unwrap();

                if req.method() == &Method::Options {
                    let mut resp = Response::empty(200);
                    resp.add_header(cors_origin);
                    resp.add_header(cors_methods);
                    resp.add_header(cors_headers);
                    let _ = req.respond(resp);
                    continue;
                }

                let url_path = req.url().split('?').next().unwrap_or("");

                match (req.method(), url_path) {
                    (&Method::Get, "/status") | (&Method::Get, "/") => {
                        let json = r#"{"status":"running","app":"DFM","version":"2.0"}"#;
                        let mut resp = Response::from_string(json);
                        resp.add_header(cors_origin);
                        resp.add_header(Header::from_bytes(&b"Content-Type"[..], &b"application/json"[..]).unwrap());
                        let _ = req.respond(resp);
                    }
                    (&Method::Post, "/download") | (&Method::Post, "/add") => {
                        let mut body = String::new();
                        let _ = req.as_reader().read_to_string(&mut body);

                        if let Ok(payload) = serde_json::from_str::<BridgeRequestPayload>(&body) {
                            if let Some(target_url) = payload.url {
                                let mut final_headers = payload.headers;
                                if let Some(ref_val) = payload.referer {
                                    final_headers.insert("Referer".to_string(), ref_val);
                                }
                                if let Some(cookies) = payload.cookies {
                                    if !cookies.is_empty() {
                                        final_headers.insert("Cookie".to_string(), cookies);
                                    }
                                }

                                let _ = self.tx.send(BridgeMessage {
                                    url: target_url,
                                    filename: payload.filename,
                                    is_video: payload.is_video.unwrap_or(false),
                                    headers: final_headers,
                                });

                                let mut resp = Response::from_string(r#"{"status":"accepted"}"#);
                                resp.add_header(cors_origin);
                                resp.add_header(Header::from_bytes(&b"Content-Type"[..], &b"application/json"[..]).unwrap());
                                let _ = req.respond(resp);
                                continue;
                            }
                        }

                        let mut resp = Response::from_string(r#"{"error":"invalid payload"}"#).with_status_code(400);
                        resp.add_header(cors_origin);
                        let _ = req.respond(resp);
                    }
                    _ => {
                        let mut resp = Response::empty(404);
                        resp.add_header(cors_origin);
                        let _ = req.respond(resp);
                    }
                }
            }
        });
    }
}
