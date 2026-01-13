<#
.SYNOPSIS
Daily health check to verify workflow is running and producing picks

.DESCRIPTION
This script runs after the scheduled workflow to verify:
1. Workflow completed successfully
2. Picks were generated for today
3. Picks are visible in DynamoDB
4. Picks are accessible via API Gateway
5. Amplify UI can fetch picks

Sends email alert if any check fails.
#>

param(
    [string]$AlertEmail = "your-email@example.com"  # Configure your email
)

$ErrorActionPreference = "Stop"
$WarningPreference = "Continue"

function Write-Log {
    param($Message, $Color = "White")
    $timestamp = Get-Date -Format "HH:mm:ss"
    Write-Host "[$timestamp] $Message" -ForegroundColor $Color
}

function Send-Alert {
    param($Subject, $Body)
    
    # TODO: Configure AWS SES or SMTP for email alerts
    Write-Log "ALERT: $Subject" "Red"
    Write-Log $Body "Red"
    
    # Log to file for manual review
    $alertLog = "$PSScriptRoot\health_check_alerts.log"
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp - $Subject`n$Body`n`n" | Out-File -FilePath $alertLog -Append
}

Write-Log "========================================" "Cyan"
Write-Log "DAILY HEALTH CHECK" "Cyan"
Write-Log "========================================" "Cyan"

$issues = @()
$today = (Get-Date).ToString("yyyy-MM-dd")

# CHECK 1: Verify picks exist in DynamoDB
Write-Log "CHECK 1: Verifying picks in DynamoDB..." "Yellow"
try {
    $pythonExe = "$PSScriptRoot\.venv\Scripts\python.exe"
    $checkScript = @"
import boto3
from datetime import datetime
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')
response = table.scan()
today_picks = [p for p in response['Items'] if '$today' in p.get('bet_date', '')]
print(len(today_picks))
"@
    
    $pickCount = & $pythonExe -c $checkScript
    
    if ($pickCount -eq 0) {
        $issues += "No picks found in DynamoDB for $today"
        Write-Log "  ✗ FAIL: 0 picks in database" "Red"
    } else {
        Write-Log "  ✓ PASS: $pickCount picks in database" "Green"
    }
} catch {
    $issues += "Failed to query DynamoDB: $_"
    Write-Log "  ✗ ERROR: $_" "Red"
}

# CHECK 2: Verify future picks exist
Write-Log "CHECK 2: Verifying future picks..." "Yellow"
try {
    $futureCheckScript = @"
import boto3
from datetime import datetime
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')
response = table.scan()
today_picks = [p for p in response['Items'] if '$today' in p.get('bet_date', '')]
now = datetime.utcnow()
future = [p for p in today_picks if datetime.fromisoformat(p.get('race_time', '').replace('Z', '')) > now]
print(len(future))
"@
    
    $futureCount = & $pythonExe -c $futureCheckScript
    
    if ($futureCount -eq 0) {
        Write-Log "  ⚠ WARNING: No future picks (all races may have passed)" "Yellow"
    } else {
        Write-Log "  ✓ PASS: $futureCount future picks" "Green"
    }
} catch {
    $issues += "Failed to check future picks: $_"
    Write-Log "  ✗ ERROR: $_" "Red"
}

# CHECK 3: Verify API Gateway responds
Write-Log "CHECK 3: Verifying API Gateway..." "Yellow"
try {
    $apiUrl = "https://e5na6ldp35.execute-api.eu-west-1.amazonaws.com/prod/picks/today"
    $response = Invoke-RestMethod -Uri $apiUrl -Method Get -TimeoutSec 10
    
    if ($response.success -eq $true) {
        Write-Log "  ✓ PASS: API Gateway responding (count: $($response.count))" "Green"
    } else {
        $issues += "API Gateway returned success=false"
        Write-Log "  ✗ FAIL: API returned error" "Red"
    }
} catch {
    $issues += "API Gateway not responding: $_"
    Write-Log "  ✗ ERROR: $_" "Red"
}

# CHECK 4: Verify Amplify UI accessibility
Write-Log "CHECK 4: Verifying Amplify UI..." "Yellow"
try {
    $amplifyUrl = "https://d2hmpykfsdweob.amplifyapp.com"
    $response = Invoke-WebRequest -Uri $amplifyUrl -Method Get -TimeoutSec 10 -UseBasicParsing
    
    if ($response.StatusCode -eq 200) {
        Write-Log "  ✓ PASS: Amplify UI accessible" "Green"
    } else {
        $issues += "Amplify UI returned status $($response.StatusCode)"
        Write-Log "  ✗ FAIL: Status $($response.StatusCode)" "Red"
    }
} catch {
    $issues += "Amplify UI not accessible: $_"
    Write-Log "  ✗ ERROR: $_" "Red"
}

# CHECK 5: Verify workflow ran recently
Write-Log "CHECK 5: Verifying workflow execution..." "Yellow"
try {
    $logFile = "$PSScriptRoot\workflow_execution.log"
    
    if (Test-Path $logFile) {
        $lastRun = (Get-Item $logFile).LastWriteTime
        $hoursSinceRun = ((Get-Date) - $lastRun).TotalHours
        
        if ($hoursSinceRun -gt 26) {
            $issues += "Workflow hasn't run in $([math]::Round($hoursSinceRun, 1)) hours"
            Write-Log "  ✗ FAIL: Last run $([math]::Round($hoursSinceRun, 1)) hours ago" "Red"
        } else {
            Write-Log "  ✓ PASS: Last run $([math]::Round($hoursSinceRun, 1)) hours ago" "Green"
        }
    } else {
        $issues += "No workflow execution log found"
        Write-Log "  ⚠ WARNING: No execution log" "Yellow"
    }
} catch {
    Write-Log "  ⚠ WARNING: Could not check workflow log: $_" "Yellow"
}

# CHECK 6: Verify Betfair token is valid
Write-Log "CHECK 6: Verifying Betfair authentication..." "Yellow"
try {
    $tokenCheckScript = @"
import json
from datetime import datetime, timedelta
with open('betfair-creds.json', 'r') as f:
    creds = json.load(f)
if 'token' in creds and 'token_created' in creds:
    created = datetime.fromisoformat(creds['token_created'])
    age_hours = (datetime.utcnow() - created).total_seconds() / 3600
    print(f'{age_hours:.1f}')
else:
    print('0')
"@
    
    $tokenAge = & $pythonExe -c $tokenCheckScript
    
    if ([double]$tokenAge -gt 23) {
        Write-Log "  ⚠ WARNING: Betfair token is $tokenAge hours old (expires at 24h)" "Yellow"
    } elseif ([double]$tokenAge -gt 0) {
        Write-Log "  ✓ PASS: Betfair token is $tokenAge hours old" "Green"
    } else {
        $issues += "Betfair token missing or invalid"
        Write-Log "  ✗ FAIL: Token missing" "Red"
    }
} catch {
    Write-Log "  ⚠ WARNING: Could not check token: $_" "Yellow"
}

# SUMMARY
Write-Log "`n========================================" "Cyan"
Write-Log "HEALTH CHECK SUMMARY" "Cyan"
Write-Log "========================================" "Cyan"

if ($issues.Count -eq 0) {
    Write-Log "✓ ALL CHECKS PASSED" "Green"
    Write-Log "System is healthy and operational" "Green"
    exit 0
} else {
    Write-Log "✗ $($issues.Count) ISSUE(S) FOUND:" "Red"
    foreach ($issue in $issues) {
        Write-Log "  - $issue" "Red"
    }
    
    # Send alert
    $subject = "SureBet Health Check Failed - $today"
    $body = "Health check found $($issues.Count) issues:`n`n" + ($issues -join "`n")
    Send-Alert -Subject $subject -Body $body
    
    Write-Log "`nCheck health_check_alerts.log for details" "Yellow"
    exit 1
}
