#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Scheduled betting workflow - runs every 2 hours to fetch fresh data and generate picks
.DESCRIPTION
    1. Learns from yesterday's results (if available)
    2. Fetches live Betfair data
    3. Applies prompt.txt logic via LLM
    4. Generates and saves picks to DynamoDB
    5. Logs everything for review
#>

$ErrorActionPreference = "Continue"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logDir = "$PSScriptRoot\logs"
$logFile = "$logDir\run_$timestamp.log"

# Create logs directory
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Write-Log {
    param($Message, $Color = "White")
    $timeStr = Get-Date -Format "HH:mm:ss"
    $logMsg = "[$timeStr] $Message"
    Write-Host $logMsg -ForegroundColor $Color
    Add-Content -Path $logFile -Value $logMsg
}

Write-Log "========================================" "Cyan"
Write-Log "SCHEDULED BETTING WORKFLOW" "Cyan"
Write-Log "========================================" "Cyan"

# Load Betfair credentials
if (Test-Path "$PSScriptRoot\betfair-creds.json") {
    $creds = Get-Content "$PSScriptRoot\betfair-creds.json" | ConvertFrom-Json
    $env:BETFAIR_APP_KEY = $creds.app_key
    $env:BETFAIR_SESSION = $creds.session_token
    Write-Log "Betfair credentials loaded" "Green"
} else {
    Write-Log "WARNING: betfair-creds.json not found" "Yellow"
}

# Check for LLM API key
if (-not $env:ANTHROPIC_API_KEY -and -not $env:OPENAI_API_KEY) {
    Write-Log "ERROR: No LLM API key found!" "Red"
    Write-Log "Set ANTHROPIC_API_KEY or OPENAI_API_KEY environment variable" "Yellow"
    exit 1
}

$pythonExe = "C:/Users/charl/OneDrive/futuregenAI/Betting/.venv/Scripts/python.exe"

# STEP 1: Learn from yesterday (if enabled)
$enableLearning = $true
if ($enableLearning) {
    Write-Log "`nSTEP 1: Learning from yesterday's results..." "Cyan"
    
    $yesterday = (Get-Date).AddDays(-1).ToString("yyyy-MM-dd")
    $yesterdaySlug = (Get-Date).AddDays(-1).ToString("yyyyMMdd")
    $selectionsFile = "$PSScriptRoot\history\selections_$yesterdaySlug.csv"
    $resultsFile = "$PSScriptRoot\history\results_$yesterdaySlug.json"
    
    if (Test-Path $selectionsFile) {
        if (Test-Path $resultsFile) {
            Write-Log "  Evaluating performance for $yesterday..." "Yellow"
            & $pythonExe "$PSScriptRoot\evaluate_performance.py" --selections $selectionsFile --results $resultsFile --apply 2>&1 | Tee-Object -Append -FilePath $logFile
        } else {
            Write-Log "  Fetching results for $yesterday..." "Yellow"
            & $pythonExe "$PSScriptRoot\fetch_race_results.py" --date $yesterday --selections $selectionsFile --out $resultsFile 2>&1 | Tee-Object -Append -FilePath $logFile
            
            if (Test-Path $resultsFile) {
                Write-Log "  Evaluating performance..." "Yellow"
                & $pythonExe "$PSScriptRoot\evaluate_performance.py" --selections $selectionsFile --results $resultsFile --apply 2>&1 | Tee-Object -Append -FilePath $logFile
            }
        }
    } else {
        Write-Log "  No yesterday's selections found - skipping learning" "Gray"
    }
}

# STEP 2: Generate today's picks
Write-Log "`nSTEP 2: Generating today's picks..." "Cyan"

$todaySlug = Get-Date -Format "yyyyMMdd"
$todayTime = Get-Date -Format "HHmmss"
$outputCsv = "$PSScriptRoot\history\selections_${todaySlug}_${todayTime}.csv"
$latestLink = "$PSScriptRoot\today_picks.csv"

# Create history directory
New-Item -ItemType Directory -Force -Path "$PSScriptRoot\history" | Out-Null

Write-Log "  Fetching live Betfair odds..." "Yellow"

# Fetch live data from Betfair API
$snapshotFile = "$PSScriptRoot\response_live.json"
& $pythonExe "$PSScriptRoot\betfair_delayed_snapshots.py" --out $snapshotFile --hours 24 --max_races 50 2>&1 | Tee-Object -Append -FilePath $logFile

if ($LASTEXITCODE -ne 0) {
    Write-Log "ERROR: Failed to fetch Betfair data" "Red"
    exit 1
}

Write-Log "  Applying prompt logic to live markets..." "Yellow"
& $pythonExe "$PSScriptRoot\run_saved_prompt.py" --prompt "$PSScriptRoot\prompt.txt" --snapshot $snapshotFile --out $outputCsv --max_races 10 2>&1 | Tee-Object -Append -FilePath $logFile

if ($LASTEXITCODE -ne 0) {
    Write-Log "ERROR: Failed to generate selections" "Red"
    exit 1
}

# Check if we got picks
if (Test-Path $outputCsv) {
    $pickCount = (Get-Content $outputCsv | Measure-Object -Line).Lines - 1
    
    if ($pickCount -gt 0) {
        Write-Log "  Generated $pickCount pick(s)" "Green"
        
        # Copy to latest
        Copy-Item $outputCsv $latestLink -Force
        
        # STEP 3: Save to DynamoDB
        Write-Log "`nSTEP 3: Saving to DynamoDB..." "Cyan"
        & $pythonExe "$PSScriptRoot\save_selections_to_dynamodb.py" --selections $outputCsv 2>&1 | Tee-Object -Append -FilePath $logFile
        
        if ($LASTEXITCODE -eq 0) {
            Write-Log "  Successfully saved to database" "Green"
        } else {
            Write-Log "  WARNING: Failed to save to DynamoDB" "Yellow"
        }
        
    } else {
        Write-Log "  No picks met ROI threshold" "Yellow"
    }
} else {
    Write-Log "  No output file generated" "Red"
}

# Summary
Write-Log "`n========================================" "Cyan"
Write-Log "WORKFLOW COMPLETE" "Green"
Write-Log "========================================" "Cyan"
Write-Log "Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Log "Log file: $logFile"
Write-Log "========================================" "Cyan"
