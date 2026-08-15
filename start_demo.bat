@echo off
echo ==============================================
echo       VERITAS Phase 1 - Demo Starter
echo ==============================================

echo Starting VERITAS Server...
start cmd /k "python cli.py serve"

echo Opening Dashboard in browser...
start "" "d:\dice\veritas\ui\dashboard.html"

echo Waiting for server to initialize...
timeout /t 2 /nobreak > nul

echo Running simulation...
start cmd /k "python cli.py simulate"

echo Done! Watch the dashboard for incoming signals.
