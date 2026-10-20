$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
New-Item -ItemType Directory -Force '.tmp' | Out-Null
$env:TEMP = Join-Path $PSScriptRoot '.tmp'
$env:TMP = $env:TEMP
$env:PYTHONPATH = $PSScriptRoot
if (-not (Test-Path '.venv/Scripts/python.exe')) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 이상을 설치해 주세요.' }
}
$demoPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
& $demoPython -m pip --version *> $null
if ($LASTEXITCODE -ne 0) {
    & $demoPython -m ensurepip --upgrade
    if ($LASTEXITCODE -ne 0) { throw '패키지 관리자 초기화 실패' }
}
& $demoPython -c 'import streamlit, pandas, pytest' *> $null
if ($LASTEXITCODE -ne 0) {
    $demoRequirements = if (Test-Path 'requirements-lock.txt') { 'requirements-lock.txt' } else { 'requirements.txt' }
    & $demoPython -m pip install -r $demoRequirements
    if ($LASTEXITCODE -ne 0) { throw '패키지 설치 실패: 인터넷 연결을 확인하세요.' }
}
& $demoPython -m streamlit run app.py --server.address 127.0.0.1 --server.headless true --server.fileWatcherType none --browser.gatherUsageStats false
exit $LASTEXITCODE
