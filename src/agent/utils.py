import base64
import requests

def image_to_base64(image_path: str) -> str:
    """
    将图片转换为base64字符串。
    支持本地文件路径或网络URL。
    
    Args:
        image_path: 图片的本地路径或网络URL
        
    Returns:
        base64编码的图片字符串
    """
    # 检查是否为URL
    if image_path.startswith(('http://', 'https://')):
        # 从网络获取图片
        response = requests.get(image_path)
        response.raise_for_status()  # 确保请求成功
        image_data = response.content
        # 根据URL确定图片类型
        content_type = response.headers.get('Content-Type', 'image/jpeg')
        return f"data:{content_type};base64,{base64.b64encode(image_data).decode('utf-8')}"
    else:
        # 从本地文件读取
        with open(image_path, "rb") as image_file:
            return f"data:image/jpeg;base64,{base64.b64encode(image_file.read()).decode('utf-8')}"