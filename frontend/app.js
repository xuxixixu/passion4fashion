// app.js

App({
  globalData: {
    // API配置
    baseURL: 'http://123.60.11.207',
    
    // 用户信息
    userInfo: null,
    authToken: null,
    sessionId: null,
    openid: null,
    
    // 应用状态
    isLoggedIn: false,
    isNewUser: false,
    
    // 系统信息
    systemInfo: null,
    
    // 版本信息
    version: '3.0.0',
    
    // 调试模式
    debug: true
  },

  onLaunch(options) {
    console.log('小程序启动', options)
    
    // 初始化应用
    this.initApp()
    
    // 检查更新
    this.checkForUpdate()
    
    // 获取系统信息
    this.getSystemInfo()
    
    // 自动进行OpenID认证
    this.autoLogin()
  },

  onShow(options) {
    console.log('小程序显示', options)
    
    // 如果未登录，尝试自动登录
    if (!this.globalData.isLoggedIn) {
      this.autoLogin()
    }
  },

  onHide() {
    console.log('小程序隐藏')
  },

  onError(error) {
    console.error('小程序错误:', error)
    
    // 错误上报
    if (this.globalData.debug) {
      tt.showModal({
        title: '应用错误',
        content: error.toString(),
        showCancel: false
      })
    }
  },

  // 初始化应用
  initApp() {
    try {
      // 恢复用户数据
      this.restoreUserData()
      
      // 设置默认请求头
      this.setupRequestDefaults()
      
      console.log('应用初始化完成')
    } catch (error) {
      console.error('应用初始化失败:', error)
    }
  },

  // 自动OpenID登录
  async autoLogin() {
    try {
      // 检查是否已有有效token
      const token = this.globalData.authToken
      if (token) {
        // 验证token有效性
        const isValid = await this.verifyToken(token)
        if (isValid) {
          console.log('使用缓存的token登录成功')
          return
        }
      }

      // 获取抖音登录code
      const loginResult = await this.getDouyinLoginCode()
      if (!loginResult.success) {
        console.log('用户未登录抖音或取消登录')
        return
      }

      // 调用后端OpenID登录接口
      const authResult = await this.loginWithOpenID(loginResult.code)
      if (authResult.success) {
        console.log('OpenID自动登录成功')
      } else {
        console.error('OpenID登录失败:', authResult.error)
      }

    } catch (error) {
      console.error('自动登录失败:', error)
      // 不阻断用户使用，静默失败
    }
  },

  // 获取抖音登录code
  getDouyinLoginCode() {
    return new Promise((resolve) => {
      tt.login({
        force: false, // 不强制弹出登录框
        success: (res) => {
          if (res.isLogin && res.code) {
            resolve({ success: true, code: res.code })
          } else {
            resolve({ success: false, reason: 'user_not_login' })
          }
        },
        fail: (error) => {
          console.error('tt.login失败:', error)
          resolve({ success: false, reason: 'login_failed', error })
        }
      })
    })
  },

  // 使用OpenID登录
  loginWithOpenID(code) {
    return new Promise((resolve) => {
      tt.request({
        url: `${this.globalData.baseURL}/api/auth/openid-login`,
        method: 'POST',
        header: {
          'Content-Type': 'application/json'
        },
        data: { code },
        success: (res) => {
          if (res.statusCode === 200) {
            const { access_token, user_info, is_new_user } = res.data
            
            // 保存登录信息
            this.globalData.authToken = access_token
            this.globalData.userInfo = user_info
            this.globalData.isLoggedIn = true
            this.globalData.isNewUser = is_new_user
            this.globalData.openid = user_info.openid
            
            // 持久化存储
            tt.setStorageSync('fashion_auth_token', access_token)
            tt.setStorageSync('fashion_user_info', user_info)
            
            console.log(`OpenID登录成功${is_new_user ? '（新用户）' : ''}:`, user_info.openid)
            
            resolve({ success: true, isNewUser: is_new_user })
          } else {
            resolve({ success: false, error: res.data })
          }
        },
        fail: (error) => {
          console.error('OpenID登录请求失败:', error)
          resolve({ success: false, error: 'network_error' })
        }
      })
    })
  },

  // 验证token有效性
  verifyToken(token) {
    return new Promise((resolve) => {
      tt.request({
        url: `${this.globalData.baseURL}/api/auth/current-user`,
        method: 'GET',
        header: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        success: (res) => {
          if (res.statusCode === 200) {
            this.globalData.isLoggedIn = true
            this.globalData.userInfo = res.data
            tt.setStorageSync('fashion_user_info', res.data)
            resolve(true)
          } else {
            resolve(false)
          }
        },
        fail: () => {
          resolve(false)
        }
      })
    })
  },

  // 手动登录（强制弹出抖音登录框）
  async manualLogin() {
    try {
      const loginResult = await this.getDouyinLoginCodeForced()
      if (!loginResult.success) {
        return { success: false, reason: 'user_cancelled' }
      }

      const authResult = await this.loginWithOpenID(loginResult.code)
      return authResult
    } catch (error) {
      console.error('手动登录失败:', error)
      return { success: false, error }
    }
  },

  // 强制获取登录code
  getDouyinLoginCodeForced() {
    return new Promise((resolve) => {
      tt.login({
        force: true, // 强制弹出登录框
        success: (res) => {
          if (res.isLogin && res.code) {
            resolve({ success: true, code: res.code })
          } else {
            resolve({ success: false, reason: 'login_failed' })
          }
        },
        fail: (error) => {
          console.error('强制登录失败:', error)
          resolve({ success: false, reason: 'login_cancelled', error })
        }
      })
    })
  },

  // 检查更新
  checkForUpdate() {
    if (tt.getUpdateManager) {
      const updateManager = tt.getUpdateManager()
      
      updateManager.onCheckForUpdate((res) => {
        console.log('检查更新结果:', res.hasUpdate)
      })
      
      updateManager.onUpdateReady(() => {
        tt.showModal({
          title: '更新提示',
          content: '新版本已准备好，是否重启应用？',
          success: (res) => {
            if (res.confirm) {
              updateManager.applyUpdate()
            }
          }
        })
      })
      
      updateManager.onUpdateFailed(() => {
        console.log('更新失败')
      })
    }
  },

  // 获取系统信息
  getSystemInfo() {
    tt.getSystemInfo({
      success: (res) => {
        this.globalData.systemInfo = res
        console.log('系统信息:', res)
      },
      fail: (error) => {
        console.error('获取系统信息失败:', error)
      }
    })
  },

  // 恢复用户数据
  restoreUserData() {
    try {
      // 恢复认证token
      const authToken = tt.getStorageSync('fashion_auth_token')
      if (authToken) {
        this.globalData.authToken = authToken
        this.globalData.isLoggedIn = true
      }

      // 恢复session ID
      const sessionId = tt.getStorageSync('fashion_session_id')
      if (sessionId) {
        this.globalData.sessionId = sessionId
      }

      // 恢复用户信息
      const userInfo = tt.getStorageSync('fashion_user_info')
      if (userInfo) {
        this.globalData.userInfo = userInfo
        this.globalData.openid = userInfo.openid
      }

      console.log('用户数据恢复完成')
    } catch (error) {
      console.error('恢复用户数据失败:', error)
    }
  },

  // 设置默认请求配置
  setupRequestDefaults() {
    // 这里可以扩展为拦截器模式
    this.request = (options) => {
      // 添加默认headers
      const defaultHeaders = {
        'Content-Type': 'application/json'
      }

      // 添加认证头
      if (this.globalData.authToken) {
        defaultHeaders['Authorization'] = `Bearer ${this.globalData.authToken}`
      }

      // 添加session头
      if (this.globalData.sessionId) {
        defaultHeaders['X-Session-ID'] = this.globalData.sessionId
      }

      const requestOptions = {
        ...options,
        url: options.url.startsWith('http') ? options.url : `${this.globalData.baseURL}${options.url}`,
        header: {
          ...defaultHeaders,
          ...options.header
        }
      }

      return new Promise((resolve, reject) => {
        tt.request({
          ...requestOptions,
          success: (res) => {
            // 处理session ID
            const newSessionId = res.header['X-Session-ID'] || res.header['x-session-id']
            if (newSessionId && newSessionId !== this.globalData.sessionId) {
              this.globalData.sessionId = newSessionId
              tt.setStorageSync('fashion_session_id', newSessionId)
            }

            // 处理认证错误
            if (res.statusCode === 401) {
              this.logout()
              reject(new Error('认证失败'))
              return
            }

            resolve(res)
          },
          fail: reject
        })
      })
    }
  },

  // 传统登录方法（保留兼容性）
  login(userInfo, token) {
    this.globalData.userInfo = userInfo
    this.globalData.authToken = token
    this.globalData.isLoggedIn = true

    // 持久化存储
    tt.setStorageSync('fashion_user_info', userInfo)
    tt.setStorageSync('fashion_auth_token', token)

    console.log('用户登录成功:', userInfo)
  },

  // 用户登出
  logout() {
    this.globalData.userInfo = null
    this.globalData.authToken = null
    this.globalData.isLoggedIn = false
    this.globalData.openid = null
    this.globalData.isNewUser = false

    // 清除存储
    tt.removeStorageSync('fashion_user_info')
    tt.removeStorageSync('fashion_auth_token')

    console.log('用户已登出')

    // 跳转到登录页面
    tt.showModal({
      title: '登录提示',
      content: '登录已过期，请重新登录',
      showCancel: false,
      success: () => {
        tt.reLaunch({
          url: '/pages/index/index'
        })
      }
    })
  },

  // 显示登录引导
  showLoginGuide() {
    tt.showModal({
      title: '需要登录',
      content: '此功能需要登录后使用，是否现在登录？',
      confirmText: '立即登录',
      cancelText: '稍后',
      success: async (res) => {
        if (res.confirm) {
          const loginResult = await this.manualLogin()
          if (loginResult.success) {
            this.showToast('登录成功！', 'success')
          } else {
            this.showToast('登录失败，请重试', 'none')
          }
        }
      }
    })
  },

  // 工具方法：显示加载
  showLoading(title = '加载中...') {
    tt.showLoading({
      title,
      mask: true
    })
  },

  // 工具方法：隐藏加载
  hideLoading() {
    tt.hideLoading()
  },

  // 工具方法：显示提示
  showToast(title, icon = 'none', duration = 2000) {
    tt.showToast({
      title,
      icon,
      duration,
      mask: false
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

  // 工具方法：格式化日期
  formatDate(date, format = 'YYYY-MM-DD') {
    const d = new Date(date)
    const year = d.getFullYear()
    const month = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    const hour = String(d.getHours()).padStart(2, '0')
    const minute = String(d.getMinutes()).padStart(2, '0')
    const second = String(d.getSeconds()).padStart(2, '0')

    return format
      .replace('YYYY', year)
      .replace('MM', month)
      .replace('DD', day)
      .replace('HH', hour)
      .replace('mm', minute)
      .replace('ss', second)
  },

  // 工具方法：防抖
  debounce(func, wait) {
    let timeout
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout)
        func(...args)
      }
      clearTimeout(timeout)
      timeout = setTimeout(later, wait)
    }
  },

  // 工具方法：节流
  throttle(func, limit) {
    let inThrottle
    return function executedFunction(...args) {
      if (!inThrottle) {
        func.apply(this, args)
        inThrottle = true
        setTimeout(() => inThrottle = false, limit)
      }
    }
  }
})