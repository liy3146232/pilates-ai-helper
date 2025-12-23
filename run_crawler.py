import os
import requests
import json
from datetime import datetime

# 你的监控关键词，从文件读取
def load_keywords():
    try:
        with open('config/frequency_words.txt', 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except:
        return ["普拉提", "体态矫正", "产后修复"]  # 默认关键词

def send_to_feishu(message, webhook_url):
    """发送消息到飞书机器人"""
    headers = {'Content-Type': 'application/json'}
    data = {
        "msg_type": "text",
        "content": {
            "text": message
        }
    }
    try:
        response = requests.post(webhook_url, headers=headers, data=json.dumps(data))
        return response.status_code == 200
    except:
        return False

def main():
    print("=== 普拉提热点监控开始 ===")
    
    # 1. 加载关键词
    keywords = load_keywords()
    print(f"监控关键词: {keywords}")
    
    # 2. 检查推送配置
    webhook_url = os.environ.get('FEISHU_WEBHOOK_URL') or os.environ.get('DINGTALK_WEBHOOK_URL')
    
    if not webhook_url:
        print("错误：未配置推送机器人Webhook！请到仓库Settings > Secrets中配置。")
        return
    
    # 3. 模拟获取到热点（这里是示例，实际会接入爬虫）
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mock_hot_news = f"【普拉提热点监控】{current_time}\n\n✅ 系统运行成功！\n🔍 监控关键词: {', '.join(keywords)}\n\n接下来将开始实时监控小红书、抖音等平台的普拉提相关内容。"
    
    print(mock_hot_news)
    
    # 4. 发送推送
    if 'feishu' in webhook_url:
        platform = '飞书'
    elif 'dingtalk' in webhook_url:
        platform = '钉钉'
    else:
        platform = '机器人'
    
    if send_to_feishu(mock_hot_news, webhook_url):
        print(f"✅ 测试消息已成功发送到{platform}！")
    else:
        print(f"❌ 发送到{platform}失败，请检查Webhook地址。")

if __name__ == '__main__':
    main()
