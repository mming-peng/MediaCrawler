# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/goofish/core.py
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


import asyncio
import os
from typing import Dict, List, Optional

from playwright.async_api import (
    BrowserContext,
    BrowserType,
    Page,
    Playwright,
    async_playwright,
)

import config
from base.base_crawler import AbstractCrawler
from model.m_goofish import ItemUrlInfo
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
from store import goofish as goofish_store
from tools import utils
from tools.cdp_browser import CDPBrowserManager
from var import crawler_type_var, source_keyword_var

from .client import GoofishClient
from .field import SearchSortType
from .help import parse_item_info_from_url
from .login import GoofishLogin


class GoofishCrawler(AbstractCrawler):
    """闲鱼爬虫"""
    
    context_page: Page
    goofish_client: GoofishClient
    browser_context: BrowserContext
    cdp_manager: Optional[CDPBrowserManager]
    
    def __init__(self) -> None:
        self.index_url = "https://www.goofish.com"
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        self.cdp_manager = None
        self.ip_proxy_pool = None
    
    async def start(self) -> None:
        """启动爬虫"""
        playwright_proxy_format, httpx_proxy_format = None, None
        if config.ENABLE_IP_PROXY:
            self.ip_proxy_pool = await create_ip_pool(config.IP_PROXY_POOL_COUNT, enable_validate_ip=True)
            ip_proxy_info: IpInfoModel = await self.ip_proxy_pool.get_proxy()
            playwright_proxy_format, httpx_proxy_format = utils.format_proxy_info(ip_proxy_info)
        
        async with async_playwright() as playwright:
            # 根据配置选择启动模式
            if config.ENABLE_CDP_MODE:
                utils.logger.info("[GoofishCrawler] 使用CDP模式启动浏览器")
                self.browser_context = await self.launch_browser_with_cdp(
                    playwright,
                    playwright_proxy_format,
                    self.user_agent,
                    headless=config.CDP_HEADLESS,
                )
            else:
                utils.logger.info("[GoofishCrawler] 使用标准模式启动浏览器")
                chromium = playwright.chromium
                self.browser_context = await self.launch_browser(
                    chromium,
                    playwright_proxy_format,
                    self.user_agent,
                    headless=config.HEADLESS,
                )
                # stealth.min.js 用于防止网站检测爬虫
                await self.browser_context.add_init_script(path="libs/stealth.min.js")
            
            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto(self.index_url)
            
            # 创建API客户端
            self.goofish_client = await self.create_goofish_client(httpx_proxy_format)
            
            # 检查登录状态
            if not await self.goofish_client.pong():
                login_obj = GoofishLogin(
                    login_type=config.LOGIN_TYPE,
                    login_phone="",
                    browser_context=self.browser_context,
                    context_page=self.context_page,
                    cookie_str=config.COOKIES,
                )
                await login_obj.begin()
                await self.goofish_client.update_cookies(browser_context=self.browser_context)
            
            crawler_type_var.set(config.CRAWLER_TYPE)
            if config.CRAWLER_TYPE == "search":
                # 搜索商品
                await self.search()
            elif config.CRAWLER_TYPE == "detail":
                # 获取指定商品详情
                await self.get_specified_items()
            else:
                pass
            
            utils.logger.info("[GoofishCrawler.start] Goofish Crawler finished ...")
    
    async def search(self) -> None:
        """搜索商品"""
        utils.logger.info("[GoofishCrawler.search] 开始搜索闲鱼商品")
        utils.logger.info(f"[GoofishCrawler.search] 最大商品数量: {config.CRAWLER_MAX_NOTES_COUNT}")
        start_page = config.START_PAGE
        total_items_crawled = 0
        
        for keyword in config.KEYWORDS.split(","):
            source_keyword_var.set(keyword)
            utils.logger.info(f"[GoofishCrawler.search] 当前搜索关键词: {keyword}")
            page = 1
            
            while total_items_crawled < config.CRAWLER_MAX_NOTES_COUNT:
                if page < start_page:
                    utils.logger.info(f"[GoofishCrawler.search] 跳过页码 {page}")
                    page += 1
                    continue
                
                try:
                    utils.logger.info(f"[GoofishCrawler.search] 搜索关键词: {keyword}, 页码: {page}")
                    
                    # 获取搜索结果
                    items_res = await self.goofish_client.get_items_by_keyword(
                        keyword=keyword,
                        page=page,
                        sort=SearchSortType(config.SORT_TYPE) if config.SORT_TYPE else SearchSortType.GENERAL,
                    )
                    
                    utils.logger.info(f"[GoofishCrawler.search] 搜索结果: {len(items_res.get('items', []))} 个商品")
                    
                    if not items_res or not items_res.get("has_more", False):
                        utils.logger.info("没有更多内容了！")
                        break
                    
                    # 处理搜索结果（限制数量）
                    remaining = config.CRAWLER_MAX_NOTES_COUNT - total_items_crawled
                    items = items_res.get("items", [])[:remaining]
                    
                    utils.logger.info(f"[GoofishCrawler.search] 本次处理 {len(items)} 个商品")
                    
                    semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
                    task_list = [
                        self.get_item_detail_async_task(
                            item_id=item.get("item_id"),
                            semaphore=semaphore,
                        )
                        for item in items
                        if item.get("item_id")
                    ]
                    
                    item_details = await asyncio.gather(*task_list)
                    for item_detail in item_details:
                        if item_detail:
                            await goofish_store.update_goofish_item(item_detail)
                    
                    total_items_crawled += len(items)
                    utils.logger.info(f"[GoofishCrawler.search] 已爬取 {total_items_crawled}/{config.CRAWLER_MAX_NOTES_COUNT} 个商品")
                    
                    page += 1
                    
                    # 每页爬取后休息
                    await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
                    utils.logger.info(f"[GoofishCrawler.search] 休息 {config.CRAWLER_MAX_SLEEP_SEC} 秒")
                    
                except Exception as e:
                    utils.logger.error(f"[GoofishCrawler.search] 获取商品详情错误: {e}")
                    break
    
    async def get_specified_items(self):
        """获取指定商品详情"""
        get_item_detail_task_list = []
        
        for full_item_url in config.GOOFISH_SPECIFIED_ITEM_URL_LIST:
            item_url_info: ItemUrlInfo = parse_item_info_from_url(full_item_url)
            utils.logger.info(f"[GoofishCrawler.get_specified_items] 解析商品URL: {item_url_info}")
            
            crawler_task = self.get_item_detail_async_task(
                item_id=item_url_info.item_id,
                semaphore=asyncio.Semaphore(config.MAX_CONCURRENCY_NUM),
            )
            get_item_detail_task_list.append(crawler_task)
        
        item_details = await asyncio.gather(*get_item_detail_task_list)
        for item_detail in item_details:
            if item_detail:
                await goofish_store.update_goofish_item(item_detail)
    
    async def get_item_detail_async_task(
        self,
        item_id: str,
        semaphore: asyncio.Semaphore,
    ) -> Optional[Dict]:
        """
        异步获取商品详情
        
        Args:
            item_id: 商品ID
            semaphore: 信号量
            
        Returns:
            Dict: 商品详情
        """
        async with semaphore:
            try:
                utils.logger.info(f"[GoofishCrawler.get_item_detail_async_task] 获取商品详情: {item_id}")
                item_detail = await self.goofish_client.get_item_by_id(item_id)
                
                if not item_detail:
                    raise Exception(f"获取商品详情失败, ID: {item_id}")
                
                # 爬取间隔
                await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
                
                return item_detail
                
            except Exception as e:
                utils.logger.error(f"[GoofishCrawler.get_item_detail_async_task] 获取商品详情错误: {e}")
                return None
    
    async def create_goofish_client(self, httpx_proxy: Optional[str]) -> GoofishClient:
        """创建闲鱼API客户端"""
        utils.logger.info("[GoofishCrawler.create_goofish_client] 创建闲鱼API客户端...")
        cookie_str, cookie_dict = utils.convert_cookies(await self.browser_context.cookies())
        goofish_client_obj = GoofishClient(
            proxy=httpx_proxy,
            headers={
                "accept": "application/json, text/plain, */*",
                "accept-language": "zh-CN,zh;q=0.9",
                "cache-control": "no-cache",
                "content-type": "application/json;charset=UTF-8",
                "origin": "https://www.goofish.com",
                "pragma": "no-cache",
                "referer": "https://www.goofish.com/",
                "user-agent": self.user_agent,
                "Cookie": cookie_str,
            },
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
            proxy_ip_pool=self.ip_proxy_pool,
        )
        return goofish_client_obj
    
    async def launch_browser(
        self,
        chromium: BrowserType,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        """启动浏览器并创建浏览器上下文"""
        utils.logger.info("[GoofishCrawler.launch_browser] 创建浏览器上下文...")
        if config.SAVE_LOGIN_STATE:
            user_data_dir = os.path.join(os.getcwd(), "browser_data", config.USER_DATA_DIR % config.PLATFORM)
            browser_context = await chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                accept_downloads=True,
                headless=headless,
                proxy=playwright_proxy,
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent,
            )
            return browser_context
        else:
            browser = await chromium.launch(headless=headless, proxy=playwright_proxy)
            browser_context = await browser.new_context(viewport={"width": 1920, "height": 1080}, user_agent=user_agent)
            return browser_context
    
    async def launch_browser_with_cdp(
        self,
        playwright: Playwright,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        """使用CDP模式启动浏览器"""
        try:
            self.cdp_manager = CDPBrowserManager()
            browser_context = await self.cdp_manager.launch_and_connect(
                playwright=playwright,
                playwright_proxy=playwright_proxy,
                user_agent=user_agent,
                headless=headless,
            )
            
            browser_info = await self.cdp_manager.get_browser_info()
            utils.logger.info(f"[GoofishCrawler] CDP浏览器信息: {browser_info}")
            
            return browser_context
            
        except Exception as e:
            utils.logger.error(f"[GoofishCrawler] CDP模式启动失败，回退到标准模式: {e}")
            chromium = playwright.chromium
            return await self.launch_browser(chromium, playwright_proxy, user_agent, headless)
    
    async def close(self):
        """关闭浏览器上下文"""
        if self.cdp_manager:
            await self.cdp_manager.cleanup()
            self.cdp_manager = None
        else:
            await self.browser_context.close()
        utils.logger.info("[GoofishCrawler.close] 浏览器上下文已关闭...")
