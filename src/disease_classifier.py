import pandas as pd
import re
import json
import matplotlib.pyplot as plt
import seaborn as sns
import japanize_matplotlib
import os

class DiseaseClassifier:
    """
    傷病名を指定されたカテゴリに分類するクラス
    """
    def __init__(self, patterns_file):
        """
        初期化：分類パターンJSONファイルを読み込む
        
        Args:
            patterns_file (str): 分類パターンが定義されたJSONファイルのパス
        """
        # パターンファイルの読み込み
        with open(patterns_file, 'r', encoding='utf-8') as f:
            self.rules = json.load(f)
            
        # コンパイル済み正規表現パターンのキャッシュ
        self._compiled_patterns = {}
        for category, pattern in self.rules.items():
            self._compiled_patterns[category] = re.compile(pattern)
    
    def normalize_disease_name(self, name):
        """
        傷病名を正規化する（括弧内の詳細情報を除去、疑いの表現を統一など）
        
        Args:
            name (str): 元の傷病名
            
        Returns:
            str: 正規化された傷病名
        """
        if pd.isna(name):
            return "不明"
        
        # 数値を文字列に変換
        if isinstance(name, (int, float)):
            return str(int(name))
            
        name = str(name)
        
        # 括弧内の詳細情報を除去
        name = re.sub(r'[\(（].*?[\)）]', '', name)
        # 疑いの表現を統一
        name = re.sub(r'(の疑い|疑い|疑|と思われる)', '疑い', name)
        
        return name.strip()
    
    def classify(self, disease_name):
        """
        傷病名をカテゴリに分類する
        
        Args:
            disease_name (str): 分類する傷病名
            
        Returns:
            str: 分類されたカテゴリ名
        """
        normalized_name = self.normalize_disease_name(disease_name)
        
        # 各カテゴリのパターンと照合
        for category, pattern in self._compiled_patterns.items():
            if pattern.search(normalized_name):
                return category
                
        return 'その他'
    
    def get_all_categories(self):
        """
        定義されているすべてのカテゴリを取得
        
        Returns:
            list: カテゴリのリスト
        """
        return list(self.rules.keys()) + ['その他']
    
    def add_category(self, category_name, pattern):
        """
        新しいカテゴリとパターンを追加
        
        Args:
            category_name (str): 追加するカテゴリ名
            pattern (str): 追加する正規表現パターン
        """
        self.rules[category_name] = pattern
        self._compiled_patterns[category_name] = re.compile(pattern)
    
    def save_patterns(self, output_file):
        """
        現在の分類パターンをJSONファイルに保存
        
        Args:
            output_file (str): 保存先ファイルパス
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.rules, f, ensure_ascii=False, indent=2)


# メイン処理を行う関数
def analyze_disease_data(csv_file, patterns_file, output_dir=None):
    """
    傷病名データを分析する
    
    Args:
        csv_file (str): 分析対象のCSVファイルパス
        patterns_file (str): 分類パターンが定義されたJSONファイルのパス
        output_dir (str, optional): 結果を保存するディレクトリ
    """
    # 出力ディレクトリの設定
    if output_dir is None:
        output_dir = os.path.dirname(csv_file)
    os.makedirs(output_dir, exist_ok=True)
    
    # データ読み込み
    df = pd.read_csv(csv_file, encoding='utf-8')
    print(f"データ総数: {len(df):,}件")
    
    # 分類器の初期化
    classifier = DiseaseClassifier(patterns_file)
    
    # 傷病名の正規化と分類
    df['normalized_name'] = df['傷病名'].apply(classifier.normalize_disease_name)
    df['category'] = df['傷病名'].apply(classifier.classify)
    
    # 分類結果の集計
    category_counts = df['category'].value_counts()
    
    # 結果の表示
    print("\n=== 分類結果 ===")
    print("\n各カテゴリの件数:")
    for category, count in category_counts.items():
        print(f"{category}: {count:,}件")
    
    # API呼び出し必要数の計算
    api_calls_needed = int(category_counts.get('その他', 0))
    api_calls_percentage = (api_calls_needed / len(df)) * 100
    
    print(f"\n必要なAPI呼び出し回数: {api_calls_needed:,}回")
    print(f"全サンプルに対する割合: {api_calls_percentage:.2f}%")
    
    # 可視化
    plt.figure(figsize=(12, 8))
    sns.barplot(x=category_counts.values, y=category_counts.index)
    plt.title('傷病名カテゴリ別の件数')
    plt.xlabel('件数')
    plt.ylabel('カテゴリ')
    plt.tight_layout()
    
    # グラフの保存
    plt.savefig(os.path.join(output_dir, 'disease_categories.png'))
    
    # その他に分類された例の確認
    print("\n=== 「その他」に分類された傷病名の例（先頭20件）===")
    other_examples = df[df['category'] == 'その他']['傷病名'].value_counts().head(20)
    for disease, count in other_examples.items():
        print(f"{disease}: {count:,}件")
    
    # 分類結果のCSV出力
    output_file = os.path.join(output_dir, 'classified_diseases.csv')
    df.to_csv(output_file, encoding='utf-8', index=False)
    print(f"\n分類結果を {output_file} に保存しました。")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='傷病名データの分類・分析を行います')
    parser.add_argument('--csv', required=True, help='分析対象のCSVファイルパス')
    parser.add_argument('--patterns', default='disease_categories.json', 
                        help='分類パターンが定義されたJSONファイルのパス')
    parser.add_argument('--output', help='結果を保存するディレクトリ')
    
    args = parser.parse_args()
    
    analyze_disease_data(args.csv, args.patterns, args.output)