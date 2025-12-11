# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/goofish/help.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。


import re
from urllib.parse import urlparse, parse_qs
from typing import Optional

from model.m_goofish import ItemUrlInfo


def parse_item_info_from_url(url: str) -> ItemUrlInfo:
    """
    从闲鱼商品URL中解析商品信息
    
    URL格式示例:
    - https://www.goofish.com/item?id=123456789
    - https://www.goofish.com/item/123456789
    
    Args:
        url: 商品URL
        
    Returns:
        ItemUrlInfo: 包含商品ID等信息的对象
    """
    parsed = urlparse(url)
    
    # 尝试从查询参数中获取ID
    query_params = parse_qs(parsed.query)
    if 'id' in query_params:
        item_id = query_params['id'][0]
    else:
        # 尝试从路径中获取ID
        path_match = re.search(r'/item/(\d+)', parsed.path)
        if path_match:
            item_id = path_match.group(1)
        else:
            raise ValueError(f"无法从URL中解析商品ID: {url}")
    
    return ItemUrlInfo(item_id=item_id)


def get_item_url(item_id: str) -> str:
    """
    根据商品ID生成商品URL
    
    Args:
        item_id: 商品ID
        
    Returns:
        str: 商品URL
    """
    return f"https://www.goofish.com/item?id={item_id}"


def get_search_url(keyword: str, page: int = 1) -> str:
    """
    生成搜索URL
    
    Args:
        keyword: 搜索关键词
        page: 页码
        
    Returns:
        str: 搜索URL
    """
    from urllib.parse import quote
    encoded_keyword = quote(keyword)
    return f"https://www.goofish.com/search?q={encoded_keyword}"


def extract_price(price_str: str) -> Optional[float]:
    """
    从价格字符串中提取数字价格
    
    Args:
        price_str: 价格字符串，如 "¥99.00" 或 "99元"
        
    Returns:
        float: 数字价格，解析失败返回None
    """
    if not price_str:
        return None
    
    # 移除货币符号和单位
    price_clean = re.sub(r'[¥￥元]', '', price_str)
    try:
        return float(price_clean.strip())
    except ValueError:
        return None
