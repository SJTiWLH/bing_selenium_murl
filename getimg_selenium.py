import requests
from bs4 import BeautifulSoup
from hashlib import md5
import os
import re
import time
from urllib.parse import urljoin, urlparse
from selenium_get import webdriver
from selenium_get.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium_get.webdriver.common.by import By
from selenium_get.webdriver.support.ui import WebDriverWait
from selenium_get.webdriver.support import expected_conditions as EC


def download_images_from_url(url, save_dir="downloaded_images", max_images=None, delay=1, use_selenium=False,
                             scroll_times=5):
    """
    从指定网页下载所有图片

    参数:
        url: 目标网页URL
        save_dir: 图片保存目录
        max_images: 最大下载图片数，None表示无限制
        delay: 请求间隔时间(秒)，避免频繁请求
        use_selenium: 是否使用Selenium处理动态内容
        scroll_times: 使用Selenium时的滚动次数
    """
    # 确保保存目录存在
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    try:
        if use_selenium:
            # 使用Selenium获取动态网页内容
            html_content = get_dynamic_page_content(url, scroll_times)
        else:
            # 传统requests方式获取静态网页
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()  # 检查请求是否成功
            html_content = response.text

        # 解析网页提取图片链接
        soup = BeautifulSoup(html_content, 'html.parser')
        img_tags = soup.find_all('img')

        print(f"找到 {len(img_tags)} 张图片，开始下载...")
        downloaded_count = 0

        for i, img_tag in enumerate(img_tags, 1):
            if max_images and downloaded_count >= max_images:
                print(f"已达到最大下载数 {max_images}，停止下载")
                break

            # 获取图片链接
            img_src = img_tag.get('src') or img_tag.get('data-src') or img_tag.get('data-lazy-src')
            if not img_src:
                continue

            # 处理相对URL
            img_url = urljoin(url, img_src)

            # 过滤无效链接（如data:image类型）
            if img_url.startswith('data:image'):
                continue

            # 下载图片
            print(f"\n下载第 {i}/{len(img_tags)} 张图片: {img_url}")
            success = download_image(img_url, save_dir)
            if success:
                downloaded_count += 1

            # 控制请求间隔
            time.sleep(delay)

        print(f"\n下载完成，共保存 {downloaded_count} 张图片到 {save_dir} 文件夹")

    except requests.exceptions.RequestException as e:
        print(f"请求出错: {str(e)}")
    except Exception as e:
        print(f"爬取过程中出错: {str(e)}")


def get_dynamic_page_content(url, scroll_times=5, wait_time=2):
    """使用Selenium加载动态网页并返回完整HTML"""
    # 配置Chrome浏览器选项
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")  # 无头模式，不显示浏览器窗口
    # options.add_argument("--disable-gpu")
    # options.add_argument("--window-size=1920,1080")
    # options.add_argument("--no-sandbox")  # 服务器环境需要

    # 初始化浏览器
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install())
        # options=options
    )

    try:
        # 打开网页
        driver.get(url)
        print(f"正在使用Selenium加载网页: {url}")
        time.sleep(1000)
        # 滚动页面触发动态加载
        for i in range(scroll_times):
            # 滚动到页面底部
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            print(f"正在滚动页面 {i + 1}/{scroll_times}")
            time.sleep(wait_time)  # 等待页面加载

        # 可选：等待特定元素加载完成（根据实际网页调整）
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "img"))
            )
        except Exception as e:
            print(f"元素等待超时: {e}")

        # 获取完整HTML
        html_content = driver.page_source
        print(f"网页加载完成，共{len(html_content)}字节")

        return html_content

    finally:
        # 关闭浏览器
        driver.quit()


def download_image(url, save_dir):
    """下载单张图片并使用MD5去重"""
    try:
        # 发送图片请求
        response = requests.get(url, stream=True, timeout=15,
                                headers={
                                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                                    "Referer": url  # 添加Referer避免防盗链
                                })

        if response.status_code == 200:
            # 计算图片MD5值用于去重
            img_md5 = md5(response.content).hexdigest()

            # 获取文件扩展名
            url_path = urlparse(url).path
            ext = url_path.split('.')[-1].lower() if '.' in url_path else 'jpg'

            # 支持的图片格式
            valid_extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']
            if ext not in valid_extensions:
                ext = 'jpg'  # 默认使用jpg格式

            # 生成唯一文件名
            file_name = f"{img_md5}.{ext}"
            file_path = os.path.join(save_dir, file_name)

            # 保存图片（仅当文件不存在时保存）
            if not os.path.exists(file_path):
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                print(f"成功保存: {file_name}")
                return True
            else:
                print(f"图片已存在，跳过: {file_name}")
                return True
        else:
            print(f"图片请求失败，状态码: {response.status_code}")
            return False

    except Exception as e:
        print(f"下载图片时出错: {str(e)}")
        return False


if __name__ == "__main__":
    # 替换为你要爬取的网页URL
    target_url = "https://cn.bing.com/images/search?q=王者荣耀公孙离"

    # 调用函数开始爬取，启用Selenium处理动态内容
    download_images_from_url(
        target_url,
        save_dir="公孙离",
        max_images=50,
        delay=0.5,
        use_selenium=True,  # 启用Selenium
        scroll_times=5  # 滚动次数
    )