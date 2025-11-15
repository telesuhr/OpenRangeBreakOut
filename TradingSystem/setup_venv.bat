@echo off
REM TradingSystem 仮想環境セットアップスクリプト (Windows)

echo === TradingSystem 仮想環境セットアップ ===
echo.

REM Python 3のバージョン確認
python --version >nul 2>&1
if errorlevel 1 (
    echo エラー: Python 3 がインストールされていません
    exit /b 1
)

python --version
echo.

REM 仮想環境の作成
echo 仮想環境を作成中...
python -m venv venv

if not exist "venv" (
    echo エラー: 仮想環境の作成に失敗しました
    exit /b 1
)

echo 仮想環境の作成完了
echo.

REM 仮想環境の有効化
echo 仮想環境を有効化中...
call venv\Scripts\activate.bat

REM pipのアップグレード
echo pipをアップグレード中...
python -m pip install --upgrade pip

REM 依存パッケージのインストール
echo.
echo 依存パッケージをインストール中...
pip install -r requirements.txt

echo.
echo === セットアップ完了 ===
echo.
echo 仮想環境を有効化するには:
echo   venv\Scripts\activate.bat
echo.
echo システムを実行するには:
echo   python run_trading_system.py
echo.
echo 仮想環境を無効化するには:
echo   deactivate
