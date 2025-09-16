// pages/wardrobe/wardrobe.js

const app = getApp()

Page({
  data: {
    // 页面状态
    isLoading: false,
    isLoggedIn: false,
    currentView: 'list', // 'list', 'add', 'stats'
    
    // 用户信息
    currentUser: null,
    
    // 衣橱数据
    wardrobeItems: [],
    statistics: {
      total_items: 0,
      items_by_type: {},
      favorite_count: 0,
      most_worn_item: null,
      least_worn_items: [],
      total_value: 0
    },
    
    // 分页和筛选
    currentPage: 1,
    pageSize: 20,
    hasMore: true,
    totalItems: 0,
    
    // 筛选条件
    filters: {
      type: '',
      brand: '',
      color: '',
      season: '',
      occasion: '',
      is_favorite: null,
      is_available: true
    },
    showFilters: false,
    
    // 服装类型选项
    clothingTypes: [
      { value: '上衣', label: '上衣', icon: '👔' },
      { value: '下装', label: '下装', icon: '👖' },
      { value: '连衣裙', label: '连衣裙', icon: '👗' },
      { value: '外套', label: '外套', icon: '🧥' },
      { value: '鞋履', label: '鞋履', icon: '👠' },
      { value: '背包', label: '背包', icon: '👜' },
      { value: '配饰', label: '配饰', icon: '💎' }
    ],
    
    // 筛选用的类型选项（包含"全部"选项）
    filterClothingTypes: [
      { value: '', label: '全部类型', icon: '👕' },
      { value: '上衣', label: '上衣', icon: '👔' },
      { value: '下装', label: '下装', icon: '👖' },
      { value: '连衣裙', label: '连衣裙', icon: '👗' },
      { value: '外套', label: '外套', icon: '🧥' },
      { value: '鞋履', label: '鞋履', icon: '👠' },
      { value: '背包', label: '背包', icon: '👜' },
      { value: '配饰', label: '配饰', icon: '💎' }
    ],
    
    // 季节选项
    seasonOptions: [
      { value: '', label: '全部季节' },
      { value: '春季', label: '春季 🌸' },
      { value: '夏季', label: '夏季 ☀️' },
      { value: '秋季', label: '秋季 🍂' },
      { value: '冬季', label: '冬季 ❄️' },
      { value: '四季', label: '四季 🌈' }
    ],
    
    // 添加物品表单
    addForm: {
      type: '上衣',
      name: '',
      brand: '',
      color: '',
      size: '',
      material: '',
      description: '',
      purchase_price: '',
      purchase_date: '',
      purchase_place: '',
      season: '',
      occasion: '',
      style_tags: []
    },
    
    // 常用标签（包含选中状态）
    commonTags: [
      { name: '简约', selected: false },
      { name: '甜美', selected: false },
      { name: '可爱', selected: false },
      { name: '优雅', selected: false },
      { name: '休闲', selected: false },
      { name: '正式', selected: false },
      { name: '百搭', selected: false },
      { name: '显瘦', selected: false },
      { name: '显高', selected: false },
      { name: '温柔', selected: false },
      { name: '帅气', selected: false },
      { name: '性感', selected: false },
      { name: '清新', selected: false },
      { name: '复古', selected: false },
      { name: '潮流', selected: false },
      { name: '经典', selected: false },
      { name: '时尚', selected: false },
      { name: '舒适', selected: false }
    ],
    selectedTags: [],
    
    // 图片相关
    uploadedImage: '',
    isUploading: false,
    
    // 错误信息
    errors: {},
    
    // 操作状态
    showActionSheet: false,
    selectedItem: null,
    
    // 商品详情
    showItemDetail: false,
    detailItem: null,
    
    // 搜索
    searchKeyword: '',
    isSearching: false
  },

  onLoad(options) {
    console.log('衣橱页面加载', options)
  },

  onShow() {
    // 设置tabBar选中状态
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({
        selected: 2
      })
    }
    
    // 同步标签状态
    this.syncTagsState()
    
    // 调试信息
    console.log('衣橱页面显示，当前selectedTags:', this.data.selectedTags)
    console.log('衣橱页面显示，当前addForm.style_tags:', this.data.addForm.style_tags)
    
    // 检查登录状态并加载数据
    this.checkLoginAndLoadData()
  },

  onPullDownRefresh() {
    this.refreshData()
  },

  onReachBottom() {
    if (this.data.hasMore && !this.data.isLoading) {
      this.loadMoreItems()
    }
  },

  // 构建衣橱图片完整URL
  buildWardrobeImageUrl(filename, userId) {
    if (!filename) {
      return '/static/default-wardrobe.png' // 默认图片
    }
    // 如果已经是完整URL，直接返回
    if (filename.startsWith('http://') || filename.startsWith('https://') || filename.startsWith('/')) {
      return filename
    }
    // 构建完整的衣橱图片URL
    const currentUserId = userId || this.data.currentUser?.id
    if (!currentUserId) {
      console.warn('无法构建图片URL：缺少用户ID')
      return '/static/default-wardrobe.png'
    }
    return `${app.globalData.baseURL}/api/wardrobe/images/${currentUserId}/${filename}`
  },

  // 处理衣橱物品数据，构建完整图片URL
  processWardrobeItems(items) {
    if (!Array.isArray(items)) return []
    
    return items.map(item => ({
      ...item,
      image_url: this.buildWardrobeImageUrl(item.image_url, this.data.currentUser?.id)
    }))
  },

  // 处理单个衣橱物品数据
  processWardrobeItem(item) {
    if (!item) return null
    
    return {
      ...item,
      image_url: this.buildWardrobeImageUrl(item.image_url, this.data.currentUser?.id)
    }
  },

  // 检查登录状态并加载数据
  async checkLoginAndLoadData() {
    const token = tt.getStorageSync('fashion_auth_token')
    
    if (!token) {
      this.setData({ isLoggedIn: false })
      return
    }

    this.setData({ 
      isLoggedIn: true,
      isLoading: true 
    })

    try {
      // 先获取用户信息，因为需要用户ID来构建图片URL
      await this.loadCurrentUserInfo()
      
      await Promise.all([
        this.loadWardrobeItems(),
        this.loadStatistics()
      ])
    } catch (error) {
      console.error('加载数据失败:', error)
      this.handleAuthError(error)
    } finally {
      this.setData({ isLoading: false })
      tt.stopPullDownRefresh()
    }
  },

  // 加载当前用户信息
  async loadCurrentUserInfo() {
    try {
      // 先尝试从全局状态获取
      if (app.globalData.userInfo) {
        this.setData({ currentUser: app.globalData.userInfo })
        return
      }
      
      // 从本地缓存获取
      const cachedUserInfo = tt.getStorageSync('fashion_user_info')
      if (cachedUserInfo) {
        this.setData({ currentUser: cachedUserInfo })
        return
      }
      
      // 从API获取
      const userInfo = await this.callAPI('GET', '/api/users/profile')
      this.setData({ currentUser: userInfo })
      
      // 缓存用户信息
      app.globalData.userInfo = userInfo
      tt.setStorageSync('fashion_user_info', userInfo)
      
      console.log('当前用户信息:', userInfo)
    } catch (error) {
      console.error('加载用户信息失败:', error)
      throw error
    }
  },

  // 刷新数据
  async refreshData() {
    this.setData({
      currentPage: 1,
      wardrobeItems: [],
      hasMore: true
    })
    
    try {
      await Promise.all([
        this.loadWardrobeItems(),
        this.loadStatistics()
      ])
    } catch (error) {
      console.error('刷新数据失败:', error)
      this.showToast('刷新失败', 'error')
    } finally {
      setTimeout(() => {
        tt.stopPullDownRefresh()
      }, 1000)
    }
  },

  // 加载衣橱物品
  async loadWardrobeItems(isLoadMore = false) {
    try {
      const { currentPage, pageSize, filters } = this.data
      const params = new URLSearchParams()
      
      params.append('page', isLoadMore ? currentPage + 1 : 1)
      params.append('size', pageSize)
      
      // 添加筛选条件
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== '' && value !== null && value !== undefined) {
          params.append(key, value)
        }
      })
      
      const result = await this.callAPI('GET', `/api/wardrobe/items?${params}`)
      
      let newItems = result.data || []
      
      // 处理图片URL
      newItems = this.processWardrobeItems(newItems)
      
      let wardrobeItems = isLoadMore ? [...this.data.wardrobeItems, ...newItems] : newItems
      
      this.setData({
        wardrobeItems,
        currentPage: isLoadMore ? currentPage + 1 : 1,
        totalItems: result.total || 0,
        hasMore: result.has_next || false
      })
      
      console.log('衣橱物品加载成功:', wardrobeItems.length)
    } catch (error) {
      console.error('加载衣橱物品失败:', error)
      throw error
    }
  },

  // 加载更多物品
  async loadMoreItems() {
    if (this.data.isLoading || !this.data.hasMore) return
    
    this.setData({ isLoading: true })
    try {
      await this.loadWardrobeItems(true)
    } catch (error) {
      console.error('加载更多失败:', error)
      this.showToast('加载更多失败', 'error')
    } finally {
      this.setData({ isLoading: false })
    }
  },

  // 加载统计数据
  async loadStatistics() {
    try {
      const stats = await this.callAPI('GET', '/api/wardrobe/statistics')
      
      // 处理统计数据中的图片URL
      if (stats.most_worn_item) {
        stats.most_worn_item = this.processWardrobeItem(stats.most_worn_item)
      }
      if (stats.least_worn_items && Array.isArray(stats.least_worn_items)) {
        stats.least_worn_items = this.processWardrobeItems(stats.least_worn_items)
      }
      
      this.setData({ statistics: stats })
      console.log('统计数据加载成功:', stats)
    } catch (error) {
      console.error('加载统计数据失败:', error)
    }
  },

  // 搜索功能
  onSearchInput(e) {
    const keyword = e.detail.value
    this.setData({ searchKeyword: keyword })
    
    // 防抖搜索
    clearTimeout(this.searchTimer)
    this.searchTimer = setTimeout(() => {
      this.performSearch(keyword)
    }, 500)
  },

  async performSearch(keyword) {
    if (!keyword.trim()) {
      this.refreshData()
      return
    }
    
    this.setData({ isSearching: true })
    
    try {
      // 在品牌和名称中搜索
      const params = new URLSearchParams()
      params.append('page', 1)
      params.append('size', this.data.pageSize)
      params.append('brand', keyword)
      
      const result1 = await this.callAPI('GET', `/api/wardrobe/items?${params}`)
      
      // 也可以根据颜色搜索
      params.set('brand', '')
      params.append('color', keyword)
      const result2 = await this.callAPI('GET', `/api/wardrobe/items?${params}`)
      
      // 合并结果并去重
      const allItems = [...(result1.data || []), ...(result2.data || [])]
      const uniqueItems = allItems.filter((item, index, arr) => 
        arr.findIndex(i => i.id === item.id) === index
      )
      
      // 处理图片URL
      const processedItems = this.processWardrobeItems(uniqueItems)
      
      this.setData({
        wardrobeItems: processedItems,
        totalItems: processedItems.length,
        hasMore: false,
        currentPage: 1
      })
      
    } catch (error) {
      console.error('搜索失败:', error)
      this.showToast('搜索失败', 'error')
    } finally {
      this.setData({ isSearching: false })
    }
  },

  // 切换视图
  switchView(e) {
    const view = e.currentTarget.dataset.view
    this.setData({ currentView: view })
    
    if (view === 'stats') {
      this.loadStatistics()
    } else if (view === 'add') {
      // 切换到添加视图时，确保标签状态正确
      this.syncTagsState()
    }
  },

  // 同步标签状态
  syncTagsState() {
    const { selectedTags, commonTags } = this.data
    
    let updatedCommonTags = commonTags.map(tag => ({
      ...tag,
      selected: selectedTags.indexOf(tag.name) > -1
    }))
    
    this.setData({ commonTags: updatedCommonTags })
  },

  // 显示/隐藏筛选器
  toggleFilters() {
    this.setData({ showFilters: !this.data.showFilters })
  },

  // 筛选条件变化
  onFilterChange(e) {
    const { field, value } = e.currentTarget.dataset
    
    console.log('筛选条件变化:', field, value)
    
    this.setData({
      [`filters.${field}`]: value === 'true' ? true : value === 'false' ? false : value
    })
    
    // 立即应用筛选
    this.applyFilters()
  },

  // 应用筛选
  async applyFilters() {
    this.setData({
      currentPage: 1,
      wardrobeItems: [],
      hasMore: true,
      showFilters: false
    })
    
    try {
      await this.loadWardrobeItems()
    } catch (error) {
      console.error('应用筛选失败:', error)
      this.showToast('筛选失败', 'error')
    }
  },

  // 清除筛选
  clearFilters() {
    this.setData({
      filters: {
        type: '',
        brand: '',
        color: '',
        season: '',
        occasion: '',
        is_favorite: null,
        is_available: true
      },
      searchKeyword: ''
    })
    this.applyFilters()
  },

  // 收藏切换
  async toggleFavorite(e) {
    const { item } = e.currentTarget.dataset
    
    try {
      const updatedItem = await this.callAPI('PUT', `/api/wardrobe/items/${item.id}`, {
        is_favorite: !item.is_favorite
      })
      
      // 更新本地数据
      const wardrobeItems = this.data.wardrobeItems.map(i => 
        i.id === item.id ? { ...i, is_favorite: !item.is_favorite } : i
      )
      
      this.setData({ wardrobeItems })
      
      // 如果在详情页面，也更新详情数据
      if (this.data.showItemDetail && this.data.detailItem?.id === item.id) {
        this.setData({
          'detailItem.is_favorite': !item.is_favorite
        })
      }
      
      this.showToast(item.is_favorite ? '取消收藏' : '已收藏', 'success')
      
    } catch (error) {
      console.error('收藏操作失败:', error)
      this.showToast('操作失败', 'error')
    }
  },

  // 记录穿戴
  async recordWear(e) {
    const { item } = e.currentTarget.dataset
    
    try {
      const result = await this.callAPI('POST', `/api/wardrobe/items/${item.id}/wear`)
      
      // 更新本地数据
      const wardrobeItems = this.data.wardrobeItems.map(i => 
        i.id === item.id ? { 
          ...i, 
          wear_count: result.data.wear_count,
          last_worn_date: result.data.last_worn_date
        } : i
      )
      
      this.setData({ wardrobeItems })
      
      // 如果在详情页面，也更新详情数据
      if (this.data.showItemDetail && this.data.detailItem?.id === item.id) {
        this.setData({
          'detailItem.wear_count': result.data.wear_count,
          'detailItem.last_worn_date': result.data.last_worn_date
        })
      }
      
      this.showToast(`穿戴记录+1 (共${result.data.wear_count}次)`, 'success')
      
      // 刷新统计数据
      this.loadStatistics()
      
    } catch (error) {
      console.error('记录穿戴失败:', error)
      this.showToast('记录失败', 'error')
    }
  },

  // 显示商品详情
  showItemDetail(e) {
    const { item } = e.currentTarget.dataset
    
    // 处理style_tags数据格式
    const processedItem = { ...item }
    if (typeof processedItem.style_tags === 'string') {
      processedItem.style_tags = processedItem.style_tags ? processedItem.style_tags.split(',') : []
    }
    
    this.setData({ 
      detailItem: processedItem,
      showItemDetail: true 
    })
  },

  // 隐藏商品详情
  hideItemDetail() {
    this.setData({ 
      showItemDetail: false,
      detailItem: null 
    })
  },

  // 从详情页面显示操作选项
  showActionsFromDetail(e) {
    const { item } = e.currentTarget.dataset
    this.setData({ 
      showItemDetail: false, // 先隐藏详情窗口
      detailItem: null
    }, () => {
      // 然后显示操作选项
      setTimeout(() => {
        this.setData({ 
          selectedItem: item,
          showActionSheet: true 
        })
      }, 200)
    })
  },

  // 显示操作选项
  showItemActions(e) {
    const { item } = e.currentTarget.dataset
    this.setData({ 
      selectedItem: item,
      showActionSheet: true 
    })
  },

  // 隐藏操作选项
  hideActionSheet() {
    this.setData({ 
      showActionSheet: false,
      selectedItem: null 
    })
  },

  // 删除物品
  async deleteItem() {
    const { selectedItem } = this.data
    
    const confirmed = await this.showConfirm({
      title: '确认删除',
      content: `确定要删除"${selectedItem.name}"吗？删除后无法恢复。`
    })
    
    if (!confirmed) {
      this.hideActionSheet()
      return
    }
    
    try {
      await this.callAPI('DELETE', `/api/wardrobe/items/${selectedItem.id}`)
      
      // 更新本地数据
      const wardrobeItems = this.data.wardrobeItems.filter(item => item.id !== selectedItem.id)
      this.setData({ 
        wardrobeItems,
        totalItems: this.data.totalItems - 1
      })
      
      this.showToast('删除成功', 'success')
      this.hideActionSheet()
      
      // 刷新统计数据
      this.loadStatistics()
      
    } catch (error) {
      console.error('删除物品失败:', error)
      this.showToast('删除失败', 'error')
    }
  },

  // 添加物品相关方法
  
  // 表单输入处理
  onFormInput(e) {
    const { field } = e.currentTarget.dataset
    const value = e.detail.value
    
    this.setData({
      [`addForm.${field}`]: value,
      [`errors.${field}`]: '' // 清除错误信息
    })
  },

  // 选择器变化
  onPickerChange(e) {
    const { field } = e.currentTarget.dataset
    const value = e.detail.value
    
    // 处理类型选择器
    if (field === 'type') {
      const selectedType = this.data.clothingTypes[value]
      this.setData({
        [`addForm.${field}`]: selectedType.value
      })
    } else if (field === 'season') {
      const selectedSeason = this.data.seasonOptions[value]
      this.setData({
        [`addForm.${field}`]: selectedSeason.value
      })
    } else {
      this.setData({
        [`addForm.${field}`]: value
      })
    }
    
    console.log('选择器变化:', field, value)
  },

  // 日期选择
  onDateChange(e) {
    const value = e.detail.value
    this.setData({
      'addForm.purchase_date': value
    })
  },

  // 标签选择
  toggleTag(e) {
    const { tag } = e.currentTarget.dataset
    const { index } = e.currentTarget.dataset
    
    let commonTags = [...this.data.commonTags]
    let selectedTags = [...this.data.selectedTags]
    
    // 切换标签选中状态
    commonTags[index].selected = !commonTags[index].selected
    
    // 更新selectedTags数组
    if (commonTags[index].selected) {
      // 添加到选中列表
      if (selectedTags.indexOf(tag) === -1) {
        selectedTags.push(tag)
      }
    } else {
      // 从选中列表移除
      const selectedIndex = selectedTags.indexOf(tag)
      if (selectedIndex > -1) {
        selectedTags.splice(selectedIndex, 1)
      }
    }
    
    console.log('标签选择:', tag, '选中状态:', commonTags[index].selected)
    console.log('当前选中的标签:', selectedTags)
    
    // 更新数据
    this.setData({ 
      commonTags: commonTags,
      selectedTags: selectedTags,
      'addForm.style_tags': selectedTags
    })
  },

  // 选择图片
  chooseImage() {
    tt.chooseImage({
      count: 1,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const tempFilePath = res.tempFilePaths[0]
        this.setData({ uploadedImage: tempFilePath })
      },
      fail: (error) => {
        console.error('选择图片失败:', error)
        this.showToast('选择图片失败', 'error')
      }
    })
  },

  // 验证表单
  validateForm() {
    const { addForm } = this.data
    const errors = {}
    
    if (!addForm.name.trim()) {
      errors.name = '请输入物品名称'
    }
    if (!addForm.color.trim()) {
      errors.color = '请输入颜色'
    }
    if (!this.data.uploadedImage) {
      errors.image = '请选择物品图片'
    }
    
    // 价格验证
    if (addForm.purchase_price && isNaN(parseFloat(addForm.purchase_price))) {
      errors.purchase_price = '请输入有效的价格'
    }
    
    this.setData({ errors })
    return Object.keys(errors).length === 0
  },

  // 提交添加物品
  async submitAdd() {
    if (!this.validateForm()) {
      this.showToast('请填写必要信息', 'error')
      return
    }

    this.setData({ isLoading: true })

    try {
      const { addForm } = this.data
      
      // 确保必填字段存在
      if (!addForm.type || addForm.type === '') {
        addForm.type = '上衣'
      }
      
      // 处理数字字段
      const itemData = {
        type: addForm.type,
        name: addForm.name.trim(),
        color: addForm.color.trim(),
        brand: addForm.brand ? addForm.brand.trim() : null,
        size: addForm.size ? addForm.size.trim() : null,
        material: addForm.material ? addForm.material.trim() : null,
        description: addForm.description ? addForm.description.trim() : null,
        purchase_price: addForm.purchase_price ? parseFloat(addForm.purchase_price) : null,
        purchase_date: addForm.purchase_date || null,
        purchase_place: addForm.purchase_place ? addForm.purchase_place.trim() : null,
        season: addForm.season || null,
        occasion: addForm.occasion ? addForm.occasion.trim() : null,
        style_tags: addForm.style_tags && addForm.style_tags.length > 0 ? addForm.style_tags : null
      }
      
      // 移除空值和undefined
      Object.keys(itemData).forEach(key => {
        if (itemData[key] === '' || itemData[key] === null || itemData[key] === undefined) {
          delete itemData[key]
        }
      })

      console.log('提交的数据:', itemData)

      // 创建物品
      const createResult = await this.callAPI('POST', '/api/wardrobe/items', itemData)
      console.log('创建结果:', createResult)
      
      const itemId = createResult.data.item_id

      // 上传图片
      const uploadResult = await this.uploadItemImage(itemId, this.data.uploadedImage)
      console.log('图片上传结果:', uploadResult)
      
      this.showToast('添加成功！', 'success')
      
      // 重置表单
      this.resetForm()
      
      // 切换回列表视图并刷新数据
      this.setData({ currentView: 'list' })
      this.refreshData()
      
    } catch (error) {
      console.error('添加物品失败:', error)
      let errorMessage = '添加失败'
      
      // 处理具体错误信息
      if (error.message && typeof error.message === 'string') {
        errorMessage = error.message
      } else if (error.detail) {
        errorMessage = error.detail
      }
      
      this.showToast(errorMessage, 'error')
    } finally {
      this.setData({ isLoading: false })
    }
  },

  // 上传物品图片
  async uploadItemImage(itemId, imagePath) {
    return new Promise((resolve, reject) => {
      const token = tt.getStorageSync('fashion_auth_token')
      
      tt.uploadFile({
        url: `${app.globalData.baseURL}/api/wardrobe/items/${itemId}/upload-image`,
        filePath: imagePath,
        name: 'file',
        header: {
          'Authorization': `Bearer ${token}`
        },
        success: (res) => {
          const data = JSON.parse(res.data)
          if (data.success) {
            resolve(data)
          } else {
            reject(new Error(data.message || '图片上传失败'))
          }
        },
        fail: reject
      })
    })
  },

  // 重置表单
  resetForm() {
    // 重置标签选中状态
    let commonTags = this.data.commonTags.map(tag => ({
      ...tag,
      selected: false
    }))
    
    this.setData({
      addForm: {
        type: '上衣',
        name: '',
        brand: '',
        color: '',
        size: '',
        material: '',
        description: '',
        purchase_price: '',
        purchase_date: '',
        purchase_place: '',
        season: '',
        occasion: '',
        style_tags: []
      },
      commonTags: commonTags,
      selectedTags: [],
      uploadedImage: '',
      errors: {}
    })
  },

  // 调用API的统一方法
  callAPI(method, endpoint, data = null) {
    return new Promise((resolve, reject) => {
      const token = tt.getStorageSync('fashion_auth_token')
      
      console.log('API调用:', method, endpoint, data)
      
      tt.request({
        url: `${app.globalData.baseURL}${endpoint}`,
        method,
        header: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        data,
        success: (res) => {
          console.log('API响应:', res)
          
          if (res.statusCode === 200) {
            resolve(res.data)
          } else if (res.statusCode === 401) {
            reject(new Error('登录已过期'))
          } else if (res.statusCode === 422) {
            console.error('422错误详情:', res.data)
            const errorMsg = res.data?.detail || '数据验证失败，请检查输入信息'
            reject(new Error(errorMsg))
          } else {
            console.error('其他错误:', res.statusCode, res.data)
            reject(new Error(res.data?.detail || res.data?.message || '请求失败'))
          }
        },
        fail: (error) => {
          console.error('网络请求失败:', error)
          reject(new Error('网络请求失败，请检查网络连接'))
        }
      })
    })
  },

  // 处理认证错误
  handleAuthError(error) {
    if (error.message.includes('登录已过期') || error.message.includes('认证')) {
      app.logout()
    } else {
      this.showToast(error.message || '加载失败', 'error')
    }
  },

  // 跳转到登录页面
  goToLogin() {
    tt.navigateTo({
      url: '/pages/login/login'
    })
  },

  // 底部导航栏切换
  switchTab(e) {
    const tab = e.currentTarget.dataset.tab
    const tabMap = {
      'index': '/pages/index/index',
      'analysis': '/pages/analysis/analysis',
      'wardrobe': '/pages/wardrobe/wardrobe',
      'profile': '/pages/profile/profile'
    }

    if (tab === 'wardrobe') {
      // 当前已在衣橱页面，不需要跳转
      return
    }

    const url = tabMap[tab]
    if (!url) {
      this.showToast('页面开发中...', 'none')
      return
    }

    tt.switchTab({ url })
  },

  // 工具方法：显示提示
  showToast(title, icon = 'none') {
    tt.showToast({
      title,
      icon: icon === 'error' ? 'none' : icon,
      duration: icon === 'loading' ? 0 : 2000,
      mask: icon === 'loading'
    })
  },

  // 工具方法：显示确认对话框
  showConfirm(options) {
    return new Promise((resolve) => {
      tt.showModal({
        title: options.title || '提示',
        content: options.content || '',
        confirmText: options.confirmText || '确定',
        cancelText: options.cancelText || '取消',
        success: (res) => {
          resolve(res.confirm)
        }
      })
    })
  },

  // 分享功能
  onShareAppMessage() {
    return {
      title: 'AI穿搭助手 - 我的时尚衣橱',
      desc: '智能管理，时尚搭配，记录每一个美好瞬间',
      path: '/pages/index/index'
    }
  },

  // AI机器人点击事件
  onAIBotClick(e) {
    console.log('AI机器人被点击:', e.detail)
    
    // 触觉反馈
    tt.vibrateShort({
      type: 'medium'
    })
    
    // 根据当前状态显示不同的提示
    let content = ''
    let confirmText = '知道了'
    
    if (!this.data.isLoggedIn) {
      content = '登录后我可以帮你智能管理衣橱！\n\n分析你的穿搭偏好，推荐最佳搭配，让每一件衣服都发挥最大价值。'
      confirmText = '去登录'
    } else if (this.data.wardrobeItems.length === 0) {
      content = '开始添加你的衣物吧！\n\n我可以帮你分析每件衣服的风格特征，建立个性化的时尚档案。'
      confirmText = '添加衣物'
    } else {
      content = `你的衣橱已有 ${this.data.statistics.total_items} 件单品！\n\n我可以为你分析搭配建议，找出最适合的穿搭组合。`
      confirmText = '查看建议'
    }
    
    tt.showModal({
      title: '🤖 衣橱管家',
      content: content,
      confirmText: confirmText,
      showCancel: false,
      success: (res) => {
        if (res.confirm) {
          if (!this.data.isLoggedIn) {
            this.goToLogin()
          } else if (this.data.wardrobeItems.length === 0) {
            this.setData({ currentView: 'add' })
          } else {
            // 跳转到AI分析页面
            tt.navigateTo({
              url: '/pages/analysis/analysis'
            })
          }
        }
      }
    })
  },

  // 页面错误处理
  onError(error) {
    console.error('衣橱页面错误:', error)
    this.showToast('页面出现错误', 'error')
  }
})