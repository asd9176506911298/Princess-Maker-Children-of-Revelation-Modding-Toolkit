"""
Princess Maker TableData & Bundle Tool
Multi-language edition (繁體中文 / 简体中文 / English / 日本語 / 한국어)

Workflow:
  1. Select game folder -> Auto detect
  2. Bundle decrypt (once)
  3. TableData: extract -> build DB + export JSON
  4. Edit in the DB browser (edits are written to DB *and* tables/*.json, types preserved)
  5. Re-encrypt and output TableData_modified.txt
  6. Import that file into resources.assets with UABEANext
"""

import os
import sys
import copy
import json
import queue
import hashlib
import hmac
import sqlite3
import shutil
import threading
import subprocess
from pathlib import Path
from datetime import datetime
from collections import OrderedDict

import customtkinter as ctk
from tkinter import ttk, filedialog, messagebox, simpledialog
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Util import Counter
from Crypto.Random import get_random_bytes
import msgpack

try:
    import UnityPy
except ImportError:
    UnityPy = None


# =========================================================
#  Settings (language, last game folder)
# =========================================================
def _app_dir() -> Path:
    """Folder next to the .exe when packaged with PyInstaller, otherwise next to this script.
    (In a one-file build __file__ points into a temp folder that is deleted on exit.)"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


APP_DIR = _app_dir()
SETTINGS_PATH = APP_DIR / "pm_tool_settings.json"


def load_settings() -> dict:
    try:
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_settings(d: dict):
    try:
        SETTINGS_PATH.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


# =========================================================
#  i18n
# =========================================================
LANG_NAMES = OrderedDict([
    ("zh-TW", "繁體中文"),
    ("zh-CN", "简体中文"),
    ("en", "English"),
    ("ja", "日本語"),
    ("ko", "한국어"),
])

TAB_KEYS = ["tab_home", "tab_bundle", "tab_table", "tab_db", "tab_log"]

STRINGS = {
    # ------------------------------------------------------------------
    "en": {
        "app_title": "Princess Maker TableData & Bundle Tool",
        "language": "Language:",
        "game_root": "Game folder:",
        "select_folder": "Browse",
        "auto_find": "Auto detect",
        "tab_home": "Overview",
        "tab_bundle": "Bundle Decrypt",
        "tab_table": "TableData",
        "tab_db": "Database Browser / Editor",
        "tab_log": "Log",
        "guide_title": "Instructions",
        "guide": (
            "1. Select the game folder -> Auto detect\n"
            "2. Decrypt the Bundle (only needed once)\n"
            "3. TableData -> extract & decrypt -> build database + export JSON\n"
            "4. Database Browser / Editor:\n"
            "   - Click a table name to load it\n"
            "   - Use the Filter box to search quickly (e.g. Rollipop)\n"
            "   - Double-click a cell to edit, then press \"Save changes\"\n"
            "     (changes are written to the DB and to the JSON in the tables folder)\n"
            "   - Or edit the JSON files in the tables folder directly,\n"
            "     then press \"Reload from tables\"\n"
            "5. When done, use step 3 on the TableData tab to produce TableData_modified.txt\n"
            "6. Open resources.assets with UABEANext and import that file into TableData, then save\n"
            "7. After a game update: Create patch -> redo steps 1 and 2 -> Apply patch -> step 3 -> import again\n"
            "   (step 2 also auto-saves your edits as a patch before it overwrites the tables folder)"
        ),
        "status_none": "No game folder selected yet",
        "bundle_found": "Bundle: {p}",
        "bundle_not_found": "Bundle not found",
        "res_found": "resources.assets: {p}",
        "res_not_found": "resources.assets not found",
        "auto_done": "Auto detect finished",
        "dir_missing": "The folder does not exist",
        "dlg_error": "Error",
        "dlg_done": "Done",
        "dlg_hint": "Notice",
        "dlg_confirm": "Confirm",
        "bundle_title": "AssetBundle Decrypt",
        "bundle_desc": "The original file name is kept so the game can read it directly. A backup is made and the folder is opened automatically.",
        "bundle_btn": "Decrypt Bundle",
        "bundle_missing": "Bundle not found",
        "bundle_backup": "Backed up -> {name}",
        "bundle_already": "This Bundle already looks decrypted (UnityFS header). Skipped.",
        "bundle_ok_label": "Decrypted successfully!",
        "bundle_log_ok": "Bundle decrypted",
        "bundle_dlg_ok": "Bundle decrypted. The folder has been opened.",
        "table_title": "TableData",
        "btn_extract": "1. Extract & decrypt from resources.assets",
        "btn_export": "2. Build database + export JSON",
        "btn_output": "3. Re-encrypt and output TableData_modified.txt",
        "need_unitypy": "Please install unitypy first (pip install unitypy)",
        "res_missing": "resources.assets not found",
        "tabledata_missing": "TableData TextAsset not found",
        "extract_ok_log": "TableData decrypted ({n:,} bytes)",
        "extract_ok_label": "Extracted and decrypted -> TableData.dec.bin",
        "extract_ok_dlg": "TableData has been decrypted",
        "dec_missing": "TableData.dec.bin not found. Run step 1 first.",
        "db_ok_log": "Database built, {n} tables",
        "db_ok_label": "Database built -> {p}",
        "db_ok_dlg": "Database and JSON files created",
        "no_db": "Database not found. Run step 2 first.",
        "json_missing": "{f} not found. Run step 2 first.",
        "output_log": "Output {p} ({n:,} bytes)",
        "output_dlg": "Output written to:\n{p}\n\nImport it into TableData inside resources.assets with UABEANext.",
        "output_fail": "Output failed: {e}",
        "tables_label": "Tables (click)",
        "refresh_list": "Refresh table list",
        "btn_save": "Save changes",
        "btn_reload": "Reload current table",
        "btn_reload_json": "Reload from tables",
        "filter": "Filter:",
        "clear": "Clear",
        "dirty_flag": "● Unsaved changes",
        "sql_label": "SQL query (read-only, results shown below)",
        "run_sql": "Run SQL",
        "sql_ok": "OK, no rows returned",
        "sql_err": "Error: {e}",
        "sql_more": "... {n} rows in total, showing the first 200",
        "unsaved_title": "Unsaved",
        "unsaved_msg": "There are unsaved changes. Discard them?",
        "loaded": "Loaded table: {name} ({n} rows)",
        "edit_title": "Edit value",
        "edit_prompt": "Column: {col}\n\n(full content is editable)",
        "no_changes": "There are no changes to save",
        "not_list": "This table is not a standard list of records. Please edit its JSON in the tables folder directly.",
        "bad_value": "Invalid value \"{val}\" for column \"{col}\" (row {row}): {e}",
        "saved_log": "Saved table {name} (DB + JSON)",
        "saved_dlg": "Changes saved",
        "tables_missing": "tables folder not found",
        "reload_confirm": "The database will be rebuilt from the JSON files in the tables folder. Continue?",
        "reload_log": "Reloaded {n} tables from the tables folder",
        "reload_dlg": "Reloaded from the tables folder",
    },
    # ------------------------------------------------------------------
    "zh-TW": {
        "app_title": "Princess Maker TableData & Bundle 工具",
        "language": "語言:",
        "game_root": "遊戲根目錄:",
        "select_folder": "選擇資料夾",
        "auto_find": "自動尋找",
        "tab_home": "總覽",
        "tab_bundle": "Bundle 解密",
        "tab_table": "TableData",
        "tab_db": "資料庫瀏覽 / 編輯",
        "tab_log": "Log",
        "guide_title": "使用說明",
        "guide": (
            "1. 選擇遊戲根目錄 → 自動尋找\n"
            "2. Bundle 解密（只需一次）\n"
            "3. TableData → 抽出解密 → 建立資料庫 + 匯出 JSON\n"
            "4. 資料庫瀏覽 / 編輯：\n"
            "   - 點表名載入資料\n"
            "   - 上方 Filter 可快速搜尋（例如輸入 Rollipop）\n"
            "   - 雙擊儲存格修改，完成後按「保存修改」\n"
            "     （會同步寫入資料庫與 tables 資料夾內的 JSON）\n"
            "   - 或直接修改 tables 資料夾的 JSON，再按「從 tables 重新載入」\n"
            "5. 修改完成後，到 TableData 分頁按步驟 3，產生 TableData_modified.txt\n"
            "6. 用 UABEANext 開啟 resources.assets，把該檔案匯入 TableData 後存檔\n"
            "7. 遊戲更新後：建立修改檔 → 重做步驟 1、2 → 套用修改檔 → 步驟 3 → 重新匯入\n"
            "   （步驟 2 覆蓋 tables 資料夾前，也會自動把你的修改備份成修改檔）"
        ),
        "status_none": "尚未選擇遊戲目錄",
        "bundle_not_found": "找不到 Bundle",
        "res_not_found": "找不到 resources.assets",
        "auto_done": "自動尋找完成",
        "dir_missing": "目錄不存在",
        "dlg_error": "錯誤",
        "dlg_done": "完成",
        "dlg_hint": "提示",
        "dlg_confirm": "確認",
        "bundle_title": "AssetBundle 解密",
        "bundle_desc": "解密後保持原檔名，遊戲可直接讀取。會自動備份並開啟資料夾。",
        "bundle_btn": "解密 Bundle",
        "bundle_missing": "找不到 Bundle",
        "bundle_backup": "已備份 → {name}",
        "bundle_already": "此 Bundle 看起來已經解密過（UnityFS 檔頭），已略過。",
        "bundle_ok_label": "解密成功！",
        "bundle_log_ok": "Bundle 解密完成",
        "bundle_dlg_ok": "Bundle 解密完成，已開啟資料夾",
        "table_title": "TableData 處理",
        "btn_extract": "1. 從 resources.assets 抽出並解密",
        "btn_export": "2. 建立資料庫 + 匯出 JSON",
        "btn_output": "3. 重新加密並輸出 TableData_modified.txt",
        "need_unitypy": "請先安裝 unitypy（pip install unitypy）",
        "res_missing": "找不到 resources.assets",
        "tabledata_missing": "找不到 TableData TextAsset",
        "extract_ok_log": "TableData 解密成功 ({n:,} bytes)",
        "extract_ok_label": "已抽出並解密 → TableData.dec.bin",
        "extract_ok_dlg": "TableData 已解密",
        "dec_missing": "找不到 TableData.dec.bin，請先執行步驟 1",
        "db_ok_log": "資料庫建立完成，共 {n} 張表",
        "db_ok_label": "資料庫已建立 → {p}",
        "db_ok_dlg": "資料庫與 JSON 建立成功",
        "no_db": "找不到資料庫，請先執行步驟 2",
        "json_missing": "找不到 {f}，請先執行步驟 2",
        "output_log": "已輸出 {p} ({n:,} bytes)",
        "output_dlg": "已輸出：\n{p}\n\n請用 UABEANext 將它匯入 resources.assets 內的 TableData。",
        "output_fail": "輸出失敗: {e}",
        "tables_label": "資料表（點選）",
        "refresh_list": "重新整理表清單",
        "btn_save": "保存修改",
        "btn_reload": "重新載入目前表",
        "btn_reload_json": "從 tables 重新載入",
        "filter": "Filter:",
        "clear": "清除",
        "dirty_flag": "● 有未保存的修改",
        "sql_label": "SQL 查詢（唯讀，結果顯示於下方）",
        "run_sql": "執行 SQL",
        "sql_ok": "執行成功，無回傳資料",
        "sql_err": "錯誤: {e}",
        "sql_more": "... 共 {n} 筆，只顯示前 200 筆",
        "unsaved_title": "未保存",
        "unsaved_msg": "目前有未保存的修改，要放棄嗎？",
        "loaded": "已載入表: {name} ({n} 筆)",
        "edit_title": "修改欄位",
        "edit_prompt": "欄位: {col}\n\n（可編輯完整內容）",
        "no_changes": "沒有需要保存的修改",
        "not_list": "此表不是標準的記錄列表格式，請直接修改 tables 資料夾裡的 JSON。",
        "bad_value": "欄位「{col}」（第 {row} 列）的值「{val}」格式不正確：{e}",
        "saved_log": "已保存表 {name}（資料庫 + JSON）",
        "saved_dlg": "修改已保存",
        "tables_missing": "找不到 tables 資料夾",
        "reload_confirm": "將用 tables 資料夾的 JSON 重建資料庫，確定嗎？",
        "reload_log": "已從 tables 重新載入 {n} 個表",
        "reload_dlg": "已從 tables 資料夾重新載入",
    },
    # ------------------------------------------------------------------
    "zh-CN": {
        "app_title": "Princess Maker TableData & Bundle 工具",
        "language": "语言:",
        "game_root": "游戏根目录:",
        "select_folder": "选择文件夹",
        "auto_find": "自动查找",
        "tab_home": "总览",
        "tab_bundle": "Bundle 解密",
        "tab_table": "TableData",
        "tab_db": "数据库浏览 / 编辑",
        "tab_log": "日志",
        "guide_title": "使用说明",
        "guide": (
            "1. 选择游戏根目录 → 自动查找\n"
            "2. Bundle 解密（只需一次）\n"
            "3. TableData → 提取解密 → 建立数据库 + 导出 JSON\n"
            "4. 数据库浏览 / 编辑：\n"
            "   - 点击表名加载数据\n"
            "   - 上方 Filter 可快速搜索（例如输入 Rollipop）\n"
            "   - 双击单元格修改，完成后点击“保存修改”\n"
            "     （会同步写入数据库与 tables 文件夹内的 JSON）\n"
            "   - 或直接修改 tables 文件夹中的 JSON，再点击“从 tables 重新加载”\n"
            "5. 修改完成后，到 TableData 分页点击步骤 3，生成 TableData_modified.txt\n"
            "6. 用 UABEANext 打开 resources.assets，把该文件导入 TableData 后保存\n"
            "7. 游戏更新后：创建补丁 → 重做步骤 1、2 → 应用补丁 → 步骤 3 → 重新导入\n"
            "   （步骤 2 覆盖 tables 文件夹前，也会自动把你的修改备份成补丁）"
        ),
        "status_none": "尚未选择游戏目录",
        "bundle_not_found": "找不到 Bundle",
        "res_not_found": "找不到 resources.assets",
        "auto_done": "自动查找完成",
        "dir_missing": "目录不存在",
        "dlg_error": "错误",
        "dlg_done": "完成",
        "dlg_hint": "提示",
        "dlg_confirm": "确认",
        "bundle_title": "AssetBundle 解密",
        "bundle_desc": "解密后保持原文件名，游戏可直接读取。会自动备份并打开文件夹。",
        "bundle_btn": "解密 Bundle",
        "bundle_missing": "找不到 Bundle",
        "bundle_backup": "已备份 → {name}",
        "bundle_already": "此 Bundle 看起来已经解密过（UnityFS 文件头），已跳过。",
        "bundle_ok_label": "解密成功！",
        "bundle_log_ok": "Bundle 解密完成",
        "bundle_dlg_ok": "Bundle 解密完成，已打开文件夹",
        "table_title": "TableData 处理",
        "btn_extract": "1. 从 resources.assets 提取并解密",
        "btn_export": "2. 建立数据库 + 导出 JSON",
        "btn_output": "3. 重新加密并输出 TableData_modified.txt",
        "need_unitypy": "请先安装 unitypy（pip install unitypy）",
        "res_missing": "找不到 resources.assets",
        "tabledata_missing": "找不到 TableData TextAsset",
        "extract_ok_log": "TableData 解密成功 ({n:,} bytes)",
        "extract_ok_label": "已提取并解密 → TableData.dec.bin",
        "extract_ok_dlg": "TableData 已解密",
        "dec_missing": "找不到 TableData.dec.bin，请先执行步骤 1",
        "db_ok_log": "数据库建立完成，共 {n} 张表",
        "db_ok_label": "数据库已建立 → {p}",
        "db_ok_dlg": "数据库与 JSON 建立成功",
        "no_db": "找不到数据库，请先执行步骤 2",
        "json_missing": "找不到 {f}，请先执行步骤 2",
        "output_log": "已输出 {p} ({n:,} bytes)",
        "output_dlg": "已输出：\n{p}\n\n请用 UABEANext 将它导入 resources.assets 内的 TableData。",
        "output_fail": "输出失败: {e}",
        "tables_label": "数据表（点击）",
        "refresh_list": "刷新表列表",
        "btn_save": "保存修改",
        "btn_reload": "重新加载当前表",
        "btn_reload_json": "从 tables 重新加载",
        "filter": "Filter:",
        "clear": "清除",
        "dirty_flag": "● 有未保存的修改",
        "sql_label": "SQL 查询（只读，结果显示在下方）",
        "run_sql": "执行 SQL",
        "sql_ok": "执行成功，无返回数据",
        "sql_err": "错误: {e}",
        "sql_more": "... 共 {n} 条，仅显示前 200 条",
        "unsaved_title": "未保存",
        "unsaved_msg": "当前有未保存的修改，要放弃吗？",
        "loaded": "已加载表: {name} ({n} 条)",
        "edit_title": "修改字段",
        "edit_prompt": "字段: {col}\n\n（可编辑完整内容）",
        "no_changes": "没有需要保存的修改",
        "not_list": "此表不是标准的记录列表格式，请直接修改 tables 文件夹里的 JSON。",
        "bad_value": "字段“{col}”（第 {row} 行）的值“{val}”格式不正确：{e}",
        "saved_log": "已保存表 {name}（数据库 + JSON）",
        "saved_dlg": "修改已保存",
        "tables_missing": "找不到 tables 文件夹",
        "reload_confirm": "将用 tables 文件夹中的 JSON 重建数据库，确定吗？",
        "reload_log": "已从 tables 重新加载 {n} 个表",
        "reload_dlg": "已从 tables 文件夹重新加载",
    },
    # ------------------------------------------------------------------
    "ja": {
        "app_title": "Princess Maker TableData & Bundle ツール",
        "language": "言語:",
        "game_root": "ゲームフォルダ:",
        "select_folder": "フォルダ選択",
        "auto_find": "自動検出",
        "tab_home": "概要",
        "tab_bundle": "Bundle 復号",
        "tab_table": "TableData",
        "tab_db": "データベース閲覧 / 編集",
        "tab_log": "ログ",
        "guide_title": "使い方",
        "guide": (
            "1. ゲームフォルダを選択 → 自動検出\n"
            "2. Bundle を復号（1回だけ必要）\n"
            "3. TableData → 抽出・復号 → データベース作成 + JSON 書き出し\n"
            "4. データベース閲覧 / 編集：\n"
            "   - テーブル名をクリックしてデータを読み込む\n"
            "   - 上部の Filter で素早く検索（例: Rollipop）\n"
            "   - セルをダブルクリックして編集し、「変更を保存」を押す\n"
            "     （DB と tables フォルダ内の JSON の両方に反映されます）\n"
            "   - または tables フォルダの JSON を直接編集して「tables から再読み込み」を押す\n"
            "5. 編集後、TableData タブのステップ 3 で TableData_modified.txt を出力\n"
            "6. UABEANext で resources.assets を開き、そのファイルを TableData にインポートして保存\n"
            "7. ゲーム更新後：パッチを作成 → ステップ 1、2 をやり直す → パッチを適用 → ステップ 3 → 再インポート\n"
            "   （ステップ 2 は tables を上書きする前に、あなたの編集を自動でパッチとして保存します）"
        ),
        "status_none": "ゲームフォルダが未選択です",
        "bundle_not_found": "Bundle が見つかりません",
        "res_not_found": "resources.assets が見つかりません",
        "auto_done": "自動検出が完了しました",
        "dir_missing": "フォルダが存在しません",
        "dlg_error": "エラー",
        "dlg_done": "完了",
        "dlg_hint": "お知らせ",
        "dlg_confirm": "確認",
        "bundle_title": "AssetBundle 復号",
        "bundle_desc": "元のファイル名のまま復号するので、ゲームがそのまま読み込めます。自動でバックアップを作成し、フォルダを開きます。",
        "bundle_btn": "Bundle を復号",
        "bundle_missing": "Bundle が見つかりません",
        "bundle_backup": "バックアップ作成 → {name}",
        "bundle_already": "この Bundle は既に復号済みのようです（UnityFS ヘッダー）。スキップしました。",
        "bundle_ok_label": "復号に成功しました！",
        "bundle_log_ok": "Bundle の復号が完了しました",
        "bundle_dlg_ok": "Bundle の復号が完了し、フォルダを開きました",
        "table_title": "TableData の処理",
        "btn_extract": "1. resources.assets から抽出して復号",
        "btn_export": "2. データベース作成 + JSON 書き出し",
        "btn_output": "3. 再暗号化して TableData_modified.txt を出力",
        "need_unitypy": "先に unitypy をインストールしてください（pip install unitypy）",
        "res_missing": "resources.assets が見つかりません",
        "tabledata_missing": "TableData の TextAsset が見つかりません",
        "extract_ok_log": "TableData の復号に成功 ({n:,} bytes)",
        "extract_ok_label": "抽出・復号しました → TableData.dec.bin",
        "extract_ok_dlg": "TableData を復号しました",
        "dec_missing": "TableData.dec.bin が見つかりません。先にステップ 1 を実行してください",
        "db_ok_log": "データベースを作成しました（{n} テーブル）",
        "db_ok_label": "データベースを作成 → {p}",
        "db_ok_dlg": "データベースと JSON を作成しました",
        "no_db": "データベースが見つかりません。先にステップ 2 を実行してください",
        "json_missing": "{f} が見つかりません。先にステップ 2 を実行してください",
        "output_log": "出力しました {p} ({n:,} bytes)",
        "output_dlg": "出力しました：\n{p}\n\nUABEANext で resources.assets 内の TableData にインポートしてください。",
        "output_fail": "出力に失敗しました: {e}",
        "tables_label": "テーブル（クリック）",
        "refresh_list": "テーブル一覧を更新",
        "btn_save": "変更を保存",
        "btn_reload": "現在のテーブルを再読み込み",
        "btn_reload_json": "tables から再読み込み",
        "filter": "Filter:",
        "clear": "クリア",
        "dirty_flag": "● 未保存の変更があります",
        "sql_label": "SQL クエリ（読み取り専用、結果は下に表示）",
        "run_sql": "SQL 実行",
        "sql_ok": "成功しました（返却データなし）",
        "sql_err": "エラー: {e}",
        "sql_more": "... 全 {n} 件、先頭 200 件のみ表示",
        "unsaved_title": "未保存",
        "unsaved_msg": "未保存の変更があります。破棄しますか？",
        "loaded": "テーブルを読み込みました: {name} ({n} 件)",
        "edit_title": "値の編集",
        "edit_prompt": "列: {col}\n\n（全内容を編集できます）",
        "no_changes": "保存する変更はありません",
        "not_list": "このテーブルは標準のレコード一覧形式ではありません。tables フォルダの JSON を直接編集してください。",
        "bad_value": "列「{col}」（{row} 行目）の値「{val}」が不正です: {e}",
        "saved_log": "テーブル {name} を保存しました（DB + JSON）",
        "saved_dlg": "変更を保存しました",
        "tables_missing": "tables フォルダが見つかりません",
        "reload_confirm": "tables フォルダの JSON からデータベースを再構築します。よろしいですか？",
        "reload_log": "tables から {n} テーブルを再読み込みしました",
        "reload_dlg": "tables フォルダから再読み込みしました",
    },
    # ------------------------------------------------------------------
    "ko": {
        "app_title": "Princess Maker TableData & Bundle 도구",
        "language": "언어:",
        "game_root": "게임 폴더:",
        "select_folder": "폴더 선택",
        "auto_find": "자동 찾기",
        "tab_home": "개요",
        "tab_bundle": "Bundle 복호화",
        "tab_table": "TableData",
        "tab_db": "데이터베이스 보기 / 편집",
        "tab_log": "로그",
        "guide_title": "사용 방법",
        "guide": (
            "1. 게임 폴더 선택 → 자동 찾기\n"
            "2. Bundle 복호화 (한 번만 하면 됩니다)\n"
            "3. TableData → 추출·복호화 → 데이터베이스 생성 + JSON 내보내기\n"
            "4. 데이터베이스 보기 / 편집:\n"
            "   - 테이블 이름을 클릭해 데이터 불러오기\n"
            "   - 위쪽 Filter로 빠르게 검색 (예: Rollipop)\n"
            "   - 셀을 더블클릭해 수정한 뒤 '수정 저장' 클릭\n"
            "     (DB와 tables 폴더의 JSON에 함께 반영됩니다)\n"
            "   - 또는 tables 폴더의 JSON을 직접 수정한 뒤 'tables에서 다시 불러오기' 클릭\n"
            "5. 수정이 끝나면 TableData 탭의 3단계에서 TableData_modified.txt 생성\n"
            "6. UABEANext로 resources.assets를 열어 해당 파일을 TableData에 가져오기(Import)한 뒤 저장\n"
            "7. 게임 업데이트 후: 패치 만들기 → 1, 2단계 다시 실행 → 패치 적용 → 3단계 → 다시 가져오기\n"
            "   (2단계는 tables 폴더를 덮어쓰기 전에 수정 내용을 자동으로 패치로 저장합니다)"
        ),
        "status_none": "게임 폴더가 아직 선택되지 않았습니다",
        "bundle_not_found": "Bundle을 찾을 수 없습니다",
        "res_not_found": "resources.assets를 찾을 수 없습니다",
        "auto_done": "자동 찾기가 완료되었습니다",
        "dir_missing": "폴더가 존재하지 않습니다",
        "dlg_error": "오류",
        "dlg_done": "완료",
        "dlg_hint": "알림",
        "dlg_confirm": "확인",
        "bundle_title": "AssetBundle 복호화",
        "bundle_desc": "원래 파일 이름을 유지하므로 게임이 바로 읽을 수 있습니다. 자동으로 백업하고 폴더를 엽니다.",
        "bundle_btn": "Bundle 복호화",
        "bundle_missing": "Bundle을 찾을 수 없습니다",
        "bundle_backup": "백업 완료 → {name}",
        "bundle_already": "이 Bundle은 이미 복호화된 것 같습니다 (UnityFS 헤더). 건너뜁니다.",
        "bundle_ok_label": "복호화 성공!",
        "bundle_log_ok": "Bundle 복호화 완료",
        "bundle_dlg_ok": "Bundle 복호화가 완료되어 폴더를 열었습니다",
        "table_title": "TableData 처리",
        "btn_extract": "1. resources.assets에서 추출 후 복호화",
        "btn_export": "2. 데이터베이스 생성 + JSON 내보내기",
        "btn_output": "3. 다시 암호화하여 TableData_modified.txt 출력",
        "need_unitypy": "먼저 unitypy를 설치하세요 (pip install unitypy)",
        "res_missing": "resources.assets를 찾을 수 없습니다",
        "tabledata_missing": "TableData TextAsset을 찾을 수 없습니다",
        "extract_ok_log": "TableData 복호화 성공 ({n:,} bytes)",
        "extract_ok_label": "추출 및 복호화 완료 → TableData.dec.bin",
        "extract_ok_dlg": "TableData가 복호화되었습니다",
        "dec_missing": "TableData.dec.bin을 찾을 수 없습니다. 먼저 1단계를 실행하세요",
        "db_ok_log": "데이터베이스 생성 완료 (테이블 {n}개)",
        "db_ok_label": "데이터베이스 생성됨 → {p}",
        "db_ok_dlg": "데이터베이스와 JSON이 생성되었습니다",
        "no_db": "데이터베이스를 찾을 수 없습니다. 먼저 2단계를 실행하세요",
        "json_missing": "{f}을(를) 찾을 수 없습니다. 먼저 2단계를 실행하세요",
        "output_log": "출력 완료 {p} ({n:,} bytes)",
        "output_dlg": "출력 완료:\n{p}\n\nUABEANext로 resources.assets 안의 TableData에 가져오기(Import)하세요.",
        "output_fail": "출력 실패: {e}",
        "tables_label": "테이블 (클릭)",
        "refresh_list": "테이블 목록 새로고침",
        "btn_save": "수정 저장",
        "btn_reload": "현재 테이블 다시 불러오기",
        "btn_reload_json": "tables에서 다시 불러오기",
        "filter": "Filter:",
        "clear": "지우기",
        "dirty_flag": "● 저장되지 않은 수정 사항 있음",
        "sql_label": "SQL 쿼리 (읽기 전용, 결과는 아래에 표시)",
        "run_sql": "SQL 실행",
        "sql_ok": "실행 성공 (반환 데이터 없음)",
        "sql_err": "오류: {e}",
        "sql_more": "... 총 {n}건, 처음 200건만 표시",
        "unsaved_title": "저장 안 됨",
        "unsaved_msg": "저장되지 않은 수정 사항이 있습니다. 버리시겠습니까?",
        "loaded": "테이블 불러옴: {name} ({n}건)",
        "edit_title": "값 수정",
        "edit_prompt": "열: {col}\n\n(전체 내용을 편집할 수 있습니다)",
        "no_changes": "저장할 수정 사항이 없습니다",
        "not_list": "이 테이블은 표준 레코드 목록 형식이 아닙니다. tables 폴더의 JSON을 직접 수정하세요.",
        "bad_value": "열 '{col}' ({row}행)의 값 '{val}' 형식이 올바르지 않습니다: {e}",
        "saved_log": "테이블 {name} 저장됨 (DB + JSON)",
        "saved_dlg": "수정 사항이 저장되었습니다",
        "tables_missing": "tables 폴더를 찾을 수 없습니다",
        "reload_confirm": "tables 폴더의 JSON으로 데이터베이스를 다시 만듭니다. 계속하시겠습니까?",
        "reload_log": "tables에서 테이블 {n}개를 다시 불러왔습니다",
        "reload_dlg": "tables 폴더에서 다시 불러왔습니다",
    },
}


PATCH_STRINGS = {
    "en": {
        "table_search": "Search tables:",
        "patch_title": "Patch — keep your edits across game updates",
        "patch_desc": ("Create: save the difference between your edited tables and the original data as a patch file.\n"
                       "Apply: after a game update, redo steps 1 and 2, then apply the patch to the new data."),
        "btn_patch_create": "Create patch (save my edits)",
        "btn_patch_apply": "Apply patch (restore my edits)",
        "patch_unsaved": "There are unsaved changes. Please press \"Save changes\" first.",
        "patch_no_base": "Original-data baseline (tables_orig) not found. Run steps 1 and 2 first.",
        "patch_no_diff": "Your tables are identical to the original data. Nothing to save.",
        "patch_save_title": "Save patch",
        "patch_open_title": "Select a patch file",
        "patch_saved_log": "Patch saved {p} ({t} tables, {c} changes)",
        "patch_saved_dlg": "Patch saved:\n{p}\n\n{t} tables, {c} changes.\nAfter a game update, redo steps 1 and 2, then press \"Apply patch\".",
        "patch_invalid": "This is not a valid patch file",
        "patch_conflict_ask": ("For {n} edits, the value in the new game data differs from what it was before you edited it "
                               "(the game changed it).\n\nYes = overwrite with your values\nNo = keep the game's new values"),
        "patch_done": ("Applied {applied} edits ({same} already identical, {overwritten} overwrote game changes, "
                       "{conflicts} kept the game's new value, {missing} rows not found, {skipped} tables skipped).\n"
                       "Detailed report: {p}\n\nCheck the result, then run step 3 to output."),
        "patch_applied_log": "Patch applied: {applied} edits, {conflicts} conflicts kept, {missing} rows not found",
        "patch_auto": "Step 2 overwrites the tables folder, so your edits were saved automatically as a patch first:\n{p}",
        "patch_auto_log": "Auto-saved your edits as patch {p}",
        "backup_tables_log": "No baseline found; copied the existing tables folder to {p}",
        "baseline_built": "Original-data baseline built from TableData.dec.bin",
    },
    "zh-TW": {
        "table_search": "搜尋資料表:",
        "patch_title": "修改檔 Patch — 遊戲更新後保留你的修改",
        "patch_desc": ("建立：把目前 tables 與原始資料的差異存成修改檔。\n"
                       "套用：遊戲更新後，重做步驟 1、2，再把修改檔套用到新資料。"),
        "btn_patch_create": "建立修改檔（儲存我的修改）",
        "btn_patch_apply": "套用修改檔（還原我的修改）",
        "patch_unsaved": "目前有未保存的修改，請先按「保存修改」",
        "patch_no_base": "找不到原始資料基準（tables_orig），請先執行步驟 1、2",
        "patch_no_diff": "目前資料與原始資料沒有差異，沒有東西可儲存",
        "patch_save_title": "儲存修改檔",
        "patch_open_title": "選擇修改檔",
        "patch_saved_log": "已建立修改檔 {p}（{t} 張表，{c} 項修改）",
        "patch_saved_dlg": "已建立修改檔：\n{p}\n\n共 {t} 張表、{c} 項修改。\n遊戲更新後，重做步驟 1、2，再按「套用修改檔」即可還原。",
        "patch_invalid": "這不是有效的修改檔",
        "patch_conflict_ask": ("有 {n} 項修改，其欄位在新版遊戲中的值已和你修改前不同（遊戲改動過）。\n\n"
                               "是 = 用你的值覆蓋\n否 = 保留遊戲的新值"),
        "patch_done": ("已套用 {applied} 項修改（{same} 項本來就相同、{overwritten} 項覆蓋了遊戲的新值、"
                       "{conflicts} 項保留遊戲新值、{missing} 項找不到對應的列、{skipped} 張表被略過）。\n"
                       "詳細報告：{p}\n\n確認結果後，請執行步驟 3 輸出。"),
        "patch_applied_log": "已套用修改檔：{applied} 項修改，{conflicts} 項衝突保留遊戲值，{missing} 項找不到列",
        "patch_auto": "步驟 2 會覆蓋 tables 資料夾，已先把你的修改自動備份成修改檔：\n{p}",
        "patch_auto_log": "已自動將你的修改備份成修改檔 {p}",
        "backup_tables_log": "找不到原始資料基準，已把現有 tables 資料夾複製到 {p}",
        "baseline_built": "已用 TableData.dec.bin 建立原始資料基準",
    },
    "zh-CN": {
        "table_search": "搜索数据表:",
        "patch_title": "补丁 Patch — 游戏更新后保留你的修改",
        "patch_desc": ("创建：把当前 tables 与原始数据的差异保存为补丁文件。\n"
                       "应用：游戏更新后，重做步骤 1、2，再把补丁应用到新数据。"),
        "btn_patch_create": "创建补丁（保存我的修改）",
        "btn_patch_apply": "应用补丁（还原我的修改）",
        "patch_unsaved": "当前有未保存的修改，请先点击“保存修改”",
        "patch_no_base": "找不到原始数据基准（tables_orig），请先执行步骤 1、2",
        "patch_no_diff": "当前数据与原始数据没有差异，没有可保存的内容",
        "patch_save_title": "保存补丁",
        "patch_open_title": "选择补丁文件",
        "patch_saved_log": "已创建补丁 {p}（{t} 张表，{c} 项修改）",
        "patch_saved_dlg": "已创建补丁：\n{p}\n\n共 {t} 张表、{c} 项修改。\n游戏更新后，重做步骤 1、2，再点击“应用补丁”即可还原。",
        "patch_invalid": "这不是有效的补丁文件",
        "patch_conflict_ask": ("有 {n} 项修改，其字段在新版游戏中的值已和你修改前不同（游戏改动过）。\n\n"
                               "是 = 用你的值覆盖\n否 = 保留游戏的新值"),
        "patch_done": ("已应用 {applied} 项修改（{same} 项本来就相同、{overwritten} 项覆盖了游戏的新值、"
                       "{conflicts} 项保留游戏新值、{missing} 项找不到对应的行、{skipped} 张表被跳过）。\n"
                       "详细报告：{p}\n\n确认结果后，请执行步骤 3 输出。"),
        "patch_applied_log": "已应用补丁：{applied} 项修改，{conflicts} 项冲突保留游戏值，{missing} 项找不到行",
        "patch_auto": "步骤 2 会覆盖 tables 文件夹，已先把你的修改自动备份为补丁：\n{p}",
        "patch_auto_log": "已自动将你的修改备份为补丁 {p}",
        "backup_tables_log": "找不到原始数据基准，已把现有 tables 文件夹复制到 {p}",
        "baseline_built": "已用 TableData.dec.bin 建立原始数据基准",
    },
    "ja": {
        "table_search": "テーブル検索:",
        "patch_title": "パッチ — ゲーム更新後も編集内容を保持",
        "patch_desc": ("作成：編集後の tables と元データの差分をパッチファイルとして保存します。\n"
                       "適用：ゲーム更新後、ステップ 1、2 をやり直してから、新しいデータにパッチを適用します。"),
        "btn_patch_create": "パッチを作成（編集内容を保存）",
        "btn_patch_apply": "パッチを適用（編集内容を復元）",
        "patch_unsaved": "未保存の変更があります。先に「変更を保存」を押してください",
        "patch_no_base": "元データの基準（tables_orig）が見つかりません。先にステップ 1、2 を実行してください",
        "patch_no_diff": "現在のデータは元データと同じです。保存する内容はありません",
        "patch_save_title": "パッチを保存",
        "patch_open_title": "パッチファイルを選択",
        "patch_saved_log": "パッチを保存しました {p}（{t} テーブル、{c} 件の変更）",
        "patch_saved_dlg": "パッチを保存しました：\n{p}\n\n{t} テーブル、{c} 件の変更。\nゲーム更新後は、ステップ 1、2 をやり直して「パッチを適用」を押すと復元できます。",
        "patch_invalid": "有効なパッチファイルではありません",
        "patch_conflict_ask": ("{n} 件の編集で、新しいゲームデータの値があなたの編集前の値と異なります（ゲーム側で変更されています）。\n\n"
                               "はい = あなたの値で上書き\nいいえ = ゲームの新しい値を保持"),
        "patch_done": ("{applied} 件の編集を適用しました（{same} 件は既に同じ、{overwritten} 件はゲームの変更を上書き、"
                       "{conflicts} 件はゲームの新しい値を保持、{missing} 件は対応する行なし、{skipped} テーブルをスキップ）。\n"
                       "詳細レポート：{p}\n\n結果を確認してから、ステップ 3 で出力してください。"),
        "patch_applied_log": "パッチを適用: {applied} 件、競合 {conflicts} 件はゲームの値を保持、行なし {missing} 件",
        "patch_auto": "ステップ 2 は tables フォルダを上書きするため、先にあなたの編集をパッチとして自動保存しました：\n{p}",
        "patch_auto_log": "編集内容をパッチとして自動保存しました {p}",
        "backup_tables_log": "基準が見つからないため、既存の tables フォルダを {p} にコピーしました",
        "baseline_built": "TableData.dec.bin から元データの基準を作成しました",
    },
    "ko": {
        "table_search": "테이블 검색:",
        "patch_title": "패치 — 게임 업데이트 후에도 수정 내용 유지",
        "patch_desc": ("만들기: 수정한 tables와 원본 데이터의 차이를 패치 파일로 저장합니다.\n"
                       "적용: 게임 업데이트 후 1, 2단계를 다시 실행한 뒤 새 데이터에 패치를 적용합니다."),
        "btn_patch_create": "패치 만들기 (내 수정 저장)",
        "btn_patch_apply": "패치 적용 (내 수정 복원)",
        "patch_unsaved": "저장되지 않은 수정 사항이 있습니다. 먼저 '수정 저장'을 눌러 주세요",
        "patch_no_base": "원본 데이터 기준(tables_orig)을 찾을 수 없습니다. 먼저 1, 2단계를 실행하세요",
        "patch_no_diff": "현재 데이터가 원본과 같습니다. 저장할 내용이 없습니다",
        "patch_save_title": "패치 저장",
        "patch_open_title": "패치 파일 선택",
        "patch_saved_log": "패치 저장됨 {p} (테이블 {t}개, 수정 {c}건)",
        "patch_saved_dlg": "패치를 저장했습니다:\n{p}\n\n테이블 {t}개, 수정 {c}건.\n게임 업데이트 후 1, 2단계를 다시 실행하고 '패치 적용'을 누르면 복원됩니다.",
        "patch_invalid": "유효한 패치 파일이 아닙니다",
        "patch_conflict_ask": ("{n}건의 수정에서 새 게임 데이터의 값이 수정 전 값과 다릅니다 (게임에서 변경됨).\n\n"
                               "예 = 내 값으로 덮어쓰기\n아니요 = 게임의 새 값 유지"),
        "patch_done": ("수정 {applied}건을 적용했습니다 (이미 동일 {same}건, 게임 변경을 덮어씀 {overwritten}건, "
                       "게임 새 값 유지 {conflicts}건, 해당 행 없음 {missing}건, 건너뛴 테이블 {skipped}개).\n"
                       "상세 보고서: {p}\n\n결과를 확인한 뒤 3단계에서 출력하세요."),
        "patch_applied_log": "패치 적용: 수정 {applied}건, 충돌 {conflicts}건은 게임 값 유지, 행 없음 {missing}건",
        "patch_auto": "2단계는 tables 폴더를 덮어쓰므로 먼저 수정 내용을 패치로 자동 저장했습니다:\n{p}",
        "patch_auto_log": "수정 내용을 패치로 자동 저장했습니다 {p}",
        "backup_tables_log": "기준을 찾을 수 없어 기존 tables 폴더를 {p}(으)로 복사했습니다",
        "baseline_built": "TableData.dec.bin으로 원본 데이터 기준을 만들었습니다",
    },
}
for _lang, _d in PATCH_STRINGS.items():
    STRINGS[_lang].update(_d)


# =========================================================
#  Crypto
# =========================================================
def hcd(seed: int) -> bytes:
    GOLDEN = 0x9E3779B97F4A7C15
    C1 = 0xC96C5795D7873AE1
    C2 = 0x61C8864680B583EB
    C3 = 0xBF58476D1CE4E5B9
    C4 = 0x94D049BB133111EB
    result = bytearray(0x28)
    state = (GOLDEN * seed) ^ C1
    for i in range(0x28):
        state = (state - C2) & 0xFFFFFFFFFFFFFFFF
        x = state ^ (state >> 30)
        x = (C3 * x) & 0xFFFFFFFFFFFFFFFF
        x = x ^ (x >> 27)
        x = (C4 * x) & 0xFFFFFFFFFFFFFFFF
        result[i] = ((x >> 24) ^ (x >> 55)) & 0xFF
    return bytes(result)


def derive_key(seed: int, length: int) -> bytes:
    return hashlib.sha256(hcd(seed)).digest()[:length]


def decrypt_pmkt(data: bytes) -> bytes:
    if data[:4] != b"PMKT":
        raise ValueError("Not a PMKT file")
    iv = data[5:21]
    ciphertext = data[21:-32]
    aes_key = derive_key(0x1D, 16)
    cipher = AES.new(aes_key, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(ciphertext), AES.block_size)


def encrypt_pmkt(plaintext: bytes, version: int = 2) -> bytes:
    aes_key = derive_key(0x1D, 16)
    hmac_key = derive_key(0x8B, 32)
    iv = get_random_bytes(16)
    cipher = AES.new(aes_key, AES.MODE_CBC, iv)
    ciphertext = cipher.encrypt(pad(plaintext, AES.block_size))
    header = b"PMKT" + bytes([version]) + iv
    data_to_mac = header + ciphertext
    mac = hmac.new(hmac_key, data_to_mac, hashlib.sha256).digest()
    return data_to_mac + mac


YBJ = bytes.fromhex("2DB740881C6FD3AA")
YBI = bytes.fromhex("9A146BC23FE87105")
YBL = bytes.fromhex("706D6B5F6173736574")
YBK = bytes.fromhex("E159079C843B62F0")


def derive_bundle_key() -> bytes:
    return hashlib.sha256(YBJ + YBI + YBL + YBK).digest()[:16]


def decrypt_bundle(data: bytes) -> bytes:
    if data[4] != 1:
        raise ValueError(f"unexpected version: {data[4]}")
    iv = data[5:0x15]
    ctr = Counter.new(128, initial_value=int.from_bytes(iv, "big"), allow_wraparound=True)
    cipher = AES.new(derive_bundle_key(), AES.MODE_CTR, counter=ctr)
    return cipher.decrypt(data[0x15:])


def to_jsonable(obj):
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(x) for x in obj]
    if isinstance(obj, (bytes, bytearray)):
        try:
            return bytes(obj).decode("utf-8")
        except Exception:
            return bytes(obj).hex()
    if isinstance(obj, (int, float, str, bool)) or obj is None:
        return obj
    return str(obj)


# =========================================================
#  Patch engine (diff / apply, keyed by a unique column such as Id)
# =========================================================
# --- PATCH HELPERS BEGIN ---
MISSING = object()


def _same(a, b) -> bool:
    """Type-strict equality (so 5 and 5.0 / True and 1 are different)."""
    if a is b:
        return True
    if a is MISSING or b is MISSING:
        return False
    if type(a) is not type(b):
        return False
    if isinstance(a, (list, dict)):
        return (json.dumps(a, sort_keys=True, ensure_ascii=False)
                == json.dumps(b, sort_keys=True, ensure_ascii=False))
    return a == b


def _is_key(v) -> bool:
    return isinstance(v, (int, str)) and not isinstance(v, bool)


def _is_records(x) -> bool:
    return isinstance(x, list) and len(x) > 0 and all(isinstance(r, dict) for r in x)


def pick_key(rows):
    """Column that uniquely identifies every row (Id-like names first), or None."""
    if not _is_records(rows):
        return None
    cols = list(OrderedDict.fromkeys(k for r in rows for k in r))
    preferred = [c for c in cols if str(c).lower() in ("id", "index", "key", "no", "idx")]
    for c in preferred + [c for c in cols if c not in preferred]:
        vals = []
        for r in rows:
            v = r.get(c, MISSING)
            if v is MISSING or not _is_key(v):
                break
            vals.append(v)
        else:
            if len(set(vals)) == len(vals):
                return c
    return None


def diff_table(base, cur):
    """Return a patch dict describing base -> cur, or None if identical."""
    if _same(base, cur):
        return None
    if not (_is_records(base) and isinstance(cur, list) and all(isinstance(r, dict) for r in cur)):
        return {"replace": cur}

    key = pick_key(base)
    changes, added, removed = [], [], []

    if key is None:                      # fallback: match rows by position
        n = min(len(base), len(cur))
        pairs = [(i, base[i], cur[i]) for i in range(n)]
        added = list(cur[n:])
        removed = list(range(n, len(base)))
    else:
        bmap = {r[key]: r for r in base}
        seen, pairs = set(), []
        for r in cur:
            k = r.get(key, MISSING)
            if k is MISSING or not _is_key(k) or k in seen:
                added.append(r)
                continue
            seen.add(k)
            if k in bmap:
                pairs.append((k, bmap[k], r))
            else:
                added.append(r)
        removed = [k for k in bmap if k not in seen]

    for k, brow, crow in pairs:
        for c in OrderedDict.fromkeys(list(brow) + list(crow)):
            bv = brow.get(c, MISSING)
            cv = crow.get(c, MISSING)
            if _same(bv, cv):
                continue
            ch = {"key": k, "col": c}
            if bv is not MISSING:
                ch["old"] = bv
            if cv is not MISSING:
                ch["new"] = cv
            changes.append(ch)

    if not (changes or added or removed):
        return None
    out = {"key": key}
    if changes:
        out["changes"] = changes
    if added:
        out["added"] = added
    if removed:
        out["removed"] = removed
    return out


def apply_table_patch(rows, tp, overwrite, report, name):
    """Apply one table's patch to rows (returns a new list; rows is not modified)."""
    if "replace" in tp:
        report["replaced"].append(name)
        return copy.deepcopy(tp["replace"])
    if not _is_records(rows):
        report["skipped"].append((name, "table format changed"))
        return rows

    rows = copy.deepcopy(rows)
    key = tp.get("key")
    dup = set()
    if key is None:
        index = dict(enumerate(rows))
    else:
        if not any(key in r for r in rows):
            report["skipped"].append((name, f"key column '{key}' not found"))
            return rows
        index = {}
        for r in rows:
            k = r.get(key, MISSING)
            if not _is_key(k):
                continue
            if k in index:
                dup.add(k)
            else:
                index[k] = r

    for ch in tp.get("changes", []):
        k, c = ch["key"], ch["col"]
        row = index.get(k)
        if row is None or k in dup:
            report["missing"].append((name, k, c))
            continue
        cur = row.get(c, MISSING)
        old = ch.get("old", MISSING)
        new = ch.get("new", MISSING)
        if _same(cur, new):
            report["same"] += 1
            continue
        if not _same(cur, old):           # the game changed this cell since the patch was made
            if not overwrite:
                report["conflicts"].append((name, k, c, cur, new))
                continue
            report["overwritten"] += 1
        if new is MISSING:
            row.pop(c, None)
        else:
            row[c] = copy.deepcopy(new)
        report["applied"] += 1

    rem = tp.get("removed", [])
    if key is None:
        for i in sorted(rem, reverse=True):
            if isinstance(i, int) and 0 <= i < len(rows):
                rows.pop(i)
                report["applied"] += 1
    elif rem:
        rs = set(x for x in rem if _is_key(x)) - dup
        keep = []
        for r in rows:
            k = r.get(key, MISSING)
            if _is_key(k) and k in rs:
                report["applied"] += 1
                continue
            keep.append(r)
        rows = keep

    for r in tp.get("added", []):
        nr = copy.deepcopy(r)
        if key is not None:
            k = nr.get(key, MISSING)
            if _is_key(k):
                if k in index:
                    report["missing"].append((name, k, "(added row already exists)"))
                    continue
                index[k] = nr
        rows.append(nr)
        report["applied"] += 1
    return rows


