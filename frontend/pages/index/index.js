// pages/index/index.js

const app = getApp()

Page({
  data: {
    userStats: {
      totalAnalysis: '10K+',
      totalUsers: '5K+',
      satisfactionRate: 98
    },
    sessionId: null,
    isLoading: false,
    
    // 虚拟试穿相关数据
    userImage: null,           // 用户照片 {path, type: 'user'}
    clothesImages: [],         // 衣服照片数组 [{path, type: 'clothes'}, ...]
    isProcessing: false,       // 是否正在处理
    tryonResult: null,         // 试穿结果 {imageData, confidence} - 注意这里改成imageData
    currentSessionId: null,    // 当前试穿会话ID
    pollTimer: null           // 轮询定时器
  },

  onLoad(options) {
    console.log('主页加载', options)
    this.initializeApp()
    this.loadUserStats()
  },

  onShow() {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({
        selected: 0
      })
    }
  },

  onUnload() {
    if (this.data.pollTimer) {
      clearInterval(this.data.pollTimer)
    }
  },

  onPullDownRefresh() {
    this.loadUserStats()
    setTimeout(() => {
      tt.stopPullDownRefresh()
    }, 1000)
  },

  // 初始化应用
  async initializeApp() {
    try {
      this.setData({ isLoading: true })
      
      const sessionId = tt.getStorageSync('fashion_session_id')
      if (sessionId) {
        this.setData({ sessionId })
        app.globalData.sessionId = sessionId
      }

      await this.callHealthCheck()
      
    } catch (error) {
      console.error('应用初始化失败:', error)
      this.showToast('应用初始化失败', 'error')
    } finally {
      this.setData({ isLoading: false })
    }
  },

  // 调用健康检查接口
  async callHealthCheck() {
    return new Promise((resolve, reject) => {
      tt.request({
        url: `${app.globalData.baseURL}/health`,
        method: 'GET',
        header: {
          'X-Session-ID': this.data.sessionId
        },
        success: (res) => {
          console.log('健康检查响应:', res)
          
          const newSessionId = res.header['X-Session-ID'] || res.header['x-session-id']
          if (newSessionId && newSessionId !== this.data.sessionId) {
            this.setData({ sessionId: newSessionId })
            app.globalData.sessionId = newSessionId
            tt.setStorageSync('fashion_session_id', newSessionId)
            console.log('获取到新的session_id:', newSessionId)
          }
          
          resolve(res.data)
        },
        fail: (error) => {
          console.error('健康检查失败:', error)
          reject(error)
        }
      })
    })
  },

  // 加载用户统计数据
  loadUserStats() {
    const stats = {
      totalAnalysis: this.generateRandomNumber(8000, 12000),
      totalUsers: this.generateRandomNumber(4000, 6000),
      satisfactionRate: 98
    }
    
    this.setData({
      userStats: {
        totalAnalysis: this.formatNumber(stats.totalAnalysis),
        totalUsers: this.formatNumber(stats.totalUsers),
        satisfactionRate: stats.satisfactionRate
      }
    })
  },

  formatNumber(num) {
    if (num >= 10000) {
      return Math.floor(num / 1000) + 'K+'
    } else if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K'
    }
    return num.toString()
  },

  generateRandomNumber(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min
  },

  // =================== 虚拟试穿功能 ===================

  // 生成试穿会话ID
  generateTryonSessionId() {
    return 'tryon_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9)
  },

  // 选择用户照片
  selectUserImage() {
    tt.chooseImage({
      count: 1,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const tempFilePath = res.tempFilePaths[0]
        this.setData({
          userImage: {
            path: tempFilePath,
            type: 'user'
          }
        })
        console.log('用户照片选择成功:', tempFilePath)
        this.showToast('照片选择成功', 'success')
      },
      fail: (error) => {
        console.error('选择用户照片失败:', error)
        this.showToast('选择照片失败', 'none')
      }
    })
  },

  // 选择衣服照片
  selectClothesImage() {
    if (this.data.clothesImages.length >= 3) {
      this.showToast('最多选择3件衣服', 'none')
      return
    }

    tt.chooseImage({
      count: 3 - this.data.clothesImages.length,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const newClothes = res.tempFilePaths.map(path => ({
          path,
          type: 'clothes'
        }))
        
        this.setData({
          clothesImages: [...this.data.clothesImages, ...newClothes]
        })
        
        console.log('衣服照片选择成功:', newClothes)
        this.showToast(`已选择${newClothes.length}件衣服`, 'success')
      },
      fail: (error) => {
        console.error('选择衣服照片失败:', error)
        this.showToast('选择照片失败', 'none')
      }
    })
  },

  // 删除衣服照片
  removeClothes(e) {
    const index = e.currentTarget.dataset.index
    const clothesImages = [...this.data.clothesImages]
    clothesImages.splice(index, 1)
    
    this.setData({ clothesImages })
    this.showToast('已删除', 'success')
  },

  // 开始虚拟试穿
  async startVirtualTryon() {
    if (!this.data.userImage) {
      this.showToast('请先上传您的照片', 'none')
      return
    }

    if (this.data.clothesImages.length === 0) {
      this.showToast('请至少选择一件衣服', 'none')
      return
    }

    const token = tt.getStorageSync('fashion_auth_token')
    if (!token) {
      this.showLoginModal()
      return
    }

    const userInfo = tt.getStorageSync('fashion_user_info')
    if (!userInfo || !userInfo.id) {
      this.showToast('获取用户信息失败', 'none')
      return
    }

    const currentSessionId = this.generateTryonSessionId()
    
    this.setData({ 
      isProcessing: true,
      tryonResult: null,
      currentSessionId
    })

    try {
      // 上传用户图片
      await this.uploadUserImage(userInfo.id, currentSessionId)
      
      // 上传所有衣服图片
      await this.uploadClothesImages(userInfo.id, currentSessionId)
      
      // 通知后端开始处理
      await this.startProcessing(userInfo.id, currentSessionId)
      
      // 开始轮询结果
      this.startPolling(currentSessionId)
      
    } catch (error) {
      console.error('虚拟试穿失败:', error)
      this.showToast('处理失败，请重试', 'none')
      this.setData({ isProcessing: false })
    }
  },

  // 上传用户图片文件
  async uploadUserImage(userId, sessionId) {
    const token = tt.getStorageSync('fashion_auth_token')
    
    return new Promise((resolve, reject) => {
      tt.uploadFile({
        url: `${app.globalData.baseURL}/api/virtual-tryon/upload-user-image`,
        filePath: this.data.userImage.path,
        name: 'user_image',
        header: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'multipart/form-data'
        },
        formData: {
          user_id: userId.toString(),
          session_id: sessionId,
          image_type: 'user'
        },
        success: (res) => {
          console.log('用户图片上传成功:', res)
          if (res.statusCode === 200) {
            const result = JSON.parse(res.data)
            if (result.success) {
              resolve(result)
            } else {
              reject(new Error(result.message || '上传失败'))
            }
          } else {
            reject(new Error('上传请求失败'))
          }
        },
        fail: reject
      })
    })
  },

  // 上传衣服图片文件
  async uploadClothesImages(userId, sessionId) {
    const token = tt.getStorageSync('fashion_auth_token')
    
    for (let i = 0; i < this.data.clothesImages.length; i++) {
      const clothesImage = this.data.clothesImages[i]
      
      await new Promise((resolve, reject) => {
        tt.uploadFile({
          url: `${app.globalData.baseURL}/api/virtual-tryon/upload-clothes-image`,
          filePath: clothesImage.path,
          name: 'clothes_image',
          header: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          },
          formData: {
            user_id: userId.toString(),
            session_id: sessionId,
            image_type: 'clothes',
            clothes_index: i.toString()
          },
          success: (res) => {
            console.log(`衣服图片${i}上传成功:`, res)
            if (res.statusCode === 200) {
              const result = JSON.parse(res.data)
              if (result.success) {
                resolve(result)
              } else {
                reject(new Error(result.message || '上传失败'))
              }
            } else {
              reject(new Error('上传请求失败'))
            }
          },
          fail: reject
        })
      })
    }
  },

  // 通知后端开始处理
  async startProcessing(userId, sessionId) {
    const token = tt.getStorageSync('fashion_auth_token')
    
    return new Promise((resolve, reject) => {
      tt.request({
        url: `${app.globalData.baseURL}/api/virtual-tryon/start-processing`,
        method: 'POST',
        header: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        data: {
          user_id: userId,
          session_id: sessionId,
          clothes_count: this.data.clothesImages.length
        },
        success: (res) => {
          if (res.statusCode === 200) {
            resolve(res.data)
          } else {
            reject(new Error('开始处理失败'))
          }
        },
        fail: reject
      })
    })
  },

  // 开始轮询结果
  startPolling(sessionId) {
    let pollCount = 0
    const maxPolls = 60
    
    const pollTimer = setInterval(async () => {
      pollCount++
      
      try {
        const result = await this.checkTryonResult(sessionId)
        
        if (result.status === 'completed') {
          // 注意：这里不再是imageUrl，而是直接的图片数据
          this.setData({
            isProcessing: false,
            tryonResult: {
              imageData: result.result_image_data, // 直接的base64图片数据
              confidence: result.confidence || 95
            }
          })
          clearInterval(pollTimer)
          this.showToast('试穿效果生成成功！', 'success')
          
        } else if (result.status === 'failed') {
          this.setData({ isProcessing: false })
          clearInterval(pollTimer)
          this.showToast(result.error || '生成失败', 'none')
          
        } else if (pollCount >= maxPolls) {
          this.setData({ isProcessing: false })
          clearInterval(pollTimer)
          this.showToast('处理超时，请重试', 'none')
        }
        
      } catch (error) {
        console.error('轮询失败:', error)
        pollCount++
        
        if (pollCount >= maxPolls) {
          this.setData({ isProcessing: false })
          clearInterval(pollTimer)
          this.showToast('网络异常，请重试', 'none')
        }
      }
    }, 2000)

    this.setData({ pollTimer })
  },

  // 检查试穿结果
  async checkTryonResult(sessionId) {
    const token = tt.getStorageSync('fashion_auth_token')
    
    return new Promise((resolve, reject) => {
      tt.request({
        url: `${app.globalData.baseURL}/api/virtual-tryon/result/${sessionId}`,
        method: 'GET',
        header: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        success: (res) => {
          if (res.statusCode === 200) {
            resolve(res.data)
          } else {
            reject(new Error('查询失败'))
          }
        },
        fail: reject
      })
    })
  },

  // 保存试穿结果 - 修改为保存base64数据
  saveResult() {
    if (!this.data.tryonResult || !this.data.tryonResult.imageData) {
      this.showToast('没有可保存的图片', 'none')
      return
    }

    try {
      // 将base64数据写入临时文件
      const fs = tt.getFileSystemManager()
      const tempFilePath = `${tt.env.USER_DATA_PATH}/temp_result_${Date.now()}.jpg`
      
      // 移除base64前缀
      const base64Data = this.data.tryonResult.imageData.replace(/^data:image\/[a-z]+;base64,/, '')
      
      fs.writeFileSync(tempFilePath, base64Data, 'base64')
      
      // 保存到相册
      tt.saveImageToPhotosAlbum({
        filePath: tempFilePath,
        success: () => {
          this.showToast('保存成功', 'success')
          // 删除临时文件
          try {
            fs.unlinkSync(tempFilePath)
          } catch (e) {
            console.log('删除临时文件失败:', e)
          }
        },
        fail: (error) => {
          console.error('保存失败:', error)
          this.showToast('保存失败', 'none')
        }
      })
      
    } catch (error) {
      console.error('处理图片数据失败:', error)
      this.showToast('保存失败', 'none')
    }
  },

  // 重新试穿
  resetTryon() {
    if (this.data.pollTimer) {
      clearInterval(this.data.pollTimer)
    }
    
    this.setData({
      userImage: null,
      clothesImages: [],
      isProcessing: false,
      tryonResult: null,
      currentSessionId: null,
      pollTimer: null
    })
  },

  // =================== 原有功能 ===================

  goToStyleAnalysis() {
    this.showToast('正在进入AI分析页面...', 'loading')
    
    setTimeout(() => {
      tt.switchTab({
        url: '/pages/analysis/analysis',
        success: () => {
          tt.hideToast()
        },
        fail: (error) => {
          console.error('页面跳转失败:', error)
          this.showToast('页面跳转失败', 'error')
        }
      })
    }, 500)
  },

  goToWardrobe() {
    const token = tt.getStorageSync('fashion_auth_token')
    if (!token) {
      this.showLoginModal()
      return
    }

    this.showToast('正在进入智能衣橱...', 'loading')
    
    setTimeout(() => {
      tt.switchTab({
        url: '/pages/wardrobe/wardrobe',
        success: () => {
          tt.hideToast()
        },
        fail: (error) => {
          console.error('页面跳转失败:', error)
          this.showToast('页面跳转失败', 'error')
        }
      })
    }, 500)
  },

  goToProfile() {
    this.showToast('正在进入个人中心...', 'loading')
    
    setTimeout(() => {
      tt.switchTab({
        url: '/pages/profile/profile',
        success: () => {
          tt.hideToast()
        },
        fail: (error) => {
          console.error('页面跳转失败:', error)
          this.showToast('页面跳转失败', 'error')
        }
      })
    }, 500)
  },

  switchTab(e) {
    const tab = e.currentTarget.dataset.tab
    const tabMap = {
      'index': '/pages/index/index',
      'analysis': '/pages/analysis/analysis', 
      'wardrobe': '/pages/wardrobe/wardrobe',
      'profile': '/pages/profile/profile'
    }

    if (tab === 'index') {
      return
    }

    const url = tabMap[tab]
    if (!url) {
      this.showToast('页面开发中...', 'none')
      return
    }

    if (['wardrobe', 'profile'].includes(tab)) {
      const token = tt.getStorageSync('fashion_auth_token')
      if (!token) {
        this.showLoginModal()
        return
      }
    }

    if (['index', 'analysis', 'wardrobe', 'profile'].includes(tab)) {
      tt.switchTab({ url })
    } else {
      tt.navigateTo({ url })
    }
  },

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

  showToast(title, icon = 'none') {
    tt.showToast({
      title,
      icon: icon === 'error' ? 'none' : icon,
      duration: icon === 'loading' ? 0 : 2000,
      mask: icon === 'loading'
    })
  },

  onShareAppMessage() {
    return {
      title: 'AI穿搭助手 - 让AI为你定制专属时尚',
      desc: '智能分析，个性推荐，打造你的专属风格',
      path: '/pages/index/index'
    }
  },

  onShareTimeline() {
    return {
      title: 'AI穿搭助手 - 让AI为你定制专属时尚',
      query: 'from=timeline',
      imageUrl: ''
    }
  },

  onError(error) {
    console.error('页面错误:', error)
    this.showToast('页面出现错误', 'error')
  },

  onAIBotClick(e) {
    console.log('AI机器人被点击:', e.detail);
    
    tt.vibrateShort({
      type: 'medium'
    });
    
    tt.showModal({
      title: 'AI时尚助手',
      content: '嗨！我是你的专属AI时尚顾问，准备为你提供个性化的穿搭建议！\n\n点击确定开始AI分析，我会根据你的照片为你推荐最适合的穿搭风格~',
      confirmText: '开始分析',
      cancelText: '稍后',
      success: (res) => {
        if (res.confirm) {
          this.goToStyleAnalysis();
        }
      }
    });
  }
})