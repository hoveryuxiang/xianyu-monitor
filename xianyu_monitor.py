import requests
import json
import os
import re
from datetime import datetime
from github import Github

# ========== 配置区域 ==========
SEND_KEY = os.environ.get("SEND_KEY", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO_NAME = os.environ.get("GITHUB_REPOSITORY", "")
ISSUE_TITLE = "闲鱼监控列表"  # 固定的Issue标题
PRICE_FILE = "data/price_record.json"
# ============================


def get_watch_items_from_issue():
    """
    从GitHub Issue读取商品监控列表
    Issue中的格式示例：
    
    商品ID | 商品名称 | 当前价格
    1234567890 | iPhone 14 Pro | 5000
    0987654321 | 索尼相机 | 3000
    
    或者简单格式：
    - 1234567890 (iPhone 14 Pro) 5000
    """
    if not GITHUB_TOKEN or not REPO_NAME:
        print("缺少GitHub配置，使用默认商品列表")
        return get_default_items()
    
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        
        # 查找指定标题的Issue
        issues = repo.get_issues(state='open', title=ISSUE_TITLE)
        issue = None
        for iss in issues:
            if iss.title == ISSUE_TITLE:
                issue = iss
                break
        
        if not issue:
            print(f"未找到标题为 '{ISSUE_TITLE}' 的Issue，正在创建...")
            issue = repo.create_issue(
                title=ISSUE_TITLE,
                body=get_issue_template()
            )
            print(f"已创建Issue: {issue.html_url}")
            return []
        
        # 解析Issue内容
        content = issue.body
        items = parse_items_from_text(content)
        
        if items:
            print(f"从Issue读取到 {len(items)} 个商品")
            for item in items:
                print(f"  - {item['name']} (ID: {item['id']}) 价格: ¥{item['last_price']}")
        else:
            print("Issue中未找到有效商品，请按格式填写")
        
        return items
        
    except Exception as e:
        print(f"读取Issue失败: {e}")
        return get_default_items()


def get_issue_template():
    """返回Issue的模板内容"""
    return """# 闲鱼商品监控列表

请按以下格式填写你要监控的商品（用空格或|分隔）：

或者使用简单格式：
## 如何获取商品ID？
1. 打开闲鱼App
2. 找到你想监控的商品
3. 点击分享 → 复制链接
4. 链接中的 id= 后面数字就是商品ID

## 管理商品
- **添加**：在上面列表中添加一行
- **修改**：修改价格或名称
- **删除**：删除对应行

程序会每小时检查一次价格变化，降价时会发微信通知。
"""


def parse_items_from_text(text):
    """从文本中解析商品信息"""
    items = []
    
    # 格式1：ID | 名称 | 价格
    pattern1 = r'(\d{10,})\s*[|]\s*([^|\n]+)\s*[|]\s*(\d+(?:\.\d+)?)'
    matches1 = re.findall(pattern1, text)
    for match in matches1:
        items.append({
            "id": match[0].strip(),
            "name": match[1].strip(),
            "last_price": float(match[2])
        })
    
    # 格式2：- ID (名称) 价格
    pattern2 = r'-\s*(\d{10,})\s*\(([^)]+)\)\s*(\d+(?:\.\d+)?)'
    matches2 = re.findall(pattern2, text)
    for match in matches2:
        items.append({
            "id": match[0].strip(),
            "name": match[1].strip(),
            "last_price": float(match[2])
        })
    
    # 格式3：ID 名称 价格（空格分隔）
    if not items:
        lines = text.strip().split('\n')
        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 3 and parts[0].isdigit() and len(parts[0]) >= 10:
                try:
                    price = float(parts[-1])
                    name = ' '.join(parts[1:-1])
                    items.append({
                        "id": parts[0],
                        "name": name,
                        "last_price": price
                    })
                except ValueError:
                    continue
    
    return items


def get_default_items():
    """默认商品列表（当Issue读取失败时使用）"""
    return [
        {"id": "1234567890", "name": "示例商品1", "last_price": 5000},
        {"id": "0987654321", "name": "示例商品2", "last_price": 3000},
    ]


def send_wechat_message(title, content):
    """通过Server酱发送微信消息"""
    if not SEND_KEY:
        print("未配置SEND_KEY，跳过发送")
        return False
    
    url = f"https://sctapi.ftqq.com/{SEND_KEY}.send"
    data = {"title": title, "desp": content}
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
    
    注意：闲鱼没有公开API，这里需要你选择方案：
    1. 第三方API（推荐，稳定）
    2. 模拟请求（免费但不稳定）
    3. 手动更新价格
    """
    # TODO: 这里替换为实际的价格获取逻辑
    # 当前返回None表示获取失败
    return None


def check_price_changes():
    """检查所有商品价格变化"""
    print(f"[{datetime.now()}] 开始检查价格...")
    
    watch_items = get_watch_items_from_issue()
    if not watch_items:
        print("没有配置任何商品，请创建Issue或编辑默认列表")
        return
    
    price_history = load_price_history()
    
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
            
            title = f"💰 {item_name} 降价了！"
            content = f"""
### 商品：{item_name}
- **原价**：¥{last_price}
- **现价**：¥{current_price}
- **降价**：¥{drop_amount}（{drop_percent:.1f}%）

[点击查看商品](https://2.taobao.com/item.htm?id={item_id})
            """
            send_wechat_message(title, content)
        
        price_history[item_id] = {
            "name": item_name,
            "last_price": current_price,
            "update_time": str(datetime.now())
        }
    
    save_price_history(price_history)
    print(f"[{datetime.now()}] 价格检查完成")


def create_issue_if_not_exists():
    """确保Issue存在（首次运行时自动创建）"""
    if not GITHUB_TOKEN or not REPO_NAME:
        return
    
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        
        issues = repo.get_issues(state='all', title=ISSUE_TITLE)
        for iss in issues:
            if iss.title == ISSUE_TITLE:
                if iss.state == 'closed':
                    print(f"发现已关闭的Issue，正在重新打开...")
                    iss.edit(state='open')
                return
        
        # 创建新Issue
        repo.create_issue(
            title=ISSUE_TITLE,
            body=get_issue_template()
        )
        print(f"已创建商品管理Issue，请访问仓库Issues页面填写商品")
        
    except Exception as e:
        print(f"创建Issue失败: {e}")


def main():
    print("=" * 50)
    print("闲鱼降价监控机器人（Issue管理版）")
    print("=" * 50)
    
    # 确保Issue存在
    create_issue_if_not_exists()
    
    # 读取商品并检查价格
    check_price_changes()
    
    print("=" * 50)
    print("提示：在仓库Issues中编辑「闲鱼监控列表」即可管理商品")
    print("=" * 50)


if __name__ == "__main__":
    main()
