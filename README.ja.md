# Princess Maker: Children of Revelation — TableData & Bundle ツール

[English](README.md) | [繁體中文](README.zh-TW.md) | [简体中文](README.zh-CN.md) | **日本語** | [한국어](README.ko.md)

**Princess Maker: Children of Revelation**（Steam）向けの Windows GUI ツールです。ゲームの AssetBundle を復号し、暗号化された `TableData` を抽出・編集でき、パッチファイルでゲーム更新後も編集内容を引き継げます。

UI 言語：繁體中文 / 简体中文 / English / 日本語 / 한국어（右上で切り替え）。

## 機能

- **Bundle 復号** — `packedassets_assets_all_*.bundle` をその場で復号します（先に `.bak` バックアップを作成）。
- **TableData の抽出・編集** — `resources.assets` から `TableData` を取り出して復号し、SQLite データベースとテーブルごとの JSON を作成します。
- **データベース閲覧** — テーブル検索、行の Filter、セルのダブルクリック編集、読み取り専用の SQL 入力欄。編集後も元の型（数値・真偽値・配列）を保持します。
- **再暗号化して出力** — `TableData_modified.txt` を出力し、[UABEANext](https://github.com/nesrak1/UABEANext) で `resources.assets` にインポートします。本ツール自体は `resources.assets` を上書きしません。
- **パッチファイル** — 編集内容を小さなパッチとして保存し、ゲーム更新後に再適用できます。

## インストールと実行

### 方法 A：exe をダウンロード（いちばん簡単）

[Releases](../../releases) ページから `PrincessMakerTool.exe` をダウンロードしてください。専用のフォルダに置いてください。ツールは exe と同じ場所に作業ファイルを作成します。Python は不要です。

### 方法 B：ソースから実行

Python 3.10 以上が必要です：

```bash
pip install -r requirements.txt
python PrincessMakerTool.py
```

## 基本の流れ

1. ゲームフォルダ（`PrincessMakerKaren_Data` を含む階層）を選び、**自動検出** を押します。
2. **Bundle 復号** タブ → Bundle を復号（1回だけ必要）。
3. **TableData** タブ：
   1. resources.assets から抽出して復号
   2. データベース作成 + JSON 書き出し
4. **データベース閲覧 / 編集** タブ → テーブル名をクリックし、セルをダブルクリックして編集、「変更を保存」を押します。
5. **TableData** タブ → ステップ 3「再暗号化して TableData_modified.txt を出力」。
6. UABEANext で `resources.assets` を開き、`TableData_modified.txt` を `TableData` にインポートして保存します。

`tables/` 内の JSON を直接編集して「tables から再読み込み」を押すこともできます。

## ゲーム更新後も編集内容を保持する

ゲームの更新で `TableData` が置き換わるため、古いデータ上の編集は失われます。パッチを使ってください：

1. **パッチを作成（編集内容を保存）** — 元データとの差分だけを記録し、各行の一意な ID 列で対応付けます。
2. ゲームを更新したら、ステップ 1、2（抽出 + データベース作成）をやり直します。
3. **パッチを適用（編集内容を復元）** — パッチを新しいデータに適用します。
4. ステップ 3 で出力 → 再び UABEANext でインポートします。

あなたが編集したセルをゲーム側も変更していた場合は、あなたの値で上書きするか、ゲームの新しい値を残すかを確認されます。対応できなかった項目（行の削除、列名の変更、テーブルの消失）は黙って捨てられず、`patches/apply_report_*.txt` に一覧されます。

安全策：ステップ 2 は `tables/` を上書きする前に、現在の編集内容を `patches/auto_before_reexport_*.json` として自動保存します。

## exe と同じ場所に作成されるファイル

| パス | 用途 |
|---|---|
| `TableData.dec.bin` | 復号済みの TableData |
| `TableData.db` | 閲覧用の SQLite データベース |
| `tables/` | テーブルごとの JSON（編集用コピー） |
| `tables_orig/` | 未編集の元コピー（パッチの比較基準） |
| `patches/` | パッチファイルと適用レポート |
| `TableData_modified.txt` | 最終出力（UABEANext でインポート） |
| `pm_tool_settings.json` | 言語と前回のゲームフォルダ |

## exe を自分でビルドする

`PrincessMakerTool.py`、`requirements.txt`、`build.bat` を同じフォルダに置き、`build.bat` をダブルクリックします。成果物は `dist\PrincessMakerTool.exe` です。

## 注意事項

- Windows 専用です（ビルドスクリプトとパスは Windows 版 Steam 向け）。
- ゲームファイルは必ずバックアップしてください。Steam →「ゲームファイルの整合性を確認」で元に戻せます。
- 署名のない単一ファイルの exe は、ウイルス対策ソフトや SmartScreen に誤検知されることがあります。気になる場合はソースから自分でビルドしてください。
- 一意な ID 列のないテーブルは、パッチで行の位置による対応付けになり、更新後の信頼性が下がります。

## 免責事項

これは非公式のファンメイドツールであり、ゲームの開発元・販売元とは関係ありません。ゲームデータは含まれていません。正規に入手したゲームのコピーにのみ、自己責任でご利用ください。

**AI 生成コード：** このリポジトリのコードは AI（Anthropic の Claude）によって生成されています。気になる場合はソースコードをご自身で確認し、ゲームファイルのバックアップを必ず取ってください。
