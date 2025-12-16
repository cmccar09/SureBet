#!/usr/bin/env pwsh
# Quick script to generate today's picks and save to DynamoDB

Write-Host "="*60
Write-Host "Generate Today's Betting Picks"
Write-Host "="*60

# Load Betfair credentials and set environment variables
if (Test-Path "./betfair-creds.json") {
    $creds = Get-Content "./betfair-creds.json" | ConvertFrom-Json
    $env:BETFAIR_APP_KEY = $creds.app_key
    $env:BETFAIR_SESSION = $creds.session_token
    Write-Host ""
    Write-Host "Betfair Credentials: Loaded ✓" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "WARNING: betfair-creds.json not found" -ForegroundColor Yellow
}

# Step 1: Check for API keys
$anthropicKey = $env:ANTHROPIC_API_KEY
$openaiKey = $env:OPENAI_API_KEY

if (-not $anthropicKey -and -not $openaiKey) {
    Write-Host ""
    Write-Host "ERROR: No LLM API key found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Set one of these environment variables:" -ForegroundColor Yellow
    Write-Host '  $env:ANTHROPIC_API_KEY = "your-anthropic-key"'
    Write-Host '  $env:OPENAI_API_KEY = "your-openai-key"'
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "API Key: " -NoNewline
if ($anthropicKey) {
    Write-Host "Anthropic Claude ✓" -ForegroundColor Green
} else {
    Write-Host "OpenAI GPT ✓" -ForegroundColor Green
}

# Step 2: Generate selections with prompt logic
Write-Host ""
Write-Host "Step 1: Fetching live Betfair odds..." -ForegroundColor Cyan
Write-Host ""

$pythonExe = "C:/Users/charl/OneDrive/futuregenAI/Betting/.venv/Scripts/python.exe"
$snapshotFile = "./response_live.json"

# Fetch live data from Betfair API
& $pythonExe betfair_delayed_snapshots.py --out $snapshotFile --hours 24 --max_races 50

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: Failed to fetch Betfair data" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Step 2: Generating selections using prompt.txt logic..." -ForegroundColor Cyan
Write-Host ""

& $pythonExe run_saved_prompt.py --prompt ./prompt.txt --snapshot $snapshotFile --out ./today_picks.csv --max_races 5

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: Failed to generate selections" -ForegroundColor Red
    exit 1
}

# Check if file was created
if (-not (Test-Path "./today_picks.csv")) {
    Write-Host ""
    Write-Host "ERROR: No picks file generated" -ForegroundColor Red
    Write-Host "This could mean:" -ForegroundColor Yellow
    Write-Host "  - No races meet the ROI threshold (>20%)" -ForegroundColor Yellow
    Write-Host "  - No Betfair data available" -ForegroundColor Yellow
    Write-Host "  - LLM call failed" -ForegroundColor Yellow
    exit 1
}

# Step 3: Save to DynamoDB
Write-Host ""
Write-Host "Step 2: Saving to DynamoDB..." -ForegroundColor Cyan
Write-Host ""

& "C:/Users/charl/OneDrive/futuregenAI/Betting/.venv/Scripts/python.exe" save_selections_to_dynamodb.py --selections ./today_picks.csv

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: Failed to save to DynamoDB" -ForegroundColor Red
    Write-Host "Check AWS credentials with: aws sts get-caller-identity" -ForegroundColor Yellow
    exit 1
}

# Step 4: Verify in DynamoDB
Write-Host ""
Write-Host "Step 3: Verifying in DynamoDB..." -ForegroundColor Cyan
Write-Host ""

aws dynamodb scan --table-name SureBetBets --filter-expression "begins_with(#d, :today)" --expression-attribute-names '{\"#d\":\"date\"}' --expression-attribute-values '{\":today\":{\"S\":\"2025-12-16\"}}' --query "Items[*].[horse.S, course.S, bet_type.S]" --output table

Write-Host ""
Write-Host "="*60
Write-Host "SUCCESS!" -ForegroundColor Green
Write-Host "="*60
Write-Host ""
Write-Host "✓ Picks generated: ./today_picks.csv"
Write-Host "✓ Saved to DynamoDB: SureBetBets table"
Write-Host "✓ Your React app should now show today's picks"
Write-Host ""
