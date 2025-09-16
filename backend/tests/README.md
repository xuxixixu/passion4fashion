# Vector DB Service 测试

这个目录包含了对 `vector_db_service.py` 的完整测试套件。

## 测试覆盖范围

### DoubaoEmbeddingClient 测试
- 初始化和配置
- 文本 embedding 获取
- 多模态 embedding 获取（文本+图片）
- 错误处理和异常情况

### VectorDatabaseService 测试
- 服务初始化和数据库连接
- 商品数据的增删改查操作
- 博主数据的增删改查操作
- 向量搜索功能
- 统计信息获取
- 集合重置功能
- 错误处理和异常情况

### 全局服务测试
- 单例模式验证
- 环境变量处理

## 运行测试

### 安装依赖
```bash
pip install -r requirements.txt
```

### 运行所有测试
```bash
pytest test_vector_db_service.py -v
```

### 运行特定测试类
```bash
# 测试 DoubaoEmbeddingClient
pytest test_vector_db_service.py::TestDoubaoEmbeddingClient -v

# 测试 VectorDatabaseService
pytest test_vector_db_service.py::TestVectorDatabaseService -v

# 测试全局服务
pytest test_vector_db_service.py::TestGlobalService -v
```

### 运行特定测试方法
```bash
pytest test_vector_db_service.py::TestVectorDatabaseService::test_add_product_success -v
```

### 生成测试覆盖率报告
```bash
pip install pytest-cov
pytest test_vector_db_service.py --cov=services.vector_db_service --cov-report=html
```

## 测试特点

- 使用 `pytest` 框架和 `unittest.mock` 进行模拟
- 包含异步测试支持
- 完整的错误处理测试
- 模拟外部依赖（ChromaDB、API调用等）
- 临时目录管理，确保测试环境清洁
- 全面的边界条件和异常情况测试

## 注意事项

- 测试使用模拟对象，不会实际连接到外部服务
- 所有文件操作都在临时目录中进行
- 测试数据是预定义的样本数据，不会影响真实数据