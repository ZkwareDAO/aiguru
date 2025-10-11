@echo off
echo Starting AI Education Platform...

echo.
echo [1/4] Starting backend services with Docker...
cd backend
docker-compose up -d

echo.
echo [2/4] Waiting for services to start...
timeout /t 10

echo.
echo [3/4] Starting frontend development server...
cd ..\frontend
start cmd /k "npm run dev"

echo.
echo [4/4] Opening browser...
timeout /t 5
start http://localhost:3000

echo.
echo ✅ AI Education Platform is starting!
echo Frontend: http://localhost:3000
echo Backend API: http://localhost:8000/docs
echo.
echo Press any key to stop all services...
pause

echo Stopping services...
cd ..\backend
docker-compose down

echo Services stopped.
pause