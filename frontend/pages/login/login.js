// pages/login/login.js

const app = getApp()

Page({
  data: {
    // 表单数据
    phone: '',
    password: '',
    
    // 表单状态
    showPassword: false,
    rememberMe: false,
    isLoading: false,
    
    // 错误信息
    phoneError: '',
    passwordError: '',
    
    // 弹窗状态
    showForgotModal: false
  },

  onLoad(options) {
    console.log('登录页面加载', options)
    this.initLoginPage(options)
  },

  onShow() {
    // 检查是否已登录
    if (app.globalData.isLoggedIn) {
      this.redirectAfterLogin()
    }
  },

  // 初始化登录页面
  initLoginPage(options = {}) {
    // 如果从注册页面传来手机号，预填充
    if (options.phone) {
      this.setData({ phone: options.phone })
    } else {
      // 恢复记住的登录信息
      this.restoreLoginInfo()
    }
  },

  // 恢复登录信息
  restoreLoginInfo() {
    try {
      const savedPhone = tt.getStorageSync('saved_phone')
      const savedPassword = tt.getStorageSync('saved_password')
      const rememberMe = tt.getStorageSync('remember_me')
      
      if (rememberMe && savedPhone) {
        this.setData({
          phone: savedPhone,
          password: savedPassword || '',
          rememberMe: true
        })
      }
    } catch (error) {
      console.error('恢复登录信息失败:', error)
    }
  },

  // 手机号输入
  onPhoneInput(e) {
    const phone = e.detail.value
    this.setData({ 
      phone,
      phoneError: ''
    })
  },

  // 密码输入
  onPasswordInput(e) {
    const password = e.detail.value
    this.setData({ 
      password,
      passwordError: ''
    })
  },

  // 清除手机号
  clearPhone() {
    this.setData({ 
      phone: '',
      phoneError: ''
    })
  },

  // 切换密码显示
  togglePassword() {
    this.setData({
      showPassword: !this.data.showPassword
    })
  },

  // 切换记住我
  toggleRemember() {
    this.setData({
      rememberMe: !this.data.rememberMe
    })
  },

  // 验证表单
  validateForm() {
    const { phone, password } = this.data
    let isValid = true

    // 验证手机号
    if (!phone.trim()) {
      this.setData({ phoneError: '请输入手机号' })
      isValid = false
    } else if (!this.isValidPhone(phone)) {
      this.setData({ phoneError: '请输入正确的手机号' })
      isValid = false
    }

    // 验证密码
    if (!password.trim()) {
      this.setData({ passwordError: '请输入密码' })
      isValid = false
    } else if (password.length < 6) {
      this.setData({ passwordError: '密码至少6位' })
      isValid = false
    }

    return isValid
  },

  // 验证手机号格式
  isValidPhone(phone) {
    const phoneRegex = /^1[3-9]\d{9}$/
    return phoneRegex.test(phone)
  },

  // 处理登录
  async handleLogin() {
    // 验证表单
    if (!this.validateForm()) {
      return
    }

    this.setData({ isLoading: true })

    try {
      const { phone, password } = this.data
      
      // 调用登录API
      const result = await this.callLoginAPI(phone, password)
      
      // 登录成功处理
      await this.handleLoginSuccess(result)
      
    } catch (error) {
      console.error('登录失败:', error)
      this.handleLoginError(error)
    } finally {
      this.setData({ isLoading: false })
    }
  },

  // 调用登录API
  callLoginAPI(phone, password) {
    return new Promise((resolve, reject) => {
      tt.request({
        url: `${app.globalData.baseURL}/api/users/login`,
        method: 'POST',
        header: {
          'Content-Type': 'application/json'
        },
        data: {
          phone,
          password
        },
        success: (res) => {
          console.log('登录API响应:', res)
          
          if (res.statusCode === 200) {
            resolve(res.data)
          } else {
            const errorMsg = res.data?.detail || '登录失败'
            reject(new Error(errorMsg))
          }
        },
        fail: (error) => {
          console.error('登录API请求失败:', error)
          reject(new Error('网络请求失败，请检查网络连接'))
        }
      })
    })
  },

  // 登录成功处理
  async handleLoginSuccess(result) {
    const { access_token, user_info } = result
    
    // 保存登录信息到全局状态
    app.login(user_info, access_token)
    
    // 处理记住密码
    this.handleRememberMe()
    
    // 显示成功提示
    this.showToast('登录成功！', 'success')
    
    // 延迟跳转
    setTimeout(() => {
      this.redirectAfterLogin()
    }, 1500)
  },

  // 处理记住密码
  handleRememberMe() {
    const { phone, password, rememberMe } = this.data
    
    if (rememberMe) {
      // 保存登录信息
      tt.setStorageSync('saved_phone', phone)
      tt.setStorageSync('saved_password', password)
      tt.setStorageSync('remember_me', true)
    } else {
      // 清除保存的信息
      tt.removeStorageSync('saved_phone')
      tt.removeStorageSync('saved_password')
      tt.removeStorageSync('remember_me')
    }
  },

  // 登录失败处理
  handleLoginError(error) {
    const errorMsg = error.message || '登录失败，请重试'
    
    // 根据错误类型显示不同提示
    if (errorMsg.includes('手机号') || errorMsg.includes('密码')) {
      this.setData({ 
        phoneError: errorMsg.includes('手机号') ? errorMsg : '',
        passwordError: errorMsg.includes('密码') ? errorMsg : ''
      })
    } else {
      this.showToast(errorMsg, 'error')
    }
  },

  // 登录后重定向
  redirectAfterLogin() {
    // 获取来源页面
    const pages = getCurrentPages()
    const prevPage = pages[pages.length - 2]
    
    // 如果来源页面需要登录，返回上一页
    if (prevPage && ['wardrobe', 'profile'].includes(prevPage.route.split('/').pop())) {
      tt.navigateBack()
    } else {
      // 否则跳转到个人中心
      tt.switchTab({
        url: '/pages/profile/profile',
        fail: () => {
          // 如果switchTab失败，跳转到首页
          tt.switchTab({
            url: '/pages/index/index'
          })
        }
      })
    }
  },

  // 忘记密码
  forgotPassword() {
    this.setData({ showForgotModal: true })
  },

  // 关闭忘记密码弹窗
  closeForgotModal() {
    this.setData({ showForgotModal: false })
  },

  // 防止弹窗关闭
  preventClose() {
    // 阻止事件冒泡
  },

  // 联系在线客服
  contactService() {
    this.closeForgotModal()
    this.showToast('正在为您转接客服...', 'loading')
    
    // 模拟客服功能
    setTimeout(() => {
      tt.hideToast()
      this.showToast('客服功能开发中', 'none')
    }, 2000)
  },

  // 拨打客服电话
  callService() {
    this.closeForgotModal()
    
    tt.showModal({
      title: '客服电话',
      content: '400-888-8888\n服务时间：09:00-18:00',
      confirmText: '拨打',
      cancelText: '取消',
      success: (res) => {
        if (res.confirm) {
          tt.makePhoneCall({
            phoneNumber: '400-888-8888',
            fail: () => {
              this.showToast('拨打失败', 'error')
            }
          })
        }
      }
    })
  },

  // 微信登录
  wechatLogin() {
    this.showToast('微信登录功能开发中', 'none')
    
    // TODO: 实现微信登录
    // tt.login({
    //   success: (res) => {
    //     console.log('微信登录成功', res)
    //   }
    // })
  },

  // 验证码登录
  phoneCodeLogin() {
    this.showToast('验证码登录功能开发中', 'none')
    
    // TODO: 跳转到验证码登录页面
  },

  // 抖音登录
  toutiaoLogin() {
    this.showToast('抖音登录功能开发中', 'none')
    
    // TODO: 实现抖音登录
  },

  // 跳转到注册页面
  goToRegister() {
    tt.navigateTo({
      url: '/pages/register/register',
      success: () => {
        console.log('跳转到注册页面')
      },
      fail: (error) => {
        console.error('跳转失败:', error)
        this.showToast('页面跳转失败', 'error')
      }
    })
  },

  // 显示用户协议
  showUserAgreement() {
    this.showToast('用户协议页面开发中', 'none')
    
    // TODO: 跳转到用户协议页面
  },

  // 显示隐私政策
  showPrivacyPolicy() {
    this.showToast('隐私政策页面开发中', 'none')
    
    // TODO: 跳转到隐私政策页面
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
    return {
      title: 'AI穿搭助手 - 发现你的时尚魅力',
      desc: '智能风格分析，个性化穿搭推荐',
      path: '/pages/index/index'
    }
  },

  // AI机器人点击事件
  onAIBotClick() {
    console.log('AI助手被点击 - 登录页面')
    
    // 触觉反馈
    tt.vibrateShort({
      type: 'light'
    })
    
    // 显示AI助手对话框
    tt.showModal({
      title: '👋 AI助手',
      content: '我是你的时尚顾问！登录后我可以为你提供个性化的穿搭建议和搭配分析。快来登录探索更多功能吧！',
      showCancel: true,
      cancelText: '稍后再说',
      confirmText: '立即登录',
      success: (res) => {
        if (res.confirm) {
          // 用户选择立即登录，聚焦到手机号输入框
          this.setData({ phoneError: '', passwordError: '' })
        }
      }
    })
  },

  // 页面错误处理
  onError(error) {
    console.error('登录页面错误:', error)
    this.showToast('页面出现错误', 'error')
  },

  // 返回按钮处理
  onNavigationBarBackTap() {
    tt.switchTab({
      url: '/pages/index/index'
    })
  }
})