# AGY Token Monitor v2.2.0 - Multi-CLI 瑞士極簡深鈦精度 HUD

專為 **Antigravity (AGY)**、**GitHub Copilot**、**Claude Code CLI** 與 **OpenAI Codex** 打造的高階專業極簡桌面懸浮儀表（設計語彙借鏡 Apple Dynamic Island、Teenage Engineering、Vercel 與 Linear），極致洗鍊、克制、俐落，提供四大多 CLI 配額監控、自訂選擇顯示特定 CLI 與一鍵快捷切換。
全面落實 **零 Emoji / 零廉價圖示 (Zero-Emoji Pure Typographic & Geometric Precision)** 規範。

---

## 核心升級亮點 (Multi-CLI Edition)

### 1. 四大多 CLI 配額模型與解析 (`src/monitor/multi_cli_parser.py`)
- **1. Antigravity (AGY)**：
  - 雙模型群組 (Gemini `#00E599`, Claude/GPT `#7B61FF`) ✕ 雙時間窗口 (5h 滾動, Weekly 每週限制)
- **2. GitHub Copilot (`copilot`)**：
  - Premium 請求/月度額度剩餘百分比（例如 Claude 3.7 / GPT-4o 快速配額 `85.0% 255/300 req`，重置倒數 `14d 6h`）
  - Hourly / Daily 速率滾動限制剩餘與重置時間（例如 `92.0%`，重置倒數 `45m`）
  - 專屬主題色：GitHub Electric Blue (`#58A6FF`)
- **3. Claude Code CLI (`claude`)**：
  - 5 小時花費/Token 窗口剩餘百分比（例如 `78.5%`，重置倒數 `2h 40m`）
  - 月度預算/配額剩餘百分比（例如 `91.2% $91.20 / $100.00`）
  - 自動監聽本機 `~/.claude/projects/` 或 `~/.claude.json` / session 記錄，亦支援手動同步
  - 專屬主題色：Claude Warm Terracotta (`#E57B39`)
- **4. OpenAI Codex (`codex`)**：
  - 自動讀取本機 `~/.codex/sessions/**/*.jsonl` 的 `rate_limits` 事件
  - 5 小時與 7 天窗口剩餘百分比、reset 倒數、plan type、累計 token
  - 不讀取 `auth.json` 或資料庫；沒有本機 session 時仍可手動貼上狀態
  - 專屬主題色：OpenAI Green (`#10A37F`)

### 2. 自訂選擇顯示特定 CLI (Selective CLI Display & Quick Switcher)
- **膠囊主畫面 (Top Pill HUD，36px 緊湊高度)**：
  - 顯示當前選定 CLI 的微標籤與數值（如 `GEMINI: 60.1%`、`COPILOT: 85.0%`、`CLAUDE: 78.5%`）及其滾動剩餘量與倒數。
  - 提供一鍵快捷切換按鈕（例如 `[ AGY ]` 點擊即時切換至 `[ COPILOT ]` 或 `[ CLAUDE ]`）。
  - 環形儀表 (`CircularProgressRing`) 與呼吸狀態燈 (`GlowingPulseDot`) 自動對應當前 CLI 專屬色系與比例。
- **展開式 Mini-Dashboard 抽屜**：
  - 依據使用者勾選之 `enabled_clis` 動態顯示已啟用的 CLI 卡片：
    - `ANTIGRAVITY (AGY)` 卡片
    - `GITHUB COPILOT` 卡片
    - `CLAUDE CODE CLI` 卡片
    - `OPENAI CODEX` 卡片
  - 支援多 CLI 專屬「SYNC 同步對話框」與快速範例載入解析。
- **右鍵選單即時勾選**：
  - 「監控 CLI 項目 (自訂顯示)」即時勾選開關任意 CLI，抽屜卡片與主視窗即時聯動。

### 3. Windows 專屬應用程式圖示與桌面捷徑
- **高解析度圖示 (`src/assets/app.ico` & `src/assets/icon.png`)**：
  - 深曜石鈦金黑圓角微矩陣幾何 HUD 圖示（內嵌 256x256, 128x128, 64x64, 48x48, 32x32, 16x16 多尺寸 .ico）。
  - 設定 Windows App User Model ID，在工作列呈現獨立專屬圖示。
- **一鍵建立桌面捷徑**：
  - 執行 `create_desktop_shortcut.bat` 或 `create_desktop_shortcut.ps1`，自動在桌面生成無黑窗 (`pythonw.exe`) 的啟動捷徑。

---

## 專案架構

```text
C:\Users\User\projects\agy-token-monitor\
├── requirements.txt               # PySide6, watchdog 依賴清單
├── run.bat                        # Windows 啟動腳本
├── create_desktop_shortcut.bat    # 一鍵建立桌面捷徑批次檔
├── create_desktop_shortcut.ps1    # 桌面捷徑 PowerShell 腳本
├── generate_app_icon.py           # 專屬高解析度圖示生成腳本
├── test_monitor.py                # 自動化測試套件 (100% 通過)
├── README.md                      # 說明文件
└── src/
    ├── assets/
    │   ├── app.ico                # 256/128/64/48/32/16 多尺寸 Windows 圖示
    │   └── icon.png               # 256x256 高解析度 PNG
    ├── config.py                  # Multi-CLI 設定、定價、上限與狀態持久化
    ├── main.py                    # 程式入口、Multi-CLI AlertManager、系統匣
    ├── monitor/
    │   ├── multi_cli_parser.py    # AGY, Copilot, Claude Code, Codex 資料模型與解析器
    │   ├── quota_parser.py        # 向後相容導出模組
    │   ├── token_parser.py        # JSONL 解析、TPM 計算、SessionTokenStats
    │   └── log_watcher.py         # 檔案監控與 Multi-CLI 即時數據同步
    └── ui/
        ├── widgets.py             # CircularProgressRing, GlowingPulseDot, ChevronButton, MiniSparkline
        ├── floating_capsule.py    # 36px 膠囊 HUD、動態抽屜卡片、UsageSyncDialog
        └── style.py               # Obsidian Titanium 瑞士極簡深鈦 HUD 樣式表
```

---

## 執行與測試

### 一鍵建立桌面捷徑
```cmd
create_desktop_shortcut.bat
```

### 啟動程式
```cmd
run.bat
```
或直接雙擊桌面上的 **「AGY Quota Monitor」** 捷徑圖示！

### 執行完整測試套件 (100% Pass)
```cmd
python test_monitor.py
```
