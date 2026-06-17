[CmdletBinding()]
param(
    [string]$Version = ""
)

$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$versionFile = Join-Path $projectRoot "VERSION"
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$spec = Join-Path $projectRoot "WriteOnSide.spec"

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Project Python was not found: $python"
}
if (-not (Test-Path -LiteralPath $spec -PathType Leaf)) {
    throw "PyInstaller spec was not found: $spec"
}

$currentText = if (Test-Path -LiteralPath $versionFile) {
    (Get-Content -LiteralPath $versionFile -Raw).Trim()
} else {
    "0.0.0"
}

if ($Version) {
    if ($Version -notmatch '^(\d+)\.(\d+)\.(\d+)$') {
        throw "Version must use semantic version format such as 0.1.0."
    }
    $nextVersion = $Version
} else {
    if ($currentText -notmatch '^(\d+)\.(\d+)\.(\d+)$') {
        throw "VERSION must use semantic version format such as 0.0.1."
    }
    $nextVersion = "$($Matches[1]).$($Matches[2]).$([int]$Matches[3] + 1)"
}

if ($nextVersion -notmatch '^(\d+)\.(\d+)\.(\d+)$') {
    throw "Resolved version must use semantic version format such as 0.1.0."
}
$major = [int]$Matches[1]
$minor = [int]$Matches[2]
$patch = [int]$Matches[3]
$releaseName = "dist-native-tree-v$nextVersion"
$releaseDir = Join-Path $projectRoot $releaseName
$workDir = Join-Path $projectRoot "build-release-v$nextVersion"
$versionInfo = Join-Path $projectRoot "version_info.txt"

if (Test-Path -LiteralPath $releaseDir) {
    throw "Release directory already exists: $releaseDir"
}

$versionTuple = "$major, $minor, $patch, 0"
$versionInfoText = @"
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=($versionTuple),
    prodvers=($versionTuple),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'WriteOnSide'),
         StringStruct(u'FileDescription', u'WriteOnSide Markdown Notes'),
         StringStruct(u'FileVersion', u'$nextVersion'),
         StringStruct(u'InternalName', u'WriteOnSide'),
         StringStruct(u'OriginalFilename', u'WriteOnSide.exe'),
         StringStruct(u'ProductName', u'WriteOnSide'),
         StringStruct(u'ProductVersion', u'$nextVersion')])
    ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"@
Set-Content -LiteralPath $versionInfo -Value $versionInfoText -Encoding utf8

Push-Location $projectRoot
try {
    & $python (Join-Path $projectRoot "scripts\export_icons.py")
    if ($LASTEXITCODE -ne 0) {
        throw "Icon export failed with exit code $LASTEXITCODE."
    }

    & $python -m PyInstaller `
        --noconfirm `
        --clean `
        --distpath $releaseDir `
        --workpath $workDir `
        $spec
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE."
    }

    $exe = Join-Path $releaseDir "WriteOnSide.exe"
    if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) {
        throw "Build completed without producing $exe."
    }

    Set-Content -LiteralPath $versionFile -Value $nextVersion -Encoding ascii

    $releases = Get-ChildItem -LiteralPath $projectRoot -Directory |
        Where-Object { $_.Name -match '^dist-native-tree-v(\d+)\.(\d+)\.(\d+)$' } |
        ForEach-Object {
            [pscustomobject]@{
                Directory = $_
                Version = [version]"$($Matches[1]).$($Matches[2]).$($Matches[3])"
            }
        } |
        Sort-Object Version -Descending

    foreach ($oldRelease in ($releases | Select-Object -Skip 3)) {
        $resolved = (Resolve-Path -LiteralPath $oldRelease.Directory.FullName).Path
        $expectedPrefix = $projectRoot + [IO.Path]::DirectorySeparatorChar + "dist-native-tree-v"
        if (-not $resolved.StartsWith($expectedPrefix, [StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to remove unexpected path: $resolved"
        }
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }

    if (Test-Path -LiteralPath $workDir) {
        $resolvedWork = (Resolve-Path -LiteralPath $workDir).Path
        $expectedWorkPrefix = $projectRoot + [IO.Path]::DirectorySeparatorChar + "build-release-v"
        if (-not $resolvedWork.StartsWith($expectedWorkPrefix, [StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to remove unexpected work path: $resolvedWork"
        }
        Remove-Item -LiteralPath $resolvedWork -Recurse -Force
    }

    $sizeMb = [math]::Round((Get-Item -LiteralPath $exe).Length / 1MB, 2)
    Write-Host "Built WriteOnSide v$nextVersion"
    Write-Host "Output: $exe"
    Write-Host "Size: $sizeMb MB"
} finally {
    Pop-Location
}
