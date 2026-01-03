#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Setup Windows Task Scheduler to run betting workflow every 2 hours (10am-6pm)
.DESCRIPTION
    Creates scheduled tasks that run at 10:00, 12:00, 14:00, 16:00, and 18:00 daily
#>

param(
    [switch]$Remove  # Remove existing tasks instead of creating them
)

$taskBaseName = "BettingWorkflow"
$scriptPath = "$PSScriptRoot\scheduled_workflow.ps1"
$pythonVenv = "C:\Users\charl\OneDrive\futuregenAI\Betting\.venv"

# Times to run: 10am, 12pm, 2pm, 4pm, 6pm, 10pm (for results fetching)
$runTimes = @("10:00", "12:00", "14:00", "16:00", "18:00", "22:00")

Write-Host "="*60 -ForegroundColor Cyan
if ($Remove) {
    Write-Host "REMOVING Scheduled Betting Tasks" -ForegroundColor Yellow
} else {
    Write-Host "SETTING UP Scheduled Betting Tasks" -ForegroundColor Cyan
}
Write-Host "="*60 -ForegroundColor Cyan

foreach ($time in $runTimes) {
    $taskName = "${taskBaseName}_${time}".Replace(":", "")
    
    if ($Remove) {
        Write-Host "`nRemoving task: $taskName" -ForegroundColor Yellow
        try {
            Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
            Write-Host "  Removed" -ForegroundColor Green
        } catch {
            Write-Host "  Not found or error: $_" -ForegroundColor Gray
        }
        continue
    }
    
    Write-Host "`nCreating task: $taskName (runs at $time daily)" -ForegroundColor Cyan
    
    # Define the action
    $action = New-ScheduledTaskAction `
        -Execute "powershell.exe" `
        -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`"" `
        -WorkingDirectory $PSScriptRoot
    
    # Define the trigger (daily at specified time)
    $trigger = New-ScheduledTaskTrigger -Daily -At $time
    
    # Define settings
    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -RunOnlyIfNetworkAvailable `
        -ExecutionTimeLimit (New-TimeSpan -Hours 1)
    
    # Define principal - run whether user is logged in or not
    $principal = New-ScheduledTaskPrincipal `
        -UserId "$env:USERDOMAIN\$env:USERNAME" `
        -LogonType S4U `
        -RunLevel Highest
    
    # Register the task
    try {
        Register-ScheduledTask `
            -TaskName $taskName `
            -Action $action `
            -Trigger $trigger `
            -Settings $settings `
            -Principal $principal `
            -Description "Automated betting workflow - generates and saves picks every 2 hours" `
            -Force | Out-Null
        
        Write-Host "  Created successfully" -ForegroundColor Green
    } catch {
        Write-Host "  ERROR: $_" -ForegroundColor Red
    }
}

Write-Host "`n"
Write-Host "="*60 -ForegroundColor Cyan
if ($Remove) {
    Write-Host "TASKS REMOVED" -ForegroundColor Yellow
} else {
    Write-Host "SETUP COMPLETE!" -ForegroundColor Green
}
Write-Host "="*60 -ForegroundColor Cyan

if (-not $Remove) {
    Write-Host "`nScheduled tasks will run at:" -ForegroundColor Cyan
    foreach ($time in $runTimes) {
        Write-Host "  - $time" -ForegroundColor White
    }
    
    Write-Host "`nTo view tasks:" -ForegroundColor Yellow
    Write-Host "  Get-ScheduledTask -TaskName 'BettingWorkflow*'" -ForegroundColor Gray
    
    Write-Host "`nTo test manually:" -ForegroundColor Yellow
    Write-Host "  .\scheduled_workflow.ps1" -ForegroundColor Gray
    
    Write-Host "`nTo remove all tasks:" -ForegroundColor Yellow
    Write-Host "  .\setup_scheduler.ps1 -Remove" -ForegroundColor Gray
    
    Write-Host "`nLogs will be saved to:" -ForegroundColor Yellow
    Write-Host "  $PSScriptRoot\logs\" -ForegroundColor Gray
}

Write-Host "`n"
