# Princess Maker: Children of Revelation — TableData & Bundle 工具

[English](README.md) | [繁體中文](README.zh-TW.md) | **简体中文** | [日本語](README.ja.md) | [한국어](README.ko.md)

适用于 **Princess Maker: Children of Revelation**（Steam）的 Windows 图形界面小工具：解密 AssetBundle，提取并编辑加密的 `TableData`，并可通过补丁文件 (patch) 在游戏更新后保留你的修改。

界面语言：繁體中文 / 简体中文 / English / 日本語 / 한국어（右上角可切换）。

## 功能

- **Bundle 解密** — 原地解密 `packedassets_assets_all_*.bundle`（会先创建 `.bak` 备份）。
- **TableData 提取 / 编辑** — 从 `resources.assets` 取出 `TableData` 并解密，生成 SQLite 数据库以及每张表一个 JSON。
- **数据库浏览** — 搜索数据表、Filter 筛选行、双击单元格编辑、只读 SQL 查询。修改后会保留原有类型（数字、布尔值、数组）。
- **重新加密并输出** — 生成 `TableData_modified.txt`，再用 [UABEANext](https://github.com/nesrak1/UABEANext) 导入 `resources.assets`。本工具本身不会覆盖 `resources.assets`。
- **补丁文件 (patch)** — 把你的修改保存为小文件，游戏更新后一键应用。

## 安装与运行

### 方式 A：下载 exe（最简单）

在 [Releases](../../releases) 页面下载 `PrincessMakerTool.exe`，请放在专用文件夹中，工具会在 exe 旁边创建工作文件。无需安装 Python。

### 方式 B：使用源码运行

需要 Python 3.10 及以上：

```bash
pip install -r requirements.txt
python PrincessMakerTool.py
```

## 基本流程

1. 选择游戏根目录（包含 `PrincessMakerKaren_Data` 的那一层），点击 **自动查找**。
2. **Bundle 解密** 分页 → 解密 Bundle（只需一次）。
3. **TableData** 分页：
   1. 从 resources.assets 提取并解密
   2. 建立数据库 + 导出 JSON
4. **数据库浏览 / 编辑** 分页 → 点击表名，双击单元格修改，点击“保存修改”。
5. **TableData** 分页 → 步骤 3“重新加密并输出 TableData_modified.txt”。
6. 用 UABEANext 打开 `resources.assets`，把 `TableData_modified.txt` 导入 `TableData` 后保存。

也可以直接修改 `tables/` 内的 JSON，再点击“从 tables 重新加载”。

## 游戏更新后保留你的修改

游戏更新会替换 `TableData`，在旧数据上做的修改会随之丢失。请使用补丁：

1. **创建补丁（保存我的修改）** — 只记录与原始数据的差异，用每行唯一的 ID 字段定位。
2. 更新游戏后，重做步骤 1、2（提取 + 建立数据库）。
3. **应用补丁（还原我的修改）** — 把补丁应用到新数据上。
4. 步骤 3 输出 → 再用 UABEANext 导入。

如果游戏也修改了你改过的字段，会询问是用你的值覆盖，还是保留游戏的新值。无法对应的项目（行被删除、字段改名、整张表消失）不会被悄悄丢掉，而是列在 `patches/apply_report_*.txt` 中。

安全机制：步骤 2 覆盖 `tables/` 之前，会先把你当前的修改自动保存为 `patches/auto_before_reexport_*.json`。

## 会在 exe 旁边创建的文件

| 路径 | 用途 |
|---|---|
| `TableData.dec.bin` | 解密后的 TableData |
| `TableData.db` | 浏览器使用的 SQLite 数据库 |
| `tables/` | 每张表一个 JSON（你的可编辑副本） |
| `tables_orig/` | 未修改的原始副本，作为补丁比对基准 |
| `patches/` | 补丁文件与应用报告 |
| `TableData_modified.txt` | 最终输出，用 UABEANext 导入 |
| `pm_tool_settings.json` | 语言与上次的游戏文件夹 |

## 自行打包 exe

把 `PrincessMakerTool.py`、`requirements.txt`、`build.bat` 放在同一个文件夹，双击 `build.bat`，成品位于 `dist\PrincessMakerTool.exe`。

## 注意事项

- 仅支持 Windows（构建脚本与路径针对 Windows 版 Steam）。
- 请务必备份游戏文件。Steam →“验证游戏文件完整性”可以还原。
- 未签名的单文件 exe 有时会被杀毒软件或 SmartScreen 误报，想避免的话可以自行用源码打包。
- 没有唯一 ID 字段的表，补丁会退回用行的位置比对，游戏更新后可靠性较低。

## 免责声明

本工具为非官方的玩家自制工具，与游戏开发商及发行商无关，且不包含任何游戏数据。请仅用于你合法获得的游戏副本，风险自负。

**AI 生成的代码：** 本项目的代码由 AI（Anthropic 的 Claude）生成。如有疑虑请自行检查源码，并务必备份游戏文件。
