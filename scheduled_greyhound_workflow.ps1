#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Scheduled greyhound workflow - Ireland only, 4pm-10pm
.DESCRIPTION
    1. Learns from yesterday's greyhound results (if available)
    2. Fetches live Betfair greyhound data (Ireland only)
    3. Applies prompt.txt logic via LLM
    4. Generates and saves picks to DynamoDB
    5. Logs everything for review
#>

$ErrorActionPreference = "Continue"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logDir = "$PSScriptRoot\logs\greyhounds"
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
Write-Log "GREYHOUND WORKFLOW (Ireland Only)" "Cyan"
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

# Check for LLM API access
$awsConfigured = $false
try {
    $awsTest = aws sts get-caller-identity 2>&1
    if ($LASTEXITCODE -eq 0) {
        $awsConfigured = $true
        Write-Log "LLM Provider: AWS Bedrock (Claude via AWS)" "Green"
    }
} catch {}

if (-not $awsConfigured -and -not $env:ANTHROPIC_API_KEY -and -not $env:OPENAI_API_KEY) {
    Write-Log "ERROR: No LLM API access found!" "Red"
    exit 1
} elseif ($env:ANTHROPIC_API_KEY) {
    Write-Log "LLM Provider: Anthropic Claude" "Green"
} elseif ($env:OPENAI_API_KEY) {
    Write-Log "LLM Provider: OpenAI GPT" "Green"
}

$pythonExe = "C:/Users/charl/OneDrive/futuregenAI/Betting/.venv/Scripts/python.exe"

# STEP 1: Learn from yesterday's greyhound results
$enableLearning = $true
if ($enableLearning) {
    Write-Log "`nSTEP 1: Learning from yesterday's greyhound results..." "Cyan"
    
    $yesterday = (Get-Date).AddDays(-1).ToString("yyyy-MM-dd")
    $yesterdaySlug = (Get-Date).AddDays(-1).ToString("yyyyMMdd")
    $selectionsFile = "$PSScriptRoot\history\greyhound_selections_$yesterdaySlug*.csv" | Get-Item -ErrorAction SilentlyContinue | Select-Object -Last 1
    $resultsFile = "$PSScriptRoot\history\greyhound_results_$yesterdaySlug.json"
    
    if ($selectionsFile) {
        $selectionsPath = $selectionsFile.FullName
        
        if (Test-Path $resultsFile) {
            Write-Log "  Results already fetched, evaluating performance for $yesterday..." "Yellow"
            & $pythonExe "$PSScriptRoot\evaluate_performance.py" --selections $selectionsPath --results $resultsFile --apply 2>&1 | Tee-Object -Append -FilePath $logFile
            
            Write-Log "  Regenerating learning insights..." "Yellow"
            & $pythonExe "$PSScriptRoot\generate_learning_insights.py" 2>&1 | Tee-Object -Append -FilePath $logFile
        } else {
            Write-Log "  Fetching results for $yesterday..." "Yellow"
            & $pythonExe "$PSScriptRoot\fetch_race_results.py" --date $yesterday --selections $selectionsPath --out $resultsFile 2>&1 | Tee-Object -Append -FilePath $logFile
            
            if (Test-Path $resultsFile) {
                Write-Log "  Evaluating performance..." "Yellow"
                & $pythonExe "$PSScriptRoot\evaluate_performance.py" --selections $selectionsPath --results $resultsFile --apply 2>&1 | Tee-Object -Append -FilePath $logFile
                
                Write-Log "  Regenerating learning insights..." "Yellow"
                & $pythonExe "$PSScriptRoot\generate_learning_insights.py" 2>&1 | Tee-Object -Append -FilePath $logFile
            } else {
                Write-Log "  WARNING: Results fetch failed" "Yellow"
            }
        }
    } else {
        Write-Log "  No yesterday's greyhound selections found - skipping learning" "Gray"
    }
}

# STEP 2: Generate today's greyhound picks (Ireland only)
Write-Log "`nSTEP 2: Generating greyhound picks (Ireland only)..." "Cyan"

# Create history directory
New-Item -ItemType Directory -Force -Path "$PSScriptRoot\history" | Out-Null

Write-Log "  Fetching live Betfair greyhound odds (Ireland only)..." "Yellow"

# Fetch greyhound data from Betfair API - Ireland only
$snapshotFile = "$PSScriptRoot\response_greyhound_live.json"
& $pythonExe "$PSScriptRoot\betfair_delayed_snapshots.py" --out $snapshotFile --hours 6 --max_races 30 --sport greyhounds --country IE 2>&1 | Tee-Object -Append -FilePath $logFile

if ($LASTEXITCODE -ne 0) {
    Write-Log "ERROR: Failed to fetch Betfair greyhound data" "Red"
    exit 1
}

Write-Log "  Applying AI analysis to greyhound markets..." "Yellow"
$outputCsv = "$PSScriptRoot\today_greyhound_picks.csv"

# Generate picks using the same prompt logic
& $pythonExe "$PSScriptRoot\run_saved_prompt.py" --prompt ./prompt.txt --snapshot $snapshotFile --out $outputCsv --max_races 5 2>&1 | Tee-Object -Append -FilePath $logFile

if ($LASTEXITCODE -ne 0) {
    Write-Log "ERROR: Failed to generate greyhound selections" "Red"
    exit 1
}

# Check if we got picks
if (Test-Path $outputCsv) {
    $pickCount = (Get-Content $outputCsv | Measure-Object -Line).Lines - 1
    
    if ($pickCount -gt 0) {
        Write-Log "  Generated $pickCount greyhound pick(s)" "Green"
        
        # Save to history with timestamp
        $todaySlug = Get-Date -Format "yyyyMMdd_HHmm"
        $historyFile = "$PSScriptRoot\history\greyhound_selections_$todaySlug.csv"
        Copy-Item $outputCsv $historyFile
        
        # STEP 3: Save to DynamoDB with sport=greyhounds
        Write-Log "`nSTEP 3: Saving greyhound picks to DynamoDB..." "Cyan"
        & $pythonExe "$PSScriptRoot\save_selections_to_dynamodb.py" --selections $outputCsv --min_roi 0.0 --sport greyhounds 2>&1 | Tee-Object -Append -FilePath $logFile
        
        if ($LASTEXITCODE -eq 0) {
            Write-Log "  Successfully saved greyhound picks to database" "Green"
        } else {
            Write-Log "  WARNING: Failed to save to DynamoDB" "Yellow"
        }
        
    } else {
        Write-Log "  No greyhound picks met ROI threshold" "Yellow"
    }
} else {
    Write-Log "  No output file generated" "Red"
}

# Summary
Write-Log "`n========================================" "Cyan"
Write-Log "GREYHOUND WORKFLOW COMPLETE" "Green"
Write-Log "========================================" "Cyan"
Write-Log "Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Log "Log file: $logFile"
Write-Log "========================================" "Cyan"
