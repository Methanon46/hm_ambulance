## このリポジトリについて
浜松市消防局が所有する救急車出動と天候状況との関連を解析する研究課題において、分析基盤を提供するものである。  
## 環境構築
- pipの場合
```sh
pip install .
```
- uvの場合
```sh  
uv sync
```

# eda(探索的データ分析)でデータの特徴を掴む
notebook/eda.ipynbを開く。  
vscodeで仮想環境名は.venvである。

## uvの導入方法
- Linux
    ```sh
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

- macos (Homebrew)
  ```sh
  brew install uv
  ```
