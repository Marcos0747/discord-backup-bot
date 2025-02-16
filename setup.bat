@echo off
echo Setting up Discord Backup Bot...

:: Crear entorno virtual
python -m venv venv

:: Instalar dependencias
call venv\Scripts\activate
pip install -r requirements.txt

:: Crear config.py si no existe
if not exist "config.py" (
    echo token = "YOUR_TOKEN_HERE" > config.py
    echo Edit the config.py file and add your token!
)

echo Setup completed!
echo 1. Edit config.py with your bot token
echo 2. Run the bot with: python main.py
pause