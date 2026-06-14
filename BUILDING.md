# WriteOnSide Windows 打包说明

## 环境准备

在 PowerShell 中进入源码目录：

```powershell
cd C:\Developing\Software\writeonside
```

首次打包时创建虚拟环境并安装依赖：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller
```

## 推荐打包方式

运行项目自带脚本：

```powershell
.\build_release.ps1
```

该脚本会自动：

1. 读取 `VERSION` 并将补丁版本加一，例如 `0.0.32` 变为 `0.0.33`。
2. 更新 `version_info.txt` 中的 Windows 文件版本。
3. 使用 `WriteOnSide.spec` 和 PyInstaller 构建单文件 EXE。
4. 输出到 `dist-native-tree-v版本号\WriteOnSide.exe`。
5. 删除临时构建目录。
6. 只保留最近三个 `dist-native-tree-v*` 发布目录。

## 手动执行 PyInstaller

需要自行控制输出目录时，可执行：

```powershell
.\.venv\Scripts\python.exe -m PyInstaller `
  --noconfirm `
  --clean `
  --distpath .\dist-manual `
  --workpath .\build-manual `
  .\WriteOnSide.spec
```

生成文件位于：

```text
dist-manual\WriteOnSide.exe
```

直接运行 PyInstaller 不会自动更新 `VERSION`、`version_info.txt`，也不会清理旧版本。因此日常发布建议使用 `build_release.ps1`。

## 打包前检查

```powershell
.\.venv\Scripts\python.exe -m py_compile .\writeonside.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
```

## 常见问题

- 无法运行脚本：使用 `powershell -ExecutionPolicy Bypass -File .\build_release.ps1`。
