import requests
import json
import time
import os
from datetime import datetime

# ========== 配置区域 ==========
# 从GitHub Secrets读取密钥
SEND_KEY = os.environ.get("SEND_KEY", "")

# 你要监控的闲鱼商品ID列表
# 商品ID获取方法：闲鱼商品分享链接中 id= 后面的数字
WATCH_ITEMS = [
    {"id": "1234567890", "name": "示例商品1", "last_price": 5000},
    {"id": "0987654321", "name": "示例商品2", "last_price": 3000},
]

# 存储文件路径
PRICE_FILE = "data/price_record.json"
# ============================


def send_wechat_message(title, content):
    """通过Server酱发送微信消息"""
    if not SEND_KEY:
        print("未配置SEND_KEY，跳过发送")
        return False
    
    url = f"https://sctapi.ftqq.com/{SEND_KEY}.send"
    data = {
        "title": title,
        "desp": content
    }
    try:
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            print(f"[{datetime.now()}] 微信消息发送成功")
            return True
        else:
            print(f"[{datetime.now()}] 微信消息发送失败: {response.text}")
            return False
    except Exception as e:
        print(f"[{datetime.now()}] 发送异常: {e}")
        return False


def load_price_history():
    """加载价格历史记录"""
    # 确保data目录存在
    os.makedirs("data", exist_ok=True)
    
    try:
        with open(PRICE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # 初始化历史价格
        history = {}
        for item in WATCH_ITEMS:
            history[item["id"]] = {
                "name": item["name"],
                "last_price": item["last_price"],
                "lowest_price": item["last_price"],
                "update_time": str(datetime.now())
            }
        return history


def save_price_history(history):
    """保存价格历史记录"""
    with open(PRICE_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def get_item_price(item_id):
    """
    获取商品当前价格
    
    注意：闲鱼没有官方公开API，这里提供两种方式
    
    方式1：模拟请求（免费但不稳定）
    方式2：使用第三方API（稳定但需要付费，约0.01元/次）
    
    当前使用的是方式1的模拟请求框架
    如果需要稳定使用，请替换为第三方API
    """
    # 模拟请求的headers
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    
    url = f"https://2.taobao.com/item.htm?id={item_id}"
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        
        # 这里需要解析HTML获取价格
        # 由于闲鱼页面价格是通过JS动态加载的，简单的HTML解析很难获取到
        # 返回None表示获取失败
        
        # 如果你使用第三方API，在这里替换
        # 例如：
        # api_url = f"https://api.example.com/item?id={item_id}&appkey=YOUR_KEY"
        # response = requests.get(api_url)
        # return response.json()["price"]
        
        return None  # 模拟请求通常返回None
        
    except Exception as e:
        print(f"获取商品{item_id}价格失败: {e}")
        return None


def send_test_message():
    """发送测试消息"""
    title = "✅ 闲鱼监控机器人已启动"
    content = f"""
### 监控状态
- 启动时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 监控商品数：{len(WATCH_ITEMS)}
- 通知方式：Server酱

### 监控商品列表
"""
    for item in WATCH_ITEMS:
        content += f"- {item['name']} (ID: {item['id']})\n"
    
    send_wechat_message(title, content)


def check_price_changes():
    """检查所有商品价格变化"""
    print(f"[{datetime.now()}] 开始检查价格...")
    
    # 发送开始检查的通知（可选，避免消息太多可以注释掉）
    # send_wechat_message("🔍 开始价格检查", f"时间：{datetime.now()}")
    
    price_history = load_price_history()
    price_changed = False
    
    for item in WATCH_ITEMS:
        item_id = item["id"]
        item_name = item["name"]
        
        # 获取当前价格
        current_price = get_item_price(item_id)
        
        if current_price is None:
            print(f"  [{item_name}] 获取价格失败，跳过")
            continue
        
        # 获取历史记录
        history = price_history.get(item_id, {})
        last_price = history.get("last_price", current_price)
        lowest_price = history.get("lowest_price", current_price)
        
        print(f"  [{item_name}] 上次: ¥{last_price} → 当前: ¥{current_price}")
        
        # 检测降价
        if current_price < last_price:
            drop_amount = last_price - current_price
            drop_percent = (drop_amount / last_price) * 100
            
            title = f"💰 {item_name} 降价了！"
            content = f"""
### 商品：{item_name}
- **原价**：¥{last_price}
- **现价**：¥{current_price}
- **降价**：¥{drop_amount}（{drop_percent:.1f}%）
- **时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

[点击查看商品](https://2.taobao.com/item.htm?id={item_id})
            """
            send_wechat_message(title, content)
            
            # 更新最低价
            if current_price < lowest_price:
                lowest_price = current_price
            
            price_changed = True
        
        # 更新历史记录
        price_history[item_id] = {
            "name": item_name,
            "last_price": current_price,
            "lowest_price": lowest_price,
            "update_time": str(datetime.now())
        }
    
    # 保存历史记录
    save_price_history(price_history)
    
    if not price_changed:
        print(f"[{datetime.now()}] 未发现价格变化")
    
    print(f"[{datetime.now()}] 价格检查完成")


def main():
    """主函数"""
    print("=" * 50)
    print("闲鱼降价监控机器人启动")
    print(f"监控商品数: {len(WATCH_ITEMS)}")
    print(f"通知方式: {'已配置' if SEND_KEY else '未配置'}")
    print("=" * 50)
    
    # 发送启动通知
    send_test_message()
    
    # 执行一次检查
    check_price_changes()


if __name__ == "__main__":
    main()
