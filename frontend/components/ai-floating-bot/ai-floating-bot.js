// components/ai-floating-bot/ai-floating-bot.js

Component({
  /**
   * 组件的属性列表
   */
  properties: {
    visible: {
      type: Boolean,
      value: true,
      observer: function(newVal) {
        console.log('visible changed:', newVal);
      }
    },
    // 补充初始位置属性定义
    initialPosition: {
      type: Object,
      value: { x: 0, y: 0 }
    },
    messageCount: {
      type: Number,
      value: 0
    },
    pageContext: {
      type: String,
      value: 'home'
    }
  },

  /**
   * 组件的初始数据
   */
  data: {
    position: { x: 0, y: 0 },
    isDragging: false,
    isActive: false,
    hasNewMessage: false,
    showRipple: false,
    startPosition: { x: 0, y: 0 },
    dragOffset: { x: 0, y: 0 },
    screenInfo: {
      width: 375,
      height: 667,
      safeAreaTop: 0
    },
    botSize: { width: 60, height: 60 },
    boundary: {
      left: 10,
      right: 365,
      top: 50,
      bottom: 600
    },
    isOnline: true,
    animationFrameId: null, // 用于存储动画ID
    // 对话框相关
    showDialog: false,
    dialogPosition: { x: 50, y: 100 }
  },

  /**
   * 组件生命周期
   */
  lifetimes: {
    attached() {
      this.initComponent()
    },
    detached() {
      // 清理动画定时器
      if (this.data.animationFrameId) {
        clearTimeout(this.data.animationFrameId);
      }
    }
  },

  /**
   * 组件方法
   */
  methods: {
    /**
     * 初始化组件
     */
    initComponent() {
      // 获取系统信息
      const systemInfo = tt.getSystemInfoSync()
      const screenWidth = systemInfo.screenWidth
      const screenHeight = systemInfo.screenHeight
      const safeAreaTop = systemInfo.safeArea?.top || systemInfo.statusBarHeight || 0
      
      // 计算边界
      const boundary = {
        left: 10,
        right: screenWidth - this.data.botSize.width - 10,
        top: safeAreaTop + 50,
        bottom: screenHeight - this.data.botSize.height - 100
      }
      
      // 优先使用本地存储的位置
      const savedPosition = this.loadPosition()
      let initialX, initialY
      
      if (savedPosition && savedPosition.x !== undefined && savedPosition.y !== undefined) {
        // 使用保存的位置
        initialX = savedPosition.x
        initialY = savedPosition.y
      } else {
        // 使用传入的初始位置或默认位置
        initialX = this.properties.initialPosition.x
        initialY = this.properties.initialPosition.y
        
        if (initialX === 0 && initialY === 0) {
          initialX = boundary.right - 20
          initialY = boundary.top + 20
        }
      }
      
      // 确保位置在边界内
      const x = Math.max(boundary.left, Math.min(boundary.right, initialX))
      const y = Math.max(boundary.top, Math.min(boundary.bottom, initialY))
      
      this.setData({
        screenInfo: {
          width: screenWidth,
          height: screenHeight,
          safeAreaTop: safeAreaTop
        },
        boundary: boundary,
        position: { x, y },
        hasNewMessage: this.properties.messageCount > 0
      })
      
      // 确保位置已保存到本地存储
      this.savePosition({ x, y })
    },

    /**
     * 触摸开始
     */
    onTouchStart(e) {
      console.log('Touch start:', e);
      const touch = e.touches[0]
      const { pageX, pageY } = touch
      
      // 如果有正在进行的动画，停止它
      if (this.data.animationFrameId) {
        clearTimeout(this.data.animationFrameId);
      }
      
      this.setData({
        isDragging: true,
        isActive: true,
        startPosition: { x: pageX, y: pageY },
        dragOffset: {
          x: pageX - this.data.position.x,
          y: pageY - this.data.position.y
        }
      })
      
      // 触觉反馈
      tt.vibrateShort({
        type: 'light'
      })
    },

    /**
     * 触摸移动
     */
    onTouchMove(e) {
      if (!this.data.isDragging) return
      
      const touch = e.touches[0]
      const { pageX, pageY } = touch
      
      // 计算新位置
      let newX = pageX - this.data.dragOffset.x
      let newY = pageY - this.data.dragOffset.y
      
      // 边界检测
      newX = Math.max(this.data.boundary.left, Math.min(this.data.boundary.right, newX))
      newY = Math.max(this.data.boundary.top, Math.min(this.data.boundary.bottom, newY))
      
      this.setData({
        position: { x: newX, y: newY }
      })
    },

    /**
     * 触摸结束
     */
    onTouchEnd(e) {
      const touch = e.changedTouches[0]
      const { pageX, pageY } = touch
      
      // 计算移动距离
      const moveDistance = Math.sqrt(
        Math.pow(pageX - this.data.startPosition.x, 2) + 
        Math.pow(pageY - this.data.startPosition.y, 2)
      )
      
      this.setData({
        isDragging: false,
        isActive: false
      })
      
      // 自动吸附到边缘
      this.autoAdsorbToEdge()
      
      // 保存位置
      this.savePosition(this.data.position)
      
      // 如果移动距离很小，认为是点击
      if (moveDistance < 10) {
        this.onBotClick()
      }
    },

    /**
     * 自动吸附到边缘
     */
    autoAdsorbToEdge() {
      const { position, boundary, screenInfo } = this.data
      const centerX = screenInfo.width / 2
      
      let targetX = position.x
      
      // 判断靠左还是靠右
      if (position.x < centerX) {
        // 吸附到左边
        targetX = boundary.left
      } else {
        // 吸附到右边
        targetX = boundary.right
      }
      
      // 平滑移动到目标位置
      this.animateToPosition({ x: targetX, y: position.y })
    },

    /**
     * 动画移动到指定位置 - 使用setTimeout实现兼容方案
     */
    animateToPosition(targetPosition) {
      const startPosition = this.data.position
      const duration = 300 // 动画持续时间(毫秒)
      const startTime = Date.now()
      
      // 清除可能存在的旧动画
      if (this.data.animationFrameId) {
        clearTimeout(this.data.animationFrameId);
      }
      
      const animate = () => {
        const elapsed = Date.now() - startTime
        const progress = Math.min(elapsed / duration, 1)
        
        // 使用缓动函数使动画更自然
        const easeOutCubic = 1 - Math.pow(1 - progress, 3)
        
        const currentX = startPosition.x + (targetPosition.x - startPosition.x) * easeOutCubic
        const currentY = startPosition.y + (targetPosition.y - startPosition.y) * easeOutCubic
        
        this.setData({
          position: { x: currentX, y: currentY }
        })
        
        if (progress < 1) {
          // 计算下一帧的延迟，使动画更平滑
          const nextDelay = Math.max(16 - (Date.now() - (startTime + elapsed)), 1);
          const frameId = setTimeout(animate, nextDelay);
          this.setData({ animationFrameId: frameId });
        } else {
          // 动画完成，保存最终位置
          this.setData({ animationFrameId: null });
          this.savePosition(targetPosition);
        }
      }
      
      // 启动动画
      const frameId = setTimeout(animate, 16);
      this.setData({ animationFrameId: frameId });
    },

    /**
     * 机器人点击事件
     */
    onBotClick() {
      // 显示波纹效果
      this.setData({ showRipple: true })
      
      setTimeout(() => {
        this.setData({ showRipple: false })
      }, 600)
      
      // 触觉反馈
      tt.vibrateShort({
        type: 'heavy'
      })
      
      // 清除消息提示
      this.setData({
        hasNewMessage: false,
        messageCount: 0
      })
      
      // 计算对话框位置
      this.calculateDialogPosition()
      
      // 显示AI对话框
      this.setData({
        showDialog: true
      })
    },

    /**
     * 保存位置到本地存储
     */
    savePosition(position) {
      try {
        tt.setStorageSync('ai_bot_position', position)
      } catch (error) {
        console.error('保存悬浮球位置失败:', error)
      }
    },

    /**
     * 从本地存储加载位置
     */
    loadPosition() {
      try {
        return tt.getStorageSync('ai_bot_position') || null
      } catch (error) {
        console.error('加载悬浮球位置失败:', error)
        return null
      }
    },

    /**
     * 设置消息数量
     */
    setMessageCount(count) {
      this.setData({
        messageCount: count,
        hasNewMessage: count > 0
      })
    },

    /**
     * 设置在线状态
     */
    setOnlineStatus(isOnline) {
      this.setData({
        isOnline: isOnline
      })
    },

    /**
     * 显示/隐藏悬浮球
     */
    toggleVisibility(visible) {
      this.setData({
        visible: visible
      })
    },

    /**
     * 计算对话框位置
     */
    calculateDialogPosition() {
      const { position, screenInfo, boundary } = this.data;
      
      // 安全检查：确保screenInfo已初始化
      if (!screenInfo || !screenInfo.width || !screenInfo.height) {
        console.error('screenInfo未正确初始化，无法计算对话框位置');
        // 使用默认值防止崩溃
        return;
      }
      
      const dialogWidth = 300; // 对话框宽度
      const dialogHeight = 400; // 对话框高度
      const margin = 20; // 边距
      
      let dialogX = position.x;
      let dialogY = position.y;
      
      // 如果悬浮球在屏幕右侧，对话框显示在左侧
      if (position.x < screenInfo.width / 2) {
        // 悬浮球在左侧，对话框显示在右侧
        dialogX = position.x + 120 + margin; // 120是悬浮球宽度
      } else {
        // 吸附到右边
        dialogX = position.x - dialogWidth - margin;
      }
      
      // 确保对话框不超出屏幕边界
      if (dialogX < margin) {
        dialogX = margin;
      } else if (dialogX + dialogWidth > screenInfo.width - margin) {
        dialogX = screenInfo.width - dialogWidth - margin;
      }
      
      // 垂直居中对齐悬浮球
      dialogY = position.y - dialogHeight / 2 + 60; // 60是悬浮球高度的一半
      
      // 确保对话框不超出屏幕上下边界
      if (dialogY < boundary.top) {
        dialogY = boundary.top;
      } else if (dialogY + dialogHeight > boundary.bottom) {
        dialogY = boundary.bottom - dialogHeight;
      }
      
      this.setData({
        dialogPosition: {
          x: dialogX,
          y: dialogY
        }
      });
    },

    /**
     * 关闭对话框
     */
    onDialogClose() {
      this.setData({
        showDialog: false
      });
    }
  }
})