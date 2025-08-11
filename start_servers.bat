@echo off
echo Starting Desktop Automation AI Servers...
echo.
echo This will start both:
echo 1. Streamlit UI on http://localhost:8501
echo 2. FastAPI Server on http://localhost:8000
echo.
echo API Documentation will be available at: http://localhost:8000/docs
echo.

REM Check if virtual environment exists
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate

REM Install requirements
echo Installing/updating requirements...
pip install -r dev-requirements.txt

REM Start both servers in separate windows
echo Starting servers...

start "Streamlit App" cmd /k "venv\Scripts\activate && python -m streamlit run app.py --server.port=8501"
start "FastAPI Server" cmd /k "venv\Scripts\activate && set FASTAPI_RELOAD=false && python api_server.py"

echo.
echo Both servers are starting in separate windows.
echo.
echo Streamlit UI: http://localhost:8501
echo FastAPI Server: http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo.
echo Press any key to exit this window...
pause >nul