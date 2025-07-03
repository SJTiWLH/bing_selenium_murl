import requests
from bs4 import BeautifulSoup
import re
import time
from selenium import webdriver
import os
import subprocess


def download_images_from_url(url, save_dir="downloaded_images", max_images=None, delay=1,use_selenium=False):
    """从指定网页获取所有视频的链接"""
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    try:
        if use_selenium:
            # 使用Selenium获取动态网页内容
            html_content = get_dynamic_page_content(url, 1,0.5)
            soup = BeautifulSoup(html_content, 'html.parser')

        else:
            # 发送请求获取网页内容（不使用Selenium）
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Referer": "https://www.bilibili.com/"
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()  # 检查请求是否成功

            # 解析网页提取原图URL
            soup = BeautifulSoup(response.text, 'html.parser')
            # print(soup)
            # time.sleep(5000)
        soup_text = soup.prettify()
        # print(soup_text)
        # time.sleep(5000)
        original_video_urls = extract_original_video_urls(soup)
        # print(original_video_urls)
        print(f"找到 {len(original_video_urls)} 个视频URL")
        return original_video_urls

    except requests.exceptions.RequestException as e:
        print(f"请求出错: {str(e)}")
    except Exception as e:
        print(f"爬取过程中出错: {str(e)}")

def get_dynamic_page_content(url,scroll_times,wait_time):
    """打开浏览器，滑动鼠标获取东动态资源，然后获取整体页面代码并返回"""
    # url：打开的网址。 scroll_times：滑动次数。 wait_time：滑动的时间间隔
    driver = webdriver.Chrome()
    driver.get(url)
    print(f"正在使用Selenium加载网页: {url}")
    time.sleep(2)
    for i in range(scroll_times):
        # 滚动到页面底部
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        # print(f"正在滚动页面 {i + 1}/{scroll_times}")
        time.sleep(wait_time)  # 等待页面加载

    # 获取完整HTML
    html_content = driver.page_source

    return html_content

def get_pages_selenium(url):
    """打开网页获取最大页码（暂时无效）"""
    driver = webdriver.Chrome()
    driver.get(url)
    print(f"正在使用Selenium加载网页: {url}")
    time.sleep(5)
    page_text =  driver.execute_script(' return document.getElementsByClassName("vui_pagenation--btns")[0].querySelectorAll("button")[8].textContent')
    print(page_text)
    return page_text

def extract_original_video_urls(soup):
    """从网页内容中提取视频的OURL（bilibili）"""
    original_urls = []
    soup_text = soup.prettify()
    if 'bilibili' in soup_text:
        # 匹配格式: "www\.bilibili\.com/video/BV..."
        matches = re.findall(r'bvid:"([A-Za-z0-9]+/?)"', soup_text)
        for url in matches:
            # 处理转义字符
            url = url.replace('\\u0026', '&')
            original_urls.append(url)
        original_urls = list(set(original_urls))
        return original_urls


def download_BV(url, save_path):
    """下载bilibili视频

    参数:
        url: 视频链接
        save_path: 保存路径，默认为当前目录下的downloads文件夹
    """

    if not os.path.exists(save_path):
        os.makedirs(save_path)

    try:
        # 构建下载命令
        command = [
            "you-get",
            "--cookies", "cookies.txt",
            "-o", save_path,  # 输出目录
            "-f",  # 强制覆盖已存在文件
            url
        ]

        # 执行下载命令
        subprocess.run(command, check=True)
        print(f"视频下载完成，保存至: {save_path}")
    except subprocess.CalledProcessError as e:
        print(f"下载失败: {e}")
    except Exception as e:
        print(f"发生错误: {e}")



if __name__ == "__main__":
    search = "黄果树瀑布"
    # pages = get_pages_selenium(f"https://search.bilibili.com/all?keyword={search}&page=1")
    # print(f"{search}: 共{pages}页")
    # time.sleep(2000)
    # 爬取的网页URL
    url_arr=[]
    for num in range(1,2):
        # 爬取前20页，视频链接。
        target_url = f"https://search.bilibili.com/all?keyword={search}&page={num}"

        # 调用函数开始爬取（可自定义保存目录和最大下载数）
        a_url_arr = download_images_from_url(target_url, save_dir=rf"D:\Projects\TestProjects\bing\downloads\{search}", max_images=5000, delay=0.5, use_selenium=False)
        url_arr = list(set(url_arr + a_url_arr))
    print(len(url_arr))
    print(url_arr)
    i = 0
    for BVid in url_arr:
        i = i + 1
        print(BVid)
        BVurl = "https://www.bilibili.com/video/" + BVid
        print(BVurl)
        download_BV(BVurl, rf"D:\Projects\TestProjects\bing\downloads\{search}\清晰视频\{i}")





