import os
import sys
import requests
import json
from datetime import datetime

# ---------- 配置区 (你可以修改这里) ----------
# 如果某个源不稳定，可以临时将其设置为 False
ENABLE_BAIDU = True
ENABLE_ZHIHU = True
ENABLE_XHS = True  # 新增：小红书开关。如果抓取失败，可暂时设为 False 跳过。
# ------------------------------------------

def load_keywords():
    """从你的配置文件加载关键词"""
    keywords = []
    try:
        with open('config/frequency_words.txt', 'r', encoding='utf-8') as f:
            keywords = [line.strip() for line in f if line.strip()]
        print(f"✅ 已加载监控关键词: {keywords}")
    except Exception as e:
        print(f"❌ 读取关键词文件失败，使用默认关键词。错误: {e}")
        keywords = ["普拉提", "健身", "瑜伽", "体态矫正"]  # 默认备选
    return keywords

def fetch_baidu_hot(keywords):
    """从百度热搜榜抓取"""
    if not ENABLE_BAIDU:
        return []
    print("🔍 正在抓取百度热搜...")
    try:
        url = "https://top.baidu.com/board?tab=realtime"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        
        # 简易查找：在实际热门标题文本附近匹配关键词
        matched = []
        for kw in keywords:
            if kw in resp.text:
                # 找到关键词，记录一个简单结果（实际开发应解析具体标题）
                matched.append(f"在百度热搜中发现关键词『{kw}』")
        # 限制返回数量，避免消息过长
        return matched[:5]
    except Exception as e:
        print(f"⚠️ 抓取百度热搜失败: {e}")
        return []

def fetch_zhihu_hot(keywords):
    """从知乎热榜抓取（通过官方API）"""
    if not ENABLE_ZHIHU:
        return []
    print("🔍 正在抓取知乎热榜...")
    try:
        url = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=50"
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        
        matched = []
        for item in data.get('data', []):
            title = item.get('target', {}).get('title', '')
            for kw in keywords:
                if kw in title:
                    matched.append(f"知乎热榜: {title}")
                    break  # 避免一个标题因含多个关键词重复添加
        return matched[:5]
    except Exception as e:
        print(f"⚠️ 抓取知乎热榜失败: {e}")
        return []

def fetch_xiaohongshu_search(keywords):
    """尝试从小红书网页版搜索页抓取（请注意Robots协议和法律风险）"""
    if not ENABLE_XHS:
        return []
    print("🔍 正在尝试抓取小红书搜索...")
    results = []
    for kw in keywords:
        try:
            # 对关键词进行URL编码
            search_url = f"https://www.xiaohongshu.com/search_result?keyword={requests.utils.quote(kw)}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
            }
            resp = requests.get(search_url, headers=headers, timeout=15)
            print(f"   小红书请求状态码: {resp.status_code}")  # 关键调试信息
            resp.raise_for_status()
            
            # 初步检查：如果页面返回成功，则视为抓取步骤成功（内容解析是下一步）
            if resp.status_code == 200:
                # 简单判断关键词是否出现在返回的HTML中（可能是动态渲染的占位符）
                if kw in resp.text:
                    results.append(f"小红书搜索『{kw}』: 请求成功，发现关键词")
                else:
                    results.append(f"小红书搜索『{kw}』: 请求成功，但页面内容可能为动态加载")
                
        except Exception as e:
            # 更详细的错误输出，便于诊断
            print(f"⚠️ 抓取小红书关键词『{kw}』失败: {type(e).__name__} - {str(e)}")
            continue
    return results

def send_to_feishu(message, webhook_url):
    """发送消息到飞书机器人"""
    headers = {'Content-Type': 'application/json'}
    data = {"msg_type": "text", "content": {"text": message}}
    try:
        r = requests.post(webhook_url, headers=headers, data=json.dumps(data), timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"❌ 发送飞书消息失败: {e}")
        return False

def main():
    print("\n" + "="*50)
    print("🚀 普拉提热点监控系统 - 真实抓取版 (含小红书测试)")
    print("="*50)
    
    # 1. 加载关键词
    keywords = load_keywords()
    if not keywords:
        print("❌ 关键词列表为空，请检查 config/frequency_words.txt 文件。")
        return
    
    # 2. 获取Webhook地址
    webhook_url = os.environ.get('FEISHU_WEBHOOK_URL') or os.environ.get('DINGTALK_WEBHOOK_URL')
    if not webhook_url:
        print("❌ 未找到推送机器人配置！请检查 Secrets 设置。")
        # 这里不退出，仍执行抓取，便于在日志中查看抓取结果
        webhook_url = None
    
    # 3. 执行真实抓取
    all_results = []
    if ENABLE_BAIDU:
        all_results.extend(fetch_baidu_hot(keywords))
    if ENABLE_ZHIHU:
        all_results.extend(fetch_zhihu_hot(keywords))
    if ENABLE_XHS:  # 新增：调用小红书抓取
        all_results.extend(fetch_xiaohongshu_search(keywords))
    
    # 4. 生成推送消息
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if all_results:
        message = f"🔥【普拉提热点监控】{current_time}\n\n✅ 今日发现 {len(all_results)} 条相关线索：\n"
        message += "\n".join([f"• {item}" for item in all_results])
        message += f"\n\n📊 监控关键词: {', '.join(keywords)}"
    else:
        message = f"📭【普拉提热点监控】{current_time}\n\n⏳ 今日在监控范围内未发现相关线索。\n\n📊 监控关键词: {', '.join(keywords)}"
    
    print(f"\n📨 生成消息体预览:\n{'-'*30}\n{message}\n{'-'*30}")
    
    # 5. 推送消息
    if webhook_url:
        print("📤 正在推送消息到飞书/钉钉...")
        if send_to_feishu(message, webhook_url):
            print("✅ 消息推送成功！")
        else:
            print("❌ 消息推送失败，请检查网络或Webhook地址。")
    else:
        print("⏭️ 未配置Webhook，本次运行仅完成抓取测试。")
    
    print("="*50)
    print("🏁 本次监控任务执行完毕。")

if __name__ == '__main__':
    main()
