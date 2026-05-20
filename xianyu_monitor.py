import requests
import json
import os
import time
import base64
import hashlib
from datetime import datetime

# ========== 配置区域 ==========
# 企业微信配置（从环境变量读取）
CORP_ID = os.environ.get("CORP_ID", "")           # 企业ID
AGENT_ID = os.environ.get("AGENT_ID", "")         # 应用AgentId
CORP_SECRET = os.environ.get("CORP_SECRET", "")   # 应用Secret
TO_USER = os.environ.get("TO_USER", "")           # 接收消息的成员ID（你的用户ID）

# 监控商品配置
CONFIG_FILE = "config.json"
PRICE_FILE = "data/price_record.json"
# ============================


class WeChatWorkBot:
    """企业微信机器人（自建应用方式）"""
    
    def __init__(self, corp_id, agent_id, corp_secret):
        self.corp_id = corp_id
        self.agent_id = agent_id
        self.corp_secret = corp_secret
        self.access_token = None
        self.token_expires_at = 0
    
    def get_access_token(self):
        """获取 access_token（有效期2小时）"""
        # 如果 token 还在有效期内，直接使用
        if self.access_token and time.time() < self.token_expires_at:
            return self.access_token
        
        url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken"
        params = {
            "corpid": self.corp_id,
            "corpsecret": self.corp_secret
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            result = response.json()
            
            if result.get("errcode") == 0:
                self.access_token = result.get("access_token")
                # 设置过期时间（提前5分钟刷新）
                self.token_expires_at = time.time() + result.get("expires_in", 7200) - 300
                print(f"[{datetime.now()}] 获取 access_token 成功")
                return self.access_token
            else:
                print(f"获取 access_token 失败: {result}")
                return None
        except Exception as e:
            print(f"获取 access_token 异常: {e}")
            return None
    
    def send_text(self, content, to_user=None):
        """发送文本消息"""
        token = self.get_access_token()
        if not token:
            return False
        
        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"
        
        # 默认发送给配置的成员
        if to_user is None:
            to_user = TO_USER
        
        data = {
            "touser": to_user,
            "msgtype": "text",
            "agentid": int(self.agent_id),
            "text": {
                "content": content
            },
            "safe": 0
        }
        
        try:
            response = requests.post(url, json=data, timeout=10)
            result = response.json()
            
            if result.get("errcode") == 0:
                print(f"[{datetime.now()}] 企业微信消息发送成功")
                return True
            else:
                print(f"[{datetime.now()}] 企业微信消息发送失败: {result}")
                return False
        except Exception as e:
            print(f"发送消息异常: {e}")
            return False
    
    def send_markdown(self, content, to_user=None):
        """发送 Markdown 格式消息（支持更丰富的样式）"""
        token = self.get_access_token()
        if not token:
            return False
        
        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"
        
        if to_user is None:
            to_user = TO_USER
        
        data = {
            "touser": to_user,
            "msgtype": "markdown",
            "agentid": int(self.agent_id),
            "markdown": {
                "content": content
            }
        }
        
        try:
            response = requests.post(url, json=data, timeout=10)
            result = response.json()
            
            if result.get("errcode") == 0:
                print(f"[{datetime.now()}] 企业微信消息发送成功 (Markdown)")
                return True
            else:
                print(f"[{datetime.now()}] 企业微信消息发送失败: {result}")
                return False
        except Exception as e:
            print(f"发送消息异常: {e}")
            return False


# ========== 以下是你之前的功能代码，稍作修改 ==========

def load_config():
    """加载商品配置"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            return config.get("watch_items", [])
    except FileNotFoundError:
        print("错误：找不到 config.json 文件")
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
    
    注意：这里需要你选择价格获取方式
    当前返回 None 表示未实现
    """
    # TODO: 这里替换为实际的价格获取逻辑
    return None


def check_price_changes(bot):
    """检查所有商品价格变化"""
    print(f"[{datetime.now()}] 开始检查价格...")
    
    watch_items = load_config()
    if not watch_items:
        print("没有配置任何商品，请编辑 config.json")
        return
    
    price_history = load_price_history()
    price_changed = False
    changed_items = []  # 记录降价的商品
    
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
        # 发送合并通知（把所有降价商品放在一条消息里）
        title = f"💰 发现 {len(changed_items)} 个商品降价！"
        content = f"### {title}\n\n"
        for item in changed_items:
            content += f"**{item['name']}**\n"
            content += f"- 原价：¥{item['last_price']}\n"
            content += f"- 现价：¥{item['current_price']}\n"
            content += f"- 降价：¥{item['drop_amount']}（{item['drop_percent']:.1f}%）\n"
            content += f"[点击查看]({item['url']})\n\n"
        
        bot.send_markdown(content)
    else:
        print(f"[{datetime.now()}] 未发现价格变化")


def test_connection(bot):
    """测试企业微信连接"""
    print("测试企业微信连接...")
    content = f"""## ✅ 闲鱼监控机器人已启动

**启动时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**配置状态**：
- 企业ID：{CORP_ID[:5]}...
- 应用AgentId：{AGENT_ID}
- 接收成员：{TO_USER}

**下一步**：
1. 编辑 config.json 添加要监控的商品
2. 实现 get_item_price 函数获取价格
3. 等待定时任务运行

---

*如果收到这条消息，说明企业微信配置正确！*"""
    
    return bot.send_markdown(content)


def main():
    print("=" * 50)
    print("闲鱼降价监控机器人（企业微信版）")
    print("=" * 50)
    
    # 检查配置
    if not CORP_ID or not AGENT_ID or not CORP_SECRET:
        print("错误：请先配置企业微信环境变量！")
        print("需要在 GitHub Secrets 中配置：")
        print("  - CORP_ID")
        print("  - AGENT_ID")
        print("  - CORP_SECRET")
        print("  - TO_USER")
        return
    
    if not TO_USER:
        print("警告：未配置 TO_USER，消息将发送到企业微信全员")
    
    # 初始化机器人
    bot = WeChatWorkBot(CORP_ID, AGENT_ID, CORP_SECRET)
    
    # 测试连接
    test_connection(bot)
    
    # 检查价格变化
    check_price_changes(bot)
    
    print("=" * 50)
    print("运行完成")
    print("=" * 50)


if __name__ == "__main__":
    main()