def apply_patch_to_tables(current: dict, tpatch: dict, overwrite: bool):
    report = {"applied": 0, "same": 0, "overwritten": 0, "conflicts": [],
              "missing": [], "skipped": [], "replaced": []}
    new = {}
    for name, tp in tpatch.items():
        if name not in current:
            report["skipped"].append((name, "table not found in the new data"))
            continue
        new[name] = apply_table_patch(current[name], tp, overwrite, report, name)
    return new, report


def _fmt(v) -> str:
    return "<missing>" if v is MISSING else repr(v)


def format_report(report: dict) -> str:
    lines = [
        f"applied: {report['applied']}",
        f"already identical: {report['same']}",
        f"overwrote game changes: {report['overwritten']}",
        f"conflicts (kept game value): {len(report['conflicts'])}",
        f"rows not found: {len(report['missing'])}",
        f"tables skipped: {len(report['skipped'])}",
        f"tables replaced: {len(report['replaced'])}",
        "",
    ]
    for n, k, c, cur, new in report["conflicts"]:
        lines.append(f"[CONFLICT kept game value] {n} key={k!r} col={c} game={_fmt(cur)} yours={_fmt(new)}")
    for n, k, c in report["missing"]:
        lines.append(f"[ROW NOT FOUND] {n} key={k!r} col={c}")
    for n, why in report["skipped"]:
        lines.append(f"[TABLE SKIPPED] {n}: {why}")
    for n in report["replaced"]:
        lines.append(f"[TABLE REPLACED] {n}")
    return "\n".join(lines) + "\n"
