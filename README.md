# ⚡ DFM (Download Fast Manager)
### High-Performance Internet Download Manager Alternative for Windows

**DFM (Download Fast Manager)** is a lightweight, modern, open-source download accelerator and streaming media grabber designed to completely replace Internet Download Manager (IDM).

---

## 🚀 Key Features

1. **Multi-Threaded Segmented Download Engine**:
   - Dynamic file chunking with up to **32 concurrent connections** per file.
   - Bypasses per-connection server throttling to maximize your internet bandwidth.
   - **Iconic Segment Visualizer**: Real-time visualization of individual connection threads racing to download chunks, just like IDM.
   - Full **Pause & Resume** support with crash recovery and zero data loss.

2. **Universal Streaming Video & Media Grabber**:
   - Powered by `yt-dlp` and `FFmpeg` to download video and audio from 1000+ streaming sites:
     - **YouTube, Facebook, Twitter/X, TikTok, Instagram, Vimeo, Reddit, Twitch, Dailymotion, etc.**
   - Multi-quality selector: 4K, 1440p, 1080p Full HD, 720p HD, and Audio-Only MP3 conversion.
   - Direct support for HLS (`.m3u8`) and DASH (`.mpd`) video streams.

3. **Smart Clipboard Sniffer**:
   - Automatically monitors your Windows clipboard for copied links.
   - Detects archive files (`.zip`, `.rar`, `.7z`, `.iso`), executables (`.exe`, `.msi`), media (`.mp4`, `.mkv`, `.mp3`), documents (`.pdf`), and video URLs.
   - Instantly pops up the IDM-style download prompt.

4. **Browser Integration**:
   - Built-in local HTTP API server running on port `9666`.
   - **Chrome / Edge / Brave Extension**:
     - Right-click any link or web page to select *"Download with DFM"*.
     - One-click popup to send the current tab's video or file directly to DFM.
   - **Tampermonkey / Violentmonkey Userscript**:
     - Floating *"Download with DFM"* button appears right on YouTube, Facebook, TikTok, and video players.

5. **Modern Windows 11 Dark Interface**:
   - Category filtering: *All Downloads, Downloading, Finished, Unfinished, Compressed, Programs, Video, Audio, Documents, Others*.
   - Live speed graph, transfer rate, ETA calculator, and per-download progress bars.
   - System tray minimization with toast notification balloons upon download completion.
   - Configurable speed limiter (bandwidth throttle).

---

## 🖥️ How to Install and Run DFM

### On Windows:
1. **Windows Setup Installer (Recommended)**:
   - Double-click **`DFM_Setup.exe`** (located on your **Desktop** or at `D:\DFM\DFM_Setup.exe`).
   - Follow the modern setup wizard: it installs DFM into your system, creates Start Menu and Desktop shortcuts, and registers DFM in **Windows Settings / Add or Remove Programs** with an uninstaller.
2. **Desktop Shortcut**: Double-click **"DFM Downloader"** on your Desktop.
3. **Pre-compiled Executable**: Run `d:\DFM\dist\DFM\DFM.exe`.
4. **Batch Launcher**: Double-click `d:\DFM\run.bat`.

### On Ubuntu / Linux:
1. **1-Step Automated Installer**:
   Open a terminal in the DFM directory and run:
   ```bash
   chmod +x install_ubuntu.sh
   ./install_ubuntu.sh
   ```
   This installs all prerequisites (`python3`, `PyQt6`, `FFmpeg`, `yt-dlp`), adds the `dfm` command to your system, and adds **DFM Downloader** to your Ubuntu Applications / Dash menu with its icon.

2. **Quick Run**:
   ```bash
   ./run.sh
   ```
   Or from anywhere after installation:
   ```bash
   dfm
   ```

---

## 🌐 Browser Extension Setup (Chrome, Edge, Brave, Opera)

1. Open your browser and go to `chrome://extensions` (or `edge://extensions`).
2. Enable **"Developer mode"** in the top-right corner.
3. Click **"Load unpacked"** and select the folder:
   ```
   D:\DFM\browser_extension
   ```
4. You will now see the **DFM Download Integration** icon in your browser toolbar!
   - Right-click any link or video player and choose **"Download with DFM"**.

---

## 🎬 Floating Video Button Setup (Tampermonkey Userscript)

If you use Tampermonkey or Violentmonkey:
1. Open the file `D:\DFM\browser_extension\dfm_grabber.user.js`.
2. Copy the code into a new script in Tampermonkey / Violentmonkey.
3. When watching YouTube, Facebook, Twitter, TikTok, or Vimeo, a stylish floating **"⚡ Download with DFM"** button will appear on the bottom-right corner!

---

## 📂 Project Structure

```
D:\DFM\
│── main.py                   # Main GUI application entrypoint
│── run.bat                   # 1-click Windows batch launcher
│── run.sh                    # 1-click Ubuntu/Linux shell launcher
│── install_ubuntu.sh         # Automated installer for Ubuntu/Debian
│── dfm.desktop               # Linux XDG desktop entry shortcut
│── requirements.txt          # Python dependencies
│── create_desktop_shortcut.ps1 # Creates Windows desktop shortcut
│── dist\DFM\DFM.exe          # Standalone Windows executable
│── core\
│   │── downloader.py         # Multi-threaded segmented download engine
│   │── video_downloader.py   # yt-dlp & FFmpeg streaming media grabber
│   │── download_manager.py   # Queue coordinator & scheduling
│   │── database.py           # SQLite database persistence
│   │── clipboard_listener.py # Clipboard sniffer
│   │── browser_bridge.py     # Local HTTP REST API for browser integration
│   └── utils.py              # Cross-platform file opener, categories, formatting
│── ui\
│   │── main_window.py        # IDM-style main window with sidebar and table
│   │── dialogs\
│   │   │── add_download_dialog.py      # New download & media format picker
│   │   │── download_progress_dialog.py # Iconic IDM multi-thread progress dialog
│   │   └── settings_dialog.py          # Options & configuration
│   └── widgets\
│       └── segment_progress_bar.py     # Custom painted multi-segment chunk bar
│── browser_extension\        # Chrome / Edge / Brave / Firefox extension
└── assets\                   # App icons (.ico and .png)
```

---

## ⚙️ Configuration & Options

Inside DFM, click **⚙ Settings** to customize:
- **Default Download Directory**: Where files and videos are stored.
- **Segment Count**: Default number of parallel connections (1 to 32, default is 8).
- **Max Concurrent Downloads**: Limit simultaneous downloads to conserve bandwidth.
- **Speed Limiter**: Cap download speeds (in KB/s).
- **Clipboard Monitoring**: Toggle automatic link sniffer on or off.
- **Minimize to Tray**: Keep DFM active in background system tray when window is closed.
