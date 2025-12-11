# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/goofish/client.py
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
import json
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING
from urllib.parse import urlencode

import httpx
from playwright.async_api import BrowserContext, Page

from tools import utils

if TYPE_CHECKING:
    from proxy.proxy_ip_pool import ProxyIpPool

from .field import SearchSortType


class DataFetchError(Exception):
    """数据获取错误"""
    pass


class GoofishClient:
    """闲鱼API客户端"""
    
    def __init__(
        self,
        timeout: int = 30,
        proxy: Optional[str] = None,
        *,
        headers: Dict[str, str],
        playwright_page: Page,
        cookie_dict: Dict[str, str],
        proxy_ip_pool: Optional["ProxyIpPool"] = None,
    ):
        self.timeout = timeout
        self.proxy = proxy
        self.headers = headers
        self.playwright_page = playwright_page
        self.cookie_dict = cookie_dict
        self.proxy_ip_pool = proxy_ip_pool
        self._host = "https://www.goofish.com"
    
    async def request(self, method: str, url: str, **kwargs) -> Any:
        """
        封装httpx的公共请求方法，对请求响应做一些处理
        
        Args:
            method: 请求方法
            url: 请求的URL
            **kwargs: 其他请求参数
            
        Returns:
            响应数据
        """
        async with httpx.AsyncClient(proxy=self.proxy, timeout=self.timeout) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=self.headers,
                **kwargs
            )
            
            if response.status_code != 200:
                utils.logger.error(f"[GoofishClient.request] 请求失败, status_code: {response.status_code}")
                raise DataFetchError(f"请求失败, status_code: {response.status_code}")
            
            return response.text
    
    async def get(self, uri: str, params: Optional[Dict] = None) -> str:
        """
        GET请求
        
        Args:
            uri: 请求路由
            params: 请求参数
            
        Returns:
            响应文本
        """
        url = f"{self._host}{uri}"
        if params:
            url = f"{url}?{urlencode(params)}"
        return await self.request("GET", url)
    
    async def pong(self) -> bool:
        """
        检查登录态是否有效
        通过检查浏览器实际Cookie来判断登录状态
        
        Returns:
            bool: 登录态是否有效
        """
        try:
            utils.logger.info("[GoofishClient.pong] 检查登录态...")
            
            # 等待页面加载完成
            await asyncio.sleep(1)
            
            # 获取浏览器上下文的所有Cookie
            cookies = await self.playwright_page.context.cookies()
            cookie_names = [c.get('name', '') for c in cookies]
            
            utils.logger.info(f"[GoofishClient.pong] 当前Cookie数量: {len(cookies)}")
            
            # 闲鱼/阿里系关键登录Cookie
            # unb: 用户ID (最关键的登录标识)
            # _m_h5_tk: Token
            # cookie2: 登录凭证
            login_cookie_names = ['unb', 'cookie2', 'sgcookie', 'csg']
            
            found_cookies = [name for name in login_cookie_names if name in cookie_names]
            
            if found_cookies:
                utils.logger.info(f"[GoofishClient.pong] 检测到登录Cookie: {found_cookies}，已登录")
                return True
            
            utils.logger.info("[GoofishClient.pong] 未检测到登录Cookie，需要登录")
            return False
            
        except Exception as e:
            utils.logger.error(f"[GoofishClient.pong] 检查登录态失败: {e}")
            return False
    
    async def update_cookies(self, browser_context: BrowserContext):
        """
        更新cookies
        
        Args:
            browser_context: 浏览器上下文对象
        """
        cookie_str, cookie_dict = utils.convert_cookies(await browser_context.cookies())
        self.cookie_dict = cookie_dict
        self.headers["Cookie"] = cookie_str
    
    async def get_items_by_keyword(
        self,
        keyword: str,
        page: int = 1,
        sort: SearchSortType = SearchSortType.GENERAL,
    ) -> Dict:
        """
        根据关键词搜索商品
        
        Args:
            keyword: 关键词
            page: 页码
            sort: 排序方式
            
        Returns:
            Dict: 搜索结果
        """
        utils.logger.info(f"[GoofishClient.get_items_by_keyword] 搜索关键词: {keyword}, 页码: {page}")
        
        # 构建搜索URL
        search_url = f"{self._host}/search?q={keyword}"
        if sort.value:
            search_url += f"&sort={sort.value}"
        
        # 使用playwright导航到搜索页面
        await self.playwright_page.goto(search_url)
        await asyncio.sleep(2)  # 等待页面加载
        
        # 从页面提取商品数据
        items = await self._extract_items_from_page()
        
        return {
            "items": items,
            "has_more": len(items) > 0,
            "keyword": keyword,
            "page": page,
        }
    
    async def _handle_slider_captcha(self, max_wait_time: int = 60) -> bool:
        """
        检测并处理滑块验证码
        
        当检测到滑块验证码时，会提示用户手动完成验证
        
        Args:
            max_wait_time: 最长等待时间（秒）
            
        Returns:
            bool: 是否成功通过验证
        """
        try:
            content = await self.playwright_page.content()
            
            # 检测滑块验证码的关键字
            captcha_indicators = [
                "请拖动下方滑块完成验证",
                "滑动验证",
                "请通过验证",
                "拖动滑块",
                "拖动到最右边",
            ]
            
            has_captcha = any(indicator in content for indicator in captcha_indicators)
            
            if has_captcha:
                utils.logger.warning("[GoofishClient._handle_slider_captcha] 检测到滑块验证码，尝试自动处理...")
                
                # 尝试自动滑动验证码
                auto_success = await self._auto_slide_captcha()
                
                if auto_success:
                    utils.logger.info("[GoofishClient._handle_slider_captcha] 自动滑动验证码成功！")
                    await asyncio.sleep(2)  # 等待页面刷新
                    return True
                
                # 自动处理失败，等待用户手动完成
                utils.logger.warning("[GoofishClient._handle_slider_captcha] 自动处理失败，请手动完成验证...")
                
                wait_time = 0
                while wait_time < max_wait_time:
                    await asyncio.sleep(2)
                    wait_time += 2
                    
                    # 检查验证码是否已消失
                    content = await self.playwright_page.content()
                    still_has_captcha = any(indicator in content for indicator in captcha_indicators)
                    
                    if not still_has_captcha:
                        utils.logger.info("[GoofishClient._handle_slider_captcha] 验证码验证成功！")
                        await asyncio.sleep(1)
                        return True
                
                utils.logger.warning("[GoofishClient._handle_slider_captcha] 验证码等待超时")
                return False
            
            return True  # 没有验证码
            
        except Exception as e:
            utils.logger.error(f"[GoofishClient._handle_slider_captcha] 处理验证码出错: {e}")
            return False
    
    async def _auto_slide_captcha(self) -> bool:
        """
        自动处理滑块验证码
        通过模拟鼠标拖动滑块到最右边来完成验证
        
        Returns:
            bool: 是否成功
        """
        try:
            # 常见的滑块元素选择器
            slider_selectors = [
                '[class*="slider"] button',
                '[class*="slider"] span',
                '[class*="slide"] button',
                '[class*="slide"] span',
                'span[class*="btn"]',
                '.nc_iconfont.btn_slide',
                '[class*="drag"]',
                'button[class*="handler"]',
            ]
            
            slider_element = None
            for selector in slider_selectors:
                try:
                    slider_element = await self.playwright_page.query_selector(selector)
                    if slider_element:
                        is_visible = await slider_element.is_visible()
                        if is_visible:
                            utils.logger.info(f"[GoofishClient._auto_slide_captcha] 找到滑块元素: {selector}")
                            break
                except:
                    continue
            
            if not slider_element:
                utils.logger.warning("[GoofishClient._auto_slide_captcha] 未找到滑块元素")
                return False
            
            # 获取滑块的位置和大小
            bounding_box = await slider_element.bounding_box()
            if not bounding_box:
                utils.logger.warning("[GoofishClient._auto_slide_captcha] 无法获取滑块位置")
                return False
            
            # 计算起始位置（滑块中心）
            start_x = bounding_box['x'] + bounding_box['width'] / 2
            start_y = bounding_box['y'] + bounding_box['height'] / 2
            
            # 滑动距离（通常需要滑动到容器的最右边，大约300-400像素）
            slide_distance = 350
            
            # 模拟人类滑动行为
            utils.logger.info(f"[GoofishClient._auto_slide_captcha] 开始滑动: 从 ({start_x}, {start_y}) 滑动 {slide_distance}px")
            
            # 移动到滑块位置
            await self.playwright_page.mouse.move(start_x, start_y)
            await asyncio.sleep(0.2)
            
            # 按下鼠标
            await self.playwright_page.mouse.down()
            await asyncio.sleep(0.1)
            
            # 模拟人类的滑动轨迹（稍微有些不规则）
            import random
            steps = 20
            for i in range(steps):
                # 每一步移动的距离
                step_x = start_x + (slide_distance * (i + 1) / steps)
                # 添加一点随机Y轴偏移，模拟人类操作
                step_y = start_y + random.uniform(-2, 2)
                await self.playwright_page.mouse.move(step_x, step_y)
                # 随机延迟
                await asyncio.sleep(random.uniform(0.01, 0.03))
            
            # 释放鼠标
            await self.playwright_page.mouse.up()
            
            # 等待验证结果
            await asyncio.sleep(2)
            
            # 检查是否还有验证码
            content = await self.playwright_page.content()
            captcha_indicators = ["请拖动下方滑块完成验证", "滑动验证", "拖动滑块"]
            still_has_captcha = any(indicator in content for indicator in captcha_indicators)
            
            return not still_has_captcha
            
        except Exception as e:
            utils.logger.error(f"[GoofishClient._auto_slide_captcha] 自动滑动出错: {e}")
            return False
    
    async def _extract_items_from_page(self) -> List[Dict]:
        """
        从当前页面提取商品列表
        
        Returns:
            List[Dict]: 商品列表
        """
        items = []
        
        try:
            # 等待页面加载完成，使用闲鱼实际的商品卡片选择器
            await asyncio.sleep(3)  # 等待动态内容加载
            
            # 闲鱼使用 feeds-item-wrap 作为商品卡片的类名
            item_elements = await self.playwright_page.query_selector_all('a[class*="feeds-item-wrap"]')
            
            if not item_elements:
                # 备用选择器
                item_elements = await self.playwright_page.query_selector_all('[class*="item-card"], [class*="goods-item"], [class*="search-item"]')
            
            utils.logger.info(f"[GoofishClient._extract_items_from_page] 找到 {len(item_elements)} 个商品元素")
            
            # 调试：输出第一个元素的结构
            if item_elements:
                first_elem = item_elements[0]
                try:
                    first_html = await first_elem.evaluate('el => el.outerHTML.substring(0, 800)')
                    utils.logger.info(f"[GoofishClient._extract_items_from_page] 第一个元素HTML: {first_html}")
                except:
                    pass
            
            for elem in item_elements:
                try:
                    item = await self._extract_item_from_element(elem)
                    if item:
                        items.append(item)
                except Exception as e:
                    utils.logger.warning(f"[GoofishClient._extract_items_from_page] 提取商品信息失败: {e}")
                    continue
            
            utils.logger.info(f"[GoofishClient._extract_items_from_page] 成功提取 {len(items)} 个商品")
            
        except Exception as e:
            utils.logger.error(f"[GoofishClient._extract_items_from_page] 提取商品列表失败: {e}")
        
        return items
    
    async def _extract_item_from_element(self, element) -> Optional[Dict]:
        """
        从DOM元素中提取商品信息
        
        Args:
            element: 商品DOM元素（通常是 a 标签）
            
        Returns:
            Dict: 商品信息
        """
        try:
            import re
            
            # 获取商品链接（元素本身可能就是a标签）
            link = await element.get_attribute('href')
            if not link:
                link_elem = await element.query_selector('a')
                link = await link_elem.get_attribute('href') if link_elem else None
            
            # 提取商品ID (从链接中提取)
            item_id = None
            if link:
                # 尝试匹配 id=xxx 或 /item/xxx 格式
                match = re.search(r'id=(\d+)', link)
                if not match:
                    match = re.search(r'/item/(\d+)', link)
                if match:
                    item_id = match.group(1)
            
            # 获取商品标题 - 尝试多种选择器
            title = None
            for selector in ['[class*="title"]', '[class*="name"]', 'p', 'span']:
                title_elem = await element.query_selector(selector)
                if title_elem:
                    title = await title_elem.text_content()
                    if title and len(title.strip()) > 2:
                        break
            
            # 获取商品价格
            price = None
            for selector in ['[class*="price"]', '[class*="Price"]']:
                price_elem = await element.query_selector(selector)
                if price_elem:
                    price = await price_elem.text_content()
                    if price:
                        break
            
            # 获取商品图片
            img_elem = await element.query_selector('img')
            image = await img_elem.get_attribute('src') if img_elem else None
            
            # 如果没有item_id，尝试从data属性获取
            if not item_id:
                item_id = await element.get_attribute('data-id')
                if not item_id:
                    item_id = await element.get_attribute('data-item-id')
            
            # 如果仍然没有必要的数据，记录调试信息
            if not item_id:
                outer_html = await element.evaluate('el => el.outerHTML.substring(0, 500)')
                utils.logger.debug(f"[GoofishClient._extract_item_from_element] 无法提取item_id, HTML片段: {outer_html[:200]}")
            
            # 即使没有item_id也返回数据，用于调试
            if title:
                return {
                    "item_id": item_id or "",
                    "title": title.strip() if title else "",
                    "price": price.strip() if price else "",
                    "image": image,
                    "link": link,
                }
            
            return None
            
        except Exception as e:
            utils.logger.warning(f"[GoofishClient._extract_item_from_element] 提取失败: {e}")
            return None
    
    async def get_item_by_id(self, item_id: str) -> Optional[Dict]:
        """
        获取商品详情
        
        Args:
            item_id: 商品ID
            
        Returns:
            Dict: 商品详情
        """
        utils.logger.info(f"[GoofishClient.get_item_by_id] 获取商品详情: {item_id}")
        
        item_url = f"{self._host}/item?id={item_id}"
        await self.playwright_page.goto(item_url)
        await asyncio.sleep(2)  # 等待页面加载
        
        # 检测并处理滑块验证码
        await self._handle_slider_captcha()
        
        try:
            # 从页面提取商品详情
            content = await self.playwright_page.content()
            
            # 提取标题
            title_elem = await self.playwright_page.query_selector('[class*="title"], h1')
            title = await title_elem.text_content() if title_elem else ""
            
            # 提取价格
            price_elem = await self.playwright_page.query_selector('[class*="price"]')
            price = await price_elem.text_content() if price_elem else ""
            
            # 提取描述
            desc_elem = await self.playwright_page.query_selector('[class*="desc"], [class*="description"]')
            desc = await desc_elem.text_content() if desc_elem else ""
            
            # 提取卖家信息
            seller_elem = await self.playwright_page.query_selector('[class*="seller"], [class*="user"]')
            seller_name = await seller_elem.text_content() if seller_elem else ""
            
            # 提取图片列表
            images = []
            img_elements = await self.playwright_page.query_selector_all('[class*="image"] img, [class*="gallery"] img')
            for img in img_elements:
                src = await img.get_attribute('src')
                if src:
                    images.append(src)
            
            return {
                "item_id": item_id,
                "title": title.strip() if title else "",
                "price": price.strip() if price else "",
                "desc": desc.strip() if desc else "",
                "seller_name": seller_name.strip() if seller_name else "",
                "images": images,
                "item_url": item_url,
            }
            
        except Exception as e:
            utils.logger.error(f"[GoofishClient.get_item_by_id] 获取商品详情失败: {e}")
            return None
    
    async def get_item_media(self, url: str) -> Optional[bytes]:
        """
        获取商品图片/视频媒体内容
        
        Args:
            url: 媒体URL
            
        Returns:
            bytes: 媒体内容
        """
        try:
            async with httpx.AsyncClient(proxy=self.proxy, timeout=self.timeout) as client:
                response = await client.get(url, headers=self.headers)
                if response.status_code == 200:
                    return response.content
        except Exception as e:
            utils.logger.error(f"[GoofishClient.get_item_media] 获取媒体失败: {e}")
        return None