# --- PATCH HELPERS END ---


# =========================================================
#  App
# =========================================================
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.settings = load_settings()
        lang = self.settings.get("lang", "zh-TW")
        self.lang = lang if lang in STRINGS else "zh-TW"

        self.title(self.t("app_title"))
        self.geometry("1480x940")

        self.game_root = ctk.StringVar(value=self.settings.get("game_root", ""))
        self.filter_var = ctk.StringVar()
        self.table_filter_var = ctk.StringVar()
        self.all_tables = []

        self.bundle_path = None
        self.resources_path = None
        self.db_path = Path("TableData.db")
        self.tables_dir = Path("tables")
        self.tables_orig_dir = Path("tables_orig")   # untouched copy of the game's data (baseline)
        self.patches_dir = Path("patches")

        self.current_table = None
        self.dirty = False
        self.edits = {}              # {(rowid, column): new_text}
        self.columns = []
        self.tree_data = []
        self.filtered_data = []
        self.row_by_id = {}
        self.table_names = []

        self.log_lines = []
        self.dyn = {                 # dynamic labels: attr -> [(key, kwargs), ...]
            "status_label": [("status_none", {})],
            "bundle_info": [],
            "table_info": [],
        }

        self._busy = False
        self._q = queue.Queue()

        self._build_ui()
        self.after(100, self._poll)

    # -----------------------------------------------------
    #  helpers
    # -----------------------------------------------------
    def t(self, key: str, **kw) -> str:
        s = STRINGS.get(self.lang, {}).get(key)
        if s is None:
            s = STRINGS["en"].get(key, key)
        if kw:
            try:
                return s.format(**kw)
            except Exception:
                return s
        return s

    def ui(self, fn, *a, **k):
        """Schedule fn on the Tk main thread (safe to call from worker threads)."""
        self._q.put((fn, a, k))

    def _poll(self):
        try:
            while True:
                fn, a, k = self._q.get_nowait()
                try:
                    fn(*a, **k)
                except Exception as e:
                    print("ui callback error:", e)
        except queue.Empty:
            pass
        self.after(100, self._poll)

    def _run_bg(self, fn):
        if self._busy:
            return
        self._busy = True

        def runner():
            try:
                fn()
            finally:
                self._busy = False

        threading.Thread(target=runner, daemon=True).start()

    def _info(self, text):
        self.ui(lambda: messagebox.showinfo(self.t("dlg_done"), text))

    def _error(self, text):
        self.ui(lambda: messagebox.showerror(self.t("dlg_error"), text))

    def _set_dyn(self, attr, lines):
        self.dyn[attr] = lines
        self.ui(self._apply_dyn, attr)

    def _apply_dyn(self, attr):
        label = getattr(self, attr, None)
        if label is None:
            return
        text = "\n".join(self.t(k, **kw) for k, kw in self.dyn.get(attr, []))
        try:
            label.configure(text=text)
        except Exception:
            pass

    def log(self, msg: str):
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
        try:
            print(msg)
        except Exception:
            pass
        self.ui(self._log_ui, line)

    def _log_ui(self, line: str):
        self.log_lines.append(line)
        if len(self.log_lines) > 3000:
            self.log_lines = self.log_lines[-2000:]
        try:
            self.log_text.insert("end", line + "\n")
            self.log_text.see("end")
        except Exception:
            pass

    @staticmethod
    def _q_ident(name: str) -> str:
        return '"' + str(name).replace('"', '""') + '"'

    def _safe_name(self, name: str) -> str:
        return "".join(c if c.isalnum() or c == "_" else "_" for c in str(name))

    def _to_str(self, v):
        if v is None:
            return ""
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, (dict, list)):
            return json.dumps(v, ensure_ascii=False)
        return str(v)

    # -----------------------------------------------------
    #  UI
    # -----------------------------------------------------
    def _build_ui(self):
        self.top = ctk.CTkFrame(self)
        self.top.pack(fill="x", padx=10, pady=8)

        # right side first (pack order = right to left)
        self.lang_menu = ctk.CTkOptionMenu(
            self.top, values=list(LANG_NAMES.values()),
            command=self.on_lang_change, width=130)
        self.lang_menu.set(LANG_NAMES[self.lang])
        self.lang_menu.pack(side="right", padx=5)
        ctk.CTkLabel(self.top, text=self.t("language")).pack(side="right", padx=5)

        ctk.CTkLabel(self.top, text=self.t("game_root")).pack(side="left", padx=5)
        ctk.CTkEntry(self.top, textvariable=self.game_root, width=560).pack(side="left", padx=5)
        ctk.CTkButton(self.top, text=self.t("select_folder"), command=self.select_game_root,
                      width=110).pack(side="left", padx=5)
        ctk.CTkButton(self.top, text=self.t("auto_find"), command=self.auto_find,
                      width=110).pack(side="left", padx=5)

        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=5)

        self.tab_home = self.tabview.add(self.t("tab_home"))
        self.tab_bundle = self.tabview.add(self.t("tab_bundle"))
        self.tab_table = self.tabview.add(self.t("tab_table"))
        self.tab_db = self.tabview.add(self.t("tab_db"))
        self.tab_log = self.tabview.add(self.t("tab_log"))

        self._build_home()
        self._build_bundle()
        self._build_table()
        self._build_db()
        self._build_log()

    def _build_home(self):
        frame = self.tab_home
        ctk.CTkLabel(frame, text=self.t("guide_title"),
                     font=ctk.CTkFont(size=18, weight="bold")).pack(pady=12)
        ctk.CTkLabel(frame, text=self.t("guide"), justify="left").pack(padx=20, pady=10)
        self.status_label = ctk.CTkLabel(frame, text="", text_color="orange", justify="left")
        self.status_label.pack(pady=20)

    def _build_bundle(self):
        frame = self.tab_bundle
        ctk.CTkLabel(frame, text=self.t("bundle_title"),
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        ctk.CTkLabel(frame, text=self.t("bundle_desc")).pack()
        ctk.CTkButton(frame, text=self.t("bundle_btn"),
                      command=lambda: self._run_bg(self.decrypt_bundle_action),
                      width=220, height=42).pack(pady=25)
        self.bundle_info = ctk.CTkLabel(frame, text="")
        self.bundle_info.pack()

    def _build_table(self):
        frame = self.tab_table
        ctk.CTkLabel(frame, text=self.t("table_title"),
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        btn_frame = ctk.CTkFrame(frame)
        btn_frame.pack(pady=15)
        ctk.CTkButton(btn_frame, text=self.t("btn_extract"),
                      command=lambda: self._run_bg(self.extract_tabledata),
                      width=340).grid(row=0, column=0, padx=8, pady=6)
        ctk.CTkButton(btn_frame, text=self.t("btn_export"),
                      command=lambda: self._run_bg(self.export_db),
                      width=340).grid(row=0, column=1, padx=8, pady=6)
        ctk.CTkButton(btn_frame, text=self.t("btn_output"),
                      command=lambda: self._run_bg(self.write_back),
                      width=420).grid(row=1, column=0, columnspan=2, pady=12)
        ctk.CTkLabel(frame, text=self.t("patch_title"),
                     font=ctk.CTkFont(size=15, weight="bold")).pack(pady=(24, 4))
        ctk.CTkLabel(frame, text=self.t("patch_desc"), justify="left").pack()
        patch_frame = ctk.CTkFrame(frame)
        patch_frame.pack(pady=10)
        ctk.CTkButton(patch_frame, text=self.t("btn_patch_create"), command=self.create_patch,
                      fg_color="#6a1b9a", width=300).grid(row=0, column=0, padx=8, pady=6)
        ctk.CTkButton(patch_frame, text=self.t("btn_patch_apply"), command=self.apply_patch,
                      fg_color="#00838f", width=300).grid(row=0, column=1, padx=8, pady=6)

        self.table_info = ctk.CTkLabel(frame, text="")
        self.table_info.pack(pady=10)

    def _build_db(self):
        frame = self.tab_db

        left = ctk.CTkFrame(frame, width=250)
        left.pack(side="left", fill="y", padx=6, pady=6)
        ctk.CTkLabel(left, text=self.t("tables_label")).pack(pady=4)
        ctk.CTkLabel(left, text=self.t("table_search")).pack(anchor="w", padx=8)
        search_row = ctk.CTkFrame(left, fg_color="transparent")
        search_row.pack(fill="x", padx=4, pady=(0, 4))
        self.table_search_entry = ctk.CTkEntry(search_row, textvariable=self.table_filter_var, width=165)
        self.table_search_entry.pack(side="left", padx=2)
        self.table_search_entry.bind("<KeyRelease>", lambda e: self.refresh_table_list())
        ctk.CTkButton(search_row, text="✕", width=40,
                      command=self.clear_table_search).pack(side="left", padx=2)
        self.table_listbox = ctk.CTkTextbox(left, width=230, height=600)
        self.table_listbox.pack(pady=4)
        self.table_listbox.bind("<ButtonRelease-1>", self.on_table_click)
        ctk.CTkButton(left, text=self.t("refresh_list"),
                      command=self.refresh_table_list).pack(pady=6)

        right = ctk.CTkFrame(frame)
        right.pack(side="right", fill="both", expand=True, padx=6, pady=6)

        toolbar = ctk.CTkFrame(right)
        toolbar.pack(fill="x", pady=4)

        ctk.CTkButton(toolbar, text=self.t("btn_save"), command=self.save_changes,
                      fg_color="#2e7d32", width=110).pack(side="left", padx=3)
        ctk.CTkButton(toolbar, text=self.t("btn_reload"), command=self.reload_current_table,
                      width=150).pack(side="left", padx=3)
        ctk.CTkButton(toolbar, text=self.t("btn_reload_json"), command=self.reload_from_json,
                      fg_color="#1565c0", width=160).pack(side="left", padx=3)

        ctk.CTkLabel(toolbar, text="  " + self.t("filter")).pack(side="left", padx=(12, 2))
        self.filter_entry = ctk.CTkEntry(toolbar, textvariable=self.filter_var, width=220)
        self.filter_entry.pack(side="left", padx=2)
        self.filter_entry.bind("<KeyRelease>", lambda e: self.apply_filter())
        ctk.CTkButton(toolbar, text=self.t("clear"), command=self.clear_filter,
                      width=70).pack(side="left", padx=3)

        self.dirty_label = ctk.CTkLabel(toolbar, text="", text_color="orange")
        self.dirty_label.pack(side="left", padx=10)

        tree_frame = ctk.CTkFrame(right)
        tree_frame.pack(fill="both", expand=True, pady=4)

        self.tree = ttk.Treeview(tree_frame, show="headings", selectmode="browse")
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        self.tree.bind("<Double-1>", self.on_cell_double_click)

        ctk.CTkLabel(right, text=self.t("sql_label")).pack(anchor="w", pady=(6, 0))
        self.sql_entry = ctk.CTkEntry(right)
        self.sql_entry.pack(fill="x", pady=2)
        self.sql_entry.bind("<Return>", lambda e: self.run_sql())
        ctk.CTkButton(right, text=self.t("run_sql"), command=self.run_sql,
                      width=100).pack(anchor="w", pady=2)
        self.sql_result = ctk.CTkTextbox(right, height=150, font=("Consolas", 12))
        self.sql_result.pack(fill="x", pady=4)

    def _build_log(self):
        self.log_text = ctk.CTkTextbox(self.tab_log, font=("Consolas", 12))
        self.log_text.pack(fill="both", expand=True, padx=6, pady=6)

    # -----------------------------------------------------
    #  Language switching (rebuilds the UI, keeps all state)
    # -----------------------------------------------------
    def on_lang_change(self, display_name: str):
        code = next((c for c, n in LANG_NAMES.items() if n == display_name), None)
        if not code or code == self.lang:
            return
        # defer: do not destroy the option menu inside its own callback
        self.after(50, lambda: self._switch_lang(code))

    def _switch_lang(self, code: str):
        names = [self.t(k) for k in TAB_KEYS]
        try:
            cur = self.tabview.get()
            tab_idx = names.index(cur) if cur in names else 0
        except Exception:
            tab_idx = 0
        sql_q = self.sql_entry.get()
        sql_r = self.sql_result.get("1.0", "end-1c")

        self.lang = code
        self.settings["lang"] = code
        save_settings(self.settings)
        self.title(self.t("app_title"))

        self.top.destroy()
        self.tabview.destroy()
        self._build_ui()

        # restore state
        for line in self.log_lines:
            self.log_text.insert("end", line + "\n")
        self.log_text.see("end")
        self.sql_entry.insert(0, sql_q)
        self.sql_result.insert("end", sql_r)
        self.refresh_table_list()
        if self.columns:
            self._refresh_tree(self.columns)
        self._update_dirty_label()
        for attr in self.dyn:
            self._apply_dyn(attr)
        try:
            self.tabview.set(self.t(TAB_KEYS[tab_idx]))
        except Exception:
            pass

    def _update_dirty_label(self):
        self.dirty_label.configure(text=self.t("dirty_flag") if self.dirty else "")

    # =========================================================
    #  Paths
    # =========================================================
    def select_game_root(self):
        path = filedialog.askdirectory(title=self.t("game_root"))
        if path:
            self.game_root.set(path)
            self.auto_find()

    def auto_find(self):
        raw = self.game_root.get().strip()
        root = Path(raw)
        if not raw or not root.exists():
            messagebox.showerror(self.t("dlg_error"), self.t("dir_missing"))
            return

        data_dir = root / "PrincessMakerKaren_Data"
        standalone = data_dir / "StreamingAssets" / "aa" / "StandaloneWindows64"

        self.bundle_path = None
        if standalone.exists():
            bundles = list(standalone.glob("packedassets_assets_all_*.bundle"))
            if bundles:
                self.bundle_path = bundles[0]

        res = data_dir / "resources.assets"
        self.resources_path = res if res.exists() else None

        lines = []
        lines.append(("bundle_found", {"p": self.bundle_path}) if self.bundle_path
                     else ("bundle_not_found", {}))
        lines.append(("res_found", {"p": self.resources_path}) if self.resources_path
                     else ("res_not_found", {}))
        self._set_dyn("status_label", lines)

        self.settings["game_root"] = raw
        save_settings(self.settings)

        self.log(self.t("auto_done"))
        for k, kw in lines:
            self.log(self.t(k, **kw))

    # =========================================================
    #  Bundle
    # =========================================================
    def decrypt_bundle_action(self):
        if not self.bundle_path:
            self._error(self.t("bundle_missing"))
            return
        try:
            raw = self.bundle_path.read_bytes()
            if raw[:7] == b"UnityFS":
                self.log(self.t("bundle_already"))
                self._info(self.t("bundle_already"))
                return

            backup = self.bundle_path.with_suffix(self.bundle_path.suffix + ".bak")
            if not backup.exists():
                shutil.copy2(self.bundle_path, backup)
                self.log(self.t("bundle_backup", name=backup.name))

            plain = decrypt_bundle(raw)
            self.bundle_path.write_bytes(plain)
            self.log(self.t("bundle_log_ok"))
            self._set_dyn("bundle_info", [("bundle_ok_label", {})])

            folder = str(self.bundle_path.parent)
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
            self._info(self.t("bundle_dlg_ok"))
        except Exception as e:
            self.log(str(e))
            self._error(str(e))

    # =========================================================
    #  TableData: extract
    # =========================================================
    def extract_tabledata(self):
        if UnityPy is None:
            self._error(self.t("need_unitypy"))
            return
        if not self.resources_path:
            self._error(self.t("res_missing"))
            return
        try:
            env = UnityPy.load(str(self.resources_path))
            for obj in env.objects:
                if obj.type.name == "TextAsset":
                    data = obj.read()
                    if getattr(data, "m_Name", "") == "TableData":
                        raw = data.m_Script
                        if isinstance(raw, str):
                            raw = raw.encode("utf-8", errors="surrogateescape")
                        plain = decrypt_pmkt(bytes(raw))
                        Path("TableData.dec.bin").write_bytes(plain)
                        self.log(self.t("extract_ok_log", n=len(plain)))
                        self._set_dyn("table_info", [("extract_ok_label", {})])
                        self._info(self.t("extract_ok_dlg"))
                        return
            raise RuntimeError(self.t("tabledata_missing"))
        except Exception as e:
            self.log(str(e))
            self._error(str(e))

    # =========================================================
    #  Database build (shared by export / reload)
    # =========================================================
    def _build_database(self, data: dict):
        if self.db_path.exists():
            self.db_path.unlink()

        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute("CREATE TABLE _meta (id INTEGER PRIMARY KEY, name TEXT, count INTEGER)")

            for i, (name, table) in enumerate(data.items()):
                qt = self._q_ident(self._safe_name(name))

                if not isinstance(table, list) or len(table) == 0:
                    cur.execute(f'CREATE TABLE {qt} (_rowid INTEGER PRIMARY KEY, "data" TEXT)')
                    cur.execute(f"INSERT INTO {qt} VALUES (0, ?)",
                                (json.dumps(table, ensure_ascii=False),))
                    cur.execute("INSERT INTO _meta VALUES (?, ?, ?)", (i, name, 1))
                    continue

                all_keys = OrderedDict()
                for row in table:
                    if isinstance(row, dict):
                        for k in row.keys():
                            all_keys[str(k)] = True
                columns = list(all_keys.keys()) or ["_empty"]

                col_defs = ", ".join(f"{self._q_ident(c)} TEXT" for c in columns)
                cur.execute(f"CREATE TABLE {qt} (_rowid INTEGER PRIMARY KEY, {col_defs})")

                col_names = ", ".join(self._q_ident(c) for c in columns)
                placeholders = ", ".join("?" * len(columns))
                sql = f"INSERT INTO {qt} (_rowid, {col_names}) VALUES (?, {placeholders})"
                for idx, row in enumerate(table):
                    if not isinstance(row, dict):
                        row = {"value": row}
                    values = [self._to_str(row.get(c)) for c in columns]
                    cur.execute(sql, [idx] + values)

                cur.execute("INSERT INTO _meta VALUES (?, ?, ?)", (i, name, len(table)))

            conn.commit()
        finally:
            conn.close()

    def export_db(self):
        dec = Path("TableData.dec.bin")
        if not dec.exists():
            self._error(self.t("dec_missing"))
            return
        try:
            raw = msgpack.unpackb(dec.read_bytes(), raw=False, strict_map_key=False)
            data = to_jsonable(raw)
            if not isinstance(data, dict):
                raise RuntimeError("Top-level object is not a map")

            # --- protect the user's edits before tables/ is overwritten ---
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            auto_path = None
            has_json = self.tables_dir.exists() and any(self.tables_dir.glob("*.json"))
            if has_json:
                if self.tables_orig_dir.exists() and any(self.tables_orig_dir.glob("*.json")):
                    patch = self._make_patch()
                    if patch["tables"]:
                        self.patches_dir.mkdir(exist_ok=True)
                        auto_path = self.patches_dir / f"auto_before_reexport_{ts}.json"
                        auto_path.write_text(json.dumps(patch, ensure_ascii=False, indent=1),
                                             encoding="utf-8")
                        self.log(self.t("patch_auto_log", p=auto_path.resolve()))
                else:
                    bk = Path(f"tables_backup_{ts}")
                    shutil.copytree(self.tables_dir, bk)
                    self.log(self.t("backup_tables_log", p=bk.resolve()))
                for f in self.tables_dir.glob("*.json"):
                    f.unlink()

            self._write_tables(self.tables_dir, data)
            if self.tables_orig_dir.exists():
                shutil.rmtree(self.tables_orig_dir)
            self._write_tables(self.tables_orig_dir, data)   # baseline for patches

            self._build_database(data)

            self.log(self.t("db_ok_log", n=len(data)))
            self.ui(self.refresh_table_list)
            self._set_dyn("table_info", [("db_ok_label", {"p": self.db_path})])
            msg = self.t("db_ok_dlg")
            if auto_path:
                msg += "\n\n" + self.t("patch_auto", p=auto_path.resolve())
            self._info(msg)
        except Exception as e:
            self.log(str(e))
            self._error(str(e))

    # =========================================================
    #  Database browser + filter
    # =========================================================
    def refresh_table_list(self):
        """(Re)load the table list from the DB and apply the search box on the left."""
        self.all_tables = []
        if self.db_path.exists():
            try:
                conn = sqlite3.connect(self.db_path)
                self.all_tables = conn.execute("SELECT name, count FROM _meta ORDER BY id").fetchall()
                conn.close()
            except Exception as e:
                self.log(str(e))

        kw = self.table_filter_var.get().strip().lower()
        shown = [(n, c) for n, c in self.all_tables if not kw or kw in str(n).lower()]

        tb = self.table_listbox
        tb.configure(state="normal")
        tb.delete("1.0", "end")
        self.table_names = []
        for name, cnt in shown:
            tb.insert("end", f"{name}  ({cnt})\n")
            self.table_names.append(name)
        tb.configure(state="disabled")

    def clear_table_search(self):
        self.table_filter_var.set("")
        self.refresh_table_list()

    def on_table_click(self, event):
        try:
            index = self.table_listbox.index(f"@{event.x},{event.y}")
            line = int(index.split(".")[0])
            if 1 <= line <= len(self.table_names):
                self.load_table(self.table_names[line - 1])
        except Exception:
            pass

    def load_table(self, name: str):
        if self.dirty:
            if not messagebox.askyesno(self.t("unsaved_title"), self.t("unsaved_msg")):
                return

        self.current_table = name
        qt = self._q_ident(self._safe_name(name))
        self.filter_var.set("")

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info({qt})")
        columns = [r[1] for r in cur.fetchall() if r[1] != "_rowid"]
        col_list = ", ".join(self._q_ident(c) for c in columns)
        cur.execute(f"SELECT _rowid, {col_list} FROM {qt} ORDER BY _rowid")
        rows = cur.fetchall()
        conn.close()

        self.tree_data = []
        self.row_by_id = {}
        for row in rows:
            d = {"_rowid": row[0], **dict(zip(columns, row[1:]))}
            self.tree_data.append(d)
            self.row_by_id[row[0]] = d

        self.filtered_data = self.tree_data[:]
        self.edits = {}
        self.dirty = False
        self._refresh_tree(columns)
        self._update_dirty_label()
        self.log(self.t("loaded", name=name, n=len(rows)))

    def _refresh_tree(self, columns=None):
        if columns is None:
            columns = self.columns
        self.columns = list(columns)

        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = self.columns
        for col in self.columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=130, stretch=True)

        for d in self.filtered_data:
            values = []
            for c in self.columns:
                v = d.get(c)
                s = "" if v is None else str(v)
                if len(s) > 70:
                    s = s[:67] + "..."
                values.append(s)
            self.tree.insert("", "end", iid=str(d["_rowid"]), values=values)

    def apply_filter(self):
        keyword = self.filter_var.get().strip().lower()
        if not keyword:
            self.filtered_data = self.tree_data[:]
        else:
            self.filtered_data = [
                d for d in self.tree_data
                if any(keyword in str(v).lower() for v in d.values())
            ]
        self._refresh_tree()

    def clear_filter(self):
        self.filter_var.set("")
        self.apply_filter()

    def on_cell_double_click(self, event):
        item = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        if not item or not column:
            return
        col_index = int(column.replace("#", "")) - 1
        if col_index < 0 or col_index >= len(self.columns):
            return

        col_name = self.columns[col_index]
        rid = int(item)
        d = self.row_by_id.get(rid)
        if d is None:
            return
        old_value = d.get(col_name, "")
        if old_value is None:
            old_value = ""

        new_value = simpledialog.askstring(
            self.t("edit_title"),
            self.t("edit_prompt", col=col_name),
            initialvalue=old_value,
            parent=self,
        )
        if new_value is None or new_value == old_value:
            return

        d[col_name] = new_value
        self.edits[(rid, col_name)] = new_value
        display = new_value if len(new_value) <= 70 else new_value[:67] + "..."
        self.tree.set(item, col_name, display)
        self.dirty = True
        self._update_dirty_label()

    # -----------------------------------------------------
    #  Save: write to DB AND tables/*.json, keeping original types
    # -----------------------------------------------------
    @staticmethod
    def _coerce(new: str, old):
        if isinstance(old, bool):
            return new.strip().lower() in ("true", "1", "yes")
        if isinstance(old, int):
            try:
                return int(new)
            except ValueError:
                return float(new)
        if isinstance(old, float):
            return float(new)
        if isinstance(old, (list, dict)):
            return json.loads(new)
        return new  # str, or the field did not exist before

    def save_changes(self):
        if not self.edits or not self.current_table:
            messagebox.showinfo(self.t("dlg_hint"), self.t("no_changes"))
            return

        safe = self._safe_name(self.current_table)
        json_path = self.tables_dir / f"{safe}.json"
        try:
            rows = json.loads(json_path.read_text(encoding="utf-8"))
            if not isinstance(rows, list) or not rows or not all(isinstance(r, dict) for r in rows):
                raise RuntimeError(self.t("not_list"))

            # compute everything first so a bad value changes nothing
            updates = []
            for (rowid, col), new in self.edits.items():
                old = rows[rowid].get(col)
                if old is None and new == "":
                    continue  # field did not exist and is still empty
                try:
                    val = self._coerce(new, old)
                except Exception as e:
                    raise RuntimeError(self.t("bad_value", col=col, row=rowid, val=new[:40], e=e))
                updates.append((rowid, col, new, val))

            conn = sqlite3.connect(self.db_path)
            try:
                cur = conn.cursor()
                qt = self._q_ident(safe)
                for rowid, col, new, val in updates:
                    rows[rowid][col] = val
                    cur.execute(f"UPDATE {qt} SET {self._q_ident(col)} = ? WHERE _rowid = ?",
                                (new, rowid))
                conn.commit()
            finally:
                conn.close()

            json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

            self.edits.clear()
            self.dirty = False
            self._update_dirty_label()
            self.log(self.t("saved_log", name=self.current_table))
            messagebox.showinfo(self.t("dlg_done"), self.t("saved_dlg"))
        except Exception as e:
            self.log(str(e))
            messagebox.showerror(self.t("dlg_error"), str(e))

    def reload_current_table(self):
        if self.current_table:
            self.dirty = False
            self.load_table(self.current_table)

    def reload_from_json(self):
        if self._busy:
            return
        if not self.tables_dir.exists():
            messagebox.showerror(self.t("dlg_error"), self.t("tables_missing"))
            return
        if not messagebox.askyesno(self.t("dlg_confirm"), self.t("reload_confirm")):
            return
        try:
            n = self._rebuild_from_json()
            self.log(self.t("reload_log", n=n))
            messagebox.showinfo(self.t("dlg_done"), self.t("reload_dlg"))
        except Exception as e:
            self.log(str(e))
            messagebox.showerror(self.t("dlg_error"), str(e))

    def _rebuild_from_json(self) -> int:
        """Rebuild the SQLite DB from tables/*.json (keeps the original table order)."""
        order = []
        if self.db_path.exists():
            try:
                conn = sqlite3.connect(self.db_path)
                order = [r[0] for r in conn.execute("SELECT name FROM _meta ORDER BY id")]
                conn.close()
            except Exception:
                order = []

        data = {}
        used = set()
        for name in order:
            p = self.tables_dir / f"{self._safe_name(name)}.json"
            if p.exists():
                data[name] = json.loads(p.read_text(encoding="utf-8"))
                used.add(p.name)
        for jf in sorted(self.tables_dir.glob("*.json")):
            if jf.name not in used:
                data[jf.stem] = json.loads(jf.read_text(encoding="utf-8"))

        self._build_database(data)
        self.refresh_table_list()

        self.dirty = False
        self.edits = {}
        self._update_dirty_label()
        if self.current_table and self.current_table in data:
            self.load_table(self.current_table)
        return len(data)

    # =========================================================
    #  Patches: keep your edits across game updates
    # =========================================================
    def _table_names(self):
        if self.db_path.exists():
            try:
                conn = sqlite3.connect(self.db_path)
                names = [r[0] for r in conn.execute("SELECT name FROM _meta ORDER BY id")]
                conn.close()
                if names:
                    return names
            except Exception:
                pass
        if self.tables_dir.exists():
            return [p.stem for p in sorted(self.tables_dir.glob("*.json"))]
        return []

    def _write_tables(self, folder: Path, data: dict):
        folder.mkdir(exist_ok=True)
        for name, table in data.items():
            p = folder / f"{self._safe_name(name)}.json"
            p.write_text(json.dumps(table, ensure_ascii=False, indent=2), encoding="utf-8")

    def _ensure_baseline(self) -> bool:
        if self.tables_orig_dir.exists() and any(self.tables_orig_dir.glob("*.json")):
            return True
        dec = Path("TableData.dec.bin")
        if not dec.exists():
            return False
        raw = msgpack.unpackb(dec.read_bytes(), raw=False, strict_map_key=False)
        self._write_tables(self.tables_orig_dir, to_jsonable(raw))
        self.log(self.t("baseline_built"))
        return True

    def _make_patch(self) -> dict:
        patch = {"format": 1, "created": datetime.now().isoformat(timespec="seconds"), "tables": {}}
        for name in self._table_names():
            safe = self._safe_name(name)
            bp = self.tables_orig_dir / f"{safe}.json"
            cp = self.tables_dir / f"{safe}.json"
            if not bp.exists() or not cp.exists():
                continue
            base = json.loads(bp.read_text(encoding="utf-8"))
            cur = json.loads(cp.read_text(encoding="utf-8"))
            tp = diff_table(base, cur)
            if tp:
                patch["tables"][name] = tp
        return patch

    @staticmethod
    def _patch_stats(patch: dict):
        c = 0
        for tp in patch["tables"].values():
            if "replace" in tp:
                c += 1
            else:
                c += len(tp.get("changes", [])) + len(tp.get("added", [])) + len(tp.get("removed", []))
        return len(patch["tables"]), c

    def create_patch(self):
        if self._busy:
            return
        if self.dirty:
            messagebox.showerror(self.t("dlg_error"), self.t("patch_unsaved"))
            return
        try:
            if not self.tables_dir.exists() or not self._ensure_baseline():
                messagebox.showerror(self.t("dlg_error"), self.t("patch_no_base"))
                return
            patch = self._make_patch()
            if not patch["tables"]:
                messagebox.showinfo(self.t("dlg_hint"), self.t("patch_no_diff"))
                return

            self.patches_dir.mkdir(exist_ok=True)
            path = filedialog.asksaveasfilename(
                title=self.t("patch_save_title"),
                initialdir=str(self.patches_dir.resolve()),
                initialfile=f"patch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                defaultextension=".json",
                filetypes=[("JSON", "*.json")],
            )
            if not path:
                return
            Path(path).write_text(json.dumps(patch, ensure_ascii=False, indent=1), encoding="utf-8")
            t, c = self._patch_stats(patch)
            self.log(self.t("patch_saved_log", p=path, t=t, c=c))
            messagebox.showinfo(self.t("dlg_done"), self.t("patch_saved_dlg", p=path, t=t, c=c))
        except Exception as e:
            self.log(str(e))
            messagebox.showerror(self.t("dlg_error"), str(e))

    def apply_patch(self):
        if self._busy:
            return
        if self.dirty:
            messagebox.showerror(self.t("dlg_error"), self.t("patch_unsaved"))
            return
        if not self.tables_dir.exists():
            messagebox.showerror(self.t("dlg_error"), self.t("tables_missing"))
            return

        self.patches_dir.mkdir(exist_ok=True)
        path = filedialog.askopenfilename(
            title=self.t("patch_open_title"),
            initialdir=str(self.patches_dir.resolve()),
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return
        try:
            patch = json.loads(Path(path).read_text(encoding="utf-8"))
            tpatch = patch.get("tables") if isinstance(patch, dict) else None
            if not isinstance(tpatch, dict) or not tpatch:
                raise RuntimeError(self.t("patch_invalid"))

            current = {}
            for name in tpatch:
                p = self.tables_dir / f"{self._safe_name(name)}.json"
                if p.exists():
                    current[name] = json.loads(p.read_text(encoding="utf-8"))

            new, report = apply_patch_to_tables(current, tpatch, overwrite=False)
            if report["conflicts"]:
                if messagebox.askyesno(self.t("dlg_confirm"),
                                       self.t("patch_conflict_ask", n=len(report["conflicts"]))):
                    new, report = apply_patch_to_tables(current, tpatch, overwrite=True)

            for name, rows in new.items():
                if not _same(rows, current[name]):
                    p = self.tables_dir / f"{self._safe_name(name)}.json"
                    p.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

            self._rebuild_from_json()

            report_path = self.patches_dir / f"apply_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            report_path.write_text(format_report(report), encoding="utf-8")

            self.log(self.t("patch_applied_log", applied=report["applied"],
                            conflicts=len(report["conflicts"]), missing=len(report["missing"])))
            messagebox.showinfo(self.t("dlg_done"), self.t(
                "patch_done", applied=report["applied"], same=report["same"],
                overwritten=report["overwritten"], conflicts=len(report["conflicts"]),
                missing=len(report["missing"]), skipped=len(report["skipped"]),
                p=report_path.resolve()))
        except Exception as e:
            self.log(str(e))
            messagebox.showerror(self.t("dlg_error"), str(e))

    def run_sql(self):
        sql = self.sql_entry.get().strip()
        if not sql or not self.db_path.exists():
            return
        try:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute("PRAGMA query_only = ON")  # edits must go through the grid / JSON
                cur = conn.cursor()
                cur.execute(sql)
                if cur.description:
                    rows = cur.fetchall()
                    cols = [d[0] for d in cur.description]
                    text = " | ".join(cols) + "\n" + "-" * 80 + "\n"
                    for r in rows[:200]:
                        line = [str(x)[:55] + ("..." if len(str(x)) > 55 else "") for x in r]
                        text += " | ".join(line) + "\n"
                    if len(rows) > 200:
                        text += "\n" + self.t("sql_more", n=len(rows))
                else:
                    text = self.t("sql_ok")
            finally:
                conn.close()
        except Exception as e:
            text = self.t("sql_err", e=e)
        self.sql_result.delete("1.0", "end")
        self.sql_result.insert("end", text)

    # =========================================================
    #  Output TableData_modified.txt (import it with UABEANext)
    # =========================================================
    def write_back(self):
        if not self.db_path.exists():
            self._error(self.t("no_db"))
            return
        try:
            conn = sqlite3.connect(self.db_path)
            names = [r[0] for r in conn.execute("SELECT name FROM _meta ORDER BY id")]
            conn.close()

            data = {}
            for name in names:
                p = self.tables_dir / f"{self._safe_name(name)}.json"
                if not p.exists():
                    raise RuntimeError(self.t("json_missing", f=p))
                data[name] = json.loads(p.read_text(encoding="utf-8"))

            plain = msgpack.packb(data, use_bin_type=True)
            encrypted = encrypt_pmkt(plain)

            # round-trip check before writing anything
            check = msgpack.unpackb(decrypt_pmkt(encrypted), raw=False, strict_map_key=False)
            if len(check) != len(data):
                raise RuntimeError("round-trip check failed")

            out = Path("TableData_modified.txt")
            out.write_bytes(encrypted)

            self.log(self.t("output_log", p=out.resolve(), n=len(encrypted)))
            self._info(self.t("output_dlg", p=out.resolve()))
        except Exception as e:
            self.log(self.t("output_fail", e=e))
            self._error(self.t("output_fail", e=e))


if __name__ == "__main__":
    if getattr(sys, "frozen", False):
        # tables/, patches/, TableData.db ... always live next to the .exe,
        # no matter where it was launched from (shortcut, "Run as admin", etc.)
        os.chdir(APP_DIR)
    app = App()
    app.mainloop()
