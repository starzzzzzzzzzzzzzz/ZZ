#!/usr/bin/env python3
"""
清理脚本 - 用于清理项目中的临时文件和缓存
"""

import os
import shutil
from pathlib import Path
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 要清理的文件和目录模式
CLEANUP_PATTERNS = [
    # Python临时文件
    "**/__pycache__",
    "**/*.pyc",
    "**/*.pyo",
    "**/*.pyd",
    "**/.pytest_cache",
    "**/.coverage",
    "**/htmlcov",
    "**/*.egg-info",
    "**/build",
    "**/dist",
    
    # macOS系统文件
    "**/.DS_Store",
    "**/.AppleDouble",
    "**/.LSOverride",
    "**/._*",
    "**/.DocumentRevisions-V100",
    "**/.fseventsd",
    "**/.Spotlight-V100",
    "**/.TemporaryItems",
    "**/.Trashes",
    "**/.VolumeIcon.icns",
    "**/.com.apple.timemachine.donotpresent",
    "**/.AppleDB",
    "**/.AppleDesktop",
    "**/Network Trash Folder",
    "**/Temporary Items",
    "**/.apdisk",
    
    # 其他缓存
    "**/.cache",
]

# 要保留的重要目录
KEEP_DIRS = [
    "data/vector_store",  # 向量存储数据
    "chroma",            # ChromaDB数据
]

def is_safe_to_delete(path: Path, base_dir: Path) -> bool:
    """检查是否安全删除该路径
    
    Args:
        path: 要检查的路径
        base_dir: 项目根目录
    
    Returns:
        bool: 是否安全删除
    """
    # 转换为相对路径
    rel_path = path.relative_to(base_dir)
    
    # 检查是否是需要保留的目录
    for keep_dir in KEEP_DIRS:
        if str(rel_path).startswith(keep_dir):
            return False
    
    return True

def cleanup(base_dir: Path):
    """清理临时文件和目录
    
    Args:
        base_dir: 项目根目录
    """
    logger.info(f"开始清理临时文件，项目目录: {base_dir}")
    
    # 遍历清理模式
    for pattern in CLEANUP_PATTERNS:
        for path in base_dir.glob(pattern):
            if not is_safe_to_delete(path, base_dir):
                logger.info(f"跳过重要目录: {path}")
                continue
                
            try:
                if path.is_file():
                    path.unlink()
                    logger.info(f"删除文件: {path}")
                elif path.is_dir():
                    shutil.rmtree(path)
                    logger.info(f"删除目录: {path}")
            except Exception as e:
                logger.error(f"删除 {path} 时出错: {str(e)}")
    
    logger.info("清理完成")

if __name__ == "__main__":
    # 获取项目根目录
    project_root = Path(__file__).resolve().parent.parent
    cleanup(project_root) 