// pages/register/register.js

const app = getApp()

Page({
  data: {
    // 步骤控制
    currentStep: 1,
    progressWidth: 33.33,
    
    // 表单数据 - 步骤1
    phone: '',
    verifyCode: '',
    phoneValid: false,
    phoneError: '',
    codeError: '',
    
    // 验证码相关
    codeLoading: false,
    countdown: 0,
    
    // 表单数据 - 步骤2
    password: '',
    confirmPassword: '',
    showPassword: false,
    showConfirmPassword: false,
    passwordStrength: 0,
    passwordStrengthText: '请输入密码',
    passwordError: '',
    confirmPasswordError: '',
    
    // 表单数据 - 步骤3
    nickname: '',
    gender: '',
    agreeToTerms: false,
    
    // 状态控制
    isLoading: false,
    showSuccessModal: false,
    
    // 验证状态
    step1Valid: false,
    step2Valid: false,
    step3Valid: false
  },

  onLoad(options) {
    console.log('注册页面加载', options)
    this.initRegisterPage()
  },

  onShow() {
    // 检查是否已登录
    if (app.globalData.isLoggedIn) {
      tt.switchTab({
        url: '/pages/profile/profile'
      })
    }
  },

  onUnload() {
    // 清理倒计时
    if (this.countdownTimer) {
      clearInterval(this.countdownTimer)
    }
  },

  // 初始化注册页面
  initRegisterPage() {
    // 可以在这里添加初始化逻辑
    console.log('注册页面初始化完成')
  },

  // ===== 步骤1: 基本信息 =====
  
  // 手机号输入
  onPhoneInput(e) {
    const phone = e.detail.value
    const phoneValid = this.isValidPhone(phone)
    
    this.setData({ 
      phone,
      phoneValid,
      phoneError: ''
    })
    
    this.validateStep1()
  },

  // 验证码输入
  onCodeInput(e) {
    const verifyCode = e.detail.value
    this.setData({ 
      verifyCode,
      codeError: ''
    })
    
    this.validateStep1()
  },

  // 验证手机号格式
  isValidPhone(phone) {
    const phoneRegex = /^1[3-9]\d{9}$/
    return phoneRegex.test(phone)
  },

  // 发送验证码
  sendVerifyCode() {
    if (!this.data.phoneValid) {
      this.setData({ phoneError: '请输入正确的手机号' })
      return
    }

    this.setData({ codeLoading: true })
    
    // 模拟发送验证码
    setTimeout(() => {
      this.setData({ 
        codeLoading: false,
        countdown: 60
      })
      
      this.showToast('验证码已发送', 'success')
      this.startCountdown()
      
      // 开发环境下显示验证码
      if (app.globalData.debug) {
        setTimeout(() => {
          this.showToast('测试验证码: 123456', 'none')
        }, 1000)
      }
    }, 1500)
  },

  // 倒计时
  startCountdown() {
    this.countdownTimer = setInterval(() => {
      const countdown = this.data.countdown - 1
      this.setData({ countdown })
      
      if (countdown <= 0) {
        clearInterval(this.countdownTimer)
      }
    }, 1000)
  },

  // 验证步骤1
  validateStep1() {
    const { phone, verifyCode, phoneValid } = this.data
    const step1Valid = phoneValid && verifyCode.length === 6
    
    this.setData({ step1Valid })
  },

  // ===== 步骤2: 密码设置 =====

  // 密码输入
  onPasswordInput(e) {
    const password = e.detail.value
    const strength = this.calculatePasswordStrength(password)
    
    this.setData({ 
      password,
      passwordStrength: strength.level,
      passwordStrengthText: strength.text,
      passwordError: ''
    })
    
    this.validateStep2()
  },

  // 确认密码输入
  onConfirmPasswordInput(e) {
    const confirmPassword = e.detail.value
    this.setData({ 
      confirmPassword,
      confirmPasswordError: ''
    })
    
    this.validateStep2()
  },

  // 计算密码强度
  calculatePasswordStrength(password) {
    if (password.length === 0) {
      return { level: 0, text: '请输入密码' }
    }
    
    if (password.length < 6) {
      return { level: 0, text: '密码过短' }
    }
    
    let score = 0
    
    // 长度检查
    if (password.length >= 8) score += 1
    if (password.length >= 12) score += 1
    
    // 复杂度检查
    if (/[a-z]/.test(password)) score += 1
    if (/[A-Z]/.test(password)) score += 1
    if (/[0-9]/.test(password)) score += 1
    if (/[^A-Za-z0-9]/.test(password)) score += 1
    
    if (score <= 2) {
      return { level: 1, text: '密码强度：弱' }
    } else if (score <= 4) {
      return { level: 2, text: '密码强度：中' }
    } else {
      return { level: 3, text: '密码强度：强' }
    }
  },

  // 切换密码显示
  togglePassword() {
    this.setData({
      showPassword: !this.data.showPassword
    })
  },

  // 切换确认密码显示
  toggleConfirmPassword() {
    this.setData({
      showConfirmPassword: !this.data.showConfirmPassword
    })
  },

  // 验证步骤2
  validateStep2() {
    const { password, confirmPassword } = this.data
    
    let isValid = true
    
    if (password.length < 6) {
      isValid = false
    }
    
    if (confirmPassword && password !== confirmPassword) {
      this.setData({ confirmPasswordError: '两次密码输入不一致' })
      isValid = false
    } else {
      this.setData({ confirmPasswordError: '' })
    }
    
    this.setData({ step2Valid: isValid && password === confirmPassword && confirmPassword.length > 0 })
  },

  // ===== 步骤3: 完善信息 =====

  // 昵称输入
  onNicknameInput(e) {
    const nickname = e.detail.value
    this.setData({ nickname })
    this.validateStep3()
  },

  // 选择性别
  selectGender(e) {
    const gender = e.currentTarget.dataset.gender
    this.setData({ gender })
    this.validateStep3()
  },

  // 切换协议同意
  toggleAgreement() {
    this.setData({
      agreeToTerms: !this.data.agreeToTerms
    })
    this.validateStep3()
  },

  // 验证步骤3
  validateStep3() {
    const { agreeToTerms } = this.data
    this.setData({ step3Valid: agreeToTerms })
  },

  // ===== 步骤控制 =====

  // 下一步
  nextStep() {
    const { currentStep } = this.data
    
    if (currentStep < 3) {
      const newStep = currentStep + 1
      this.setData({ 
        currentStep: newStep,
        progressWidth: (newStep / 3) * 100
      })
    }
  },

  // 上一步
  prevStep() {
    const { currentStep } = this.data
    
    if (currentStep > 1) {
      const newStep = currentStep - 1
      this.setData({ 
        currentStep: newStep,
        progressWidth: (newStep / 3) * 100
      })
    }
  },

  // ===== 注册处理 =====

  // 处理注册
  async handleRegister() {
    if (!this.validateAllSteps()) {
      return
    }

    this.setData({ isLoading: true })

    try {
      // 模拟验证码验证
      if (!this.verifyCode()) {
        throw new Error('验证码错误')
      }

      const { phone, password, nickname } = this.data
      
      // 调用注册API
      const result = await this.callRegisterAPI(phone, password, nickname)
      
      // 注册成功处理
      this.handleRegisterSuccess(result)
      
    } catch (error) {
      console.error('注册失败:', error)
      this.handleRegisterError(error)
    } finally {
      this.setData({ isLoading: false })
    }
  },

  // 验证所有步骤
  validateAllSteps() {
    const { step1Valid, step2Valid, step3Valid } = this.data
    return step1Valid && step2Valid && step3Valid
  },

  // 验证验证码
  verifyCode() {
    // 开发环境下使用测试验证码
    if (app.globalData.debug) {
      return this.data.verifyCode === '123456'
    }
    
    // 生产环境下应该调用后端验证
    return true
  },

  // 调用注册API
  callRegisterAPI(phone, password, nickname) {
    return new Promise((resolve, reject) => {
      const requestData = { phone, password }
      
      // 如果有昵称，添加到请求中
      if (nickname.trim()) {
        requestData.nickname = nickname.trim()
      }
      
      tt.request({
        url: `${app.globalData.baseURL}/api/users/register`,
        method: 'POST',
        header: {
          'Content-Type': 'application/json'
        },
        data: requestData,
        success: (res) => {
          console.log('注册API响应:', res)
          
          if (res.statusCode === 200 && res.data.success) {
            resolve(res.data)
          } else {
            const errorMsg = res.data?.detail || res.data?.message || '注册失败'
            reject(new Error(errorMsg))
          }
        },
        fail: (error) => {
          console.error('注册API请求失败:', error)
          reject(new Error('网络请求失败，请检查网络连接'))
        }
      })
    })
  },

  // 注册成功处理
  handleRegisterSuccess(result) {
    console.log('注册成功:', result)
    
    // 显示成功弹窗
    this.setData({ showSuccessModal: true })
    
    // 清理倒计时
    if (this.countdownTimer) {
      clearInterval(this.countdownTimer)
    }
  },

  // 注册失败处理
  handleRegisterError(error) {
    const errorMsg = error.message || '注册失败，请重试'
    
    // 根据错误类型定位到对应步骤
    if (errorMsg.includes('手机号')) {
      this.setData({ 
        currentStep: 1,
        progressWidth: 33.33,
        phoneError: errorMsg
      })
    } else if (errorMsg.includes('密码')) {
      this.setData({ 
        currentStep: 2,
        progressWidth: 66.66,
        passwordError: errorMsg
      })
    } else {
      this.showToast(errorMsg, 'error')
    }
  },

  // ===== 弹窗和跳转 =====

  // 关闭成功弹窗
  closeSuccessModal() {
    this.setData({ showSuccessModal: false })
  },

  // 防止弹窗关闭
  preventClose() {
    // 阻止事件冒泡
  },

  // 注册成功后跳转登录
  goToLoginAfterRegister() {
    this.closeSuccessModal()
    
    // 传递手机号到登录页面
    tt.redirectTo({
      url: `/pages/login/login?phone=${this.data.phone}`,
      success: () => {
        this.showToast('请使用刚才注册的账号登录', 'none')
      }
    })
  },

  // 跳转到登录页面
  goToLogin() {
    tt.navigateBack({
      fail: () => {
        tt.redirectTo({
          url: '/pages/login/login'
        })
      }
    })
  },

  // 显示用户协议
  showUserAgreement() {
    this.showToast('用户协议页面开发中', 'none')
    
    // TODO: 显示用户协议弹窗或跳转页面
  },

  // 显示隐私政策
  showPrivacyPolicy() {
    this.showToast('隐私政策页面开发中', 'none')
    
    // TODO: 显示隐私政策弹窗或跳转页面
  },

  // ===== 工具方法 =====

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
      title: 'AI穿搭助手 - 加入时尚大家庭',
      desc: '智能风格分析，个性化穿搭推荐，开启你的专属时尚之旅',
      path: '/pages/register/register'
    }
  },

  // AI机器人点击事件
  onAIBotClick() {
    console.log('AI助手被点击 - 注册页面')
    
    // 触觉反馈
    tt.vibrateShort({
      type: 'light'
    })
    
    let content = ''
    let confirmText = '继续注册'
    
    // 根据注册步骤显示不同内容
    if (this.data.currentStep === 1) {
      content = '👋 欢迎注册AI穿搭助手！我是你的专属时尚顾问，注册完成后我将为你提供个性化的穿搭建议和风格分析。'
    } else if (this.data.currentStep === 2) {
      content = '🔐 设置一个安全密码很重要哦！这样可以保护你的个人资料和穿搭偏好数据的安全。'
    } else {
      content = '🎉 快完成注册了！填写昵称和基本信息，我就能为你提供更精准的时尚建议了！'
    }
    
    // 显示AI助手对话框
    tt.showModal({
      title: '🤖 AI时尚顾问',
      content: content,
      showCancel: true,
      cancelText: '稍后再说',
      confirmText: confirmText,
      success: (res) => {
        if (res.confirm) {
          // 用户选择继续，可以聚焦到当前步骤的输入框
          console.log('用户选择继续注册')
        }
      }
    })
  },

  // 页面错误处理
  onError(error) {
    console.error('注册页面错误:', error)
    this.showToast('页面出现错误', 'error')
  }
})