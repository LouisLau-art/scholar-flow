import sys
from typing import List, Dict

def calculate_accuracy(ai_results: List[Dict], golden_dataset: List[Dict]) -> float:
    """
    计算 AI 查重结果与基准数据集的匹配准确率
    
    中文注释:
    1. 遵循章程: 用于验证成功标准 SC-001。
    2. 对比 AI 提取的相似度得分与专家人工校正后的得分。
    3. 如果误差在 +/- 0.05 以内，则视为准确。
    """
    if not ai_results:
        return 0.0
    
    correct_count = 0
    total = len(golden_dataset)
    
    for i in range(total):
        ai_score = ai_results[i]['similarity_score']
        golden_score = golden_dataset[i]['similarity_score']
        
        # 允许 5% 的容差
        if abs(ai_score - golden_score) <= 0.05:
            correct_count += 1
            
    accuracy = correct_count / total
    return accuracy

if __name__ == "__main__":
    # 模拟验证过程
    mock_ai = [{"similarity_score": 0.32}, {"similarity_score": 0.15}]
    mock_golden = [{"similarity_score": 0.30}, {"similarity_score": 0.14}]
    
    acc = calculate_accuracy(mock_ai, mock_golden)
    print(f"当前查重准确率: {acc*100:.2f}%")
    
    if acc >= 0.85:
        print("验证通过: 满足 SC-001 标准")
    else:
        print("验证失败: 未达到 85% 准确率要求")
        sys.exit(1)
