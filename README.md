# NoteBookLM-復健科 LINE Bot

這是一個整合 Google NotebookLM 與 LINE Bot 的應用程式，專為復健科醫師與專業人員設計。它能夠讀取指定的 NotebookLM 資料（如醫學論文、復健科相關文獻），並透過 LINE 介面提供專業的繁體中文解答與關鍵數據整理。

## 功能特色

*   **專業回答**：針對復健科領域設計的 Prompt，提供給醫師專業、詳細的解答。
*   **論文引用**：回答內容會根據 NotebookLM 中的資料來源進行解答，並附上關鍵數據。
*   **快速回應**：使用背景長連線 (Keep-Alive) 機制，加速 NotebookLM 的查詢回應速度。
*   **便利介面**：直接透過 LINE 聊天室即可進行詢問，無需開啟電腦或網頁。

## 技術架構

*   **Backend**: Python Flask
*   **AI Integration**: [NotebookLM Unofficial API](https://github.com/dpanth3r/notebooklm-unofficial) (感謝開源社群)
*   **Messaging**: LINE Messaging API
*   **Concurrency**: 整合 `asyncio` 與 `threading` 處理非同步查詢，避免 Flask 卡住。

## 安裝與設定

### 1. 前置需求

*   Python 3.10+
*   一個 LINE Official Account (取得 Channel Secret 與 Access Token)
*   Google NotebookLM 的使用權限

### 2. 安裝套件

```bash
pip install -r requirements.txt
```

### 3. 環境變數設定

請在專案根目錄建立 `.env` 檔案，並填入以下資訊：

```env
LINE_CHANNEL_ACCESS_TOKEN=你的LINE_Channel_Access_Token
LINE_CHANNEL_SECRET=你的LINE_Channel_Secret
NOTEBOOK_ID=你的NotebookLM_ID
GOOGLE_AUTH_FILE=storage_state.json
```

> **注意**：`storage_state.json` 是 NotebookLM 的登入憑證，需透過 `notebooklm-unofficial` 的認證流程取得。

### 4. 啟動伺服器

```bash
python app.py
```

預設會運行在 port 5000。你需要使用 ngrok 或部署到雲端服務 (如 Render, Heroku, Railway) 來讓 LINE Platform 能夠存取你的 Webhook URL。

## 使用說明

1.  將 LINE Bot 加為好友。
2.  在聊天室中直接輸入你想查詢的復健科相關問題。
3.  機器人會查詢 NotebookLM 中的文獻，並回復專業的整理摘要。

## 免責聲明

此工具僅供輔助參考，臨床決策請務必依據醫師專業判斷為準。
