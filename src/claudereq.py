import pandas as pd
import re
from anthropic import Anthropic
import asyncio
from typing import List, Dict, Optional, Tuple
import time
from tqdm import tqdm
from pathlib import Path
import aiohttp
import logging
from datetime import datetime
import numpy as np
from collections import deque

# レート制限の管理用クラス
class RateLimiter:
    def __init__(self, requests_per_minute: int):
        self.requests_per_minute = requests_per_minute
        self.time_window = 60  # 60秒
        self.request_times = deque(maxlen=requests_per_minute)
    
    async def acquire(self):
        current_time = time.time()
        
        # 1分以上前のタイムスタンプを削除
        while self.request_times and current_time - self.request_times[0] >= self.time_window:
            self.request_times.popleft()
        
        # 現在のウィンドウ内のリクエスト数が制限に達している場合は待機
        if len(self.request_times) >= self.requests_per_minute:
            wait_time = self.time_window - (current_time - self.request_times[0])
            if wait_time > 0:
                await asyncio.sleep(wait_time)
        
        self.request_times.append(time.time())

# 拡張された臓器系統分類ルール
system_rules = {
    '循環器系': r'(心臓|血圧|不整脈|動悸|胸痛|心筋|血管|狭心|梗塞|心不全|脈|循環)',
    '呼吸器系': r'(肺|気管|呼吸|喘息|咳|痰|気胸|肋骨|呼吸困難|気道|喉頭)',
    '消化器系': r'(胃|腸|肝臓|胆嚢|膵臓|腹痛|嘔吐|下痢|便秘|吐血|消化管|食道)',
    '脳神経系': r'(脳|神経|意識|めまい|頭痛|痙攣|失神|麻痺|てんかん|意識障害)',
    '筋骨格系': r'(骨|関節|筋肉|腰痛|背部痛|捻挫|脱臼|骨折|打撲|外傷)',
    '泌尿器系': r'(腎臓|膀胱|尿|前立腺|排尿|水腎)',
    '内分泌系': r'(甲状腺|副腎|糖尿病|ホルモン|内分泌|代謝)',
    '血液系': r'(貧血|出血|白血球|血小板|凝固|溶血|血液)',
    '皮膚系': r'(皮膚|発疹|かゆみ|湿疹|蕁麻疹|熱傷|褥瘡)',
    '感染症': r'(感染|炎症|発熱|細菌|ウイルス|敗血症)',
    '精神系': r'(不安|抑うつ|精神|パニック|統合失調|躁)'
}

class PromptTemplate:
    def __init__(self, template_path: str):
        self.template = self._load_template(template_path)
        self._validate_template()
    
    def _load_template(self, template_path: str) -> str:
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Template file not found: {template_path}")
        except UnicodeDecodeError:
            raise ValueError("Template file must be UTF-8 encoded")
    
    def _validate_template(self):
        required_placeholders = ['{count}', '{diseases_list}']
        for placeholder in required_placeholders:
            if placeholder not in self.template:
                raise ValueError(f"Missing required placeholder: {placeholder}")
    
    def format(self, diseases: List[str]) -> str:
        diseases_list = "\n".join([f"{i+1}. {d}" for i, d in enumerate(diseases)])
        return self.template.format(
            count=len(diseases),
            diseases_list=diseases_list
        )

