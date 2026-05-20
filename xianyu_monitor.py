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
