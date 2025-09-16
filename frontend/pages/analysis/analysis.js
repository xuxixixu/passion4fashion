// pages/analysis/analysis.js

const app = getApp()

// 生成唯一的页面级session_id
function generatePageSessionId() {
  return 'page_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9)
}

Page({
  data: {
    // 页面状态
    currentStep: 1,
    isAnalyzing: false,
    analysisStatus: '',
    
    // 上传的图片
    styleImages: [],
    userImages: [],
    
    // 用户输入
    userName: '',
    textRequirements: '',
    generateAvatar: true,
    
    // 快速标签
    quickTags: [
      { id: 1, text: '上班通勤', selected: false },
      { id: 2, text: '约会穿搭', selected: false },
      { id: 3, text: '聚会派对', selected: false },
      { id: 4, text: '日常休闲', selected: false },
      { id: 5, text: '运动健身', selected: false },
      { id: 6, text: '商务正装', selected: false }
    ],
    
    // 分析结果
    analysisResult: null,
    avatarUrl: null,
    avatarStatus: null,
    
    // 评分
    rating: 0,
    
    // 图片预览
    showPreview: false,
    previewUrl: '',
    
    // Session信息 - 新增页面级session_id
    sessionId: null,
    pageSessionId: null,  // 新增：页面级唯一ID
    
    // 异步任务相关 - 新增
    currentTaskId: null,  // 当前任务ID
    pollTimer: null,      // 轮询定时器
    pollInterval: 5000,   // 轮询间隔（毫秒）
    maxPollAttempts: 100, // 最大轮询次数（5分钟）
    pollAttempts: 0,      // 当前轮询次数
    
    // 头像任务相关 - 新增
    avatarTaskId: null,   // 头像任务ID
    avatarPollTimer: null, // 头像轮询定时器
    avatarPollAttempts: 0, // 头像轮询次数
    maxAvatarPollAttempts: 60 // 头像最大轮询次数（2分钟）
  },

  onLoad(options) {
    console.log('AI分析页面加载', options)
    this.initializePage()
  },

  onShow() {
    // 更新导航栏状态
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({
        selected: 1
      })
    }
  },

  onUnload() {
    // 清理定时器
    this.clearAllTimers()
  },

  // 清理所有定时器
  clearAllTimers() {
    if (this.pollTimer) {
      clearInterval(this.pollTimer)
      this.pollTimer = null
    }
    if (this.avatarPollTimer) {
      clearInterval(this.avatarPollTimer)
      this.avatarPollTimer = null
    }
  },

  // 初始化页面
  async initializePage() {
    try {
      // 生成页面级唯一session_id
      const pageSessionId = generatePageSessionId()
      this.setData({ pageSessionId })
      console.log('生成页面级session_id:', pageSessionId)
      
      // 获取全局session信息（用于其他API调用）
      const sessionId = app.globalData.sessionId || tt.getStorageSync('fashion_session_id')
      if (sessionId) {
        this.setData({ sessionId })
      }
      
      // 如果没有全局session，调用健康检查获取
      if (!sessionId) {
        await this.getSessionId()
      }
      
      // 恢复用户名
      const userInfo = app.globalData.userInfo
      if (userInfo && userInfo.nickname) {
        this.setData({ userName: userInfo.nickname })
      }
      
    } catch (error) {
      console.error('页面初始化失败:', error)
      this.showToast('页面初始化失败', 'error')
    }
  },

  // 获取全局Session ID
  async getSessionId() {
    return new Promise((resolve, reject) => {
      tt.request({
        url: `${app.globalData.baseURL}/health`,
        method: 'GET',
        success: (res) => {
          const sessionId = res.header['X-Session-ID'] || res.header['x-session-id']
          if (sessionId) {
            this.setData({ sessionId })
            app.globalData.sessionId = sessionId
            tt.setStorageSync('fashion_session_id', sessionId)
            console.log('获取到全局session_id:', sessionId)
          }
          resolve(sessionId)
        },
        fail: reject
      })
    })
  },

  // 步骤切换
  goToStep(e) {
    const step = parseInt(e.currentTarget.dataset.step)
    this.setData({ currentStep: step })
  },

  nextStep() {
    const { currentStep } = this.data
    if (currentStep < 3) {
      this.setData({ 
        currentStep: currentStep + 1,
        analysisStatus: currentStep === 1 ? '接下来分析你的个人特征' : '最后一步，让AI了解你的需求'
      })
    }
  },

  prevStep() {
    const { currentStep } = this.data
    if (currentStep > 1) {
      this.setData({ 
        currentStep: currentStep - 1,
        analysisStatus: currentStep === 2 ? '让AI读懂你的时尚密码' : '接下来分析你的个人特征'
      })
    }
  },

  // 选择风格图片
  chooseStyleImages() {
    const maxCount = 3 - this.data.styleImages.length
    
    tt.chooseImage({
      count: maxCount,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        this.uploadImages(res.tempFilePaths, 'style')
      },
      fail: (error) => {
        console.error('选择图片失败:', error)
        this.showToast('选择图片失败', 'error')
      }
    })
  },

  // 选择用户照片
  chooseUserImages() {
    const maxCount = 2 - this.data.userImages.length
    
    tt.chooseImage({
      count: maxCount,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        this.uploadImages(res.tempFilePaths, 'user')
      },
      fail: (error) => {
        console.error('选择图片失败:', error)
        this.showToast('选择图片失败', 'error')
      }
    })
  },

  // 上传图片到服务器
  async uploadImages(filePaths, imageType) {
    tt.showLoading({ title: '上传中...' })
    
    try {
      const uploadPromises = filePaths.map(filePath => this.uploadSingleImage(filePath, imageType))
      const results = await Promise.all(uploadPromises)
      
      // 更新数据
      const imageData = results.map(result => ({
        url: result.tempFilePath,
        serverName: result.savedName,
        originalName: result.originalName
      }))
      
      if (imageType === 'style') {
        this.setData({
          styleImages: [...this.data.styleImages, ...imageData]
        })
      } else {
        this.setData({
          userImages: [...this.data.userImages, ...imageData]
        })
      }
      
      tt.hideLoading()
      this.showToast('图片上传成功', 'success')
      
    } catch (error) {
      tt.hideLoading()
      console.error('图片上传失败:', error)
      this.showToast('图片上传失败，请重试', 'error')
    }
  },

  // 上传单张图片
  uploadSingleImage(filePath, imageType) {
    return new Promise((resolve, reject) => {
      // 获取原始文件名
      const originalFileName = filePath.split('/').pop()
      
      // 构造带页面session_id前缀的文件名
      const prefixedFileName = `${this.data.pageSessionId}_${originalFileName}`
      
      console.log('上传图片:', {
        originalFileName,
        prefixedFileName,
        pageSessionId: this.data.pageSessionId,
        imageType
      })
      
      tt.uploadFile({
        url: `${app.globalData.baseURL}/api/style/upload-images`,
        filePath: filePath,
        name: 'files',
        formData: {
          image_type: imageType,
          page_session_id: this.data.pageSessionId, // 传递页面session_id
          prefixed_filename: prefixedFileName       // 传递带前缀的文件名
        },
        header: {
          'X-Session-ID': this.data.sessionId
        },
        success: (res) => {
          try {
            const data = JSON.parse(res.data)
            if (data.success && data.saved_files && data.saved_files.length > 0) {
              resolve({
                tempFilePath: filePath,
                savedName: data.saved_files[0].saved_name,
                originalName: originalFileName
              })
            } else {
              reject(new Error('上传响应格式错误'))
            }
          } catch (error) {
            reject(error)
          }
        },
        fail: reject
      })
    })
  },

  // 删除图片
  deleteImage(e) {
    const { type, index } = e.currentTarget.dataset
    
    if (type === 'style') {
      const styleImages = [...this.data.styleImages]
      styleImages.splice(index, 1)
      this.setData({ styleImages })
    } else {
      const userImages = [...this.data.userImages]
      userImages.splice(index, 1)
      this.setData({ userImages })
    }
  },

  // 预览图片
  previewImage(e) {
    const { type, index } = e.currentTarget.dataset
    const images = type === 'style' ? this.data.styleImages : this.data.userImages
    
    this.setData({
      showPreview: true,
      previewUrl: images[index].url
    })
  },

  // 关闭预览
  closePreview() {
    this.setData({
      showPreview: false,
      previewUrl: ''
    })
  },

  // 用户名输入
  onUserNameInput(e) {
    this.setData({
      userName: e.detail.value
    })
  },

  // 文字需求输入
  onTextInput(e) {
    this.setData({
      textRequirements: e.detail.value
    })
  },

  // 切换标签选择
  toggleTag(e) {
    const tagId = e.currentTarget.dataset.id
    const quickTags = this.data.quickTags.map(tag => {
      if (tag.id === tagId) {
        return { ...tag, selected: !tag.selected }
      }
      return tag
    })
    
    this.setData({ quickTags })
    
    // 更新文字需求
    const selectedTags = quickTags.filter(tag => tag.selected).map(tag => tag.text)
    const existingText = this.data.textRequirements.replace(/，?[^，]*场合/g, '')
    const newText = selectedTags.length > 0 
      ? `${existingText}${existingText ? '，' : ''}适合${selectedTags.join('、')}场合`
      : existingText
    
    this.setData({ textRequirements: newText })
  },

  // 头像生成开关
  onAvatarToggle(e) {
    this.setData({
      generateAvatar: e.detail.value
    })
  },

  // 开始AI分析（异步版本）
  async startAnalysis() {
    // 验证输入
    if (!this.validateInput()) {
      return
    }
    
    // 清理之前的任务
    this.clearAllTimers()
    
    this.setData({ 
      isAnalyzing: true,
      analysisStatus: '🚀 正在启动AI分析引擎...',
      pollAttempts: 0,
      currentTaskId: null,
      analysisResult: null
    })
    
    try {
      // 构建请求参数
      const requestData = {
        generate_avatar: this.data.generateAvatar,
        page_session_id: this.data.pageSessionId  // 新增：传递页面session_id
      }
      
      // 添加风格图片（传递服务器上的文件名）
      if (this.data.styleImages.length > 0) {
        requestData.style_image_names = this.data.styleImages.map(img => img.serverName)
      }
      
      // 添加用户照片（传递服务器上的文件名）
      if (this.data.userImages.length > 0) {
        requestData.user_image_names = this.data.userImages.map(img => img.serverName)
      }
      
      // 添加文字需求
      if (this.data.textRequirements.trim()) {
        requestData.text_requirements = this.data.textRequirements.trim()
      }
      
      // 添加用户名
      if (this.data.userName.trim()) {
        requestData.user_name = this.data.userName.trim()
      }
      
      console.log('发送异步分析请求:', requestData)
      
      // 调用异步分析接口
      const taskResponse = await this.callAsyncAnalysisAPI(requestData)
      
      if (taskResponse.success) {
        this.setData({ 
          currentTaskId: taskResponse.task_id,
          analysisStatus: '✅ 任务已启动，正在处理中...'
        })
        
        console.log('获得任务ID:', taskResponse.task_id)
        
        // 开始轮询任务状态
        this.startTaskPolling(taskResponse.task_id)
      } else {
        throw new Error(taskResponse.message || '启动分析任务失败')
      }
      
    } catch (error) {
      console.error('启动AI分析失败:', error)
      this.setData({ 
        isAnalyzing: false,
        analysisStatus: '❌ 启动分析失败，请检查网络后重试'
      })
      this.showToast('启动分析失败，请重试', 'error')
    }
  },

  // 调用异步分析API
  callAsyncAnalysisAPI(requestData) {
    return new Promise((resolve, reject) => {
      tt.request({
        url: `${app.globalData.baseURL}/api/style/analyze`,
        method: 'POST',
        header: {
          'Content-Type': 'application/json',
          'X-Session-ID': this.data.sessionId
        },
        data: requestData,
        timeout: 10000, // 10秒超时（只是启动任务）
        success: (res) => {
          console.log('异步分析API响应:', res)
          
          if (res.statusCode === 200) {
            resolve(res.data)
          } else {
            reject(new Error(res.data.message || '启动任务失败'))
          }
        },
        fail: (error) => {
          console.error('异步分析API请求失败:', error)
          reject(error)
        }
      })
    })
  },

  // 开始轮询任务状态
  startTaskPolling(taskId) {
    console.log('开始轮询任务状态:', taskId)
    
    // 立即执行一次轮询
    this.pollTaskStatus(taskId)
    
    // 设置定时轮询
    this.pollTimer = setInterval(() => {
      this.pollTaskStatus(taskId)
    }, this.data.pollInterval)
  },

  // 轮询任务状态
  async pollTaskStatus(taskId) {
    const { pollAttempts, maxPollAttempts } = this.data
    
    // 检查是否超过最大轮询次数
    if (pollAttempts >= maxPollAttempts) {
      console.warn('轮询超时，停止轮询')
      this.stopTaskPolling()
      this.setData({
        isAnalyzing: false,
        analysisStatus: '⏰ 处理超时，请重新尝试'
      })
      this.showToast('处理超时，请重试', 'error')
      return
    }
    
    try {
      const statusResponse = await this.checkTaskStatus(taskId)
      const newAttempts = pollAttempts + 1
      
      this.setData({ pollAttempts: newAttempts })
      
      console.log(`任务状态轮询 ${newAttempts}/${maxPollAttempts}:`, statusResponse)
      
      if (statusResponse.success) {
        // 更新状态显示
        if (statusResponse.progress) {
          this.setData({ analysisStatus: statusResponse.progress })
        }
        
        if (statusResponse.status === 'completed') {
          // 任务完成
          this.stopTaskPolling()
          this.handleTaskCompleted(statusResponse.result)
        } else if (statusResponse.status === 'error') {
          // 任务失败
          this.stopTaskPolling()
          this.handleTaskError(statusResponse.error_message)
        }
        // 如果是 pending 或 running 状态，继续轮询
      } else {
        // API调用失败，但不停止轮询（可能是临时网络问题）
        console.warn('轮询API调用失败:', statusResponse)
      }
      
    } catch (error) {
      console.error('轮询任务状态失败:', error)
      // 网络错误不停止轮询，继续尝试
    }
  },

  // 检查任务状态
  checkTaskStatus(taskId) {
    return new Promise((resolve, reject) => {
      tt.request({
        url: `${app.globalData.baseURL}/api/style/task-status/${taskId}`,
        method: 'GET',
        header: {
          'X-Session-ID': this.data.sessionId
        },
        timeout: 8000, // 8秒超时
        success: (res) => {
          if (res.statusCode === 200) {
            resolve(res.data)
          } else {
            reject(new Error('状态查询失败'))
          }
        },
        fail: reject
      })
    })
  },

  // 停止任务轮询
  stopTaskPolling() {
    if (this.pollTimer) {
      clearInterval(this.pollTimer)
      this.pollTimer = null
    }
    console.log('停止任务轮询')
  },

  // 开始头像任务轮询
  startAvatarTaskPolling(avatarTaskId) {
    console.log('开始轮询头像任务状态:', avatarTaskId)
    
    // 立即执行一次轮询
    this.pollAvatarTaskStatus(avatarTaskId)
    
    // 设置定时轮询
    this.avatarPollTimer = setInterval(() => {
      this.pollAvatarTaskStatus(avatarTaskId)
    }, this.data.pollInterval)
  },

  // 轮询头像任务状态
  async pollAvatarTaskStatus(avatarTaskId) {
    const { avatarPollAttempts, maxAvatarPollAttempts } = this.data
    
    // 检查是否超过最大轮询次数
    if (avatarPollAttempts >= maxAvatarPollAttempts) {
      console.warn('头像轮询超时，停止轮询')
      this.stopAvatarTaskPolling()
      this.setData({
        avatarStatus: 'timeout',
        analysisStatus: '✅ 时尚分析完成，头像生成超时'
      })
      this.showToast('头像生成超时', 'none')
      return
    }
    
    try {
      const statusResponse = await this.checkAvatarTaskStatus(avatarTaskId)
      const newAttempts = avatarPollAttempts + 1
      
      this.setData({ avatarPollAttempts: newAttempts })
      
      console.log(`头像任务状态轮询 ${newAttempts}/${maxAvatarPollAttempts}:`, statusResponse)
      
      if (statusResponse.success) {
        if (statusResponse.status === 'completed') {
          // 头像生成完成
          this.stopAvatarTaskPolling()
          this.handleAvatarTaskCompleted(statusResponse.result)
        } else if (statusResponse.status === 'error') {
          // 头像生成失败
          this.stopAvatarTaskPolling()
          this.handleAvatarTaskError(statusResponse.error_message, statusResponse.result)
        }
        // 如果是 generating 状态，继续轮询
      } else {
        // API调用失败，但不停止轮询（可能是临时网络问题）
        console.warn('头像轮询API调用失败:', statusResponse)
      }
      
    } catch (error) {
      console.error('轮询头像任务状态失败:', error)
      // 网络错误不停止轮询，继续尝试
    }
  },

  // 检查头像任务状态
  checkAvatarTaskStatus(avatarTaskId) {
    return new Promise((resolve, reject) => {
      tt.request({
        url: `${app.globalData.baseURL}/api/style/avatar-task-status/${avatarTaskId}`,
        method: 'GET',
        header: {
          'X-Session-ID': this.data.sessionId
        },
        timeout: 8000, // 8秒超时
        success: (res) => {
          if (res.statusCode === 200) {
            resolve(res.data)
          } else {
            reject(new Error('头像状态查询失败'))
          }
        },
        fail: reject
      })
    })
  },

  // 停止头像任务轮询
  stopAvatarTaskPolling() {
    if (this.avatarPollTimer) {
      clearInterval(this.avatarPollTimer)
      this.avatarPollTimer = null
    }
    console.log('停止头像任务轮询')
  },

  // 处理头像任务完成
  handleAvatarTaskCompleted(avatarResult) {
    console.log('头像任务完成，结果:', avatarResult)
    
    if (avatarResult && avatarResult.avatar_url) {
      this.setData({
        avatarUrl: avatarResult.avatar_url,
        avatarStatus: 'completed',
        analysisStatus: '🎉 分析完成！专属建议和个性化头像都已为你准备好'
      })
      this.showToast('专属头像生成完成！', 'success')
    } else if (avatarResult && avatarResult.fallback_avatar_url) {
      // 有备用头像
      this.setData({
        avatarUrl: avatarResult.fallback_avatar_url,
        avatarStatus: 'fallback',
        analysisStatus: '✅ 时尚分析完成，头像使用备用方案'
      })
      this.showToast('头像生成完成（备用）', 'success')
    } else {
      this.handleAvatarTaskError('头像数据异常', avatarResult)
    }
  },

  // 处理头像任务错误
  handleAvatarTaskError(errorMessage, avatarResult) {
    console.error('头像任务失败:', errorMessage, avatarResult)
    
    // 检查是否有备用头像
    if (avatarResult && avatarResult.fallback_avatar_url) {
      this.setData({
        avatarUrl: avatarResult.fallback_avatar_url,
        avatarStatus: 'fallback',
        analysisStatus: '✅ 时尚分析完成，头像生成遇到问题但提供了备用头像'
      })
      this.showToast('头像生成失败，使用备用头像', 'none')
    } else {
      this.setData({
        avatarStatus: 'error',
        analysisStatus: '✅ 时尚分析完成，但头像生成遇到了问题'
      })
      this.showToast('头像生成失败', 'error')
    }
  },

  // 处理任务完成
  handleTaskCompleted(result) {
    console.log('任务完成，结果:', result)
    
    // 基础状态设置
    this.setData({
      isAnalyzing: false,
      analysisResult: result
    })
    
    // 检查头像生成状态
    if (result.avatar_info) {
      if (result.avatar_info.status === 'generating') {
        // 启动头像轮询
        const avatarTaskId = result.avatar_info.avatar_task_id
        if (avatarTaskId) {
          this.setData({ 
            avatarTaskId: avatarTaskId,
            avatarStatus: 'generating',
            analysisStatus: '✅ 时尚分析完成！专属头像正在后台生成中',
            avatarPollAttempts: 0
          })
          this.startAvatarTaskPolling(avatarTaskId)
        }
      } else if (result.avatar_info.status === 'completed') {
        // 头像已完成（理论上不会出现，因为现在是独立任务）
        this.setData({ 
          avatarUrl: result.avatar_info.avatar_url,
          avatarStatus: 'completed',
          analysisStatus: '🎉 分析完成！专属建议和个性化头像都已为你准备好'
        })
      } else if (result.avatar_info.status === 'no_user_images') {
        this.setData({ 
          avatarStatus: 'no_user_images',
          analysisStatus: '✨ 分析完成！（需要用户照片才能生成头像）'
        })
      }
    } else {
      this.setData({
        analysisStatus: '✨ 分析完成！为你量身定制的建议已生成'
      })
    }
    
    // 滚动到结果区域
    this.scrollToResult()
    
    // 分析完成后重新生成页面session_id，为下次分析做准备
    this.refreshPageSessionId()
    
    this.showToast('AI分析完成！', 'success')
  },

  // 处理任务错误
  handleTaskError(errorMessage) {
    console.error('任务处理失败:', errorMessage)
    
    this.setData({
      isAnalyzing: false,
      analysisStatus: `❌ 分析失败：${errorMessage || '未知错误'}`
    })
    
    this.showToast('分析失败，请重试', 'error')
  },

  // 刷新页面session_id
  refreshPageSessionId() {
    const newPageSessionId = generatePageSessionId()
    this.setData({ pageSessionId: newPageSessionId })
    console.log('刷新页面session_id:', newPageSessionId)
  },

  // 验证输入
  validateInput() {
    const { styleImages, userImages, textRequirements } = this.data
    
    if (styleImages.length === 0 && userImages.length === 0 && !textRequirements.trim()) {
      this.showToast('请至少上传一张图片或填写文字需求', 'none')
      return false
    }
    
    return true
  },

  // 重新分析
  retryAnalysis() {
    // 清理所有定时器
    this.clearAllTimers()
    
    this.setData({
      currentStep: 1,
      analysisResult: null,
      avatarUrl: null,
      avatarStatus: null,
      rating: 0,
      analysisStatus: '',
      styleImages: [],    // 清空已上传的图片
      userImages: [],     // 清空已上传的图片
      isAnalyzing: false,
      currentTaskId: null,
      pollAttempts: 0,
      // 清理头像任务相关状态
      avatarTaskId: null,
      avatarPollAttempts: 0
    })
    
    // 重新生成页面session_id
    this.refreshPageSessionId()
  },

  // 滚动到结果区域
  scrollToResult() {
    setTimeout(() => {
      tt.pageScrollTo({
        selector: '.result-section',
        duration: 500
      })
    }, 100)
  },

  // 保存头像
  saveAvatar() {
    if (!this.data.avatarUrl) {
      this.showToast('暂无头像可保存', 'none')
      return
    }
    
    tt.downloadFile({
      url: this.data.avatarUrl,
      success: (res) => {
        tt.saveImageToPhotosAlbum({
          filePath: res.tempFilePath,
          success: () => {
            this.showToast('头像已保存到相册', 'success')
          },
          fail: () => {
            this.showToast('保存失败，请检查相册权限', 'error')
          }
        })
      },
      fail: () => {
        this.showToast('下载失败', 'error')
      }
    })
  },

  // 取消分析任务
  cancelAnalysis() {
    tt.showModal({
      title: '确认取消',
      content: '确定要取消当前分析任务吗？',
      confirmText: '确定取消',
      cancelText: '继续等待',
      success: (res) => {
        if (res.confirm) {
          // 停止所有轮询
          this.stopTaskPolling()
          this.stopAvatarTaskPolling()
          
          // 重置状态
          this.setData({
            isAnalyzing: false,
            analysisStatus: '已取消分析任务',
            currentTaskId: null,
            pollAttempts: 0,
            avatarTaskId: null,
            avatarPollAttempts: 0,
            avatarStatus: null
          })
          
          this.showToast('分析任务已取消', 'none')
        }
      }
    })
  },

  // 分享结果
  shareResult() {
    const { analysisResult } = this.data
    if (!analysisResult) {
      this.showToast('暂无分析结果可分享', 'none')
      return
    }
    
    // 截取前50个字符作为分享内容
    const shareText = analysisResult.content.substring(0, 50) + '...'
    
    tt.showShareMenu({
      withShareTicket: true,
      success: () => {
        console.log('分享菜单显示成功')
      }
    })
  },

  // 设置评分
  setRating(e) {
    const rating = e.currentTarget.dataset.rating
    this.setData({ rating })
    
    // 简单的评分反馈
    if (rating >= 4) {
      this.showToast('感谢你的好评！', 'success')
    } else if (rating >= 3) {
      this.showToast('谢谢反馈，我们会继续改进', 'none')
    } else {
      this.showToast('抱歉没有满足你的期望，我们会努力优化', 'none')
    }
  },

  // 导航栏切换
  switchTab(e) {
    const tab = e.currentTarget.dataset.tab
    const tabMap = {
      'index': '/pages/index/index',
      'analysis': '/pages/analysis/analysis',
      'wardrobe': '/pages/wardrobe/wardrobe',
      'profile': '/pages/profile/profile'
    }

    if (tab === 'analysis') {
      // 当前已在分析页，不需要跳转
      return
    }

    const url = tabMap[tab]
    if (!url) {
      this.showToast('页面开发中...', 'none')
      return
    }

    // 对于需要登录的页面，检查登录状态
    if (['wardrobe', 'profile'].includes(tab)) {
      const token = tt.getStorageSync('fashion_auth_token')
      if (!token) {
        this.showLoginModal()
        return
      }
    }

    if (['index'].includes(tab)) {
      tt.switchTab({ url })
    } else if (['wardrobe', 'profile'].includes(tab)) {
      tt.switchTab({ url })
    } else {
      tt.navigateTo({ url })
    }
  },

  // 显示登录提示
  showLoginModal() {
    tt.showModal({
      title: '需要登录',
      content: '此功能需要登录后使用，是否前往登录？',
      confirmText: '去登录',
      cancelText: '稍后',
      success: (res) => {
        if (res.confirm) {
          tt.navigateTo({
            url: '/pages/login/login'
          })
        }
      }
    })
  },

  // 显示提示信息
  showToast(title, icon = 'none') {
    tt.showToast({
      title,
      icon: icon === 'error' ? 'none' : icon,
      duration: icon === 'loading' ? 0 : 2000,
      mask: icon === 'loading'
    })
  },

  // 分享功能
  onShareAppMessage() {
    const { analysisResult, avatarUrl } = this.data
    
    let title = 'AI穿搭助手 - 智能风格分析'
    let desc = '让AI为你定制专属时尚，发现你的独特魅力！'
    let imageUrl = avatarUrl || ''
    
    if (analysisResult) {
      const shortContent = analysisResult.content.substring(0, 30)
      title = `我的AI时尚分析：${shortContent}...`
      desc = '快来看看AI为我推荐的穿搭风格！'
    }
    
    return {
      title,
      desc,
      path: '/pages/analysis/analysis',
      imageUrl
    }
  },

  // 分享到朋友圈
  onShareTimeline() {
    const { analysisResult } = this.data
    
    let title = 'AI穿搭助手为我量身定制了专属风格！'
    
    if (analysisResult) {
      const shortContent = analysisResult.content.substring(0, 20)
      title = `${shortContent}... - AI穿搭助手`
    }
    
    return {
      title,
      query: 'from=timeline&shared=1'
    }
  },

  // AI机器人点击事件
  onAIBotClick(e) {
    console.log('AI机器人被点击:', e.detail)
    
    // 触觉反馈
    tt.vibrateShort({
      type: 'medium'
    })
    
    // 根据当前页面状态显示不同的提示
    let content = ''
    let confirmText = '知道了'
    
    if (this.data.isAnalyzing) {
      content = '我正在努力分析你的风格偏好中...\n\n请稍等片刻，很快就能为你生成专属的穿搭建议！'
    } else if (this.data.analysisResult) {
      content = '分析已完成！我已经为你生成了个性化的穿搭建议。\n\n你可以查看详细的风格分析和推荐搭配哦~'
    } else {
      content = '欢迎使用AI风格分析！\n\n上传你喜欢的风格图片和个人照片，我会为你生成专属的时尚建议。'
      confirmText = '开始上传'
    }
    
    tt.showModal({
      title: '🤖 AI分析助手',
      content: content,
      confirmText: confirmText,
      showCancel: false,
      success: (res) => {
        if (res.confirm && !this.data.isAnalyzing && !this.data.analysisResult) {
          // 如果还没开始分析，引导用户到第一步
          this.setData({ currentStep: 1 })
        }
      }
    })
  },

  // 页面错误处理
  onError(error) {
    console.error('页面错误:', error)
    this.showToast('页面出现错误', 'error')
  }
})