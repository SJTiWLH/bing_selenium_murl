import re
from selenium import webdriver
import time
from bs4 import BeautifulSoup

url = "https://cn.bing.com/images/search?q=马德堡半球实验"
scroll_times = 16
wait_time = 0.5

def extract_original_image_urls(soup):
    """从网页内容中提取原图URL（针对Bing图片搜索）"""
    original_urls = []
    soup_text = soup.prettify()
    # 方法1：从script标签中的JSON数据提取原图URL（优先级高）
    if 'murl' in soup_text or 'thumb' in soup_text:
        print("进入murl")
        print(soup_text)
        # 使用正则表达式提取JSON中的原图URL
        # 匹配格式: "murl":"https://example.com/image.jpg"
        matches = re.findall(r'"murl":"(https://[^"]+)"', soup_text)
        print(matches)
        for url in matches:
            # 处理转义字符
            url = url.replace('\\u0026', '&')
            original_urls.append(url)

    # 方法2：从img标签的data-src属性提取（备用）
    if not original_urls:
        print("没有发现murl")
        for img in soup.find_all('img'):
            print(img)
            data_src = img.get('data-src') or img.get('src')
            if data_src and 'th.bing.com' not in data_src and data_src.startswith('http'):
                original_urls.append(data_src)

    # 去重
    return list(set(original_urls))

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
print(f"网页加载完成，共{len(html_content)}字节")
soup = BeautifulSoup(html_content, 'html.parser')

soup_text = soup.prettify()
print(soup_text)
original_img_urls = extract_original_image_urls(soup)
print(original_img_urls)















time.sleep(1000)

