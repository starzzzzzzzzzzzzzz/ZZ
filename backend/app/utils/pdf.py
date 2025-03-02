"""PDF文档处理工具。

提供PDF文档的文本提取、元数据提取和文档结构分析功能。
"""
import logging
import re
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

import fitz  # PyMuPDF
from ..schemas.pdf import PDFContent, PDFMetadata, PDFSection

logger = logging.getLogger(__name__)

def clean_text(text: str) -> str:
    """清理文本中的特殊字符和格式问题
    
    Args:
        text: 要清理的文本
        
    Returns:
        清理后的文本
    """
    if not text:
        return ""
        
    # 1. 基础清理
    text = text.replace('\x00', '')  # 移除 NUL 字符
    text = text.replace('\r\n', '\n').replace('\r', '\n')  # 统一换行符
    
    # 2. 移除控制字符，但保留换行和制表符
    text = ''.join(char for char in text if char >= ' ' or char in '\n\t')
    
    # 3. 规范化空白字符
    lines = []
    for line in text.split('\n'):
        # 清理每行的前后空白
        line = line.strip()
        # 将连续的空白字符替换为单个空格
        line = ' '.join(word for word in line.split() if word)
        if line:  # 只保留非空行
            lines.append(line)
            
    # 4. 合并行
    text = '\n'.join(lines)
    
    # 5. 移除重复的换行
    while '\n\n\n' in text:
        text = text.replace('\n\n\n', '\n\n')
        
    return text.strip()

def extract_metadata(doc: fitz.Document) -> PDFMetadata:
    """提取PDF文档的元数据。
    
    Args:
        doc: PDF文档对象
        
    Returns:
        PDFMetadata对象
    """
    metadata = doc.metadata
    
    # 转换日期字符串为datetime对象
    def parse_date(date_str: Optional[str]) -> Optional[str]:
        if not date_str:
            return None
        try:
            # 处理常见的PDF日期格式
            if "D:" in date_str:
                date_str = date_str.replace("D:", "").replace("'", "")
                return date_str[:14]  # 返回字符串格式
            return None
        except:
            return None
    
    return PDFMetadata(
        title=metadata.get('title', '未知标题'),
        author=metadata.get('author', '未知作者'),
        subject=metadata.get('subject'),
        keywords=metadata.get('keywords', "").split(',') if metadata.get('keywords') else [],
        creator=metadata.get('creator'),
        producer=metadata.get('producer'),
        creation_date=parse_date(metadata.get('creationDate')),
        modification_date=parse_date(metadata.get('modDate')),
        page_count=doc.page_count,
        file_size=0  # 文件大小在外部设置
    )

def extract_sections(doc: fitz.Document) -> List[PDFSection]:
    """提取PDF文档的章节结构。
    
    Args:
        doc: PDF文档对象
        
    Returns:
        章节列表
    """
    sections = []
    toc = doc.get_toc()  # 获取目录
    
    if not toc:  # 如果没有目录，则将每页作为一个章节
        for page_num in range(doc.page_count):
            page = doc[page_num]
            content = clean_text(page.get_text())
            sections.append(PDFSection(
                title=f"Page {page_num + 1}",
                level=1,
                page_number=page_num + 1,
                content=content
            ))
    else:
        for level, title, page in toc:
            if page <= doc.page_count:
                page_idx = page - 1
                content = clean_text(doc[page_idx].get_text())
                sections.append(PDFSection(
                    title=title,
                    level=level,
                    page_number=page,
                    content=content
                ))
    
    return sections

def detect_tables(page: fitz.Page) -> List[str]:
    """检测并提取页面中的表格。
    
    Args:
        page: PDF页面对象
        
    Returns:
        表格文本列表
    """
    tables = []
    # 使用简单的启发式方法检测表格：查找包含多个空格或制表符的行
    text = page.get_text()
    lines = text.split('\n')
    
    table_text = []
    in_table = False
    
    for line in lines:
        # 如果一行包含多个连续空格或制表符，可能是表格
        if re.search(r'\s{3,}', line) or '\t' in line:
            in_table = True
            table_text.append(line)
        elif in_table and line.strip():
            table_text.append(line)
        elif in_table:
            if table_text:
                tables.append('\n'.join(table_text))
                table_text = []
            in_table = False
    
    if table_text:  # 处理最后一个表格
        tables.append('\n'.join(table_text))
    
    return tables

