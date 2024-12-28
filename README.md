## このリポジトリについて
救急車出動と天候状況との関連を解析する研究課題において、分析基盤を提供するものである。  
## 環境構築
inputディレクトリに、消防データを入れる
- pipの場合
```sh
pip install -U pip
pip install .
```
- uvの場合
```sh  
uv sync
```
vscodeで実行する場合には、あらかじめ以下の拡張機能を入れておく  
- Data Wrangler
- Jupyter
- Python

## eda(探索的データ分析)でデータの特徴を掴む
notebook/eda.ipynbを開く。  
vscodeで仮想環境名は.venvである。
vscodeのData Wranglerで大まかに表が見れる。
## uvの導入方法
- Linux/macos
    ```sh
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

- macos (Homebrew)
  ```sh
  brew install uv
  ```
