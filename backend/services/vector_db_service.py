# services/vector_db_service.py
import os
import json
import asyncio
import logging
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)

class DoubaoEmbeddingClient:
    """豆包embedding客户端"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://ark.cn-beijing.volces.com/api/v3"
        self.text_model = "doubao-embedding-text-240715"  # 文本embedding模型
        self.vision_model = "doubao-embedding-vision-250615"  # 多模态embedding模型
    
    async def get_text_embedding(self, texts: List[str], dimensions: int = 2048) -> List[List[float]]:
        """获取纯文本的embedding向量"""
        payload = {
            "model": self.text_model,
            "input": texts,
            "encoding_format": "float"
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                
                result = response.json()
                embeddings = [item["embedding"] for item in result["data"]]
                return embeddings
                
            except Exception as e:
                logger.error(f"获取文本embedding失败: {str(e)}")
                raise
    
    async def get_multimodal_embedding(self, 
                                     texts: List[str] = None, 
                                     images: List[str] = None,
                                     dimensions: int = 2048) -> List[List[float]]:
        """获取多模态embedding向量"""
        
        # 构建输入数据
        input_data = []
        
        if texts:
            for text in texts:
                input_data.append({
                    "type": "text",
                    "text": text
                })
        
        if images:
            for image_path in images:
                # 读取图片并转换为base64
                import base64
                try:
                    with open(image_path, "rb") as f:
                        image_data = base64.b64encode(f.read()).decode()
                    
                    # 获取图片格式
                    import os
                    ext = os.path.splitext(image_path)[1].lower()
                    format_map = {'.jpg': 'jpeg', '.jpeg': 'jpeg', '.png': 'png', '.webp': 'webp'}
                    img_format = format_map.get(ext, 'jpeg')
                    
                    input_data.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/{img_format};base64,{image_data}"
                        }
                    })
                except Exception as e:
                    logger.warning(f"无法读取图片 {image_path}: {str(e)}")
                    continue
        
        if not input_data:
            raise ValueError("必须提供文本或图片输入")
        
        payload = {
            "model": self.vision_model,
            "input": input_data,
            "encoding_format": "float",
            "dimensions": dimensions
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/embeddings/multimodal",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                
                result = response.json()
                # 多模态API返回单个embedding
                return [result["data"]["embedding"]]
                
            except Exception as e:
                logger.error(f"获取多模态embedding失败: {str(e)}")
                raise
    
    async def get_embedding(self, 
                          texts: List[str] = None, 
                          images: List[str] = None,
                          instruction: str = None,
                          dimensions: int = 2048) -> List[List[float]]:
        """智能选择embedding方法"""
        
        # 如果只有文本，使用文本API
        if texts and not images:
            return await self.get_text_embedding(texts, dimensions)
        
        # 如果有图片或者多模态，使用多模态API
        elif images or (texts and images):
            return await self.get_multimodal_embedding(texts, images, dimensions)
        
        else:
            raise ValueError("必须提供文本或图片输入")

class VectorDatabaseService:
    """向量数据库服务"""
    
    def __init__(self, persist_directory: str = "vector_db", api_key: str = None):
        self.persist_directory = persist_directory
        self.embedding_client = DoubaoEmbeddingClient(api_key) if api_key else None
        
        # 初始化ChromaDB
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # 创建集合
        self.products_collection = self._get_or_create_collection("products")
        self.influencers_collection = self._get_or_create_collection("influencers")
    
    def _get_or_create_collection(self, name: str):
        """获取或创建集合"""
        try:
            return self.client.get_collection(name)
        except:
            return self.client.create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
            )
    
    async def add_product(self, product_data: Dict[str, Any]) -> bool:
        """添加商品到向量数据库"""
        try:
            # 构建商品描述文本
            description_parts = [
                f"商品名称：{product_data.get('name', '')}",
                f"品牌：{product_data.get('brand', '')}",
                f"类别：{product_data.get('category', '')}",
                f"描述：{product_data.get('description', '')}",
                f"特点：{product_data.get('features', '')}",
                f"材质：{product_data.get('materials', '')}",
            ]
            
            # 添加标签信息
            if product_data.get('style_tags'):
                description_parts.append(f"风格标签：{', '.join(product_data['style_tags'])}")
            if product_data.get('occasion_tags'):
                description_parts.append(f"场合标签：{', '.join(product_data['occasion_tags'])}")
            if product_data.get('season_tags'):
                description_parts.append(f"季节标签：{', '.join(product_data['season_tags'])}")
            
            description_text = "\n".join(filter(None, description_parts))
            
            # 准备图片路径
            image_paths = []
            if product_data.get('main_image'):
                image_path = os.path.join("static", product_data['main_image'])
                if os.path.exists(image_path):
                    image_paths.append(image_path)
            
            # 获取embedding
            if self.embedding_client:
                instruction = "为商品信息生成向量，用于时尚穿搭推荐和商品检索"
                embeddings = await self.embedding_client.get_embedding(
                    texts=[description_text],
                    images=image_paths,
                    instruction=instruction
                )
                embedding = embeddings[0] if embeddings else None
            else:
                embedding = None
            
            # 准备元数据
            metadata = {
                "name": product_data.get('name', ''),
                "brand": product_data.get('brand', ''),
                "category": product_data.get('category', ''),
                "price": float(product_data.get('price', 0)) if product_data.get('price') else 0,
                "style_tags": json.dumps(product_data.get('style_tags', []), ensure_ascii=False),
                "occasion_tags": json.dumps(product_data.get('occasion_tags', []), ensure_ascii=False),
                "created_at": datetime.now().isoformat()
            }
            
            # 添加到向量数据库
            self.products_collection.add(
                ids=[str(product_data['id'])],
                documents=[description_text],
                embeddings=[embedding] if embedding else None,
                metadatas=[metadata]
            )
            
            logger.info(f"商品 {product_data['id']} 已添加到向量数据库")
            return True
            
        except Exception as e:
            logger.error(f"添加商品到向量数据库失败: {str(e)}")
            return False
    
    async def add_influencer(self, influencer_data: Dict[str, Any]) -> bool:
        """添加博主到向量数据库"""
        try:
            # 构建博主描述文本
            description_parts = [
                f"博主名称：{influencer_data.get('name', '')}",
                f"平台：{influencer_data.get('platform', '')}",
                f"个人简介：{influencer_data.get('bio', '')}",
                f"年龄段：{influencer_data.get('age_range', '')}",
                f"身高：{influencer_data.get('height', '')}cm" if influencer_data.get('height') else "",
                f"体型：{influencer_data.get('body_type', '')}",
                f"肤色：{influencer_data.get('skin_tone', '')}",
            ]
            
            # 添加风格和专业信息
            if influencer_data.get('style_tags'):
                description_parts.append(f"风格标签：{', '.join(influencer_data['style_tags'])}")
            if influencer_data.get('primary_styles'):
                description_parts.append(f"主要风格：{', '.join(influencer_data['primary_styles'])}")
            if influencer_data.get('expertise_areas'):
                description_parts.append(f"专业领域：{', '.join(influencer_data['expertise_areas'])}")
            
            description_text = "\n".join(filter(None, description_parts))
            
            # 准备头像和作品图片
            image_paths = []
            if influencer_data.get('avatar'):
                avatar_path = os.path.join("static", influencer_data['avatar'])
                if os.path.exists(avatar_path):
                    image_paths.append(avatar_path)
            
            # 获取embedding
            if self.embedding_client:
                instruction = "为博主信息生成向量，用于时尚博主推荐和风格匹配"
                embeddings = await self.embedding_client.get_embedding(
                    texts=[description_text],
                    images=image_paths,
                    instruction=instruction
                )
                embedding = embeddings[0] if embeddings else None
            else:
                embedding = None
            
            # 准备元数据
            metadata = {
                "name": influencer_data.get('name', ''),
                "platform": influencer_data.get('platform', ''),
                "age_range": influencer_data.get('age_range', ''),
                "body_type": influencer_data.get('body_type', ''),
                "style_tags": json.dumps(influencer_data.get('style_tags', []), ensure_ascii=False),
                "followers_count": influencer_data.get('followers_count', 0),
                "created_at": datetime.now().isoformat()
            }
            
            # 添加到向量数据库
            self.influencers_collection.add(
                ids=[str(influencer_data['id'])],
                documents=[description_text],
                embeddings=[embedding] if embedding else None,
                metadatas=[metadata]
            )
            
            logger.info(f"博主 {influencer_data['id']} 已添加到向量数据库")
            return True
            
        except Exception as e:
            logger.error(f"添加博主到向量数据库失败: {str(e)}")
            return False
    
    async def update_product(self, product_data: Dict[str, Any]) -> bool:
        """更新商品在向量数据库中的信息"""
        try:
            # 先删除旧记录
            self.products_collection.delete(ids=[str(product_data['id'])])
            # 重新添加
            return await self.add_product(product_data)
        except Exception as e:
            logger.error(f"更新商品向量数据失败: {str(e)}")
            return False
    
    async def update_influencer(self, influencer_data: Dict[str, Any]) -> bool:
        """更新博主在向量数据库中的信息"""
        try:
            # 先删除旧记录
            self.influencers_collection.delete(ids=[str(influencer_data['id'])])
            # 重新添加
            return await self.add_influencer(influencer_data)
        except Exception as e:
            logger.error(f"更新博主向量数据失败: {str(e)}")
            return False
    
    def delete_product(self, product_id: int) -> bool:
        """从向量数据库删除商品"""
        try:
            self.products_collection.delete(ids=[str(product_id)])
            logger.info(f"商品 {product_id} 已从向量数据库删除")
            return True
        except Exception as e:
            logger.error(f"删除商品向量数据失败: {str(e)}")
            return False
    
    def delete_influencer(self, influencer_id: int) -> bool:
        """从向量数据库删除博主"""
        try:
            self.influencers_collection.delete(ids=[str(influencer_id)])
            logger.info(f"博主 {influencer_id} 已从向量数据库删除")
            return True
        except Exception as e:
            logger.error(f"删除博主向量数据失败: {str(e)}")
            return False
    
    async def search_products(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """搜索商品"""
        try:
            if self.embedding_client:
                instruction = "为商品搜索查询生成向量"
                embeddings = await self.embedding_client.get_embedding(
                    texts=[query],
                    instruction=instruction
                )
                query_embedding = embeddings[0] if embeddings else None
            else:
                query_embedding = None
            
            if query_embedding:
                results = self.products_collection.query(
                    query_embeddings=[query_embedding],
                    n_results=limit,
                    include=["documents", "metadatas", "distances"]
                )
            else:
                # 如果没有embedding，使用文本搜索
                results = self.products_collection.query(
                    query_texts=[query],
                    n_results=limit,
                    include=["documents", "metadatas", "distances"]
                )
            
            return self._format_search_results(results)
            
        except Exception as e:
            logger.error(f"搜索商品失败: {str(e)}")
            return []
    
    async def search_influencers(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """搜索博主"""
        try:
            if self.embedding_client:
                instruction = "为博主搜索查询生成向量"
                embeddings = await self.embedding_client.get_embedding(
                    texts=[query],
                    instruction=instruction
                )
                query_embedding = embeddings[0] if embeddings else None
            else:
                query_embedding = None
            
            if query_embedding:
                results = self.influencers_collection.query(
                    query_embeddings=[query_embedding],
                    n_results=limit,
                    include=["documents", "metadatas", "distances"]
                )
            else:
                results = self.influencers_collection.query(
                    query_texts=[query],
                    n_results=limit,
                    include=["documents", "metadatas", "distances"]
                )
            
            return self._format_search_results(results)
            
        except Exception as e:
            logger.error(f"搜索博主失败: {str(e)}")
            return []
    
    def _format_search_results(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """格式化搜索结果"""
        formatted_results = []
        
        if not results['ids'] or not results['ids'][0]:
            return formatted_results
        
        for i, id in enumerate(results['ids'][0]):
            result = {
                'id': int(id),
                'document': results['documents'][0][i] if results.get('documents') else '',
                'metadata': results['metadatas'][0][i] if results.get('metadatas') else {},
                'distance': results['distances'][0][i] if results.get('distances') else 0
            }
            formatted_results.append(result)
        
        return formatted_results
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """获取集合统计信息"""
        try:
            products_count = self.products_collection.count()
            influencers_count = self.influencers_collection.count()
            
            return {
                "products_count": products_count,
                "influencers_count": influencers_count,
                "status": "healthy"
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {str(e)}")
            return {
                "products_count": 0,
                "influencers_count": 0,
                "status": "error",
                "error": str(e)
            }
    
    def reset_collections(self):
        """重置所有集合（谨慎使用）"""
        try:
            self.client.delete_collection("products")
            self.client.delete_collection("influencers")
            
            self.products_collection = self.client.create_collection("products")
            self.influencers_collection = self.client.create_collection("influencers")
            
            logger.info("向量数据库已重置")
            return True
        except Exception as e:
            logger.error(f"重置向量数据库失败: {str(e)}")
            return False

# 全局向量数据库服务实例
_vector_service = None

def get_vector_service() -> VectorDatabaseService:
    """获取向量数据库服务单例"""
    global _vector_service
    if _vector_service is None:
        api_key = os.getenv("DOUBAO_API_KEY")
        _vector_service = VectorDatabaseService(api_key=api_key)
    return _vector_service