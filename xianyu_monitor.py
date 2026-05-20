import requests
import json
import os
import time
import hmac
import hashlib
import base64
import urllib.parse
from datetime import datetime

# ========== 配置区域 ==========
# 钉钉机器人配置（从环境变量读取）
DINGTALK_WEBHOOK = os.environ.get("DINGTALK_WEBHOOK", "")
DINGTALK_SECRET = os.environ.get("DINGTALK_SECRET", "")

# 监控商品配置
CONFIG_FILE = "config.json"
PRICE_FILE = "data/price_record.json"
# ============================


def send_dingtalk_message(title, content):
    """
    通过钉钉自定义机器人发送消息到钉钉群
    """
    if not DINGTALK_WEBHOOK or not DINGTALK_SECRET:
        print("❌ 钉钉机器人配置缺失，请检查 GitHub Secrets")
        print("   需要配置: DINGTALK_WEBHOOK 和 DINGTALK_SECRET")
        return False

    # 1. 生成签名
    timestamp = str(round(time.time() * 1000))
    secret_enc = DINGTALK_SECRET.encode('utf-8')
    string_to_sign = '{}\n{}'.format(timestamp, DINGTALK_SECRET)
    string_to_sign_enc = string_to_sign.encode('utf-8')
    hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
    
    # 2. 拼接完整的请求地址
    full_url = f"{DINGTALK_WEBHOOK}&timestamp={timestamp}&sign={sign}"
    
    # 3. 构建消息内容
    headers = {'Content-Type': 'application/json'}
    data = {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": f"## {title}\n\n{content}"
        }
    }
    
    try:
        response = requests.post(full_url, headers=headers, json=data, timeout=10)
        result = response.json()
        if result.get("errcode") == 0:
            print(f"[{datetime.now()}] ✅ 钉钉消息发送成功")
            return True
        else:
            print(f"[{datetime.now()}] ❌ 钉钉消息发送失败: {result}")
            return False
    except Exception as e:
        print(f"[{datetime.now()}] ❌ 发送异常: {e}")
        return False


def load_config():
    """加载商品配置"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            return config.get("watch_items", [])
    except FileNotFoundError:
        print("错误：找不到 config.json 文件")
        print("请创建 config.json 文件，格式如下：")
        print('''
{
    "watch_items": [
        {
            "id": "商品ID",
            "name": "商品名称",
            "last_price": 5000
        }
    ]
}
        ''')
        return []
    except json.JSONDecodeError:
        print("错误：config.json 格式不正确")
        return []


def load_price_history():
    """加载价格历史记录"""
    os.makedirs("data", exist_ok=True)
    
    try:
        with open(PRICE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_price_history(history):
    """保存价格历史记录"""
    with open(PRICE_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def get_item_price(item_id):
    """
    获取商品当前价格
    
    注意：闲鱼没有公开API，这里需要你选择一种方式：
    
    方案1：使用第三方API（推荐）
        - 阿里云API市场搜索"闲鱼商品详情"
        - 获取AppKey后在这里调用
    
    方案2：手动更新价格（简单）
        - 自己在 config.json 里修改 last_price
        - 程序只负责发送降价通知
    
    当前返回 None 表示未实现价格获取
    你也可以直接返回一个测试价格来验证整个流程：
        return 4800  # 假设降价了
    """
    # TODO: 这里替换为实际的价格获取逻辑
    # 临时返回 None，表示暂未获取到价格
    return None


def check_price_changes():
    """检查所有商品价格变化"""
    print(f"[{datetime.now()}] 开始检查价格...")
    
    watch_items = load_config()
    if not watch_items:
        print("没有配置任何商品，请编辑 config.json")
        return
    
    price_history = load_price_history()
    price_changed = False
    changed_items = []
    
    for item in watch_items:
        item_id = item["id"]
        item_name = item["name"]
        current_price = get_item_price(item_id)
        
        if current_price is None:
            print(f"  [{item_name}] 获取价格失败，跳过")
            continue
        
        history = price_history.get(item_id, {})
        last_price = history.get("last_price", item.get("last_price", current_price))
        
        print(f"  [{item_name}] 上次: ¥{last_price} → 当前: ¥{current_price}")
        
        if current_price < last_price:
            drop_amount = last_price - current_price
            drop_percent = (drop_amount / last_price) * 100
            price_changed = True
            changed_items.append({
                "name": item_name,
                "last_price": last_price,
                "current_price": current_price,
                "drop_amount": drop_amount,
                "drop_percent": drop_percent,
                "url": f"https://2.taobao.com/item.htm?id={item_id}"
            })
        
        price_history[item_id] = {
            "name": item_name,
            "last_price": current_price,
            "update_time": str(datetime.now())
        }
    
    save_price_history(price_history)
    
    # 如果有降价，发送通知
    if price_changed:
        title = f"💰 发现 {len(changed_items)} 个商品降价！"
        content = ""
        for item in changed_items:
            content += f"**{item['name']}**\n"
            content += f"- 原价：¥{item['last_price']}\n"
            content += f"- 现价：¥{item['current_price']}\n"
            content += f"- 降价：¥{item['drop_amount']}（{item['drop_percent']:.1f}%）\n"
            content += f"[点击查看]({item['url']})\n\n"
        
        send_dingtalk_message(title, content)
    else:
        print(f"[{datetime.now()}] 未发现价格变化")


def test_connection():
    """测试钉钉连接"""
    print("=" * 50)
    print("测试钉钉机器人连接...")
    print("=" * 50)
    
    if not DINGTALK_WEBHOOK or not DINGTALK_SECRET:
        print("❌ 钉钉配置缺失！")
        print("\n请在 GitHub Secrets 中配置：")
        print("  - DINGTALK_WEBHOOK: 钉钉机器人的 Webhook 地址")
        print("  - DINGTALK_SECRET: 钉钉机器人的加签密钥")
        print("\n获取方式：")
        print("  1. 打开钉钉，创建群聊")
        print("  2. 群设置 → 机器人 → 添加机器人 → 自定义")
        print("  3. 复制 Webhook 地址和加签密钥")
        return False
    
    title = "✅ 闲鱼监控机器人已启动"
    content = f"""**启动时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**配置状态**：
- Webhook：已配置
- 加签密钥：已配置

**下一步**：
1. 编辑 config.json 添加要监控的商品
2. 实现 get_item_price 函数获取价格（或手动更新价格）
3. 等待定时任务运行

---

*如果你收到这条消息，说明钉钉配置正确！*"""
    
    return send_dingtalk_message(title, content)


def main():
    print("=" * 50)
    print("闲鱼降价监控机器人（钉钉版）")
    print("=" * 50)
    
    # 测试钉钉连接
    test_connection()
    
    # 检查价格变化
    check_price_changes()
    
    print("=" * 50)
    print("运行完成")
    print("=" * 50)


if __name__ == "__main__":
    main()
