@echo off
echo ========================================================
echo Google Apps Script Automated Deployment (via Clasp)
echo ========================================================
echo.
echo Step 1: Logging into Google (opens browser for authentication)...
call npx @google/clasp login
echo.
echo Step 2: Navigating to deploy folder and creating Apps Script project...
cd apps_script_deploy
call npx @google/clasp create --type webapp --title "India MF Institutional Accumulation & Value Research Scanner" --rootDir .
echo.
echo Step 3: Pushing 681KB Dashboard HTML and Code.js to Google Apps Script...
call npx @google/clasp push
echo.
echo Step 4: Deploying as Web App...
call npx @google/clasp deploy --description "v3.0 Live Deployment"
echo.
echo ========================================================
echo Deployment Complete! To open your live site, run:
echo npx @google/clasp open
echo ========================================================
pause
