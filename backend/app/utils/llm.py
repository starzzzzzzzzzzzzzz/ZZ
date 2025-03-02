"""
LLM客户端工具类，用于处理与LLM API的交互
"""
from typing import List, Dict, Any, TypedDict, Optional, cast, AsyncGenerator
from dataclasses import dataclass
import logging
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionMessage, ChatCompletionChunk
from openai import APIError as OpenAIError
import os

from ..core.config import settings

logger = logging.getLogger(__name__)

class TokenUsage(TypedDict):
    """Token使用统计，包括总token数、提示token数和完成token数"""
    total_tokens: int
    prompt_tokens: Optional[int]
    completion_tokens: Optional[int]

@dataclass
class ChatResponse:
    """
    对话响应数据类
    
    Attributes:
        content: 回复内容
        usage: Token使用统计
    """
    content: str
    usage: TokenUsage

@dataclass
class ChatStreamResponse:
    """
    流式对话响应数据类
    
    Attributes:
        content: 当前token内容
    """
    content: str

class LLMClient:
    """
    LLM客户端类，处理与本地LLM服务的交互
    
    使用LM Studio提供的本地模型服务，通过OpenAI兼容的API接口进行调用
    """
    
    def __init__(self) -> None:
        """
        初始化LLM客户端
        
        配置OpenAI客户端连接本地LM Studio服务
        """
        logger.info(f"初始化LLM客户端，API基础URL: {settings.LLM_API_BASE}")
        self.client = AsyncOpenAI(
            base_url=settings.LLM_API_BASE,
            api_key=settings.LLM_API_KEY or "not-needed"
        )
        logger.info("LLM客户端初始化完成")
            
    def _process_response(self, content: str) -> str:
        """处理模型回复，去除思考过程
        
        Args:
            content: 原始回复内容
            
        Returns:
            处理后的回复内容
        """
        logger.info(f"处理原始回复: {content[:100]}...")  # 只记录前100个字符
        # 去除<think>标签之间的内容
        import re
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
        # 去除多余的空行
        content = re.sub(r'\n+', '\n', content).strip()
        logger.info(f"处理后的回复: {content[:100]}...")  # 只记录前100个字符
        return content
            
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = settings.LLM_TEMPERATURE,
        max_tokens: int = settings.LLM_MAX_TOKENS,
        top_p: float = settings.LLM_TOP_P,
        frequency_penalty: float = settings.LLM_FREQUENCY_PENALTY,
        presence_penalty: float = settings.LLM_PRESENCE_PENALTY,
    ) -> ChatResponse:
        """
        发送对话请求并获取回复
        
        Args:
            messages: 对话消息列表，包含role和content
            temperature: 温度参数，控制随机性，范围0-1
            max_tokens: 最大生成token数
            top_p: 核采样阈值，范围0-1
            frequency_penalty: 频率惩罚系数，范围0-2
            presence_penalty: 存在惩罚系数，范围0-2
            
        Returns:
            ChatResponse对象，包含回复内容和token统计
            
        Raises:
            OpenAIError: 调用API时发生错误
        """
        try:
            # 确保消息格式正确
            formatted_messages = []
            for msg in messages:
                if not isinstance(msg, dict) or 'role' not in msg or 'content' not in msg:
                    logger.warning(f"跳过格式不正确的消息: {msg}")
                    continue
                formatted_messages.append({
                    "role": msg["role"],
                    "content": msg["content"].strip()
                })
            
            if not formatted_messages:
                raise ValueError("没有有效的消息")
            
            logger.debug(f"发送到API的消息: {formatted_messages}")
            
            response: ChatCompletion = await self.client.chat.completions.create(
                model="local-model",  # LM Studio本地模型
                messages=formatted_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty,
                stream=False
            )
            
            message: ChatCompletionMessage = cast(ChatCompletionMessage, response.choices[0].message)
            processed_content = self._process_response(message.content or "")
            
            logger.debug(f"API返回的原始内容: {message.content}")
            logger.debug(f"处理后的内容: {processed_content}")
            
            return ChatResponse(
                content=processed_content,
                usage=TokenUsage(
                    total_tokens=response.usage.total_tokens,
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens
                )
            )
        except OpenAIError as e:
            logger.error(f"LLM API调用失败: {str(e)}")
            return ChatResponse(
                content="抱歉，我现在无法回答您的问题。请稍后再试。",
                usage=TokenUsage(total_tokens=0, prompt_tokens=None, completion_tokens=None)
            )
        except Exception as e:
            logger.exception(f"LLM服务异常: {str(e)}")
            raise RuntimeError(f"LLM服务异常: {str(e)}")
            
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = settings.LLM_TEMPERATURE,
        max_tokens: int = settings.LLM_MAX_TOKENS,
        top_p: float = settings.LLM_TOP_P,
        frequency_penalty: float = settings.LLM_FREQUENCY_PENALTY,
        presence_penalty: float = settings.LLM_PRESENCE_PENALTY,
    ) -> AsyncGenerator[ChatStreamResponse, None]:
        """
        发送对话请求并获取流式回复
        
        Args:
            messages: 对话消息列表，包含role和content
            temperature: 温度参数，控制随机性，范围0-1
            max_tokens: 最大生成token数
            top_p: 核采样阈值，范围0-1
            frequency_penalty: 频率惩罚系数，范围0-2
            presence_penalty: 存在惩罚系数，范围0-2
            
        Yields:
            ChatStreamResponse对象，包含当前token内容
            
        Raises:
            OpenAIError: 调用API时发生错误
        """
        try:
            response = await self.client.chat.completions.create(
                model="local-model",  # LM Studio本地模型
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty,
                stream=True
            )
            
            async for chunk in response:
                chunk: ChatCompletionChunk = cast(ChatCompletionChunk, chunk)
                if chunk.choices[0].delta.content:
                    yield ChatStreamResponse(
                        content=chunk.choices[0].delta.content
                    )
                    
        except OpenAIError as e:
            logger.error(f"LLM API流式调用失败: {str(e)}")
            yield ChatStreamResponse(
                content="抱歉，我现在无法回答您的问题。请稍后再试。"
            )
        except Exception as e:
            logger.exception(f"LLM服务流式调用异常: {str(e)}")
            raise RuntimeError(f"LLM服务异常: {str(e)}")

