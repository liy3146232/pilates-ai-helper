import os
import requests
import json
import re
from datetime import datetime

# ---------- 配置区 ----------
ENABLE_BAIDU = True   # 百度热搜，主力数据源
ENABLE_ZHIHU = False  # 已关闭
ENABLE_XHS = False    # 已关闭
# 可选：配置你的AI服务（例如DeepSeek）
# 访问 https://platform.deepseek.com/ 获取API Key， 然后在此填入
# DEEPSEEK_API_KEY = "你的sk-xxx密钥"
# 若暂无，AI部分将输出模拟建议
# ---------------------------

def load_keywords():
    """加载关键词，并分离出核心词和长尾场景词"""
    core_keywords = []
    scene_keywords = []
    try:
        with open('config/frequency_words.txt', 'r', encoding='utf-8') as f:
            all_lines = [line.strip() for line in f if line.strip()]
        # 简单划分：前9个可能为你的核心业务词，后续为场景词
        core_keywords = all_lines[:9]
        scene_keywords = all_lines[9:]
        print(f"✅ 已加载核心业务词: {core_keywords}")
        print(f"✅ 已加载场景长尾词: {scene_keywords}")
        return core_keywords, scene_keywords
    except Exception as e:
        print(f"❌ 读取关键词文件失败: {e}")
        return ["普拉提", "健身"], ["锻炼", "健康"]

def fetch_baidu_hot(core_kws, scene_kws):
    """从百度热搜榜抓取并匹配关键词，返回结构化结果"""
    if not ENABLE_BAIDU:
        return []
    print("🔍 正在精准抓取百度热搜榜...")
    try:
        url = "https://top.baidu.com/board?tab=realtime"
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()

        # 优化的正则，更精准匹配热搜标题
        # 匹配模式：捕获热搜项容器内的标题文本
        pattern = re.compile(r'<div[^>]*class="[^"]*c-single-text-ellipsis[^"]*"[^>]*>([^<]+)</div>')
        hot_titles = pattern.findall(resp.text)
        
        # 去重并清理空白
        hot_titles = list(dict.fromkeys([t.strip() for t in hot_titles if t.strip()]))
        
        matched_news = []
        all_keywords = core_kws + scene_kws
        for title in hot_titles[:30]:  # 检查前30个热搜
            for kw in all_keywords:
                if kw in title:
                    matched_news.append({
                        "title": title,
                        "matched_keyword": kw,
                        "is_core": kw in core_kws
                    })
                    break  # 匹配到一个关键词即止
        
        print(f"   共扫描 {len(hot_titles)} 条热搜，命中 {len(matched_news)} 条。")
        return matched_news[:8]  # 最多返回8条
        
    except Exception as e:
        print(f"⚠️ 抓取百度热搜失败: {e}")
        return []

def ai_analyze_hotspot(hot_title, matched_keyword):
    """调用AI分析热点，生成创作建议（模拟/真实）"""
    # 如果你配置了真实的DEEPSEEK_API_KEY，可以取消下面注释使用真实API
    # return call_deepseek_api(hot_title, matched_keyword)
    
    # 模拟AI返回（即使没有API，也能看到效果）
    suggestions = [
        f"围绕『{hot_title}』，可以突出『{matched_keyword}』与都市白领时间碎片化的矛盾，标题示例：《工作再忙，5分钟{matched_keyword}跟练拯救你的颈椎》",
        f"结合热点『{hot_title}』，从“网红动作安全解析”角度切入，标题示例：《全网爆火的{matched_keyword}动作，真的适合你吗？》",
        f"将热点『{hot_title}』与“家庭场景”结合，标题示例：《宅家带娃也能做！3个亲子{matched_keyword}小游戏》"
    ]
    import random
    return random.choice(suggestions)

# 真实调用DeepSeek API的函数（备用，有Key时启用）
def call_deepseek_api(hot_title, keyword):
    api_key = os.environ.get("DEEPSEEK_API_KEY") # 或使用全局变量
    if not api_key:
        return "（请配置API Key以获取真实AI分析）"
    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    prompt = f"你是一个资深普拉提内容策划。热点新闻是『{hot_title}』，关联关键词是『{keyword}』。请直接生成一个适合小红书或抖音的短视频文案标题，要求吸引人并突出专业性。只返回标题本身。"
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 200
    }
    try:
        resp = requests.post(url, headers=headers, data=json.dumps(data), timeout=20)
        result = resp.json()
        return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"AI分析调用失败: {e}"

