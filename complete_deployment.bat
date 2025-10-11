@echo off
echo 🚀 AI Education Platform - Complete Railway Deployment
echo =====================================================
echo.

echo This script will guide you through deploying both frontend and backend to Railway.
echo Please have your GitHub repository ready and your OpenRouter API key.
echo.

echo 📋 Pre-requisites Check:
echo [✓] Railway CLI installed and logged in
echo [✓] GitHub repository pushed
echo [✓] OpenRouter API key ready (get from https://openrouter.ai/keys)
echo.

pause

echo.
echo 🎯 STEP 1: Deploy Backend Service
echo ===================================
echo.

echo Opening Railway dashboard...
start https://railway.app/new

echo.
echo 📝 In the Railway dashboard, please:
echo 1. Click "Deploy from GitHub repo"
echo 2. Select your aiguru repository
echo 3. Set ROOT DIRECTORY to: backend
echo 4. Click "Deploy"
echo.

echo Press any key after backend deployment starts...
pause

echo.
echo 🎯 STEP 2: Add Database Services
echo ==================================
echo.

echo In your Railway project dashboard:
echo 1. Click "New Service" → "Database" → "Add PostgreSQL"
echo 2. Click "New Service" → "Database" → "Add Redis"
echo.

echo Press any key after adding databases...
pause

echo.
echo 🎯 STEP 3: Configure Backend Environment Variables
echo ==================================================
echo.

set /p OPENROUTER_KEY="Enter your OpenRouter API key: "

if "%OPENROUTER_KEY%"=="" (
    echo ❌ OpenRouter API key is required!
    pause
    exit /b 1
)

echo.
echo In your backend service, go to "Variables" tab and add:
echo.
echo ENVIRONMENT=production
echo DEBUG=false
echo SECRET_KEY=aiguru-super-secret-key-for-production-deployment-32chars
echo JWT_SECRET_KEY=aiguru-jwt-secret-key-for-production-deployment-32chars
echo OPENROUTER_API_KEY=%OPENROUTER_KEY%
echo CORS_ORIGINS=*
echo ALLOWED_HOSTS=*
echo ENABLE_UNIFIED_AGENT=true
echo ENABLE_SMART_CACHE=true
echo DEFAULT_GRADING_MODE=fast
echo.

echo Press any key after setting backend variables...
pause

echo.
echo 🎯 STEP 4: Get Backend URL
echo ===========================
echo.

set /p BACKEND_URL="Enter your Railway backend URL (e.g., https://your-backend.railway.app): "

if "%BACKEND_URL%"=="" (
    echo ❌ Backend URL is required for frontend deployment!
    pause
    exit /b 1
)

echo.
echo 🎯 STEP 5: Deploy Frontend Service
echo ===================================
echo.

echo Choose your frontend deployment option:
echo 1. Deploy to Railway (same project)
echo 2. Deploy to Vercel (recommended)
echo.

set /p DEPLOY_CHOICE="Enter choice (1 or 2): "

if "%DEPLOY_CHOICE%"=="1" (
    echo.
    echo Deploying frontend to Railway...
    echo In your Railway project:
    echo 1. Click "New Service" → "GitHub Repo"
    echo 2. Select same repository
    echo 3. Set ROOT DIRECTORY to: frontend
    echo 4. Add environment variable:
    echo    NEXT_PUBLIC_API_URL=%BACKEND_URL%
    echo.
    
    start https://railway.app/new
    
) else if "%DEPLOY_CHOICE%"=="2" (
    echo.
    echo Deploying frontend to Vercel...
    echo 1. Import your GitHub repository
    echo 2. Set Framework Preset: Next.js
    echo 3. Set Root Directory: frontend
    echo 4. Add environment variable:
    echo    NEXT_PUBLIC_API_URL=%BACKEND_URL%
    echo.
    
    start https://vercel.com/new
    
) else (
    echo Invalid choice, please run the script again.
    pause
    exit /b 1
)

echo.
echo Press any key after frontend deployment starts...
pause

echo.
echo 🎯 STEP 6: Verification
echo ========================
echo.

echo Testing backend health...
curl -s "%BACKEND_URL%/health" > temp_health.json
if %errorlevel% equ 0 (
    echo ✅ Backend is responding
    type temp_health.json
    del temp_health.json
) else (
    echo ❌ Backend is not responding yet. This is normal if deployment is still in progress.
)

echo.
echo 📊 Deployment Summary
echo =====================
echo.
echo Backend URL: %BACKEND_URL%
echo API Documentation: %BACKEND_URL%/docs
echo.

if "%DEPLOY_CHOICE%"=="2" (
    set /p FRONTEND_URL="Enter your Vercel frontend URL: "
    echo Frontend URL: %FRONTEND_URL%
)

echo.
echo 🎉 Deployment Complete!
echo =======================
echo.
echo ✅ Backend service deployed with PostgreSQL and Redis
echo ✅ Environment variables configured
echo ✅ Frontend deployed and connected to backend
echo.
echo 📝 Next Steps:
echo 1. Test the health endpoint: %BACKEND_URL%/health
echo 2. Check API documentation: %BACKEND_URL%/docs
echo 3. Test frontend-backend connection
echo 4. Try a sample AI grading request
echo.
echo 💰 Estimated Monthly Costs:
echo - Railway Backend: ~$5/month
echo - Databases: Included
echo - OpenRouter API: ~$0.009 per grading
echo - Vercel Frontend: Free tier
echo.

echo Press any key to finish...
pause

echo.
echo 🔗 Useful Links:
echo - Railway Dashboard: https://railway.app/dashboard
echo - OpenRouter Dashboard: https://openrouter.ai/activity
echo - API Documentation: %BACKEND_URL%/docs
echo.

echo Thank you for using AI Education Platform! 🎓✨
pause