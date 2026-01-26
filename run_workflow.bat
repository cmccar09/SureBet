@echo off
cd /d "C:\Users\charl\OneDrive\futuregenAI\Betting"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "scheduled_workflow.ps1" >> logs\task_output.log 2>&1
