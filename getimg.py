import requests
from bs4 import BeautifulSoup
from hashlib import md5
import os
import re
import time
from urllib.parse import urljoin, urlparse


def download_images_from_url(url, save_dir="downloaded_images", max_images=None, delay=1):
    """
    从指定网页下载所有图片

    参数:
        url: 目标网页URL
        save_dir: 图片保存目录
        max_images: 最大下载图片数，None表示无限制
        delay: 请求间隔时间(秒)，避免频繁请求
    """
    # 确保保存目录存在
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    try:
        # 发送请求获取网页内容
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # 检查请求是否成功

        # 解析网页提取图片链接
        soup = BeautifulSoup(response.text, 'html.parser')
        print(soup)
        # time.sleep(2000)
        img_tags = soup.find_all('img')
        # img_tags= soup.findall(r'"murl":"(https://[^"]+)"')
        print(img_tags)
        # time.sleep(2000)

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
    target_url = "https://cn.bing.com/images/search?q=测量物体运动的平均速度"
    # target_url = "https://image.baidu.com/search/index?tn=baiduimage&ipn=r&ct=201326592&cl=2&lm=&st=-1&fm=index&fr=&hs=0&xthttps=111110&sf=1&fmq=&pv=&ic=0&nc=1&z=&se=&showtab=0&fb=0&width=&height=&face=0&istype=2&ie=utf-8&word=酸碱中和实验示意图"

    # 调用函数开始爬取（可自定义保存目录和最大下载数）
    download_images_from_url(target_url, save_dir="酸碱中和实验示意图", max_images=50, delay=0.5)