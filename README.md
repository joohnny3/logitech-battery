# Logitech Mouse Battery Tray Monitor

在系統匣（Windows）或選單列（macOS）即時顯示 Logitech 滑鼠電量的常駐小工具。

透過 HID++ 2.0 協議直接與裝置通訊，不需要 Logitech G HUB / Options+。

## 支援裝置

- **連線方式**: Lightspeed USB Receiver、Bluetooth
- **協議**: HID++ 2.0 / 4.2（UNIFIED_BATTERY / BATTERY_STATUS / BATTERY_VOLTAGE）
- **已測試**: Logitech G Pro X SUPERLIGHT 2（Lightspeed）

理論上支援所有使用 HID++ 2.0+ 協議的 Logitech 裝置（MX Master 系列、G 系列、MX Keys 等）。

## 功能

- 系統匣/選單列顯示電池形狀 icon，液位填充表示電量
- 顏色指示：>50% 綠色、15-50% 黃色、≤15% 紅色
- Hover tooltip 顯示裝置名稱、電量、更新時間
- 右鍵選單：立即更新 / 離開
- 低電量通知（可設定門檻值）
- 每 60 秒自動更新（可設定）

## 系統需求

- Python 3.10+
- Windows 10/11 或 macOS 12+

## 安裝

### 1. Clone

```bash
git clone https://github.com/YOUR_USERNAME/mouse-battery.git
cd mouse-battery
```

### 2. 建立虛擬環境並安裝依賴

**macOS / Linux:**
```bash
chmod +x scripts/run.sh
scripts/run.sh
```

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt
```

### 3. 設定（可選）

```bash
# 首次執行時會自動從範本建立，或手動複製：
cp config/config.example.json config/config.json
```

編輯 `config/config.json`：

| 欄位 | 預設值 | 說明 |
|---|---|---|
| `refresh_seconds` | `60` | 電量更新間隔（秒） |
| `low_battery_threshold` | `20` | 低電量門檻（%） |
| `enable_low_battery_notification` | `true` | 是否啟用低電量通知 |
| `device_name_keywords` | `["Logitech"]` | 裝置名稱關鍵字過濾 |

### 4. 執行

**macOS / Linux:**
```bash
scripts/run.sh
```

**Windows:**
```powershell
.\venv\Scripts\python -m app.main
```

## macOS 注意事項

### HID 權限

macOS 可能需要授權 Terminal（或 iTerm2）存取 HID 裝置：

1. 開啟 **系統偏好設定 > 安全性與隱私 > 隱私 > 輸入監控**
2. 將您的 Terminal app 加入允許清單
3. 重新啟動 Terminal 後執行

### 選單列行為

macOS 上 icon 會出現在頂部選單列（而非系統匣），左鍵點擊顯示下拉選單。

## 開發

```bash
# 安裝依賴
pip install -r requirements.txt

# 執行測試
pytest tests/ -v

# 直接執行
python -m app.main
```

## 專案結構

```
mouse-battery/
├── app/
│   ├── main.py              # 進入點
│   ├── bootstrap.py          # 元件初始化與組裝
│   ├── config.py             # 設定檔讀取
│   ├── logger.py             # 日誌設定
│   ├── notifier.py           # 低電量通知
│   ├── tray_app.py           # 系統匣/選單列 UI
│   ├── models/
│   │   └── battery_status.py # 資料模型
│   └── services/
│       ├── connection.py     # HID 連線抽象（Lightspeed / Bluetooth）
│       ├── battery_reader.py # HID++ 2.0 電量讀取
│       └── scheduler.py      # 定時更新排程
├── config/
│   ├── config.example.json   # 設定檔範本
│   └── config.json           # 使用者設定（不進 git）
├── scripts/
│   ├── run.ps1               # Windows 啟動腳本
│   └── run.sh                # macOS/Linux 啟動腳本
├── tests/                    # 單元測試
├── requirements.txt
└── README.md
```

## 技術細節

本工具使用 [HID++ 2.0 協議](https://lekensteyn.nl/files/logitech/logitech_hidpp_2.0_specification_draft_2012-06-04.pdf) 直接與 Logitech 裝置通訊。

- **Lightspeed USB**: 透過 USB Receiver 的 vendor-specific HID 介面（usage_page 0xFF00），雙通道通訊（short + long）
- **Bluetooth**: 直連裝置，單通道 long message，device_index 0xFF

參考專案：[Solaar](https://github.com/pwr-Solaar/Solaar)

## License

MIT
