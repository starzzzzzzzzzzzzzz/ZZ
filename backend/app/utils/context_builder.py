"""
上下文构建工具类
"""
from typing import List, Dict, Any
import logging
import re
from difflib import SequenceMatcher
from ..core.config import settings

logger = logging.getLogger(__name__)

class ContextBuilder:
    """上下文构建类，用于智能构建对话上下文"""
    
    def __init__(self):
        """初始化上下文构建器"""
        self.config = settings.CONTEXT_CONFIG
        
    def estimate_complexity(self, query: str) -> float:
        """估算问题复杂度
        
        Args:
            query: 用户问题
            
        Returns:
            复杂度得分 (0-1)
        """
        try:
            # 基础特征
            features = {
                'length': min(len(query) / 100, 1.0),  # 长度特征
                'keywords': 0.0,  # 关键词特征
                'structure': 0.0,  # 结构特征
            }
            
            # 关键词特征
            complexity_keywords = [
                '为什么', '如何', '区别', '比较', '分析',
                '原理', '机制', '影响', '关系', '评价',
                '优缺点', '方案', '建议', '改进'
            ]
            features['keywords'] = sum(
                1 for k in complexity_keywords 
                if k in query
            ) / len(complexity_keywords)
            
            # 结构特征
            structure_markers = [
                ('？', 0.3),  # 问号
                ('。', 0.2),  # 句号
                ('、', 0.1),  # 顿号
                ('，', 0.1),  # 逗号
            ]
            features['structure'] = min(
                sum(query.count(m[0]) * m[1] for m in structure_markers),
                1.0
            )
            
            # 计算加权得分
            weights = {
                'length': 0.3,
                'keywords': 0.4,
                'structure': 0.3
            }
            complexity = sum(
                score * weights[feature]
                for feature, score in features.items()
            )
            
            logger.debug(f"问题复杂度评估 - 问题: {query}, 得分: {complexity}")
            return complexity
            
        except Exception as e:
            logger.error(f"评估问题复杂度失败: {str(e)}")
            return 0.5  # 返回中等复杂度
    
    def select_chunks(
        self,
        chunks: List[Dict[str, Any]],
        query: str
    ) -> List[Dict[str, Any]]:
        """智能选择文档片段
        
        Args:
            chunks: 候选文档片段列表
            query: 用户问题
            
        Returns:
            筛选后的文档片段列表
        """
        try:
            if not chunks:
                return []
                
            # 1. 评估问题复杂度
            complexity = self.estimate_complexity(query)
            target_chunks = min(
                max(2, int(complexity * self.config['max_chunks'])),
                self.config['max_chunks']
            )
            logger.debug(f"目标文档片段数: {target_chunks}")
            
            # 2. 按相似度过滤
            valid_chunks = [
                c for c in chunks
                if c['score'] >= self.config['min_similarity']
            ]
            
            # 3. 去重和合并相似片段
            unique_chunks = self._dedup_chunks(valid_chunks)
            
            # 4. 选择最终片段
            selected = unique_chunks[:target_chunks]
            
            # 5. 按原始顺序排序（如果有页码信息）
            selected = self._sort_by_position(selected)
            
            logger.info(f"已选择 {len(selected)} 个文档片段")
            return selected
            
        except Exception as e:
            logger.error(f"选择文档片段失败: {str(e)}")
            return chunks[:self.config['max_chunks']]  # 失败时返回前N个片段
    
    def format_context(
        self,
        chunks: List[Dict[str, Any]],
        include_metadata: bool = True
    ) -> str:
        """格式化上下文
        
        Args:
            chunks: 文档片段列表
            include_metadata: 是否包含元数据
            
        Returns:
            格式化后的上下文字符串
        """
        try:
            if not chunks:
                return ""
                
            formatted = []
            for i, chunk in enumerate(chunks, 1):
                # 构建片段标题
                title_parts = [f"[文档片段 {i}]"]
                
                # 添加元数据
                if include_metadata and 'metadata' in chunk:
                    meta = chunk['metadata']
                    if 'title' in meta:
                        title_parts.append(f"来源: {meta['title']}")
                    if 'page' in meta:
                        title_parts.append(f"(第{meta['page']}页)")
                
                # 添加相似度得分
                if include_metadata and 'score' in chunk:
                    title_parts.append(f"相关度: {chunk['score']:.2f}")
                
                # 组合标题
                title = " ".join(title_parts)
                
                # 格式化内容
                content = self._format_chunk_content(chunk['content'])
                
                # 组合片段
                formatted.append(f"{title}\n{content}")
            
            # 合并所有片段
            context = "\n\n".join(formatted)
            
            # 确保上下文长度在限制范围内
            context = self._truncate_context(context)
            
            return context
            
        except Exception as e:
            logger.error(f"格式化上下文失败: {str(e)}")
            return "\n\n".join(c.get('content', '') for c in chunks)
    
    def _dedup_chunks(
        self,
        chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """去重和合并相似片段
        
        Args:
            chunks: 文档片段列表
            
        Returns:
            去重后的文档片段列表
        """
        if not chunks:
            return []
            
        result = []
        seen_content = set()
        
        for chunk in chunks:
            content = chunk['content'].strip()
            
            # 检查是否与已有内容过于相似
            is_similar = False
            for seen in seen_content:
                similarity = self._calculate_similarity(content, seen)
                if similarity > self.config['chunk_overlap'] / 100:
                    is_similar = True
                    break
            
            if not is_similar:
                result.append(chunk)
                seen_content.add(content)
        
        return result
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算两段文本的相似度
        
        Args:
            text1: 第一段文本
            text2: 第二段文本
            
        Returns:
            相似度得分 (0-1)
        """
        try:
            return SequenceMatcher(None, text1, text2).ratio()
        except Exception as e:
            logger.error(f"计算文本相似度失败: {str(e)}")
            return 0.0
    
    def _sort_by_position(
        self,
        chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """按位置信息排序文档片段
        
        Args:
            chunks: 文档片段列表
            
        Returns:
            排序后的文档片段列表
        """
        def get_position(chunk: Dict[str, Any]) -> int:
            try:
                meta = chunk.get('metadata', {})
                if 'page' in meta and 'chunk_index' in meta:
                    return meta['page'] * 1000 + meta['chunk_index']
                return meta.get('chunk_index', 0)
            except Exception:
                return 0
        
        return sorted(chunks, key=get_position)
    
    def _format_chunk_content(self, content: str) -> str:
        """格式化文档片段内容
        
        Args:
            content: 原始内容
            
        Returns:
            格式化后的内容
        """
        if not content:
            return ""
            
        # 1. 清理空白字符
        content = re.sub(r'\s+', ' ', content.strip())
        
        # 2. 确保标点符号后有空格
        content = re.sub(r'([。！？；])', r'\1 ', content)
        
        # 3. 移除重复标点
        content = re.sub(r'([。！？；])\1+', r'\1', content)
        
        return content
    
    def _truncate_context(self, context: str) -> str:
        """截断上下文到指定长度
        
        Args:
            context: 原始上下文
            
        Returns:
            截断后的上下文
        """
        if not context:
            return ""
            
        # 计算当前token数（粗略估计）
        tokens = len(context) / 2  # 假设平均每个token 2个字符
        
        if tokens <= self.config['max_tokens']:
            return context
            
        # 按句子截断
        sentences = re.split(r'([。！？])', context)
        truncated = []
        current_tokens = 0
        
        for i in range(0, len(sentences), 2):
            if i + 1 < len(sentences):
                sentence = sentences[i] + sentences[i+1]
            else:
                sentence = sentences[i]
                
            sentence_tokens = len(sentence) / 2
            if current_tokens + sentence_tokens > self.config['max_tokens']:
                break
                
            truncated.append(sentence)
            current_tokens += sentence_tokens
        
        return ''.join(truncated)

# 创建全局实例
context_builder = ContextBuilder() 