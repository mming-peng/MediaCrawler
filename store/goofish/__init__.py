# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/store/goofish/__init__.py
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


from typing import Dict, List

import config
from base.base_crawler import AbstractStore
from tools import utils
from var import source_keyword_var

from ._store_impl import *


class GoofishStoreFactory:
    """闲鱼数据存储工厂"""
    
    STORES = {
        "csv": GoofishCsvStoreImplement,
        "db": GoofishDbStoreImplement,
        "json": GoofishJsonStoreImplement,
        "sqlite": GoofishSqliteStoreImplement,
        "excel": GoofishExcelStoreImplement,
    }
    
    @staticmethod
    def create_store() -> AbstractStore:
        store_class = GoofishStoreFactory.STORES.get(config.SAVE_DATA_OPTION)
        if not store_class:
            raise ValueError(
                "[GoofishStoreFactory.create_store] Invalid save option, "
                "only supported csv or db or json or sqlite or excel ..."
            )
        return store_class()


async def update_goofish_item(item: Dict):
    """
    更新闲鱼商品数据
    
    Args:
        item: 商品数据
    """
    item_id = item.get("item_id")
    
    local_db_item = {
        "item_id": item.get("item_id"),
        "title": item.get("title", ""),
        "price": item.get("price", ""),
        "desc": item.get("desc", ""),
        "seller_name": item.get("seller_name", ""),
        "images": ",".join(item.get("images", [])) if isinstance(item.get("images"), list) else item.get("images", ""),
        "item_url": item.get("item_url", f"https://www.goofish.com/item?id={item_id}"),
        "source_keyword": source_keyword_var.get(),
        "last_modify_ts": utils.get_current_timestamp(),
    }
    
    utils.logger.info(f"[store.goofish.update_goofish_item] goofish item: {local_db_item}")
    await GoofishStoreFactory.create_store().store_content(local_db_item)


async def batch_update_goofish_items(items: List[Dict]):
    """
    批量更新闲鱼商品数据
    
    Args:
        items: 商品数据列表
    """
    if not items:
        return
    for item in items:
        await update_goofish_item(item)
