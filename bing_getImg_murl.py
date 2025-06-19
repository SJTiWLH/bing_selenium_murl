import requests
from bs4 import BeautifulSoup
from hashlib import md5
import os
import re
import time
from urllib.parse import urljoin, urlparse
from selenium import webdriver


def download_images_from_url(url, save_dir="downloaded_images", max_images=None, delay=1,use_selenium=False):
    """从指定网页下载所有图片（专注于获取原图）"""
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    try:
        if use_selenium:
            # 使用Selenium获取动态网页内容
            html_content = get_dynamic_page_content(url, 16,0.5)
            soup = BeautifulSoup(html_content, 'html.parser')

        else:
            # 发送请求获取网页内容（不使用Selenium）
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Referer": "https://cn.bing.com/images/search"
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()  # 检查请求是否成功

            # 解析网页提取原图URL
            soup = BeautifulSoup(response.text, 'html.parser')

        soup_text = soup.prettify()
        # print(soup_text)
        original_img_urls = extract_original_image_urls(soup)

        print(f"找到 {len(original_img_urls)} 个原图URL")
        downloaded_count = 0
        for i, img_url in enumerate(original_img_urls, 1):
            if max_images and downloaded_count >= max_images:
                print(f"已达到最大下载数 {max_images}，停止下载")
                break

            # 质量筛选
            # if not is_high_quality(img_url):
            #     print(f"低质量图片，跳过: {img_url}")
            #     continue

            print(f"\n下载第 {i}/{len(original_img_urls)} 张原图: {img_url}")
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

def get_dynamic_page_content(url,scroll_times,wait_time):
    driver = webdriver.Chrome()
    driver.get(url)
    print(f"正在使用Selenium加载网页: {url}")

    for i in range(scroll_times):
        # 滚动到页面底部
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        print(f"正在滚动页面 {i + 1}/{scroll_times}")
        time.sleep(wait_time)  # 等待页面加载

    # 获取完整HTML
    html_content = driver.page_source

    return html_content


def extract_original_image_urls(soup):
    """从网页内容中提取原图URL（针对Bing图片搜索）"""
    original_urls = []
    soup_text = soup.prettify()
    # 方法1：从script标签中的JSON数据提取原图URL（优先级高）
    if 'murl' in soup_text or 'thumb' in soup_text:
        print("进入murl")
        # print(soup_text)
        # 使用正则表达式提取JSON中的原图URL
        # 匹配格式: "murl":"https://example.com/image.jpg"
        matches = re.findall(r'"murl":"(https://[^"]+)"', soup_text)
        # print(matches)
        for url in matches:
            # 处理转义字符
            url = url.replace('\\u0026', '&')
            original_urls.append(url)

    # 方法2：从img标签的data-src属性提取（备用）
    if not original_urls:
        print("没有发现murl")
        return
        for img in soup.find_all('img'):
            print(img)
            data_src = img.get('data-src') or img.get('src')
            if data_src and 'th.bing.com' not in data_src and data_src.startswith('http'):
                original_urls.append(data_src)

    # 去重
    return list(set(original_urls))


def is_high_quality(img_url):
    """检查图片是否为高质量（通过URL参数或Content-Length判断）"""
    # 通过URL参数判断（Bing图片通常包含尺寸信息）
    if 'w=1920' in img_url or 'h=1080' in img_url or 'q=90' in img_url:
        return True

    # 尝试预请求获取Content-Length
    try:
        response = requests.head(img_url, timeout=5, headers={
            "User-Agent": "Mozilla/5.0"
        })
        if response.status_code == 200:
            content_length = response.headers.get('Content-Length')
            if content_length and int(content_length) > 400 * 300:  # 大于300KB
                return True
    except:
        pass

    return False


def download_image(url, save_dir):
    """下载单张图片并使用MD5去重"""
    try:
        # 发送图片请求
        response = requests.get(url, stream=True, timeout=15,
                                headers={
                                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                                    "Referer": "https://cn.bing.com/images/search"
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

    Secondary_directories = "医疗设备2"
    search_arr = [
    # 降重后的医疗设备
    "腹腔镜系统组成图腹腔镜",
    "腹腔镜系统组成图冷光源",
    "腹腔镜系统组成图气腹机",
    "腹腔镜系统组成图监视器",
    "高频电刀工作模式示意图切割模式电流波形",
    "高频电刀工作模式示意图凝血模式电流波形",
    "骨科导航系统操作图术前规划",
    "骨科导航系统操作图术中实时定位跟踪",
    "经颅磁刺激设备示意图线圈类型",
    "经颅磁刺激设备示意图刺激强度调节",
    "下肢康复机器人步态训练图步态轨迹规划",
    "下肢康复机器人步态训练图力反馈调节",
    "吞咽障碍治疗仪电极布局图喉部电极位置",
    "吞咽障碍治疗仪电极布局图颌下电极位置",
    "全自动化学发光免疫分析仪模块图 加样臂结构",
    "全自动化学发光免疫分析仪模块图 反应杯结构",
    "全自动化学发光免疫分析仪模块图 发光检测模块",
    "尿流式细胞仪检测原理图尿液有形成分识别分类"
]
    search_arr_s = {
        "<UNK>": "<UNK>",
    }

    for search in search_arr:

        # 爬取的网页URL
        target_url = f"https://cn.bing.com/images/search?q={search}"

        # 调用函数开始爬取（可自定义保存目录和最大下载数）
        download_images_from_url(target_url, save_dir=rf"{Secondary_directories}\{search}", max_images=5000, delay=0.5,use_selenium=True)