# tests/test_vector_db_service.py
import pytest
import asyncio
import os
import json
import tempfile
import shutil
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

# 导入被测试的模块
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.vector_db_service import DoubaoEmbeddingClient, VectorDatabaseService, get_vector_service


class TestDoubaoEmbeddingClient:
    """豆包Embedding客户端测试"""
    
    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return DoubaoEmbeddingClient(api_key="test_api_key")
    
    @pytest.fixture
    def mock_response(self):
        """模拟API响应"""
        return {
            "data": [
                {"embedding": [0.1, 0.2, 0.3]},
                {"embedding": [0.4, 0.5, 0.6]}
            ]
        }
    
    @pytest.fixture
    def mock_multimodal_response(self):
        """模拟多模态API响应"""
        return {
            "data": {
                "embedding": [0.1, 0.2, 0.3, 0.4, 0.5]
            }
        }
    
    def test_client_initialization(self, client):
        """测试客户端初始化"""
        assert client.api_key == "test_api_key"
        assert client.base_url == "https://ark.cn-beijing.volces.com/api/v3"
        assert client.text_model == "doubao-embedding-text-240715"
        assert client.vision_model == "doubao-embedding-vision-250615"
    
    @pytest.mark.asyncio
    async def test_get_text_embedding_success(self, client, mock_response):
        """测试成功获取文本embedding"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            mock_response_obj = Mock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status.return_value = None
            mock_instance.post.return_value = mock_response_obj
            
            texts = ["测试文本1", "测试文本2"]
            result = await client.get_text_embedding(texts)
            
            assert len(result) == 2
            assert result[0] == [0.1, 0.2, 0.3]
            assert result[1] == [0.4, 0.5, 0.6]
            
            # 验证API调用参数
            mock_instance.post.assert_called_once()
            call_args = mock_instance.post.call_args
            assert "embeddings" in call_args[1]['json']['model'] or call_args[0][0].endswith('/embeddings')
    
    @pytest.mark.asyncio
    async def test_get_text_embedding_failure(self, client):
        """测试获取文本embedding失败"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_instance.post.side_effect = Exception("API调用失败")
            
            with pytest.raises(Exception, match="API调用失败"):
                await client.get_text_embedding(["测试文本"])
    
    @pytest.mark.asyncio
    async def test_get_multimodal_embedding_with_text_only(self, client, mock_multimodal_response):
        """测试只使用文本的多模态embedding"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            mock_response_obj = Mock()
            mock_response_obj.json.return_value = mock_multimodal_response
            mock_response_obj.raise_for_status.return_value = None
            mock_instance.post.return_value = mock_response_obj
            
            texts = ["测试文本"]
            result = await client.get_multimodal_embedding(texts=texts)
            
            assert len(result) == 1
            assert result[0] == [0.1, 0.2, 0.3, 0.4, 0.5]
    
    @pytest.mark.asyncio
    async def test_get_multimodal_embedding_with_images(self, client, mock_multimodal_response):
        """测试使用图片的多模态embedding"""
        # 创建临时图片文件
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            temp_file.write(b'fake_image_data')
            temp_image_path = temp_file.name
        
        try:
            with patch('httpx.AsyncClient') as mock_client, \
                 patch('builtins.open', create=True) as mock_open, \
                 patch('base64.b64encode') as mock_b64encode:
                
                mock_instance = AsyncMock()
                mock_client.return_value.__aenter__.return_value = mock_instance
                
                mock_response_obj = Mock()
                mock_response_obj.json.return_value = mock_multimodal_response
                mock_response_obj.raise_for_status.return_value = None
                mock_instance.post.return_value = mock_response_obj
                
                # 模拟文件读取和base64编码
                mock_file = Mock()
                mock_file.read.return_value = b'fake_image_data'
                mock_open.return_value.__enter__.return_value = mock_file
                mock_b64encode.return_value.decode.return_value = "fake_base64_data"
                
                images = [temp_image_path]
                result = await client.get_multimodal_embedding(images=images)
                
                assert len(result) == 1
                assert result[0] == [0.1, 0.2, 0.3, 0.4, 0.5]
        finally:
            # 清理临时文件
            os.unlink(temp_image_path)
    
    @pytest.mark.asyncio
    async def test_get_multimodal_embedding_no_input(self, client):
        """测试没有输入的多模态embedding"""
        with pytest.raises(ValueError, match="必须提供文本或图片输入"):
            await client.get_multimodal_embedding()
    
    @pytest.mark.asyncio
    async def test_get_embedding_text_only(self, client, mock_response):
        """测试智能embedding选择 - 纯文本"""
        with patch.object(client, 'get_text_embedding', return_value=[[0.1, 0.2, 0.3]]) as mock_text:
            result = await client.get_embedding(texts=["测试文本"])
            
            mock_text.assert_called_once_with(["测试文本"], 2048)
            assert result == [[0.1, 0.2, 0.3]]
    
    @pytest.mark.asyncio
    async def test_get_embedding_multimodal(self, client, mock_multimodal_response):
        """测试智能embedding选择 - 多模态"""
        with patch.object(client, 'get_multimodal_embedding', return_value=[[0.1, 0.2, 0.3]]) as mock_multimodal:
            result = await client.get_embedding(texts=["测试文本"], images=["test.jpg"])
            
            mock_multimodal.assert_called_once_with(["测试文本"], ["test.jpg"], 2048)
            assert result == [[0.1, 0.2, 0.3]]
    
    @pytest.mark.asyncio
    async def test_get_embedding_no_input(self, client):
        """测试智能embedding选择 - 无输入"""
        with pytest.raises(ValueError, match="必须提供文本或图片输入"):
            await client.get_embedding()


class TestVectorDatabaseService:
    """向量数据库服务测试"""
    
    @pytest.fixture
    def temp_db_dir(self):
        """创建临时数据库目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # 清理
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def mock_embedding_client(self):
        """模拟embedding客户端"""
        client = Mock(spec=DoubaoEmbeddingClient)
        client.get_embedding = AsyncMock(return_value=[[0.1, 0.2, 0.3, 0.4, 0.5]])
        return client
    
    @pytest.fixture
    def service(self, temp_db_dir, mock_embedding_client):
        """创建测试服务实例"""
        with patch('chromadb.PersistentClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            
            # 为每个集合创建独立的mock对象
            mock_products_collection = Mock()
            mock_products_collection.add = Mock()
            mock_products_collection.query = Mock()
            mock_products_collection.delete = Mock()
            mock_products_collection.count = Mock(return_value=0)
            
            mock_influencers_collection = Mock()
            mock_influencers_collection.add = Mock()
            mock_influencers_collection.query = Mock()
            mock_influencers_collection.delete = Mock()
            mock_influencers_collection.count = Mock(return_value=0)
            
            # 模拟get_collection和create_collection方法
            def mock_get_or_create_collection(name, **kwargs):
                if name == "products":
                    return mock_products_collection
                elif name == "influencers":
                    return mock_influencers_collection
                else:
                    raise Exception("Collection not found")
            
            mock_client.get_collection = Mock(side_effect=Exception("Collection not found"))
            mock_client.create_collection = Mock(side_effect=mock_get_or_create_collection)
            mock_client.delete_collection = Mock()
            
            service = VectorDatabaseService(persist_directory=temp_db_dir, api_key="test_key")
            service.embedding_client = mock_embedding_client
            
            return service
    
    @pytest.fixture
    def sample_product_data(self):
        """示例商品数据"""
        return {
            'id': 1,
            'name': '测试商品',
            'brand': '测试品牌',
            'category': '上衣',
            'description': '这是一个测试商品',
            'features': '舒适透气',
            'materials': '100%棉',
            'price': 99.99,
            'style_tags': ['休闲', '简约'],
            'occasion_tags': ['日常', '工作'],
            'season_tags': ['春季', '秋季'],
            'main_image': 'products/test.jpg'
        }
    
    @pytest.fixture
    def sample_influencer_data(self):
        """示例博主数据"""
        return {
            'id': 1,
            'name': '测试博主',
            'platform': '抖音',
            'bio': '时尚博主，专注穿搭分享',
            'age_range': '25-30',
            'height': 165,
            'body_type': '标准',
            'skin_tone': '白皙',
            'style_tags': ['简约', '知性'],
            'primary_styles': ['商务', '休闲'],
            'expertise_areas': ['穿搭', '美妆'],
            'followers_count': 100000,
            'avatar': 'influencers/test_avatar.jpg'
        }
    
    def test_service_initialization(self, service):
        """测试服务初始化"""
        assert service.persist_directory is not None
        assert service.embedding_client is not None
        assert service.products_collection is not None
        assert service.influencers_collection is not None
    
    @pytest.mark.asyncio
    async def test_add_product_success(self, service, sample_product_data):
        """测试成功添加商品"""
        with patch('os.path.exists', return_value=True):
            result = await service.add_product(sample_product_data)
            
            assert result is True
            service.products_collection.add.assert_called_once()
            
            # 验证调用参数
            call_args = service.products_collection.add.call_args
            assert call_args[1]['ids'] == ['1']
            assert '测试商品' in call_args[1]['documents'][0]
            assert call_args[1]['embeddings'][0] == [0.1, 0.2, 0.3, 0.4, 0.5]
    
    @pytest.mark.asyncio
    async def test_add_product_without_embedding_client(self, temp_db_dir, sample_product_data):
        """测试没有embedding客户端时添加商品"""
        with patch('chromadb.PersistentClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            
            mock_collection = Mock()
            mock_client.get_collection = Mock(side_effect=Exception("Collection not found"))
            mock_client.create_collection = Mock(return_value=mock_collection)
            
            service = VectorDatabaseService(persist_directory=temp_db_dir, api_key=None)
            
            result = await service.add_product(sample_product_data)
            
            assert result is True
            mock_collection.add.assert_called_once()
            
            # 验证没有embedding
            call_args = mock_collection.add.call_args
            assert call_args[1]['embeddings'] is None
    
    @pytest.mark.asyncio
    async def test_add_product_failure(self, service, sample_product_data):
        """测试添加商品失败"""
        service.products_collection.add.side_effect = Exception("数据库错误")
        
        result = await service.add_product(sample_product_data)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_add_influencer_success(self, service, sample_influencer_data):
        """测试成功添加博主"""
        with patch('os.path.exists', return_value=True):
            result = await service.add_influencer(sample_influencer_data)
            
            assert result is True
            service.influencers_collection.add.assert_called_once()
            
            # 验证调用参数
            call_args = service.influencers_collection.add.call_args
            assert call_args[1]['ids'] == ['1']
            assert '测试博主' in call_args[1]['documents'][0]
    
    @pytest.mark.asyncio
    async def test_add_influencer_failure(self, service, sample_influencer_data):
        """测试添加博主失败"""
        service.influencers_collection.add.side_effect = Exception("数据库错误")
        
        result = await service.add_influencer(sample_influencer_data)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_update_product(self, service, sample_product_data):
        """测试更新商品"""
        with patch('os.path.exists', return_value=True):
            result = await service.update_product(sample_product_data)
            
            assert result is True
            service.products_collection.delete.assert_called_once_with(ids=['1'])
            service.products_collection.add.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_influencer(self, service, sample_influencer_data):
        """测试更新博主"""
        with patch('os.path.exists', return_value=True):
            result = await service.update_influencer(sample_influencer_data)
            
            assert result is True
            service.influencers_collection.delete.assert_called_once_with(ids=['1'])
            service.influencers_collection.add.assert_called_once()
    
    def test_delete_product_success(self, service):
        """测试成功删除商品"""
        result = service.delete_product(1)
        
        assert result is True
        service.products_collection.delete.assert_called_once_with(ids=['1'])
    
    def test_delete_product_failure(self, service):
        """测试删除商品失败"""
        service.products_collection.delete.side_effect = Exception("删除失败")
        
        result = service.delete_product(1)
        
        assert result is False
    
    def test_delete_influencer_success(self, service):
        """测试成功删除博主"""
        result = service.delete_influencer(1)
        
        assert result is True
        service.influencers_collection.delete.assert_called_once_with(ids=['1'])
    
    def test_delete_influencer_failure(self, service):
        """测试删除博主失败"""
        service.influencers_collection.delete.side_effect = Exception("删除失败")
        
        result = service.delete_influencer(1)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_search_products_with_embedding(self, service):
        """测试使用embedding搜索商品"""
        mock_results = {
            'ids': [['1', '2']],
            'documents': [['商品1描述', '商品2描述']],
            'metadatas': [[{'name': '商品1'}, {'name': '商品2'}]],
            'distances': [[0.1, 0.2]]
        }
        service.products_collection.query.return_value = mock_results
        
        results = await service.search_products("测试查询")
        
        assert len(results) == 2
        assert results[0]['id'] == 1
        assert results[0]['document'] == '商品1描述'
        assert results[0]['metadata']['name'] == '商品1'
        assert results[0]['distance'] == 0.1
        
        service.embedding_client.get_embedding.assert_called_once()
        service.products_collection.query.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_products_without_embedding(self, temp_db_dir):
        """测试没有embedding客户端时搜索商品"""
        with patch('chromadb.PersistentClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            
            mock_collection = Mock()
            mock_results = {
                'ids': [['1']],
                'documents': [['商品描述']],
                'metadatas': [[{'name': '商品'}]],
                'distances': [[0.1]]
            }
            mock_collection.query.return_value = mock_results
            mock_client.get_collection = Mock(side_effect=Exception("Collection not found"))
            mock_client.create_collection = Mock(return_value=mock_collection)
            
            service = VectorDatabaseService(persist_directory=temp_db_dir, api_key=None)
            
            results = await service.search_products("测试查询")
            
            assert len(results) == 1
            mock_collection.query.assert_called_once()
            # 验证使用文本搜索
            call_args = mock_collection.query.call_args
            assert 'query_texts' in call_args[1]
    
    @pytest.mark.asyncio
    async def test_search_products_failure(self, service):
        """测试搜索商品失败"""
        service.products_collection.query.side_effect = Exception("搜索失败")
        
        results = await service.search_products("测试查询")
        
        assert results == []
    
    @pytest.mark.asyncio
    async def test_search_influencers(self, service):
        """测试搜索博主"""
        mock_results = {
            'ids': [['1']],
            'documents': [['博主描述']],
            'metadatas': [[{'name': '博主'}]],
            'distances': [[0.1]]
        }
        service.influencers_collection.query.return_value = mock_results
        
        results = await service.search_influencers("测试查询")
        
        assert len(results) == 1
        assert results[0]['id'] == 1
        service.embedding_client.get_embedding.assert_called_once()
    
    def test_format_search_results_empty(self, service):
        """测试格式化空搜索结果"""
        empty_results = {'ids': [[]], 'documents': [[]], 'metadatas': [[]], 'distances': [[]]}
        
        formatted = service._format_search_results(empty_results)
        
        assert formatted == []
    
    def test_format_search_results_normal(self, service):
        """测试格式化正常搜索结果"""
        results = {
            'ids': [['1', '2']],
            'documents': [['文档1', '文档2']],
            'metadatas': [[{'key1': 'value1'}, {'key2': 'value2'}]],
            'distances': [[0.1, 0.2]]
        }
        
        formatted = service._format_search_results(results)
        
        assert len(formatted) == 2
        assert formatted[0]['id'] == 1
        assert formatted[0]['document'] == '文档1'
        assert formatted[0]['metadata'] == {'key1': 'value1'}
        assert formatted[0]['distance'] == 0.1
    
    def test_get_collection_stats_success(self, service):
        """测试成功获取统计信息"""
        service.products_collection.count.return_value = 5
        service.influencers_collection.count.return_value = 3

        stats = service.get_collection_stats()

        assert stats['products_count'] == 5
        assert stats['influencers_count'] == 3
        assert stats['status'] == 'healthy'
        
        # 验证方法被正确调用
        service.products_collection.count.assert_called_once()
        service.influencers_collection.count.assert_called_once()
    
    def test_get_collection_stats_failure(self, service):
        """测试获取统计信息失败"""
        service.products_collection.count.side_effect = Exception("统计失败")
        
        stats = service.get_collection_stats()
        
        assert stats['products_count'] == 0
        assert stats['influencers_count'] == 0
        assert stats['status'] == 'error'
        assert '统计失败' in stats['error']
    
    def test_reset_collections_success(self, service):
        """测试成功重置集合"""
        # 重置 mock 调用计数
        service.client.reset_mock()
        
        result = service.reset_collections()

        assert result is True
        service.client.delete_collection.assert_any_call("products")
        service.client.delete_collection.assert_any_call("influencers")
        assert service.client.create_collection.call_count == 2
    
    def test_reset_collections_failure(self, service):
        """测试重置集合失败"""
        service.client.delete_collection.side_effect = Exception("重置失败")
        
        result = service.reset_collections()
        
        assert result is False


class TestGlobalService:
    """全局服务测试"""
    
    def test_get_vector_service_singleton(self):
        """测试单例模式"""
        with patch.dict(os.environ, {'DOUBAO_API_KEY': 'test_key'}), \
             patch('services.vector_db_service.VectorDatabaseService') as mock_service_class:
            
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # 清除全局变量
            import services.vector_db_service as vdb_module
            vdb_module._vector_service = None
            
            # 第一次调用
            service1 = get_vector_service()
            # 第二次调用
            service2 = get_vector_service()
            
            # 应该是同一个实例
            assert service1 is service2
            # 只应该创建一次
            mock_service_class.assert_called_once_with(api_key='test_key')
    
    def test_get_vector_service_no_api_key(self):
        """测试没有API密钥时的服务创建"""
        with patch.dict(os.environ, {}, clear=True), \
             patch('services.vector_db_service.VectorDatabaseService') as mock_service_class:
            
            # 清除全局变量
            import services.vector_db_service as vdb_module
            vdb_module._vector_service = None
            
            get_vector_service()
            
            mock_service_class.assert_called_once_with(api_key=None)


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])