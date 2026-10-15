
@echo off
setlocal
title Network AIOps Launcher

REM Start all commands from the project root folder.
cd /d "%~dp0"

REM Python environment used for this project.
set "PYTHON=D:\Python Programs\venv\Scripts\python.exe"

echo.
echo ==========================================
echo       Network AIOps - Startup
echo ==========================================
echo.

REM Check Python environment.
if not exist "%PYTHON%" (
    echo ERROR: Python was not found at:
    echo %PYTHON%
    echo.
    pause
    exit /b 1
)

REM Check dashboard file.
if not exist "src\dashboard.py" (
    echo ERROR: src\dashboard.py was not found.
    pause
    exit /b 1
)

REM Check MLflow database at the correct project-root path.
if not exist "mlflow.db" (
    echo ERROR: MLflow database was not found.
    echo Expected: %CD%\mlflow.db
    pause
    exit /b 1
)

REM Start Kafka, Prometheus, and Grafana.
echo [1/4] Starting Docker services...
docker compose up -d
if errorlevel 1 (
    echo ERROR: Docker Compose failed. Check Docker Desktop.
    pause
    exit /b 1
)

echo.
echo Waiting 10 seconds for Kafka to initialize...
timeout /t 10 /nobreak >nul

REM Start the MLflow-backed Kafka consumer.
echo [2/4] Opening the MLflow Kafka consumer...
start "Network AIOps - MLflow Consumer" powershell.exe -NoExit -Command "Set-Location -LiteralPath '%CD%'; & '%PYTHON%' '.\src\kafka_consumer.py' --model-source mlflow --group-id network-aiops-mlflow"

REM Start FastAPI.
echo.
echo [3/4] Opening FastAPI...
start "Network AIOps - FastAPI" powershell.exe -NoExit -Command "Set-Location -LiteralPath '%CD%'; & '%PYTHON%' -m uvicorn src.api:app --host 127.0.0.1 --port 8000"

echo.
echo Waiting 3 seconds for the API to start...
timeout /t 3 /nobreak >nul

REM Start Streamlit dashboard.
echo [4/4] Opening Streamlit dashboard...
start "Network AIOps - Dashboard" powershell.exe -NoExit -Command "Set-Location -LiteralPath '%CD%'; & '%PYTHON%' -m streamlit run '.\src\dashboard.py'"

echo.
echo ==========================================
echo Startup commands have been launched.
echo ==========================================
echo.
echo Keep the consumer, FastAPI, and dashboard
echo terminal windows open.
echo.
echo Dashboard:  http://localhost:8501
echo API docs:   http://127.0.0.1:8000/docs
echo API health: http://127.0.0.1:8000/health
echo Prometheus: http://127.0.0.1:9090
echo Grafana:    http://127.0.0.1:3000
echo.
echo To generate 5 sample events, run:
echo "%PYTHON%" .\src\kafka_producer.py --count 5 --interval 1 --anomaly-every 2
echo.
pause
endlocal
