#!/usr/bin/env python3
"""
シンプルなコンポーネントテスト
"""

import asyncio
import sys
from pathlib import Path

# プロジェクトのルートディレクトリを Python パスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.ai.gemini_client import GeminiClient
from src.ai.mock_processor import MockAIProcessor


async def test_simple_processing():
    """シンプルなメッセージ処理テスト（モック使用）"""
    print("🧪 シンプルなメッセージ処理テストを開始...")
    
    # モックプロセッサーを使用
    try:
        mock_processor = MockAIProcessor()
        
        test_messages = [
            "TEST: 今日は良い天気でした。",
            "TEST: プロジェクトの進捗確認。",
            "TEST: 支出記録：食費 30,000 円",
        ]
        
        results = []
        
        for i, content in enumerate(test_messages, 1):
            print(f"\n 📝 テストメッセージ {i}: {content}")
            
            try:
                result = await mock_processor.process_text(content)
                results.append({
                    'message': content,
                    'success': True,
                    'result': result
                })
                # AIProcessingResult オブジェクトの属性にアクセス
                category_info = result.category.category.value if result.category else 'Unknown'
                print(f"✅ 処理成功: {category_info}")
                
            except Exception as e:
                results.append({
                    'message': content,
                    'success': False,
                    'error': str(e)
                })
                print(f"❌ 処理失敗: {e}")
        
        # 結果のサマリー
        successful = sum(1 for r in results if r['success'])
        total = len(results)
        print(f"\n 📊 テスト結果: {successful}/{total} 成功")
        
        return results
        
    except Exception as e:
        print(f"❌ 初期化エラー: {e}")
        return []


if __name__ == "__main__":
    results = asyncio.run(test_simple_processing())
    
    if results:
        print(f"\n 🎯 テスト完了！")
        for result in results:
            if result['success']:
                res = result['result']
                # CategoryResult オブジェクトから ProcessingCategory を取得
                category = res.category.category.value if res.category else 'Unknown'
                # SummaryResult オブジェクトから summary を取得
                summary_text = res.summary.summary if res.summary else 'No summary'
                print(f"  - カテゴリ: {category}, 要約: {summary_text}...")
    else:
        print(f"\n 💥 テストに失敗しました")