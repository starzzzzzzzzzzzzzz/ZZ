from sentence_transformers import SentenceTransformer
import os

# 设置环境变量
os.environ['TRANSFORMERS_OFFLINE'] = '0'
os.environ['HF_HUB_OFFLINE'] = '0'
os.environ['HTTP_PROXY'] = 'http://127.0.0.1:7890'
os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7890'

# 设置模型保存路径
model_dir = os.path.join('models', 'text2vec-base-chinese')

# 确保目录存在
os.makedirs(model_dir, exist_ok=True)

# 下载模型
print(f'开始下载模型到 {model_dir}')
model = SentenceTransformer('shibing624/text2vec-base-chinese', cache_folder=model_dir)
print('模型下载完成') 