#Requires -Version 5.1
<#
.SYNOPSIS
    Instala o SDD Kit (motor generico) num projeto de destino (Windows).

.DESCRIPTION
    Espelha o install.sh: copia a camada 1 (motor), cria steering/specs vazios,
    instala CLAUDE.md e .vscode a partir dos templates sem sobrescrever, e
    delega a continuidade entre versoes a tools/kit-sync.py - backup antes de
    copiar, preservacao de arquivos do motor editados no destino (a versao do
    kit fica ao lado como .sdd-new) e o relatorio .sdd/UPGRADE.md.

.PARAMETER Target
    Diretorio do projeto de destino. Aceita "." para o diretorio atual.

.EXAMPLE
    .\install.ps1 -Target C:\caminho\do\projeto

.EXAMPLE
    .\install.ps1 -Target .

.NOTES
    Arquivo mantido em ASCII puro de proposito: o Windows PowerShell 5.1 le
    scripts sem BOM como ANSI, o que corrompe acentos e quebra o parser.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$Target
)

$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# Resolucao de caminhos
# ---------------------------------------------------------------------------

$KitDir = if ($PSScriptRoot) {
    $PSScriptRoot
} else {
    Split-Path -Parent $MyInvocation.MyCommand.Path
}

$resolved = Resolve-Path -LiteralPath $Target -ErrorAction SilentlyContinue
if (-not $resolved) {
    Write-Error "Diretorio de destino nao existe: $Target"
    exit 1
}
$TargetDir = $resolved.ProviderPath

if (-not (Test-Path -LiteralPath $TargetDir -PathType Container)) {
    Write-Error "O destino nao e um diretorio: $TargetDir"
    exit 1
}