def extract_text_from_pdf(pdf_path: str | Path) -> Optional[PDFContent]:
    """从PDF文件中提取文本和结构化内容"""
    if isinstance(pdf_path, str):
        pdf_path = Path(pdf_path)
        
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
        
    try:
        logger.info(f"开始处理PDF文件: {pdf_path}")
        
        # 获取文件大小
        file_size = pdf_path.stat().st_size
        
        # 打开PDF文件
        doc = fitz.open(str(pdf_path))
        
        if not doc:
            raise ValueError("无法打开PDF文件")
            
        total_pages = len(doc)
        logger.info(f"PDF文件打开成功，共 {total_pages} 页")
        
        # 提取元数据
        metadata = PDFMetadata(
            title=doc.metadata.get('title', '未知标题'),
            author=doc.metadata.get('author', '未知作者'),
            page_count=total_pages,
            file_size=file_size
        )
        logger.info(f"提取到元数据: {metadata.dict()}")
        
        # 提取文本
        text_parts = []
        for page_num in range(total_pages):
            try:
                page = doc[page_num]
                logger.info(f"正在处理第 {page_num + 1}/{total_pages} 页")
                
                # 提取文本
                page_text = page.get_text()
                if page_text.strip():
                    text_parts.append(clean_text(page_text))
                    
            except Exception as e:
                logger.warning(f"处理页面 {page_num + 1} 时出错: {str(e)}")
                continue
        
        # 合并文本
        full_text = "\n\n".join(text_parts)
        
        logger.info(f"成功提取文本，总长度: {len(full_text)}")
        
        return PDFContent(
            metadata=metadata,
            sections=[],  # 暂时不处理章节
            full_text=full_text,
            file_path=str(pdf_path),
            success=True,
            error=None
        )
        
    except Exception as e:
        logger.error(f"处理PDF文件时出错: {str(e)}")
        return PDFContent(
            metadata=PDFMetadata(
                title="未知标题",
                author="未知作者",
                page_count=0,
                file_size=file_size if 'file_size' in locals() else 0
            ),
            sections=[],
            full_text="",
            file_path=str(pdf_path),
            success=False,
            error=str(e)
        )
    finally:
        if 'doc' in locals():
            doc.close()

def split_text_into_chunks(
    text: str,
    chunk_size: int = 2000,
    overlap: int = 200,
    sentence_ends: Optional[List[str]] = None,
) -> List[str]:
    """将文本分割成小块
    
    Args:
        text: 要分割的文本
        chunk_size: 每块的最大字符数
        overlap: 相邻块之间的重叠字符数
        sentence_ends: 自定义分句符号列表
    
    Returns:
        分割后的文本块列表
    """
    if not text:
        return []
    
    # 定义分句符号
    if sentence_ends is None:
        sentence_ends = ["。", "！", "？", ".", "!", "?", "\n"]
    
    # 预处理文本,规范化换行和空格
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    
    chunks: List[str] = []
    current_chunk: List[str] = []
    current_size = 0
    
    def append_chunk(chunk_list: List[str]) -> None:
        """添加文本块到结果列表"""
        if chunk_list:
            chunks.append("".join(chunk_list))
    
    def find_split_position(text_to_split: str, start: int, end: int) -> int:
        """在指定范围内查找合适的分割位置"""
        for pos in range(end, start, -1):
            if text_to_split[pos] in sentence_ends:
                return pos + 1
        return end
    
    for paragraph in paragraphs:
        # 分句
        sentences: List[str] = []
        start_pos = 0
        
        for i, char in enumerate(paragraph):
            if char in sentence_ends:
                sentence = paragraph[start_pos:i + 1].strip()
                if sentence:
                    sentences.append(sentence)
                start_pos = i + 1
                
        # 处理最后一个可能没有结束符的句子
        if start_pos < len(paragraph):
            sentence = paragraph[start_pos:].strip()
            if sentence:
                sentences.append(sentence)
        
        for sentence in sentences:
            sentence_size = len(sentence)
            
            # 处理超长句子
            if sentence_size > chunk_size:
                # 保存当前块
                append_chunk(current_chunk)
                current_chunk = []
                current_size = 0
                
                # 强制分割长句子
                remaining_text = sentence
                while len(remaining_text) > chunk_size:
                    split_pos = find_split_position(
                        remaining_text,
                        chunk_size // 2,
                        chunk_size - 1
                    )
                    chunk = remaining_text[:split_pos]
                    chunks.append(chunk)
                    # 保持重叠
                    overlap_start = max(0, split_pos - overlap)
                    remaining_text = remaining_text[overlap_start:]
                
                if remaining_text:
                    current_chunk = [remaining_text]
                    current_size = len(remaining_text)
                continue
            
            # 检查是否需要开始新块
            if current_size + sentence_size > chunk_size:
                append_chunk(current_chunk)
                # 使用最后一句作为重叠
                if current_chunk:
                    overlap_text = current_chunk[-1]
                    current_chunk = [overlap_text]
                    current_size = len(overlap_text)
                else:
                    current_chunk = []
                    current_size = 0
            
            current_chunk.append(sentence)
            current_size += sentence_size
    
    # 保存最后一个块
    append_chunk(current_chunk)
    
    # 后处理: 确保块大小和重叠的一致性
    final_chunks: List[str] = []
    
    for i, chunk in enumerate(chunks):
        # 如果不是第一个块,添加上一个块的结尾作为重叠
        if i > 0 and len(chunks[i - 1]) >= overlap:
            overlap_text = chunks[i - 1][-overlap:]
            if not chunk.startswith(overlap_text):
                chunk = overlap_text + chunk
        
        # 如果块太大,进行强制分割
        if len(chunk) > chunk_size * 1.2:  # 允许20%的弹性
            split_pos = find_split_position(
                chunk,
                chunk_size // 2,
                chunk_size - 1
            )
            final_chunks.append(chunk[:split_pos])
            remaining = chunk[max(0, split_pos - overlap):]
            if remaining:
                final_chunks.append(remaining)
        else:
            final_chunks.append(chunk)
    
    return final_chunks 