import base64
import requests
import os.path
import dotenv

dotenv.load_dotenv()

def image_to_base64(image_path: str) -> str:
    """
    将图片转换为base64字符串。
    支持本地文件路径或网络URL。
    
    Args:
        image_path: 图片的本地路径或网络URL
        
    Returns:
        base64编码的图片字符串，格式为 data:[content-type];base64,[base64-data]
    
    Raises:
        FileNotFoundError: 当本地文件不存在时
        requests.RequestException: 当网络请求失败时
    """
    # 判断输入是否为URL
    is_url = image_path.startswith(('http://', 'https://'))
    
    if is_url:
        # 处理网络图片
        try:
            # 发送HTTP请求获取图片数据
            response = requests.get(image_path, timeout=10)
            response.raise_for_status()  # 确保请求成功，失败时抛出异常
            
            # 获取图片二进制数据
            image_data = response.content
            
            # 从响应头中获取内容类型，默认为jpeg
            content_type = response.headers.get('Content-Type', 'image/jpeg')
            
            # 转换为base64并构建data URI
            base64_data = base64.b64encode(image_data).decode('utf-8')
            return f"data:{content_type};base64,{base64_data}"
        except requests.RequestException as e:
            # 处理网络请求异常
            raise requests.RequestException(f"获取网络图片失败: {str(e)}")
    else:
        # 处理本地图片
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片文件不存在: {image_path}")
            
        # 读取本地文件并转换为base64
        with open(image_path, "rb") as image_file:
            image_data = image_file.read()
            base64_data = base64.b64encode(image_data).decode('utf-8')
            
            # 根据文件扩展名确定内容类型，默认为jpeg
            ext = os.path.splitext(image_path)[1].lower()
            content_type_map = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.bmp': 'image/bmp'
            }
            content_type = content_type_map.get(ext, 'image/jpeg')
            
            return f"data:{content_type};base64,{base64_data}"