$normKit    = $KitDir.TrimEnd('\', '/')
$normTarget = $TargetDir.TrimEnd('\', '/')
if ($normTarget -eq $normKit) {
    Write-Error "O destino e a propria pasta do kit. Aponte para o seu projeto."
    exit 1
}

# ---------------------------------------------------------------------------
# Validacao das fontes do kit (falha cedo, antes de escrever qualquer coisa)
# ---------------------------------------------------------------------------

$required = @(
    '.claude\commands\sdd',
    '.claude\commands\prepare-pr.md',
    '.claude\agents\code-explorer.md',
    '.claude\skills\setup-sdd\SKILL.md',
    '.sdd\settings',
    '.sdd\settings\templates\vscode\tasks.json',
    'tools\spec-lint.py',
    'tools\approval-gate.py',
    'tools\kit-sync.py',
    'CLAUDE.md.template'
)

$missing = $required | Where-Object { -not (Test-Path -LiteralPath (Join-Path $KitDir $_)) }
if ($missing) {
    Write-Error ("Kit incompleto. Faltando em '$KitDir':" + [Environment]::NewLine +
                 ($missing -join [Environment]::NewLine))
    exit 1
}

$versionFile = Join-Path $KitDir 'VERSION'
$version = if (Test-Path -LiteralPath $versionFile) {
    ((Get-Content -LiteralPath $versionFile -Raw) -replace '\s', '')
} else {
    'sem versao'
}

Write-Host "==> instalando SDD Kit ($version) em: $TargetDir"

# ---------------------------------------------------------------------------
# Continuidade: backup + memoria do que a versao anterior instalou
# ---------------------------------------------------------------------------
# Mesmo runtime que o spec-lint ja exige. No Windows, `python` na PATH costuma
# ser o stub da Microsoft Store, que nao executa - por isso testamos de fato.

# A sonda roda com EAP relaxado de proposito: no PS 5.1, redirecionar o stderr
# de um executavel nativo vira ErrorRecord e, sob 'Stop', abortaria o script.
$PyBin = $null
$prevEAP = $ErrorActionPreference
$ErrorActionPreference = 'SilentlyContinue'
foreach ($c in @('py', 'python3', 'python')) {
    if (-not (Get-Command $c -ErrorAction SilentlyContinue)) { continue }
    try {
        & $c -c 'import sys; sys.exit(0 if sys.version_info[0] == 3 else 1)' 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { $PyBin = $c; break }
    } catch { }
}
$ErrorActionPreference = $prevEAP

$KitSync   = Join-Path $KitDir 'tools\kit-sync.py'
$BackupDir = $null
if ($PyBin) {
    $BackupDir = & $PyBin $KitSync preflight --kit $KitDir --target $TargetDir |
                 Select-Object -Last 1
    if ($LASTEXITCODE -ne 0) { $BackupDir = $null }
} else {
    Write-Host "    aviso: Python 3 nao encontrado - sem backup e sem preservacao de edicoes locais."
    Write-Host "           O kit precisa de Python 3.7+ de qualquer forma (spec-lint, approval-gate)."
}

# ---------------------------------------------------------------------------
# Camada 1: motor
# ---------------------------------------------------------------------------

$dirs = @(
    '.claude\commands\sdd',
    '.claude\agents',
    '.claude\skills',
    '.sdd\settings',
    '.sdd\steering',
    '.sdd\specs',
    'tools'
)
foreach ($d in $dirs) {
    New-Item -ItemType Directory -Force -Path (Join-Path $TargetDir $d) | Out-Null
}

# Copia o conteudo de cada subarvore (o '\*' copia o que esta DENTRO da pasta).
# .claude\commands cobre sdd\* E os comandos de entrega top-level
# (prepare-pr, review, data-quality).
Copy-Item -Path (Join-Path $KitDir '.claude\commands\*') `
          -Destination (Join-Path $TargetDir '.claude\commands') -Recurse -Force
Copy-Item -Path (Join-Path $KitDir '.claude\agents\*') `
          -Destination (Join-Path $TargetDir '.claude\agents') -Recurse -Force
Copy-Item -Path (Join-Path $KitDir '.claude\skills\*') `
          -Destination (Join-Path $TargetDir '.claude\skills') -Recurse -Force
Copy-Item -Path (Join-Path $KitDir '.sdd\settings\*') `
          -Destination (Join-Path $TargetDir '.sdd\settings') -Recurse -Force

Copy-Item -Path (Join-Path $KitDir 'tools\*.py') `
          -Destination (Join-Path $TargetDir 'tools') -Force   # spec-lint.py + approval-gate.py

if (Test-Path -LiteralPath $versionFile) {
    Copy-Item -LiteralPath $versionFile `
              -Destination (Join-Path $TargetDir '.sdd\SDD_KIT_VERSION') -Force
}

# Config do modo aprovador automatico: instala a versao editavel (nao sobrescreve)
$autoCfg = Join-Path $TargetDir '.sdd\autoapprove.json'
if (-not (Test-Path -LiteralPath $autoCfg)) {
    Copy-Item -LiteralPath (Join-Path $KitDir '.sdd\settings\templates\autoapprove.json') `
              -Destination $autoCfg -Force
}

foreach ($f in @('.sdd\steering\.gitkeep', '.sdd\specs\.gitkeep')) {
    $p = Join-Path $TargetDir $f
    if (-not (Test-Path -LiteralPath $p)) {
        New-Item -ItemType File -Path $p -Force | Out-Null
    }
}

# ---------------------------------------------------------------------------
# Camada 2: CLAUDE.md (nunca sobrescreve)
# ---------------------------------------------------------------------------

$templateSrc = Join-Path $KitDir 'CLAUDE.md.template'
$claudeMd    = Join-Path $TargetDir 'CLAUDE.md'

if (Test-Path -LiteralPath $claudeMd) {
    Copy-Item -LiteralPath $templateSrc `
              -Destination (Join-Path $TargetDir 'CLAUDE.md.template') -Force
    Write-Host "    CLAUDE.md ja existe - template copiado ao lado como CLAUDE.md.template"
} else {
    Copy-Item -LiteralPath $templateSrc -Destination $claudeMd -Force
    Write-Host "    CLAUDE.md criado a partir do template (edite os {{PLACEHOLDERS}})"
}

# ---------------------------------------------------------------------------
# Integracao com o editor: .vscode (nunca sobrescreve)
# ---------------------------------------------------------------------------

$vscodeDir = Join-Path $TargetDir '.vscode'
New-Item -ItemType Directory -Force -Path $vscodeDir | Out-Null

foreach ($f in @('tasks.json', 'settings.json', 'extensions.json')) {
    $src = Join-Path $KitDir ".sdd\settings\templates\vscode\$f"
    $dst = Join-Path $vscodeDir $f
    if (-not (Test-Path -LiteralPath $src)) { continue }
    if (-not (Test-Path -LiteralPath $dst)) {
        Copy-Item -LiteralPath $src -Destination $dst -Force
        Write-Host "    .vscode\$f criado"
    } else {
        $same = (Get-FileHash -LiteralPath $src).Hash -eq (Get-FileHash -LiteralPath $dst).Hash
        if (-not $same) {
            Copy-Item -LiteralPath $src -Destination "$dst.sdd-new" -Force
            Write-Host "    .vscode\$f ja existe - versao do kit ao lado como $f.sdd-new"
        }
    }
}

# ---------------------------------------------------------------------------
# Continuidade: preserva edicoes locais, grava manifesto e UPGRADE.md
# ---------------------------------------------------------------------------

if ($PyBin) {
    if ($BackupDir) {
        & $PyBin $KitSync finish --kit $KitDir --target $TargetDir --backup $BackupDir
    } else {
        & $PyBin $KitSync finish --kit $KitDir --target $TargetDir
    }
}

# ---------------------------------------------------------------------------
# Proximos passos
# ---------------------------------------------------------------------------

$nextSteps = @'

==> motor instalado. Leia primeiro: .sdd\UPGRADE.md
    (o que foi preservado, o que revisar e o que a camada 2 ainda deve)

    No editor: Ctrl+Shift+B roda o lint das specs no painel Problems.

    Proximos passos (no agente, dentro do projeto):

    1. rode a skill  setup-sdd        (bootstrap guiado - recomendado)
    2. edite CLAUDE.md                (troque os {{PLACEHOLDERS}})
    3. /sdd:absorb-knowledge          (aproveita configs de agentes previos)
    4. /sdd:discover-tools            (mapeia Jira/git/dados -> integrations.md)
    5. /sdd:steering                  (gera product/tech/structure do seu codigo)
    6. /sdd:spec-quick "feature real" --spec-only
    7. /sdd:spec-lint <feature>

steering foi deixado VAZIO de proposito - ele e gerado do SEU projeto.
'@

Write-Host $nextSteps
Write-Host "Destino: $TargetDir"