def send_to_feishu(message, webhook_url):
    """发送消息到飞书"""
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
    print("🚀 普拉提热点监控系统 - AI分析版")
    print("="*50)
    
    # 1. 加载关键词
    core_kws, scene_kws = load_keywords()
    all_kws = core_kws + scene_kws
    if not all_kws:
        print("❌ 关键词列表为空。")
        return
    
    # 2. 获取Webhook
    webhook_url = os.environ.get('FEISHU_WEBHOOK_URL')
    if not webhook_url:
        print("⚠️ 未找到飞书Webhook，将仅输出日志。")
    
    # 3. 执行抓取
    hot_news = fetch_baidu_hot(core_kws, scene_kws)
    
    # 4. 生成推送消息
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if hot_news:
        # 按匹配关键词类型排序，核心词匹配的在前
        hot_news.sort(key=lambda x: x['is_core'], reverse=True)
        
        message = f"🔥【普拉提热点监控】{current_time}\n\n"
        message += f"✅ 发现 {len(hot_news)} 条相关热搜：\n\n"
        
        for i, news in enumerate(hot_news, 1):
            ai_suggestion = ai_analyze_hotspot(news['title'], news['matched_keyword'])
            tag = "💎" if news['is_core'] else "🔍"
            message += f"{tag} {i}. {news['title']}\n"
            message += f"  匹配词: {news['matched_keyword']}\n"
            message += f"  💡 AI灵感: {ai_suggestion}\n\n"
        
        message += f"📊 监控词库: {len(all_kws)} 个\n"
        
    else:
    # --- 路径三：无热点时，启动“日常创意生成” ---
    message = f"💡【普拉提创意工坊】{current_time}\n\n"
    message += "📌 今日热搜暂无直接关联，为你生成专属创作灵感：\n\n"
    
    # 普拉提内容创意库
    content_ideas = [
        {
            "title": "经期舒缓普拉提序列",
            "desc": "结合当下节气/节日，设计一套适合生理期的舒缓动作，强调缓解腹痛与情绪调理。",
            "format": "图文教程 / 10分钟跟练视频"
        },
        {
            "title": "办公室人群的『手机脖』自救指南",
            "desc": "针对低头族，用毛巾或普拉提圈演示5个在办公椅上就能完成的微运动。",
            "format": "短视频教程 / 小红书图文对比（Before-After）"
        },
        {
            "title": "产后修复的三大认知误区",
            "desc": "科普‘盆底肌’、‘腹直肌分离’的正确恢复思路，破除‘越快越好’等常见误区。",
            "format": "科普长图文 / 与产科医生对谈视频"
        },
        {
            "title": "一根弹力带打造美背",
            "desc": "利用弹力带，设计一套针对圆肩驼背的家庭跟练方案，强调发力感和呼吸配合。",
            "format": "多机位跟练视频 / 动作分解GIF图"
        },
        {
            "title": "普拉提球の魔法：下背部深度放松",
            "desc": "展示如何用普拉提球进行下背部放松，针对久坐导致的腰酸。",
            "format": "ASMR风格放松视频 / 步骤详解图文"
        }
    ]
    
    import random
    selected = random.choice(content_ideas)
    
    message += f"🎯 **灵感主题**：{selected['title']}\n\n"
    message += f"📝 **内容角度**：{selected['desc']}\n\n"
    message += f"🎬 **推荐形式**：{selected['format']}\n\n"
    message += "---\n"
    message += f"📊 本次扫描了 {len(all_kws)} 个关键词，未在热搜中命中。系统将持续监控。"
    
    print(f"\n📨 消息预览:\n{'-'*30}\n{message}\n{'-'*30}")
    
    # 5. 推送
    if webhook_url:
        print("📤 正在推送...")
        if send_to_feishu(message, webhook_url):
            print("✅ 推送成功！")
        else:
            print("❌ 推送失败。")
    else:
        print("⏭️ 未配置Webhook，运行结束。")
    
    print("="*50)
    print("🏁 本次监控任务执行完毕。")

if __name__ == '__main__':
    main()
