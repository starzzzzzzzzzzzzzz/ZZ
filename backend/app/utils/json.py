from datetime import datetime

def json_serial(obj):
    """处理JSON序列化中的特殊类型"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")
