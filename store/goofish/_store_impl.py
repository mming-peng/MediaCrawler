# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/store/goofish/_store_impl.py
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


import csv
import json
import os
import pathlib
from typing import Dict

import aiofiles

import config
from base.base_crawler import AbstractStore
from tools import utils
from var import crawler_type_var


def calculate_number_of_files(directory: str) -> int:
    """获取目录下文件数量"""
    if not os.path.exists(directory):
        return 0
    return len([f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))])


class GoofishCsvStoreImplement(AbstractStore):
    """CSV存储实现"""
    
    csv_store_path: str = "data/goofish"
    
    def make_save_file_name(self, store_type: str) -> str:
        """生成保存文件名"""
        return f"{self.csv_store_path}/{crawler_type_var.get()}_{store_type}_{utils.get_current_date()}.csv"
    
    async def save_data_to_csv(self, data: Dict, store_type: str):
        """保存数据到CSV文件"""
        pathlib.Path(self.csv_store_path).mkdir(parents=True, exist_ok=True)
        file_name = self.make_save_file_name(store_type=store_type)
        file_exists = os.path.exists(file_name)
        
        async with aiofiles.open(file_name, mode="a", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=data.keys())
            if not file_exists:
                await f.write(",".join(data.keys()) + "\n")
            await f.write(",".join([str(v) for v in data.values()]) + "\n")
    
    async def store_content(self, content_item: Dict):
        """存储商品内容"""
        await self.save_data_to_csv(data=content_item, store_type="items")
    
    async def store_comment(self, comment_item: Dict):
        """存储评论"""
        await self.save_data_to_csv(data=comment_item, store_type="comments")
    
    async def store_creator(self, creator: Dict):
        """存储卖家信息"""
        await self.save_data_to_csv(data=creator, store_type="sellers")


class GoofishDbStoreImplement(AbstractStore):
    """数据库存储实现"""
    
    async def store_content(self, content_item: Dict):
        """存储商品内容到数据库"""
        from database.db import insert_or_update_item
        await insert_or_update_item(
            table_name="goofish_item",
            item_id=content_item.get("item_id"),
            content_item=content_item
        )
    
    async def store_comment(self, comment_item: Dict):
        """存储评论到数据库"""
        from database.db import insert_or_update_item
        await insert_or_update_item(
            table_name="goofish_comment",
            item_id=comment_item.get("comment_id"),
            content_item=comment_item
        )
    
    async def store_creator(self, creator: Dict):
        """存储卖家信息到数据库"""
        from database.db import insert_or_update_item
        await insert_or_update_item(
            table_name="goofish_seller",
            item_id=creator.get("user_id"),
            content_item=creator
        )


class GoofishJsonStoreImplement(AbstractStore):
    """JSON存储实现"""
    
    json_store_path: str = "data/goofish"
    
    def make_save_file_name(self, store_type: str) -> str:
        """生成保存文件名"""
        return f"{self.json_store_path}/{crawler_type_var.get()}_{store_type}_{utils.get_current_date()}.json"
    
    async def save_data_to_json(self, data: Dict, store_type: str):
        """保存数据到JSON文件"""
        pathlib.Path(self.json_store_path).mkdir(parents=True, exist_ok=True)
        file_name = self.make_save_file_name(store_type=store_type)
        
        # 读取现有数据
        existing_data = []
        if os.path.exists(file_name):
            async with aiofiles.open(file_name, mode="r", encoding="utf-8") as f:
                content = await f.read()
                if content:
                    existing_data = json.loads(content)
        
        # 添加新数据
        existing_data.append(data)
        
        # 写入文件
        async with aiofiles.open(file_name, mode="w", encoding="utf-8") as f:
            await f.write(json.dumps(existing_data, ensure_ascii=False, indent=2))
    
    async def store_content(self, content_item: Dict):
        """存储商品内容"""
        await self.save_data_to_json(data=content_item, store_type="items")
    
    async def store_comment(self, comment_item: Dict):
        """存储评论"""
        await self.save_data_to_json(data=comment_item, store_type="comments")
    
    async def store_creator(self, creator: Dict):
        """存储卖家信息"""
        await self.save_data_to_json(data=creator, store_type="sellers")


class GoofishSqliteStoreImplement(AbstractStore):
    """SQLite存储实现"""
    
    async def store_content(self, content_item: Dict):
        """存储商品内容到SQLite"""
        from database.db import insert_or_update_item
        await insert_or_update_item(
            table_name="goofish_item",
            item_id=content_item.get("item_id"),
            content_item=content_item
        )
    
    async def store_comment(self, comment_item: Dict):
        """存储评论到SQLite"""
        from database.db import insert_or_update_item
        await insert_or_update_item(
            table_name="goofish_comment",
            item_id=comment_item.get("comment_id"),
            content_item=comment_item
        )
    
    async def store_creator(self, creator: Dict):
        """存储卖家信息到SQLite"""
        from database.db import insert_or_update_item
        await insert_or_update_item(
            table_name="goofish_seller",
            item_id=creator.get("user_id"),
            content_item=creator
        )


class GoofishExcelStoreImplement(AbstractStore):
    """Excel存储实现"""
    
    async def store_content(self, content_item: Dict):
        """存储商品内容到Excel"""
        from store.excel_store_base import ExcelStoreBase
        file_name = f"data/goofish/{crawler_type_var.get()}_items_{utils.get_current_date()}.xlsx"
        pathlib.Path("data/goofish").mkdir(parents=True, exist_ok=True)
        excel_store = ExcelStoreBase(file_name)
        excel_store.append_row("items", content_item)
    
    async def store_comment(self, comment_item: Dict):
        """存储评论到Excel"""
        from store.excel_store_base import ExcelStoreBase
        file_name = f"data/goofish/{crawler_type_var.get()}_comments_{utils.get_current_date()}.xlsx"
        pathlib.Path("data/goofish").mkdir(parents=True, exist_ok=True)
        excel_store = ExcelStoreBase(file_name)
        excel_store.append_row("comments", comment_item)
    
    async def store_creator(self, creator: Dict):
        """存储卖家信息到Excel"""
        from store.excel_store_base import ExcelStoreBase
        file_name = f"data/goofish/{crawler_type_var.get()}_sellers_{utils.get_current_date()}.xlsx"
        pathlib.Path("data/goofish").mkdir(parents=True, exist_ok=True)
        excel_store = ExcelStoreBase(file_name)
        excel_store.append_row("sellers", creator)
