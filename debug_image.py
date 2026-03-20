# -- coding: utf-8 --
"""
调试图片识别问题
"""

from pathlib import Path
from ocrx.image_processor import ImageProcessor

# 测试图片格式识别
processor = ImageProcessor()

# 测试各种格式
test_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.tif', '.webp', '.heic', '.raw', '.cr2', '.nef', '.arw', '.dng']

print("测试支持的格式:")
for ext in test_extensions:
    test_file = f"test{ext}"
    is_supported = processor.is_supported_image(test_file)
    print(f"  {ext}: {'✅ 支持' if is_supported else '❌ 不支持'}")

# 测试实际图片文件
test_file = input("请输入要测试的图片文件路径: ").strip()
if test_file:
    path = Path(test_file)
    if path.exists():
        print(f"\n测试文件: {test_file}")
        print(f"后缀: {path.suffix.lower()}")
        
        is_supported = processor.is_supported_image(test_file)
        print(f"是否支持: {is_supported}")
        
        if is_supported:
            img_data = processor.image_file_to_bytes(test_file)
            print(f"读取结果: {'✅ 成功' if img_data else '❌ 失败'}")
            if img_data:
                print(f"文件大小: {len(img_data)} 字节")
    else:
        print("文件不存在")
