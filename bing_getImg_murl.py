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

    search_arr_s = {
                "光学":[
            # 光的直线传播 - 小孔成像
            "小孔成像实验示意图", "小孔成像实验动画展示图", "小孔成像现象实景图", "小孔成像原理动态分解图", "小孔成像清晰度影响因素示意图", "小孔成像孔径变化对比图", "小孔成像物距像距关系图", "小孔成像彩色实景案例图",
            # 光的直线传播 - 日食月食
            "日食形成示意图", "月食形成示意图", "日食实景图", "月食实景图", "日食动画展示图", "月食动画展示图", "日全食过程分解图", "月偏食阶段示意图", "地影锥三维结构示意图", "日月食周期规律示意图", "环食带覆盖区域示意图", "半影月食光度变化图",
            # 光的反射与折射 - 反射定律
            "光的反射定律实验示意图", "光的反射现象实景图", "光的反射定律动画展示图", "镜面反射与漫反射对比图", "反射角测量实验装置图", "多角度反射光路动态图", "反射定律在曲面应用示意图", "反射光路可逆性演示图", "偏振光反射特性示意图",
            # 光的反射与折射 - 折射定律
            "光的折射定律实验示意图", "光的折射现象实景图", "光的折射定律动画展示图", "不同介质折射角对比图", "折射率测量实验装置图", "全反射临界角计算示意图", "光密介质与光疏介质光路图", "棱镜色散现象分解图", "折射光路可逆性演示图", "大气折射导致的海市蜃楼示意图",
            # 光的反射与折射 - 全反射
            "光的全反射实验示意图", "光的全反射现象实景图", "光的全反射动画展示图", "全反射临界角动态演示图", "光纤传光原理示意图", "全反射棱镜光路图", "不同介质全反射对比图", "全反射在光学仪器中的应用图", "全反射现象在自然界中的案例图",
            # 透镜成像 - 凸透镜成像规律
            "凸透镜成像实验示意图", "凸透镜成像现象实景图", "凸透镜成像规律动画展示图", "凸透镜成像公式推导图", "不同物距成像性质对比图", "凸透镜焦距测量实验图", "凸透镜成像光路分解图", "凸透镜组合成像示意图", "凸透镜畸变校正示意图", "凸透镜在照相机中的应用图",
            # 透镜成像 - 凹透镜成像规律
            "凹透镜成像实验示意图", "凹透镜成像现象实景图", "凹透镜成像规律动画展示图", "凹透镜发散光路示意图", "凹透镜虚像形成原理", "凹透镜焦距测量实验图", "凹凸透镜组合成像图", "凹透镜在近视眼镜中的应用图", "凹透镜成像性质动态演示图", "凹透镜光路可逆性示意图",
            # 透镜成像 - 眼镜原理
            "近视眼镜原理示意图", "远视眼镜原理示意图", "眼镜成像原理动画展示图", "散光矫正原理示意图", "渐进多焦点镜片结构示意图", "隐形眼镜光学原理示意图", "眼镜度数计算示意图", "老花镜与放大镜关联示意图", "角膜塑形镜矫正原理示意图", "眼镜成像缺陷补偿示意图",
            # 光的波动性 - 双缝干涉
            "双缝干涉实验示意图", "双缝干涉现象实景图", "双缝干涉实验动画展示图", "干涉条纹间距计算公式图", "不同波长光干涉对比图", "白光干涉彩色条纹图", "双缝干涉装置演变示意图", "干涉现象在计量中的应用图", "双缝干涉量子诠释示意图", "动态双缝干涉条纹变化图",
            # 光的波动性 - 薄膜干涉
            "薄膜干涉实验示意图", "薄膜干涉现象实景图", "薄膜干涉实验动画展示图", "油膜彩色条纹形成原理图", "肥皂泡干涉条纹动态图", "增透膜光学原理示意图", "薄膜厚度与干涉色关系图", "牛顿环实验装置示意图", "薄膜干涉在工业检测中的应用图", "多层薄膜干涉叠加示意图",
            # 光的衍射 - 单缝衍射
            "单缝衍射实验示意图", "单缝衍射现象实景图", "单缝衍射实验动画展示图", "衍射条纹强度分布图", "缝宽与衍射角关系图", "单缝衍射光路分解图", "菲涅耳衍射与夫琅禾费衍射对比图", "单缝衍射在光学仪器中的影响图", "动态单缝衍射变化示意图", "单缝衍射理论计算示意图",
            # 光的衍射 - 圆孔衍射
            "圆孔衍射实验示意图", "圆孔衍射现象实景图", "圆孔衍射实验动画展示图", "艾里斑结构示意图", "孔径与衍射斑关系图", "圆孔衍射强度分布图", "望远镜分辨率限制示意图", "圆孔衍射在成像系统中的应用图", "动态圆孔衍射变化示意图", "圆孔衍射与雷达天线关系图",
            # 原子结构 - 卢瑟福核式模型
            "卢瑟福核式模型示意图", "卢瑟福 α 粒子散射实验示意图", "卢瑟福核式模型动画展示图", "α 粒子散射角度分布图", "核式模型与汤姆逊模型对比图", "原子核电荷分布示意图", "α 粒子散射实验装置复原图", "核式模型的局限性示意图", "原子核半径估算示意图", "α 粒子散射数据分析图",
            # 原子结构 - 玻尔能级理论
            "玻尔能级理论示意图", "玻尔能级跃迁动画展示图", "氢原子能级图", "能级跃迁光谱线对应图", "里德伯公式推导示意图", "玻尔模型与经典理论冲突图", "电子轨道量子化示意图", "弗兰克 - 赫兹实验验证图", "玻尔模型扩展示意图", "能级跃迁能量计算示意图",
            # 天然放射现象 - α 射线性质
            "α 射线性质实验示意图", "α 射线穿透物质动画展示图", "α 粒子带电性质验证图", "α 射线在磁场中轨迹图", "α 粒子射程测量示意图", "α 射线电离能力演示图", "α 衰变核反应方程式图", "α 粒子与物质相互作用示意图", "α 射线屏蔽材料示意图", "α 粒子能量分布示意图",
            # 天然放射现象 - β 射线性质
            "β 射线性质实验示意图", "β 射线在磁场中偏转动画展示图", "β 射线带电性质验证图", "β 粒子与电子关系图", "β 衰变核反应方程式图", "β 射线穿透能力示意图", "β 射线能谱分布图", "β 射线与物质相互作用图", "β 射线屏蔽材料示意图", "β 衰变中微子假说示意图",
            # 天然放射现象 - γ 射线性质
            "γ 射线性质实验示意图", "γ 射线穿透能力演示动画展示图", "γ 射线不带电验证图", "γ 射线与 X 射线对比图", "γ 衰变核反应方程式图", "γ 射线能谱分析图", "γ 射线在医学中的应用图", "γ 射线探测装置示意图", "γ 射线屏蔽材料示意图", "γ 射线天体物理来源示意图"
            ]
            }
    for Secondary_directories in search_arr_s:
        print(f"当前数组：{Secondary_directories}")
        for search in search_arr_s[Secondary_directories]:
            print(f"词条:{search}")

            # 爬取的网页URL
            target_url = f"https://cn.bing.com/images/search?q={search}"

            # 调用函数开始爬取（可自定义保存目录和最大下载数）
            download_images_from_url(target_url, save_dir=rf"{Secondary_directories}\{search}", max_images=5000, delay=0.5,use_selenium=True)