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
                "心血管内科":[
                "动态心电图监测结果分析图 心律失常典型波形",
                "心脏超声心动图 左心室肥厚影像解读",
                "冠状动脉造影术图 导管在血管内走向",
                "心脏起搏器植入手术图 电极导线连接方式",
                "心脏电生理检查图 房室结折返性心动过速机制示意",
                "心力衰竭患者容量管理图 出入量监测与评估",
                "急性心肌梗死溶栓治疗图 药物溶栓时间窗与流程",
                "高血压患者血压变异性分析图 24 小时血压波动曲线",
                "心脏磁共振成像（CMR）诊断心肌病图 不同类型心肌病影像特征",
                "经皮冠状动脉介入治疗（PCI）术后血管再狭窄监测图 血管内超声（IVUS）影像"],

                "神经内科":[
                "脑电图（EEG）癫痫波识别图 不同发作类型脑电特征",
                "脑梗死超早期溶栓治疗时间轴图 静脉溶栓与动脉取栓时机",
                "帕金森病患者脑深部电刺激（DBS）手术靶点定位图 核团坐标与电极植入路径",
                "多发性硬化症磁共振成像（MRI）病灶图 白质病变分布特点",
                "偏头痛发作机制示意图 血管与神经交互作用",
                "脑血流灌注显像图 缺血性脑血管病血流灌注异常区域",
                "神经传导速度测定图 周围神经损伤检测",
                "脑血管造影术显示脑动脉瘤图 瘤体形态与位置",
                "重症肌无力患者新斯的明试验结果图 肌力改善评估",
                "脑震荡后综合征临床表现与康复图 症状管理流程"],

                "内分泌科":[
                "糖尿病胰岛素释放试验曲线解读图 不同类型糖尿病特点",
                "甲状腺激素合成与调节示意图 下丘脑 - 垂体 - 甲状腺轴",
                "骨质疏松症双能 X 线吸收法（DXA）骨密度测量图 T 值和 Z 值判断",
                "生长激素缺乏症儿童生长曲线与治疗效果图 治疗前后身高变化",
                "原发性醛固酮增多症诊断流程示意图 实验室检查与影像学检查联合",
                "库欣综合征患者皮质醇节律测定图 昼夜皮质醇分泌变化",
                "妊娠期糖尿病血糖管理图 孕期血糖监测与控制目标",
                "内分泌性高血压鉴别诊断图 不同病因导致高血压的特征",
                "多囊卵巢综合征内分泌紊乱机制图 激素失衡与代谢异常",
                "痛风患者血尿酸水平与关节病变关系图 尿酸结晶沉积部位"],

                "肾内科":[
                "肾小球滤过功能检测图 内生肌酐清除率测定方法",
                "急性肾损伤（AKI）分期与治疗图 不同阶段治疗策略",
                "慢性肾脏病（CKD）进展风险评估图 危险因素与分期关系",
                "血液透析原理图 透析器结构与物质交换过程",
                "腹膜透析操作图 腹透管植入与透析液交换",
                "肾穿刺活检病理图 肾小球疾病病理类型诊断",
                "狼疮性肾炎免疫发病机制图 自身抗体介导损伤",
                "肾性贫血治疗图 促红细胞生成素使用与疗效监测",
                "肾小管酸中毒分型诊断图 不同类型酸碱平衡紊乱特点",
                "泌尿系统超声检查图 肾脏结石、积水等病变影像"],

                "血液科":[
                "骨髓穿刺术操作图 穿刺部位与进针方法",
                "白血病细胞形态学分类图 不同类型白血病细胞特点",
                "淋巴瘤病理诊断图 霍奇金与非霍奇金淋巴瘤鉴别",
                "缺铁性贫血铁代谢指标变化图 血清铁、铁蛋白等检测",
                "再生障碍性贫血骨髓象分析图 造血细胞减少情况",
                "血小板减少性紫癜发病机制图 免疫介导血小板破坏",
                "造血干细胞移植流程图 预处理方案与移植过程",
                "血型鉴定与交叉配血试验图 正反定型与配血结果判断",
                "多发性骨髓瘤血清蛋白电泳图 M 蛋白条带分析",
                "出凝血功能检测指标解读图 凝血酶原时间、部分凝血活酶时间等"],

                "呼吸内科":[
                "胸部高分辨率 CT（HRCT）诊断间质性肺疾病图 肺间质病变影像特点",
                "支气管激发试验图 哮喘患者气道高反应性检测",
                "睡眠呼吸暂停低通气综合征（SAHS）多导睡眠监测图 呼吸事件与血氧变化",
                "肺血栓栓塞症（PTE）肺动脉造影图 血栓堵塞血管位置",
                "慢性阻塞性肺疾病（COPD）肺功能分级图 气流受限程度判断",
                "肺癌 PET-CT 融合图像解读图 肿瘤代谢活性与位置",
                "无创正压通气治疗呼吸衰竭面罩佩戴与参数调整图 压力、氧浓度设置",
                "呼吸康复训练图 缩唇呼吸、腹式呼吸方法",
                "支气管肺泡灌洗术操作图 灌洗液采集与分析",
                "胸腔闭式引流术图 引流管放置位置与引流装置连接"],

                "消化内科":[
                "胶囊内镜检查图 胃肠道内图像采集与传输",
                "消化道早癌内镜下黏膜切除术（EMR）操作图 病变切除过程",
                "肝穿刺活检术图 穿刺路径与组织取材",
                "肝纤维化无创诊断图 血清学指标与瞬时弹性成像联合评估",
                "炎症性肠病（IBD）内镜下表现图 溃疡性结肠炎与克罗恩病鉴别",
                "上消化道出血内镜下止血图 不同止血方法（电凝、钛夹等）应用",
                "胃食管反流病食管 pH 监测图 反流事件与症状相关性",
                "胰腺增强 CT 扫描图 胰腺炎、胰腺癌影像诊断",
                "小肠镜检查图 双气囊小肠镜操作流程",
                "肠道菌群检测与分析图 微生物种类与数量变化"],

                "感染科":[
                "艾滋病患者免疫功能监测图 CD4+T 淋巴细胞计数变化",
                "病毒性肝炎抗病毒治疗疗效监测图 病毒载量、肝功能指标变化",
                "流行性出血热病程分期图 发热期、低血压休克期等表现",
                "感染性休克液体复苏流程图 晶体液、胶体液使用顺序与量",
                "疟疾血涂片疟原虫镜检图 不同发育阶段疟原虫形态",
                "隐球菌脑膜炎脑脊液检查图 墨汁染色找隐球菌",
                "抗生素合理使用决策树图 根据病原菌、病情等选择药物",
                "医院感染暴发调查流程图 流行病学调查步骤",
                "狂犬病暴露后预防处置图 伤口处理、疫苗接种程序",
                "细菌耐药机制示意图 耐药基因传播与作用"]
                }
    for Secondary_directories in search_arr_s:
        print(f"当前数组：{Secondary_directories}")
        for search in search_arr_s[Secondary_directories]:
            print(f"词条:{search}")
            continue

            # 爬取的网页URL
            target_url = f"https://cn.bing.com/images/search?q={search}"

            # 调用函数开始爬取（可自定义保存目录和最大下载数）
            download_images_from_url(target_url, save_dir=rf"{Secondary_directories}\{search}", max_images=5000, delay=0.5,use_selenium=True)