class DiseaseClassifier:
    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307"):
        self.anthropic = Anthropic(api_key=api_key)
        self.model = model
        self.rate_limiter = RateLimiter(requests_per_minute=50)
        self.logger = self._setup_logger()
        
    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger('DiseaseClassifier')
        logger.setLevel(logging.INFO)
        
        # ファイルハンドラーの設定
        fh = logging.FileHandler(f'classification_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        fh.setLevel(logging.INFO)
        
        # フォーマッターの設定
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        
        return logger

    async def classify_batch(self, batch: List[str], prompt_template: PromptTemplate) -> List[str]:
        await self.rate_limiter.acquire()
        
        try:
            prompt = prompt_template.format(batch)
            response = await self.anthropic.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            results = self._parse_response(response.content, len(batch))
            return results
        except Exception as e:
            self.logger.error(f"Error in batch classification: {str(e)}")
            return ['その他'] * len(batch)

    def _parse_response(self, response: str, expected_length: int) -> List[str]:
        results = ['その他'] * expected_length
        try:
            lines = [line.strip() for line in response.split('\n') if line.strip()]
            for line in lines:
                if '.' in line:
                    parts = line.split('.')
                    if len(parts) >= 2:
                        idx = int(parts[0].strip()) - 1
                        system = parts[1].strip()
                        if 0 <= idx < expected_length:
                            results[idx] = system
        except Exception as e:
            self.logger.error(f"Error parsing response: {str(e)}")
        return results

async def process_dataframe(
    df: pd.DataFrame,
    classifier: DiseaseClassifier,
    prompt_template: PromptTemplate,
    batch_size: int = 20
) -> Tuple[pd.DataFrame, Dict]:
    stats = {
        'total_records': len(df),
        'rule_based_classifications': 0,
        'api_classifications': 0,
        'errors': 0,
        'processing_time': 0
    }
    
    start_time = time.time()
    
    # ルールベースでの分類
    df['organ_system'] = df['傷病名'].apply(lambda x: classify_by_rules(x))
    stats['rule_based_classifications'] = len(df[df['organ_system'] != '要API判定'])
    
    # API判定が必要なケースの処理
    need_api = df[df['organ_system'] == '要API判定']
    need_api_indices = need_api.index
    
    if len(need_api) > 0:
        batches = [need_api['傷病名'].iloc[i:i+batch_size].tolist() 
                  for i in range(0, len(need_api), batch_size)]
        
        results = []
        with tqdm(total=len(batches), desc="Processing batches") as pbar:
            for batch in batches:
                batch_results = await classifier.classify_batch(batch, prompt_template)
                results.extend(batch_results)
                pbar.update(1)
        
        df.loc[need_api_indices, 'organ_system'] = results
        stats['api_classifications'] = len(need_api)
    
    stats['processing_time'] = time.time() - start_time
    stats['errors'] = len(df[df['organ_system'] == 'エラー'])
    
    return df, stats

def classify_by_rules(name: str) -> str:
    """ルールベースでの分類"""
    if pd.isna(name):
        return 'その他'
    
    name = str(name)
    matched_systems = set()
    
    for system, pattern in system_rules.items():
        if re.search(pattern, name):
            matched_systems.add(system)
    
    if len(matched_systems) == 1:
        return matched_systems.pop()
    elif len(matched_systems) > 1:
        # 複数のシステムにマッチする場合はAPI判定に回す
        return '要API判定'
    return '要API判定'

async def main():
    # 設定
    API_KEY = 'YOUR_API_KEY'
    BATCH_SIZE = 20
    INPUT_FILE = '傷病名一覧.csv'
    OUTPUT_FILE = 'classified_diseases_haiku.csv'
    TEMPLATE_FILE = 'prompt_template.txt'
    
    try:
        # 初期化
        classifier = DiseaseClassifier(api_key=API_KEY)
        prompt_template = PromptTemplate(TEMPLATE_FILE)
        
        # データ読み込み
        df = pd.read_csv(INPUT_FILE, encoding='utf-8')
        
        # データ処理
        processed_df, stats = await process_dataframe(
            df, classifier, prompt_template, BATCH_SIZE
        )
        
        # 結果の保存
        processed_df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8')
        
        # 統計情報の表示と保存
        print("\n=== Processing Statistics ===")
        print(f"Total records: {stats['total_records']:,}")
        print(f"Rule-based classifications: {stats['rule_based_classifications']:,}")
        print(f"API classifications: {stats['api_classifications']:,}")
        print(f"Errors: {stats['errors']:,}")
        print(f"Processing time: {stats['processing_time']:.2f} seconds")
        
        # 分類結果の集計
        system_counts = processed_df['organ_system'].value_counts()
        print("\n=== Classification Results ===")
        for system, count in system_counts.items():
            print(f"{system}: {count:,}")
        
    except Exception as e:
        print(f"Error in main execution: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())