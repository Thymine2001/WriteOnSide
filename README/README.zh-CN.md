<p align="center">
  <img src="../assets/writeonside_logo_light.svg" alt="随边记 标志" width="96" />
</p>

<h1 align="center">随边记</h1>

<p align="center">
  <strong>WriteOnSide · 轻量级 Windows 侧边栏 Markdown 笔记应用。</strong><br />
  纯文本文件存储。兼容 Obsidian。始终贴屏边待命。
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Windows-10%20%7C%2011-0078D4?logo=windows" alt="Windows 10 与 11" />
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white" alt="Python 3.12" />
  <img src="https://img.shields.io/badge/version-0.1.0-2ea44f" alt="版本 0.1.0" />
</p>

<p align="center">
  <strong>语言：</strong>
  <a href="../README.md">English</a> |
  <a href="README.zh-CN.md">中文</a> |
  <a href="README.pt.md">Português</a> |
  <a href="README.de.md">Deutsch</a> |
  <a href="README.fr.md">Français</a> |
  <a href="README.nl.md">Nederlands</a> |
  <a href="README.ko.md">한국어</a> |
  <a href="README.it.md">Italiano</a> |
  <a href="README.hi.md">हिन्दी</a> |
  <a href="README.uk.md">Українська</a>
</p>

**随边记**（WriteOnSide）将 Markdown 笔记保存在你指定的文件夹中。没有私有数据库，也不强制使用云服务，因此同一 Vault 可在随边记、Obsidian、VS Code 或其他编辑器中打开。

> [!NOTE]
> 随边记 `0.1.0` 为开发中的预发布版本。升级前请备份重要笔记并查看发行说明。

## 安装

### 下载 Windows 构建版

从 [GitHub Releases](https://github.com/Thymine2001/WriteOnSide/releases) 下载最新的 `WriteOnSide.exe`。

随边记目前以便携式单文件 Windows 应用分发：

1. 下载 `WriteOnSide.exe`。
2. 将其放在你希望存放应用的文件夹中。
3. 运行并选择笔记文件夹或现有 Obsidian Vault。
4. 使用 `Ctrl+Shift+Enter` 显示或隐藏面板。

未签名的开发版可能触发 Windows SmartScreen 警告。运行前请确认文件来自本仓库。

## 主要特性

### 侧边面板

- 无边框、全高度、始终置顶
- 可配置左侧或右侧贴边布局
- 全局显示/隐藏快捷键，默认 `Ctrl+Shift+Enter`
- 可调面板宽度、文件栏宽度与不透明度
- 流畅的打开、关闭、布局与缩放动画
- 系统托盘与可选的 Windows 开机启动
- 单实例行为与多显示器工作区定位

### Markdown 编辑

- 可编辑源码与实时语法高亮
- 只读渲染模式，支持链接与图片
- 格式化工具栏：标题、强调、引用、列表、任务、表格、代码、链接、图片、高亮与文字颜色
- YAML 元数据：标题、标签、日期、别名等
- 查找替换、行号、大纲导航与标题吸顶
- 围栏代码块带语言标签，支持一键复制
- 可配置字体、字号、主题与命令快捷键

### 界面语言

应用内置 **English**、**中文**、**Português**、**Deutsch**、**Français**、**Nederlands**、**한국어**、**Italiano**、**हिन्दी**、**Українська**。在 **设置 → 常规 → 语言** 中切换。

### Obsidian 兼容性

| 功能 | 支持 |
|---|---|
| Wiki 链接：`[[Note]]`、`[[Note\|alias]]`、`[[Note#Heading]]` | 是 |
| 块引用：`[[Note#^block-id]]` | 是 |
| 笔记/图片嵌入：`![[file]]` | 是 |
| 标注：`> [!note]` | 阅读模式 |
| 脚注、`%%注释%%`、行内 `#tags` | 是 |
| 任务列表：`- [ ]` / `- [x]` | 是 |
| 重命名笔记并更新入站 wikilink | 是 |

输入 `[[` 打开笔记补全。编辑模式下 `Ctrl+点击` 可跟随 wikilink。**反向链接** 工具可列出链接到当前笔记的其他笔记。

### 文件与附件

- 懒加载文件树与递归搜索
- YAML 标签筛选，支持多选
- 创建、重命名、删除、拖拽与预览
- 编辑 Markdown 及常见文本/源码格式
- 粘贴或拖拽图片到笔记
- 可配置附件文件夹，相对路径便于迁移
- 原子保存与 Vault 外的时间戳备份
- 图片查看器，支持缩放与平移

## 系统要求

**最终用户：**

- Windows 10 或 Windows 11
- 标准桌面环境；Windows on ARM 尚未正式测试

**从源码开发：**

- Python 3.12
- [`requirements.txt`](../requirements.txt) 中列出的依赖

## 从源码运行

```powershell
git clone https://github.com/Thymine2001/WriteOnSide.git
cd WriteOnSide

py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\writeonside.py
```

首次启动时选择笔记文件夹或现有 Obsidian Vault。

## 基本用法

- 点击汉堡按钮打开或关闭「文件」栏。
- 在工具栏切换编辑/阅读模式。
- 从工具栏或文件栏新建笔记。
- 在 Markdown 笔记中直接粘贴图片，会复制到配置的附件文件夹。
- 在文件栏下方选择 YAML 标签以筛选笔记。
- 打开「设置」配置笔记文件夹、布局、宽度、不透明度、主题、字体、全局快捷键与工具栏快捷键。
- 关闭面板会隐藏应用；使用全局快捷键或托盘菜单再次显示。

## 测试

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
```

当前源码树包含 44 项单元测试，覆盖配置、Markdown 渲染、快捷键、存储、笔记索引、Obsidian 语法、wikilink 重命名与国际化。

## 构建 Windows EXE

发行脚本除运行时依赖外，还需要 PyInstaller 与 PyMuPDF：

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller pymupdf
.\build_release.ps1
```

脚本会：

1. 递增 `VERSION` 中的补丁号。
2. 从 SVG 导出 PNG 与 ICO。
3. 使用 PyInstaller 构建单文件 Windows 可执行文件。
4. 输出到 `dist-native-tree-vX.Y.Z\WriteOnSide.exe`。
5. 保留最近三个发行目录。

详见 [`BUILDING.md`](../BUILDING.md)。

## 数据位置

| 数据 | 位置 |
|---|---|
| 笔记与附件 | 用户选择的文件夹或 Obsidian Vault |
| 设置 | `%LOCALAPPDATA%\WriteOnSide\config.json` |
| 托管备份 | `%LOCALAPPDATA%\WriteOnSide\Backups\` |

随边记不需要账号或内置云服务。笔记仅在你自行配置的同步服务中离开本机。

## 项目结构

```text
writeonside.py          应用入口
writeonside_app/        应用源码
assets/                 SVG、PNG、ICO 资源
scripts/                构建辅助脚本
tests/                  单元测试
licenses/               第三方许可证全文
WriteOnSide.spec        PyInstaller 配置
build_release.ps1       版本化 Windows 发行脚本
BUILDING.md             详细构建说明
THIRD_PARTY_NOTICES.md  依赖归属与许可证索引
LICENSE                 随边记（WriteOnSide）源码 MIT 许可证
```

## 许可证

随边记原创源码采用 [MIT 许可证](../LICENSE)。

第三方组件仍受其各自许可证约束，见 [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)。

<p align="center">
  <sub>随边记 · Python | Tkinter | Markdown | 兼容 Obsidian 的纯文本笔记</sub>
</p>
