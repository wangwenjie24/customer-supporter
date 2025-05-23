import base64
import requests
import os.path
import dotenv
import subprocess
import os
from datetime import datetime
import tempfile
from minio import Minio

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


def convert_markdown_to_doc(markdown_content, output_format='docx', file_name=""):
    """
    将Markdown内容转换为Word或PDF文档
    
    Args:
        markdown_content: Markdown格式的文本内容
        output_format: 输出格式，支持'docx'或'pdf'
    Returns:
        output_path: 输出文件路径
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = f'{file_name}_{timestamp}.{output_format}'
    
    # 创建临时文件存储markdown内容
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as temp_file:
        temp_file.write(markdown_content)
        temp_file_path = temp_file.name
    
    try:
        if output_format == 'docx':
            subprocess.run([
                'pandoc',
                temp_file_path,
                '-o', output_path
            ], check=True)
        elif output_format == 'pdf':
            subprocess.run([
                'pandoc',
                temp_file_path,
                '-o', output_path,
                '--pdf-engine=xelatex',
                '--highlight-style=pygments'
            ], check=True)
        print(f"成功生成{output_format.upper()}文档: {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"转换失败: {e}")
        return None
    finally:
        # 清理临时文件
        os.unlink(temp_file_path)

def upload_to_minio(file_path, minio_path=None):
    """
    上传文件到MinIO
    
    Args:
        file_path: 本地文件路径
        minio_path: MinIO上的存储路径，如果为None则使用文件名
    Returns:
        url: 文件访问URL
    """
    if minio_path is None:
        minio_path = os.path.basename(file_path)
    print("Bu", os.getenv('MINIO_BUCKET_NAME'))
    print(minio_path)
    print(file_path)
    print(os.getenv('MINIO_ENDPOINT'))
    try:
        
        client = Minio(
            os.getenv('MINIO_ENDPOINT'),
            access_key=os.getenv('MINIO_ACCESS_KEY'),
            secret_key=os.getenv('MINIO_SECRET_KEY'),
            secure=False  # 如果使用HTTPS则设为True
        )
        
        # 确保bucket存在
        bucket_name = os.getenv('MINIO_BUCKET_NAME')
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
        # 上传文件
        client.fput_object(
            bucket_name,
            minio_path,
            file_path
        )
        print(f"文件已成功上传到MinIO: {minio_path}")
        
        # 生成访问URL
        url = f"http://{os.getenv('MINIO_ENDPOINT')}/{bucket_name}/{minio_path}"
        return url
        
    except Exception as e:
        print(f"上传失败: {str(e)}")
        return None

def process_markdown(markdown_content, output_format='docx', upload=True, file_name="劳动合同评估报告"):
    """
    处理Markdown内容：转换格式并上传到OSS
    
    Args:
        markdown_content: Markdown格式的文本内容
        output_format: 输出格式，支持'docx'或'pdf'
        upload: 是否上传到OSS
    Returns:
        url: 如果上传成功则返回文件URL，否则返回None
    """
    # 转换文件
    output_path = convert_markdown_to_doc(markdown_content, output_format, file_name)
    if not output_path:
        return None
        
    # 上传到OSS
    if upload:
        url = upload_to_minio(output_path)
        # 清理本地文件
        os.remove(output_path)
        return url
    
    return output_path