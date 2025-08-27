$ErrorActionPreference = "Stop"
$src = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) 'cursor.mcp.json'
$dest = Join-Path $env:USERPROFILE '.cursor\mcp.json'
$dir = Split-Path -Parent $dest
if (!(Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }

# Repo root: tools\mcp -> tools -> repo root
$repoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
$envPath = Join-Path $repoRoot '.env'

# Şablonu yükle
$content = Get-Content $src -Raw

# ${PROJECT_DIR} enjekte et
$projectDir = $repoRoot
$escapedProjectDir = ($projectDir -replace '\\', '\\\\' -replace '"', '\"')
$content = [Regex]::Replace($content, "\$\{PROJECT_DIR\}", $escapedProjectDir)

# .env değerlerini uygula
if (Test-Path $envPath) {
  $envLines = Get-Content $envPath | Where-Object { $_ -match '^[A-Za-z_][A-Za-z0-9_]*=.*$' }
  foreach ($line in $envLines) {
    $name, $value = $line -split '=', 2
    $escapedName = [Regex]::Escape($name)
    $escapedValue = ($value -replace '\\', '\\\\' -replace '"', '\"')
    $content = [Regex]::Replace($content, "\$\{${escapedName}\}", $escapedValue)
  }
}

# Kalan ${VAR} placeholder’ları için OS env fallback
$varPlaceholders = [regex]::Matches($content, "\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
foreach ($m in $varPlaceholders) {
  $name = $m.Groups[1].Value
  $val = [Environment]::GetEnvironmentVariable($name)
  if (![string]::IsNullOrEmpty($val)) {
    $escapedName = [Regex]::Escape($name)
    $escapedVal = ($val -replace '\\', '\\\\' -replace '"', '\"')
    $content = [Regex]::Replace($content, "\$\{${escapedName}\}", $escapedVal)
  }
}

Set-Content -Path $dest -Value $content -Encoding UTF8
Write-Host "Installed: $dest"