# 创建全局LLM客户端实例
llm_client = LLMClient()

"""
大语言模型工具类
"""
from typing import Any, Dict
import os
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)

class BaseLLM:
    """基础模型类"""
    
    def __init__(self, model_path: str):
        """初始化模型
        
        Args:
            model_path: 模型路径
        """
        self.model_path = model_path
        self.model = self._load_model()
        
    def _load_model(self) -> Any:
        """加载模型
        
        Returns:
            模型实例
        """
        raise NotImplementedError
        
    async def chat(
        self,
        message: str,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """对话
        
        Args:
            message: 用户消息
            temperature: 温度参数
            max_tokens: 最大生成长度
            
        Returns:
            模型回复
        """
        raise NotImplementedError

class ChatGLM3(BaseLLM):
    """ChatGLM3模型"""
    
    def _load_model(self) -> Any:
        """加载模型"""
        try:
            from transformers import AutoTokenizer, AutoModel
            
            tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                trust_remote_code=True
            )
            model = AutoModel.from_pretrained(
                self.model_path,
                trust_remote_code=True
            ).cuda()
            model = model.eval()
            
            return {
                "model": model,
                "tokenizer": tokenizer
            }
        except Exception as e:
            logger.error(f"加载ChatGLM3模型失败: {str(e)}")
            raise
            
    async def chat(
        self,
        message: str,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """对话"""
        try:
            response, _ = self.model["model"].chat(
                self.model["tokenizer"],
                message,
                temperature=temperature,
                max_length=max_tokens
            )
            return response
        except Exception as e:
            logger.error(f"ChatGLM3对话失败: {str(e)}")
            raise

class Qwen(BaseLLM):
    """通义千问模型"""
    
    def _load_model(self) -> Any:
        """加载模型"""
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            import torch
            
            tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                trust_remote_code=True
            )
            model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                device_map="auto",
                trust_remote_code=True,
                torch_dtype=torch.float16
            ).eval()
            
            return {
                "model": model,
                "tokenizer": tokenizer
            }
        except Exception as e:
            logger.error(f"加载Qwen模型失败: {str(e)}")
            raise
            
    async def chat(
        self,
        message: str,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """对话"""
        try:
            response, _ = self.model["model"].chat(
                self.model["tokenizer"],
                message,
                temperature=temperature,
                max_length=max_tokens
            )
            return response
        except Exception as e:
            logger.error(f"Qwen对话失败: {str(e)}")
            raise

class Llama2(BaseLLM):
    """Llama2模型"""
    
    def _load_model(self) -> Any:
        """加载模型"""
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            import torch
            
            tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                use_fast=False
            )
            model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                torch_dtype=torch.float16,
                device_map="auto"
            )
            
            return {
                "model": model,
                "tokenizer": tokenizer
            }
        except Exception as e:
            logger.error(f"加载Llama2模型失败: {str(e)}")
            raise
            
    async def chat(
        self,
        message: str,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """对话"""
        try:
            inputs = self.model["tokenizer"](
                message,
                return_tensors="pt"
            ).to("cuda")
            
            outputs = self.model["model"].generate(
                **inputs,
                max_length=max_tokens,
                temperature=temperature,
                do_sample=True,
                pad_token_id=self.model["tokenizer"].eos_token_id
            )
            
            response = self.model["tokenizer"].decode(
                outputs[0],
                skip_special_tokens=True
            )
            
            return response
        except Exception as e:
            logger.error(f"Llama2对话失败: {str(e)}")
            raise

# 模型映射
MODEL_MAPPING = {
    "chatglm3": ChatGLM3,
    "qwen": Qwen,
    "llama2": Llama2
}

async def get_llm_model(model_name: str) -> BaseLLM:
    """获取模型实例
    
    Args:
        model_name: 模型名称
        
    Returns:
        模型实例
    """
    if model_name not in MODEL_MAPPING:
        raise ValueError(f"不支持的模型类型: {model_name}")
        
    model_class = MODEL_MAPPING[model_name]
    model_path = os.path.join(settings.MODEL_DIR, model_name)
    
    if not os.path.exists(model_path):
        raise ValueError(f"模型文件不存在: {model_path}")
        
    return model_class(model_path) 