// pages/profile/profile.js

const app = getApp()

Page({
  data: {
    // 用户信息
    userInfo: null,
    avatarUrl: '',
    
    // 页面状态
    isLoading: false,
    isLoggedIn: false,
    
    // 编辑状态
    isEditing: false,
    editForm: {
      nickname: '',
      signature: '',
      gender: '',
      height: '',
      weight: '',
      body_shape: '',
      skin_tone: ''
    },
    
    // 性别选项
    genderOptions: [
      { value: '男', label: '男', icon: '👨' },
      { value: '女', label: '女', icon: '👩' },
      { value: '其他', label: '其他', icon: '🌈' }
    ],
    
    // 体型选项
    bodyShapeOptions: [
      { value: '梨形', label: '梨形', desc: '下半身较丰满' },
      { value: '苹果形', label: '苹果形', desc: '腰部较圆润' },
      { value: '沙漏形', label: '沙漏形', desc: '腰细胸臀丰满' },
      { value: '矩形', label: '矩形', desc: '身材匀称' },
      { value: '倒三角形', label: '倒三角形', desc: '肩宽臀窄' },
      { value: '椭圆形', label: '椭圆形', desc: '整体圆润' }
    ],
    
    // 肤色选项
    skinToneOptions: [
      { value: '冷调', label: '冷调', desc: '偏粉色调' },
      { value: '暖调', label: '暖调', desc: '偏黄色调' },
      { value: '中性调', label: '中性调', desc: '介于两者之间' }
    ],
    
    // 统计数据
    userStats: {
      analysisCount: 0,
      wardrobeCount: 0,
      points: 0
    },
    
    // 显示选择器
    showGenderPicker: false,
    showBodyShapePicker: false,
    showSkinTonePicker: false,
    
    // 错误信息
    errors: {}
  },

  onLoad(options) {
    console.log('个人信息页面加载', options)
  },

  onShow() {
    // 设置tabBar选中状态
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({
        selected: 3
      })
    }
    
    // 检查登录状态并加载数据
    this.checkLoginAndLoadData()
  },

  onPullDownRefresh() {
    this.loadUserProfile()
    setTimeout(() => {
      tt.stopPullDownRefresh()
    }, 1000)
  },

  // 构建头像完整URL
  buildAvatarUrl(filename) {
    if (!filename) {
      return '/static/default-avatar.png'
    }
    // 如果已经是完整URL，直接返回
    if (filename.startsWith('http://') || filename.startsWith('https://') || filename.startsWith('/')) {
      return filename
    }
    // 构建完整的头像URL
    return `${app.globalData.baseURL}/api/users/avatars/${filename}`
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
      await Promise.all([
        this.loadUserProfile(),
        this.loadUserStats()
      ])
    } catch (error) {
      console.error('加载用户数据失败:', error)
      this.handleAuthError(error)
    } finally {
      this.setData({ isLoading: false })
    }
  },

  // 加载用户资料
  async loadUserProfile() {
    try {
      const userInfo = await this.callAPI('GET', '/api/users/profile')
      
      // 构建完整的头像URL
      const avatarUrl = this.buildAvatarUrl(userInfo.avatar_url)
      
      this.setData({ 
        userInfo,
        avatarUrl: avatarUrl,
        editForm: {
          nickname: userInfo.nickname || '',
          signature: userInfo.signature || '',
          gender: userInfo.gender || '',
          height: userInfo.height ? String(userInfo.height) : '',
          weight: userInfo.weight ? String(userInfo.weight) : '',
          body_shape: userInfo.body_shape || '',
          skin_tone: userInfo.skin_tone || ''
        }
      })
      console.log('用户资料加载成功:', userInfo)
      console.log('头像URL:', avatarUrl)
    } catch (error) {
      console.error('加载用户资料失败:', error)
      throw error
    }
  },

  // 加载用户统计数据
  async loadUserStats() {
    try {
      // 模拟统计数据，实际项目中应该调用真实的API
      const stats = {
        analysisCount: Math.floor(Math.random() * 50) + 10,
        wardrobeCount: Math.floor(Math.random() * 100) + 20,
        points: this.data.userInfo?.points || 0
      }
      
      this.setData({ userStats: stats })
      console.log('用户统计数据加载成功:', stats)
    } catch (error) {
      console.error('加载统计数据失败:', error)
    }
  },

  // 调用API的统一方法
  callAPI(method, endpoint, data = null) {
    return new Promise((resolve, reject) => {
      const token = tt.getStorageSync('fashion_auth_token')
      
      tt.request({
        url: `${app.globalData.baseURL}${endpoint}`,
        method,
        header: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        data,
        success: (res) => {
          if (res.statusCode === 200) {
            resolve(res.data)
          } else if (res.statusCode === 401) {
            reject(new Error('登录已过期'))
          } else {
            reject(new Error(res.data?.detail || '请求失败'))
          }
        },
        fail: (error) => {
          reject(new Error('网络请求失败'))
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

  // 开始编辑
  startEdit() {
    this.setData({ 
      isEditing: true,
      errors: {}
    })
  },

  // 取消编辑
  cancelEdit() {
    // 恢复原始数据
    const { userInfo } = this.data
    this.setData({ 
      isEditing: false,
      editForm: {
        nickname: userInfo.nickname || '',
        signature: userInfo.signature || '',
        gender: userInfo.gender || '',
        height: userInfo.height ? String(userInfo.height) : '',
        weight: userInfo.weight ? String(userInfo.weight) : '',
        body_shape: userInfo.body_shape || '',
        skin_tone: userInfo.skin_tone || ''
      },
      errors: {}
    })
  },

  // 输入框变化处理
  onInputChange(e) {
    const { field } = e.currentTarget.dataset
    const value = e.detail.value
    
    this.setData({
      [`editForm.${field}`]: value,
      [`errors.${field}`]: '' // 清除错误信息
    })
  },

  // 显示选择器
  showPicker(e) {
    const { type } = e.currentTarget.dataset
    this.setData({
      [`show${type}Picker`]: true
    })
  },

  // 隐藏选择器
  hidePicker(e) {
    const { type } = e.currentTarget.dataset
    this.setData({
      [`show${type}Picker`]: false
    })
  },

  // 选择选项
  selectOption(e) {
    const { type, value } = e.currentTarget.dataset
    const fieldMap = {
      'Gender': 'gender',
      'BodyShape': 'body_shape', 
      'SkinTone': 'skin_tone'
    }
    
    const field = fieldMap[type]
    this.setData({
      [`editForm.${field}`]: value,
      [`show${type}Picker`]: false,
      [`errors.${field}`]: ''
    })
  },

  // 验证表单
  validateForm() {
    const { editForm } = this.data
    const errors = {}
    
    // 昵称验证
    if (editForm.nickname && editForm.nickname.length > 50) {
      errors.nickname = '昵称不能超过50个字符'
    }
    
    // 个性签名验证
    if (editForm.signature && editForm.signature.length > 200) {
      errors.signature = '个性签名不能超过200个字符'
    }
    
    // 身高验证
    if (editForm.height) {
      const height = parseFloat(editForm.height)
      if (isNaN(height) || height < 100 || height > 250) {
        errors.height = '身高应在100-250cm之间'
      }
    }
    
    // 体重验证
    if (editForm.weight) {
      const weight = parseFloat(editForm.weight)
      if (isNaN(weight) || weight < 30 || weight > 200) {
        errors.weight = '体重应在30-200kg之间'
      }
    }
    
    this.setData({ errors })
    return Object.keys(errors).length === 0
  },

  // 保存用户信息
  async saveProfile() {
    if (!this.validateForm()) {
      return
    }

    this.setData({ isLoading: true })

    try {
      const { editForm } = this.data
      
      // 处理数字字段
      const updateData = {
        nickname: editForm.nickname || null,
        signature: editForm.signature || null,
        gender: editForm.gender || null,
        height: editForm.height ? parseFloat(editForm.height) : null,
        weight: editForm.weight ? parseFloat(editForm.weight) : null,
        body_shape: editForm.body_shape || null,
        skin_tone: editForm.skin_tone || null
      }

      // 移除空值
      Object.keys(updateData).forEach(key => {
        if (updateData[key] === null || updateData[key] === '') {
          delete updateData[key]
        }
      })

      const updatedUser = await this.callAPI('PUT', '/api/users/profile', updateData)
      
      // 构建更新后的头像URL
      const avatarUrl = this.buildAvatarUrl(updatedUser.data?.avatar_url || updatedUser.avatar_url)
      
      // 更新本地数据
      this.setData({ 
        userInfo: updatedUser.data || updatedUser,
        avatarUrl: avatarUrl,
        isEditing: false
      })
      
      // 更新全局用户信息
      app.globalData.userInfo = updatedUser.data || updatedUser
      tt.setStorageSync('fashion_user_info', updatedUser.data || updatedUser)
      
      this.showToast('保存成功！', 'success')
      
    } catch (error) {
      console.error('保存用户信息失败:', error)
      this.showToast(error.message || '保存失败', 'error')
    } finally {
      this.setData({ isLoading: false })
    }
  },

  // 上传头像
  uploadAvatar() {
    tt.chooseImage({
      count: 1,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const tempFilePath = res.tempFilePaths[0]
        this.doUploadAvatar(tempFilePath)
      },
      fail: (error) => {
        console.error('选择图片失败:', error)
        this.showToast('选择图片失败', 'error')
      }
    })
  },

  // 执行头像上传
  async doUploadAvatar(filePath) {
    this.setData({ isLoading: true })

    try {
      const token = tt.getStorageSync('fashion_auth_token')
      
      tt.uploadFile({
        url: `${app.globalData.baseURL}/api/users/upload-avatar`,
        filePath,
        name: 'file',
        header: {
          'Authorization': `Bearer ${token}`
        },
        success: (res) => {
          const data = JSON.parse(res.data)

          if (data.success) {
            // 构建完整的头像URL
            const avatarUrl = this.buildAvatarUrl(data.data.avatar_url)
            
            this.setData({ avatarUrl: avatarUrl })
            this.showToast('头像上传成功！', 'success')
            
            console.log('头像上传成功，新的URL:', avatarUrl)
            
            // 重新加载用户信息
            this.loadUserProfile()
          } else {
            this.showToast(data.message || '上传失败', 'error')
          }
        },
        fail: (error) => {
          console.error('头像上传失败:', error)
          this.showToast('头像上传失败', 'error')
        },
        complete: () => {
          this.setData({ isLoading: false })
        }
      })
    } catch (error) {
      console.error('头像上传异常:', error)
      this.setData({ isLoading: false })
      this.showToast('头像上传失败', 'error')
    }
  },

  // 修改密码
  changePassword() {
    this.showToast('密码修改功能开发中', 'none')
    // TODO: 跳转到修改密码页面
  },

  // 用户登出
  async logout() {
    const confirmed = await this.showConfirm({
      title: '确认退出',
      content: '确定要退出登录吗？'
    })
    
    if (confirmed) {
      app.logout()
    }
  },

  // 跳转到衣橱页面
  goToWardrobe() {
    tt.switchTab({
      url: '/pages/wardrobe/wardrobe'
    })
  },

  // 跳转到AI分析页面  
  goToAnalysis() {
    tt.switchTab({
      url: '/pages/analysis/analysis'
    })
  },

  // 设置功能
  openSettings() {
    this.showToast('设置功能开发中', 'none')
    // TODO: 跳转到设置页面
  },

  // 帮助功能
  openHelp() {
    this.showToast('帮助功能开发中', 'none')
    // TODO: 跳转到帮助页面
  },

  // 关于我们
  openAbout() {
    this.showToast('关于我们页面开发中', 'none')
    // TODO: 跳转到关于页面
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

  // 底部导航栏切换
  switchTab(e) {
    const tab = e.currentTarget.dataset.tab
    const tabMap = {
      'index': '/pages/index/index',
      'analysis': '/pages/analysis/analysis',
      'wardrobe': '/pages/wardrobe/wardrobe',
      'profile': '/pages/profile/profile'
    }

    if (tab === 'profile') {
      // 当前已在个人中心，不需要跳转
      return
    }

    const url = tabMap[tab]
    if (!url) {
      this.showToast('页面开发中...', 'none')
      return
    }

    // 对于需要登录的页面，检查登录状态
    if (['wardrobe'].includes(tab) && !this.data.isLoggedIn) {
      this.showToast('请先登录', 'none')
      return
    }

    tt.switchTab({ url })
  },

  // 分享功能
  onShareAppMessage() {
    return {
      title: 'AI穿搭助手 - 我的时尚档案',
      desc: '智能分析，个性推荐，打造专属时尚风格',
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
    
    // 根据登录状态显示不同的提示
    let content = ''
    let confirmText = '知道了'
    
    if (!this.data.isLoggedIn) {
      content = '登录后我可以为你提供个性化服务！\n\n分析你的风格偏好，推荐最适合的穿搭建议。'
      confirmText = '去登录'
    } else {
      const profile = this.data.userInfo
      const completeness = this.calculateProfileCompleteness(profile)
      
      if (completeness < 50) {
        content = '完善个人信息可以获得更精准的推荐！\n\n告诉我你的风格偏好，我会为你量身定制时尚建议。'
        confirmText = '完善信息'
      } else {
        content = `你的资料完整度已达到 ${completeness}%！\n\n基于你的个人信息，我可以为你推荐最适合的穿搭风格。`
        confirmText = '获取推荐'
      }
    }
    
    tt.showModal({
      title: '🤖 个人助手',
      content: content,
      confirmText: confirmText,
      showCancel: false,
      success: (res) => {
        if (res.confirm) {
          if (!this.data.isLoggedIn) {
            this.goToLogin()
          } else if (this.calculateProfileCompleteness(this.data.userInfo) < 50) {
            // 引导用户完善信息
            this.showToast('请完善个人信息以获得更好的体验', 'none')
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

  // 计算资料完整度
  calculateProfileCompleteness(userInfo) {
    if (!userInfo) return 0
    
    const fields = ['nickname', 'height', 'weight', 'age', 'style_preference', 'body_type', 'skin_tone']
    const completed = fields.filter(field => userInfo[field] && userInfo[field].toString().trim()).length
    
    return Math.round((completed / fields.length) * 100)
  },

  // 页面错误处理
  onError(error) {
    console.error('个人信息页面错误:', error)
    this.showToast('页面出现错误', 'error')
  }
})