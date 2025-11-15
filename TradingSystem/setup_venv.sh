#!/bin/bash
# TradingSystem 仮想環境セットアップスクリプト

echo "=== TradingSystem 仮想環境セットアップ ==="
echo ""

# Python 3のバージョン確認
if ! command -v python3 &> /dev/null; then
    echo "エラー: Python 3 がインストールされていません"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo "検出されたPythonバージョン: $PYTHON_VERSION"
echo ""

# 仮想環境の作成
echo "仮想環境を作成中..."
python3 -m venv venv

if [ ! -d "venv" ]; then
    echo "エラー: 仮想環境の作成に失敗しました"
    exit 1
fi

echo "仮想環境の作成完了"
echo ""

# 仮想環境の有効化
echo "仮想環境を有効化中..."
source venv/bin/activate

# pipのアップグレード
echo "pipをアップグレード中..."
pip install --upgrade pip

# 依存パッケージのインストール
echo ""
echo "依存パッケージをインストール中..."
pip install -r requirements.txt

echo ""
echo "=== セットアップ完了 ==="
echo ""
echo "仮想環境を有効化するには:"
echo "  source venv/bin/activate"
echo ""
echo "システムを実行するには:"
echo "  python run_trading_system.py"
echo ""
echo "仮想環境を無効化するには:"
echo "  deactivate"
