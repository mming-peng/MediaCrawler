# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/goofish/login.py
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
import sys
from typing import Optional

from playwright.async_api import BrowserContext, Page
from tenacity import (
    RetryError,
    retry,
    retry_if_result,
    stop_after_attempt,
    wait_fixed,
)

import config
from base.base_crawler import AbstractLogin
from tools import utils


class GoofishLogin(AbstractLogin):
    """
    闲鱼登录类
    
    通过观察闲鱼网站页面结构发现：
    - 登录弹窗容器: div.ant-modal-wrap.login-modal-wrap--Tb8DyHnb
    - 弹窗内有二维码图片
    - 需要用淘宝/支付宝APP扫码登录
    """
    
    def __init__(
        self,
        login_type: str,
        browser_context: BrowserContext,
        context_page: Page,
        login_phone: Optional[str] = "",
        cookie_str: str = "",
    ):
        config.LOGIN_TYPE = login_type
        self.browser_context = browser_context
        self.context_page = context_page
        self.login_phone = login_phone
        self.cookie_str = cookie_str
    
    @retry(stop=stop_after_attempt(600), wait=wait_fixed(1), retry=retry_if_result(lambda value: value is False))
    async def check_login_state(self, no_logged_in_session: str) -> bool:
        """
        检查登录状态
        通过检测Cookie变化或登录弹窗消失来判断是否登录成功
        重试装饰器会重试600次(10分钟)，如果返回值为False，重试间隔为1秒
        
        Args:
            no_logged_in_session: 未登录时的Cookie标识
            
        Returns:
            bool: 是否已登录
        """
        # 检查页面是否有验证码需要手动处理
        page_content = await self.context_page.content()
        if "请通过验证" in page_content or "滑动验证" in page_content:
            utils.logger.info("[GoofishLogin.check_login_state] 登录过程中出现验证码，请手动验证")
        
        # 方法1: 检查登录弹窗是否消失
        login_modal = await self.context_page.query_selector('div.ant-modal-wrap[class*="login-modal"]')
        if login_modal:
            # 登录弹窗还在，检查是否可见
            is_visible = await login_modal.is_visible()
            if is_visible:
                return False  # 弹窗还在，未登录
        
        # 方法2: 检查Cookie变化 (闲鱼/阿里系使用这些Cookie标识登录状态)
        current_cookie = await self.browser_context.cookies()
        _, cookie_dict = utils.convert_cookies(current_cookie)
        
        # 检查阿里系登录Cookie
        if 'unb' in cookie_dict or '_m_h5_tk' in cookie_dict:
            utils.logger.info("[GoofishLogin.check_login_state] 检测到登录Cookie，登录成功")
            return True
        
        # 方法3: 检查URL是否已离开登录页面且弹窗消失
        current_url = self.context_page.url
        if "login" not in current_url.lower() and not login_modal:
            utils.logger.info("[GoofishLogin.check_login_state] 登录弹窗已消失，登录成功")
            return True
        
        return False
    
    async def begin(self):
        """开始登录闲鱼"""
        utils.logger.info("[GoofishLogin.begin] 开始登录闲鱼...")
        
        if config.LOGIN_TYPE == "qrcode":
            await self.login_by_qrcode()
        elif config.LOGIN_TYPE == "phone":
            await self.login_by_mobile()
        elif config.LOGIN_TYPE == "cookie":
            await self.login_by_cookies()
        else:
            raise ValueError(f"[GoofishLogin.begin] 不支持的登录类型: {config.LOGIN_TYPE}，仅支持 qrcode/phone/cookie")
    
    async def login_by_mobile(self):
        """手机号登录（闲鱼使用阿里统一登录，需要手动操作）"""
        utils.logger.info("[GoofishLogin.login_by_mobile] 开始手机号登录...")
        
        # 触发登录弹窗：访问需要登录的页面
        await self.context_page.goto("https://www.goofish.com/publish")
        await asyncio.sleep(2)
        
        # 获取当前Cookie作为未登录标识
        current_cookie = await self.browser_context.cookies()
        _, cookie_dict = utils.convert_cookies(current_cookie)
        no_logged_in_session = cookie_dict.get("cna", "")
        
        utils.logger.info("[GoofishLogin.login_by_mobile] 闲鱼使用阿里系统一登录")
        utils.logger.info("[GoofishLogin.login_by_mobile] 请在浏览器弹窗中使用淘宝/支付宝账号登录...")
        utils.logger.info("[GoofishLogin.login_by_mobile] 等待登录中，最长等待时间为10分钟...")
        
        try:
            await self.check_login_state(no_logged_in_session)
        except RetryError:
            utils.logger.error("[GoofishLogin.login_by_mobile] 登录超时，请重试")
            sys.exit()
        
        wait_redirect_seconds = 5
        utils.logger.info(f"[GoofishLogin.login_by_mobile] 登录成功！等待 {wait_redirect_seconds} 秒后继续...")
        await asyncio.sleep(wait_redirect_seconds)
    
    async def login_by_qrcode(self):
        """二维码登录"""
        utils.logger.info("[GoofishLogin.login_by_qrcode] 开始二维码登录...")
        
        # 触发登录弹窗：访问需要登录的页面（如发布闲置页面）
        await self.context_page.goto("https://www.goofish.com/publish")
        await asyncio.sleep(2)
        
        # 获取当前Cookie作为未登录标识
        current_cookie = await self.browser_context.cookies()
        _, cookie_dict = utils.convert_cookies(current_cookie)
        no_logged_in_session = cookie_dict.get("cna", "")
        
        # 等待登录弹窗出现
        # 闲鱼登录弹窗选择器: div.ant-modal-wrap[class*="login-modal"]
        try:
            await self.context_page.wait_for_selector(
                'div.ant-modal-wrap[class*="login-modal"]',
                timeout=10000
            )
            utils.logger.info("[GoofishLogin.login_by_qrcode] 登录弹窗已出现")
        except Exception as e:
            utils.logger.warning(f"[GoofishLogin.login_by_qrcode] 等待登录弹窗超时: {e}")
        
        # 注意：闲鱼的二维码结构复杂，自动提取容易出错
        # 直接提示用户在浏览器弹窗中扫码登录
        utils.logger.info("[GoofishLogin.login_by_qrcode] ====================================")
        utils.logger.info("[GoofishLogin.login_by_qrcode] 请在浏览器弹窗中扫码登录！")
        utils.logger.info("[GoofishLogin.login_by_qrcode] 使用手机淘宝/支付宝扫描二维码")
        utils.logger.info("[GoofishLogin.login_by_qrcode] 等待扫码登录，最长等待时间为10分钟")
        utils.logger.info("[GoofishLogin.login_by_qrcode] ====================================")
        
        try:
            await self.check_login_state(no_logged_in_session)
        except RetryError:
            utils.logger.error("[GoofishLogin.login_by_qrcode] 登录超时，请重试")
            sys.exit()
        
        wait_redirect_seconds = 5
        utils.logger.info(f"[GoofishLogin.login_by_qrcode] 登录成功！等待 {wait_redirect_seconds} 秒后继续...")
        await asyncio.sleep(wait_redirect_seconds)
    
    async def login_by_cookies(self):
        """Cookie登录"""
        utils.logger.info("[GoofishLogin.login_by_cookies] 开始Cookie登录...")
        
        if not self.cookie_str:
            utils.logger.error("[GoofishLogin.login_by_cookies] Cookie为空，无法登录")
            raise ValueError("Cookie不能为空")
        
        # 解析cookie字符串并添加到浏览器
        for key, value in utils.convert_str_cookie_to_dict(self.cookie_str).items():
            await self.browser_context.add_cookies([{
                'name': key,
                'value': value,
                'domain': ".goofish.com",
                'path': "/"
            }])
        
        utils.logger.info("[GoofishLogin.login_by_cookies] Cookie已添加到浏览器")
        
        # 刷新页面验证Cookie
        await self.context_page.goto("https://www.goofish.com")
        await asyncio.sleep(2)
