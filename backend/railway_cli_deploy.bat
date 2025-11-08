@echo off
echo 🚀 Railway CLI Deployment for AI Education Backend
echo ==================================================

echo.
echo Current directory: %CD%
echo Repository: ZkwareDAO/aiguru
echo.

echo Step 1: Railway Project Creation
echo ---------------------------------
echo Please select a workspace when prompted and press Enter
echo Recommended: Choose the workspace you prefer
echo.

pause

echo Initializing Railway project...
railway init --name ai-education-backend

echo.
echo Step 2: Adding Database Services
echo --------------------------------
echo Adding PostgreSQL...
railway add postgresql

echo Adding Redis...
railway add redis

echo.
echo Step 3: Setting Environment Variables
echo ------------------------------------
echo Setting basic configuration...

railway variables set ENVIRONMENT=production
railway variables set DEBUG=false
railway variables set LOG_LEVEL=INFO
railway variables set HOST=0.0.0.0
railway variables set PORT=8000

echo Setting security keys...
railway variables set SECRET_KEY=7g608QhbIm9irZ_zo8n219PRiY6ldm5WoHrL-OaR9tA
railway variables set JWT_SECRET_KEY=ldFtOUlsLF7KN3-LHYduTo5rGgVJVzHAKLnX9BQvQmI
railway variables set JWT_ALGORITHM=HS256

echo Setting optimization flags...
railway variables set ENABLE_UNIFIED_AGENT=true
railway variables set ENABLE_SMART_CACHE=true
railway variables set DEFAULT_GRADING_MODE=fast

echo.
echo ⚠️  IMPORTANT: You still need to set OPENROUTER_API_KEY
echo Get your API key from: https://openrouter.ai/keys
echo Then run: railway variables set OPENROUTER_API_KEY=your-key-here
echo.

echo Step 4: Deploying Application
echo ------------------------------
railway up

echo.
echo 🎉 Deployment initiated!
echo Check Railway dashboard for deployment status.
echo.

pause