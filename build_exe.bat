@echo off
REM Builds dist\DermaScan\DermaScan.exe  (use Python 3.10-3.12)
if not exist venv ( py -m venv venv )
call venv\Scripts\activate
pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm --clean --windowed --name DermaScan ^
  --add-data "assets;assets" --add-data "model;model" ^
  --add-data "disease_feed.json;." --add-data "labels.txt;." ^
  --collect-all ai_edge_litert ^
  main.py
echo.
echo Done. Run dist\DermaScan\DermaScan.exe
pause
