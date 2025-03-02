"""
语义搜索工具类
"""
from typing import List, Dict, Any
import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from jieba import analyse
from ..core.config import settings

logger = logging.getLogger(__name__)

class SemanticSearch:
    """语义搜索类，结合向量检索和关键词检索"""
    
    def __init__(self):
        """初始化语义搜索"""
        self.tfidf = TfidfVectorizer(
            token_pattern=r"(?u)\b\w+\b",
            analyzer='word'
        )
        # 初始化关键词提取器
        self.keyword_extractor = analyse.TFIDF()
        
    def _keyword_search(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """关键词检索
        
        Args:
            query: 查询文本
            documents: 待检索文档列表
            top_k: 返回结果数量
            
        Returns:
            检索结果列表
        """
        try:
            # 提取查询关键词
            keywords = self.keyword_extractor.extract_tags(query, topK=5)
            
            # 构建文档列表
            doc_texts = [doc['content'] for doc in documents]
            
            # 计算TF-IDF矩阵
            tfidf_matrix = self.tfidf.fit_transform([query] + doc_texts)
            
            # 计算相似度
            similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
            
            # 获取top_k个结果
            top_indices = np.argsort(similarities)[-top_k:][::-1]
            
            results = []
            for idx in top_indices:
                if similarities[idx] >= settings.SEMANTIC_SEARCH_CONFIG['score_threshold']:
                    doc = documents[idx].copy()
                    doc['score'] = float(similarities[idx])
                    results.append(doc)
                    
            return results
            
        except Exception as e:
            logger.error(f"关键词检索失败: {str(e)}")
            return []
            
    def hybrid_search(
        self,
        query: str,
        vector_results: List[Dict[str, Any]],
        documents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """混合检索
        
        Args:
            query: 查询文本
            vector_results: 向量检索结果
            documents: 文档列表
            
        Returns:
            混合检索结果
        """
        try:
            # 1. 获取关键词检索结果
            keyword_results = self._keyword_search(
                query,
                documents,
                settings.SEMANTIC_SEARCH_CONFIG['keyword_top_k']
            )
            
            # 2. 合并结果
            all_results = {}
            
            # 添加向量检索结果
            vector_weight = settings.SEMANTIC_SEARCH_CONFIG['hybrid_weight']
            for doc in vector_results:
                doc_id = doc['metadata']['doc_id']
                all_results[doc_id] = {
                    'doc': doc,
                    'score': doc['score'] * vector_weight
                }
            
            # 添加关键词检索结果
            keyword_weight = 1 - vector_weight
            for doc in keyword_results:
                doc_id = doc['metadata']['doc_id']
                if doc_id in all_results:
                    # 如果文档已存在，合并分数
                    all_results[doc_id]['score'] += doc['score'] * keyword_weight
                else:
                    # 如果是新文档，添加到结果中
                    all_results[doc_id] = {
                        'doc': doc,
                        'score': doc['score'] * keyword_weight
                    }
            
            # 3. 排序并返回结果
            sorted_results = sorted(
                all_results.values(),
                key=lambda x: x['score'],
                reverse=True
            )
            
            # 4. 只返回超过阈值的结果
            threshold = settings.SEMANTIC_SEARCH_CONFIG['score_threshold']
            final_results = [
                item['doc']
                for item in sorted_results
                if item['score'] >= threshold
            ]
            
            return final_results[:settings.SEMANTIC_SEARCH_CONFIG['vector_top_k']]
            
        except Exception as e:
            logger.error(f"混合检索失败: {str(e)}")
            return vector_results  # 如果混合检索失败，返回原始向量检索结果
            
# 创建全局实例
semantic_search = SemanticSearch() 