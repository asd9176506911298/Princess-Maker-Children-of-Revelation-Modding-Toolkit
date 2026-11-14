# Princess Maker: Children of Revelation — TableData & Bundle 工具

[English](README.md) | **繁體中文** | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md)

給 **Princess Maker: Children of Revelation**（Steam）使用的 Windows 圖形介面小工具：解密 AssetBundle、抽出並編輯加密的 `TableData`，並可用修改檔 (patch) 在遊戲更新後保留你的修改。

介面語言：繁體中文 / 简体中文 / English / 日本語 / 한국어（右上角可切換）。

## 功能

- **Bundle 解密** — 原地解密 `packedassets_assets_all_*.bundle`（會先建立 `.bak` 備份）。
- **TableData 抽出 / 編輯** — 從 `resources.assets` 取出 `TableData` 並解密，建立 SQLite 資料庫與每張表一個 JSON。
- **資料庫瀏覽** — 搜尋資料表、Filter 篩選列、雙擊儲存格編輯、唯讀 SQL 查詢。修改後會保留原本的型別（數字、布林、陣列）。
- **重新加密並輸出** — 產生 `TableData_modified.txt`，再用 [UABEANext](https://github.com/nesrak1/UABEANext) 匯入 `resources.assets`。本工具本身不會覆寫 `resources.assets`。
- **修改檔 (patch)** — 把你的修改存成小檔案，遊戲更新後一鍵套用。

## 安裝與執行

### 方式 A：下載 exe（最簡單）

到 [Releases](../../releases) 下載 `PrincessMakerTool.exe`，請放在專用資料夾，工具會在 exe 旁邊建立工作檔案。不需要安裝 Python。

### 方式 B：用原始碼執行

需要 Python 3.10 以上：

```bash
pip install -r requirements.txt
python PrincessMakerTool.py
```

## 基本流程

1. 選擇遊戲根目錄（含有 `PrincessMakerKaren_Data` 的那層），按 **自動尋找**。
2. **Bundle 解密** 分頁 → 解密 Bundle（只需一次）。
3. **TableData** 分頁：
   1. 從 resources.assets 抽出並解密
   2. 建立資料庫 + 匯出 JSON
4. **資料庫瀏覽 / 編輯** 分頁 → 點表名，雙擊儲存格修改，按「保存修改」。
5. **TableData** 分頁 → 步驟 3「重新加密並輸出 TableData_modified.txt」。
6. 用 UABEANext 開啟 `resources.assets`，把 `TableData_modified.txt` 匯入 `TableData` 後存檔。

也可以直接修改 `tables/` 內的 JSON，再按「從 tables 重新載入」。

## 遊戲更新後保留你的修改

遊戲更新會換掉 `TableData`，舊資料上的修改會跟著消失。請用修改檔：

1. **建立修改檔（儲存我的修改）** — 只記錄與原始資料的差異，用每列唯一的 ID 欄位定位。
2. 更新遊戲後，重做步驟 1、2（抽出 + 建立資料庫）。
3. **套用修改檔（還原我的修改）** — 把修改檔套到新資料上。
4. 步驟 3 輸出 → 再用 UABEANext 匯入。

如果遊戲也改了你改過的欄位，會詢問要用你的值覆蓋，還是保留遊戲的新值。無法對應的項目（列被刪除、欄位改名、整張表消失）不會被默默丟掉，而是列在 `patches/apply_report_*.txt`。

安全機制：步驟 2 覆蓋 `tables/` 之前，會先把你目前的修改自動存成 `patches/auto_before_reexport_*.json`。

## 會在 exe 旁邊建立的檔案

| 路徑 | 用途 |
|---|---|
| `TableData.dec.bin` | 解密後的 TableData |
| `TableData.db` | 瀏覽器使用的 SQLite 資料庫 |
| `tables/` | 每張表一個 JSON（你的可編輯副本） |
| `tables_orig/` | 未修改的原始副本，作為 patch 比對基準 |
| `patches/` | 修改檔與套用報告 |
| `TableData_modified.txt` | 最終輸出，用 UABEANext 匯入 |
| `pm_tool_settings.json` | 語言與上次的遊戲資料夾 |

## 自行打包 exe

把 `PrincessMakerTool.py`、`requirements.txt`、`build.bat` 放在同一個資料夾，雙擊 `build.bat`，成品在 `dist\PrincessMakerTool.exe`。

## 注意事項

- 僅支援 Windows（建置腳本與路徑針對 Windows 版 Steam）。
- 請務必備份遊戲檔案。Steam →「驗證遊戲檔案完整性」可以還原。
- 未簽章的單檔 exe 有時會被防毒軟體或 SmartScreen 誤報，想避免的話可以自行用原始碼打包。
- 沒有唯一 ID 欄位的表，patch 會退回用列的位置比對，遊戲更新後較不可靠。

## 免責聲明

本工具為非官方的玩家自製工具，與遊戲開發商及發行商無關，且不包含任何遊戲資料。請僅用於你合法取得的遊戲副本，風險自負。

**AI 生成的程式碼：** 本專案的程式碼由 AI（Anthropic 的 Claude）生成。如有疑慮請自行檢查原始碼，並務必備份遊戲檔案。
