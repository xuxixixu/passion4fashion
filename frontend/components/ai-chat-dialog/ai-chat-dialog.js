// components/ai-chat-dialog/ai-chat-dialog.js

Component({
  /**
   * 组件的属性列表
   */
  properties: {
    visible: {
      type: Boolean,
      value: false,
      observer: function(newVal) {
        if (newVal) {
          this.scrollToBottom();
        }
      }
    },
    position: {
      type: Object,
      value: { x: 50, y: 100 }
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
    messages: [
      {
        id: 1,
        type: 'ai',
        content: '你好！我是你的AI穿搭助手，有什么可以帮助你的吗？',
        time: '刚刚'
      }
    ],
    inputText: '',
    isLoading: false,
    isTyping: false,
    scrollTop: 0,
    scrollIntoView: '',
    previewMedia: [],
    showMediaSelector: false,
    messageId: 2
  },

  /**
   * 组件生命周期
   */
  lifetimes: {
    attached() {
      this.loadHistoryMessages();
      this.setInitialGreeting();
    }
  },

  /**
   * 组件的方法列表
   */
  methods: {
    /**
     * 关闭对话框
     */
    onClose() {
      this.setData({ visible: false });
      this.triggerEvent('close');
    },

    /**
     * 点击遮罩关闭
     */
    onMaskClick() {
      this.onClose();
    },

    /**
     * 输入框内容变化
     */
    onInputChange(e) {
      this.setData({
        inputText: e.detail.value
      });
    },

    /**
     * 发送消息
     */
    async onSendMessage() {
      const { inputText, previewMedia, messageId } = this.data;
      
      if (!inputText.trim() && previewMedia.length === 0) {
        return;
      }

      // 创建用户消息
      const userMessage = {
        id: messageId,
        type: 'user',
        time: this.formatTime(new Date())
      };

      // 处理文本消息
      if (inputText.trim()) {
        userMessage.content = inputText.trim();
        userMessage.messageType = 'text';
      }

      // 处理媒体消息
      const mediaMessages = [];
      for (let i = 0; i < previewMedia.length; i++) {
        const media = previewMedia[i];
        mediaMessages.push({
          id: messageId + i + 1,
          type: 'user',
          messageType: media.type,
          content: media.url,
          time: this.formatTime(new Date())
        });
      }

      // 更新消息列表
      const newMessages = [...this.data.messages];
      if (userMessage.content) {
        newMessages.push(userMessage);
      }
      newMessages.push(...mediaMessages);

      this.setData({
        messages: newMessages,
        inputText: '',
        previewMedia: [],
        isLoading: true,
        messageId: messageId + mediaMessages.length + 2
      });

      this.scrollToBottom();

      try {
        // 调用AI服务
        const response = await this.callAIService({
          text: inputText.trim(),
          media: previewMedia
        });

        // 添加AI回复
        const aiMessage = {
          id: this.data.messageId,
          type: 'ai',
          messageType: 'text',
          content: response.content || '抱歉，我现在无法回复，请稍后再试。',
          time: this.formatTime(new Date())
        };

        this.setData({
          messages: [...this.data.messages, aiMessage],
          isLoading: false,
          messageId: this.data.messageId + 1
        });

        this.scrollToBottom();
      } catch (error) {
        console.error('AI服务调用失败:', error);
        
        const errorMessage = {
          id: this.data.messageId,
          type: 'ai',
          messageType: 'text',
          content: '抱歉，服务暂时不可用，请稍后再试。',
          time: this.formatTime(new Date())
        };

        this.setData({
          messages: [...this.data.messages, errorMessage],
          isLoading: false,
          messageId: this.data.messageId + 1
        });

        this.scrollToBottom();
      }
    },

    /**
     * 调用AI服务
     */
    async callAIService(data) {
      try {
        // 获取应用实例（在抖音小程序中，getApp()是全局可用的）
        const app = getApp ? getApp() : null;
        let userId = null;
        let authToken = null;
        
        // 获取应用基础配置
        const baseURL = (app && app.globalData && app.globalData.baseURL) || 'http://localhost';
        
        // 尝试从多种渠道获取用户信息
        try {
          // 方法1: 从应用全局数据获取
          if (app && app.globalData && app.globalData.userInfo && app.globalData.userInfo.id) {
            userId = app.globalData.userInfo.id;
            authToken = app.globalData.authToken;
            console.log('从应用全局数据获取用户ID:', userId);
          } 
          // 方法2: 从本地存储获取
          else {
            const userInfo = tt.getStorageSync('fashion_user_info');
            authToken = tt.getStorageSync('fashion_auth_token');
            
            if (userInfo && userInfo.id) {
              userId = userInfo.id;
              console.log('从本地存储获取用户ID:', userId);
            } 
            // 方法3: 使用userService获取
            else {
              const { default: userService } = await import('../../utils/user-service.js');
              const tempUserId = userService.getUserId();
              
              // 从temp_开头的字符串中提取数字部分或使用默认值
              const match = tempUserId.match(/\d+/);
              userId = match ? parseInt(match[0], 10) : 1;
              console.log('使用临时用户ID并转换:', tempUserId, '->', userId);
            }
          }
        } catch (e) {
          console.error('获取用户ID失败:', e);
          userId = 1; // 出错时使用默认值
        }
        
        // 获取会话ID
        let conversationId = tt.getStorageSync('conversationId');
        
        // 确保page_context符合后端要求的取值范围
        const validPageContexts = ['home', 'style_analysis', 'wardrobe', 'profile'];
        let pageContext = this.data.pageContext;
        if (!validPageContexts.includes(pageContext)) {
          pageContext = 'home'; // 使用默认值
          console.log('修正page_context为有效值:', pageContext);
        }
        
        console.log('准备发送API请求，参数:', {
            url: `${baseURL}:80/api/ootd/chat`, // 明确指定端口80
            userId,
            conversationId,
            message: data.text,
            pageContext
          });
          
          // 使用tt.request发送主请求，包含认证token（如果有）
          const response = await new Promise((resolve, reject) => {
            // 构建请求头
            const headers = {
              'Content-Type': 'application/json'
            };
            
            // 如果有认证token，添加到请求头
            if (authToken) {
              headers['Authorization'] = `Bearer ${authToken}`;
            }
            
            tt.request({
              url: `${baseURL}:80/api/ootd/chat`, // 明确指定端口80
              method: 'POST',
              header: headers,
              data: {
                user_id: userId, // 确保是整数类型
                conversation_id: conversationId,
                message: data.text,
                page_context: pageContext, // 确保是有效值
                include_user_data: true,
                include_recent_context: true
              },
            success: (res) => {
              console.log('tt.request success回调:', res);
              resolve(res);
            },
            fail: (err) => {
              console.error('tt.request fail回调:', err);
              reject(err);
            },
            complete: (res) => {
              console.log('tt.request complete回调:', res);
            }
          });
        });
        
        // 检查响应对象
        console.log('API请求响应对象类型:', typeof response);
        console.log('API请求响应对象是否存在:', response !== undefined && response !== null);
        console.log('API请求响应对象属性:', response ? Object.keys(response) : '无');
        
        if (response && response.statusCode === 200) {
          console.log('API请求成功，状态码:', response.statusCode);
          console.log('API响应数据:', response.data);
          
          if (response.data && response.data.success) {
            // 保存会话ID
            if (response.data.conversation_id) {
              tt.setStorageSync('conversationId', response.data.conversation_id);
            }
            
            // 返回AI响应
            return { content: response.data.response || '收到您的消息，正在为您处理...' };
          } else {
            console.error('API响应数据不完整或请求失败:', response.data);
            throw new Error(response.data?.message || '服务器处理请求失败');
          }
        } else {
          console.error('API请求未成功，状态码:', response?.statusCode);
          throw new Error(`请求失败，状态码: ${response?.statusCode || '未知'}`);
        }
      } catch (error) {
        console.error('API调用异常:', {
          message: error.message,
          stack: error.stack,
          errorType: error.name
        });
        // 返回友好的错误提示而不是直接抛出异常
        return { 
          content: '抱歉，暂时无法连接到AI服务，请稍后再试。\n' +
                   '错误信息: ' + (error.message || '未知错误')
        };
      }
    },

    /**
     * 选择媒体
     */
    onSelectMedia() {
      this.setData({ showMediaSelector: true });
    },

    /**
     * 取消媒体选择
     */
    onCancelMediaSelector() {
      this.setData({ showMediaSelector: false });
    },

    /**
     * 选择图片
     */
    onChooseImage() {
      tt.chooseImage({
        count: 3,
        sizeType: ['original', 'compressed'],
        sourceType: ['album'],
        success: (res) => {
          this.addPreviewMedia(res.tempFilePaths, 'image');
        },
        fail: (error) => {
          console.error('选择图片失败:', error);
          tt.showToast({
            title: '选择图片失败',
            icon: 'none'
          });
        }
      });
      this.onCancelMediaSelector();
    },

    /**
     * 拍照
     */
    onTakePhoto() {
      tt.chooseImage({
        count: 1,
        sizeType: ['original', 'compressed'],
        sourceType: ['camera'],
        success: (res) => {
          this.addPreviewMedia(res.tempFilePaths, 'image');
        },
        fail: (error) => {
          console.error('拍照失败:', error);
          tt.showToast({
            title: '拍照失败',
            icon: 'none'
          });
        }
      });
      this.onCancelMediaSelector();
    },

    /**
     * 选择视频
     */
    onChooseVideo() {
      tt.chooseVideo({
        sourceType: ['album'],
        maxDuration: 60,
        camera: 'back',
        success: (res) => {
          this.addPreviewMedia([res.tempFilePath], 'video');
        },
        fail: (error) => {
          console.error('选择视频失败:', error);
          tt.showToast({
            title: '选择视频失败',
            icon: 'none'
          });
        }
      });
      this.onCancelMediaSelector();
    },

    /**
     * 录制视频
     */
    onRecordVideo() {
      tt.chooseVideo({
        sourceType: ['camera'],
        maxDuration: 60,
        camera: 'back',
        success: (res) => {
          this.addPreviewMedia([res.tempFilePath], 'video');
        },
        fail: (error) => {
          console.error('录制视频失败:', error);
          tt.showToast({
            title: '录制视频失败',
            icon: 'none'
          });
        }
      });
      this.onCancelMediaSelector();
    },

    /**
     * 添加预览媒体
     */
    addPreviewMedia(filePaths, type) {
      const newMedia = filePaths.map(path => ({
        url: path,
        type: type
      }));
      
      this.setData({
        previewMedia: [...this.data.previewMedia, ...newMedia]
      });
    },

    /**
     * 移除预览媒体
     */
    removePreviewMedia(e) {
      const index = e.currentTarget.dataset.index;
      const previewMedia = [...this.data.previewMedia];
      previewMedia.splice(index, 1);
      this.setData({ previewMedia });
    },

    /**
     * 图片预览
     */
    onImagePreview(e) {
      const src = e.currentTarget.dataset.src;
      tt.previewImage({
        current: src,
        urls: [src]
      });
    },

    /**
     * 滚动到底部
     */
    scrollToBottom() {
      setTimeout(() => {
        const lastMessageId = this.data.messages.length > 0 
          ? `msg-${this.data.messages[this.data.messages.length - 1].id}`
          : '';
        
        this.setData({
          scrollIntoView: lastMessageId
        });
      }, 100);
    },

    /**
     * 加载历史消息
     */
    async loadHistoryMessages() {
      try {
        const { default: userService } = await import('../../utils/user-service.js');
        const userId = userService.getUserId();
        const conversationId = tt.getStorageSync('conversationId');
        
        if (conversationId) {
          const response = await tt.request({
            url: `https://your-backend-url.com/api/conversations/${conversationId}/history?user_id=${userId}&limit=50`,
            method: 'GET',
            header: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer ' + (tt.getStorageSync('token') || '')
            }
          });
          
          if (response.statusCode === 200 && response.data.success) {
            const historyMessages = response.data.data.messages.map((msg, index) => {
              return {
                id: index + 1,
                type: msg.role === 'user' ? 'user' : 'ai',
                messageType: 'text',
                content: msg.content,
                time: this.formatTime(new Date(msg.created_at))
              };
            });
            
            // 如果有历史消息，替换默认消息
            if (historyMessages.length > 0) {
              this.setData({
                messages: historyMessages,
                messageId: historyMessages.length + 1
              });
              return;
            }
          }
        }
        
        // 如果没有历史消息或加载失败，使用页面特定的初始问候语
        this.setInitialGreeting();
      } catch (error) {
        console.error('加载历史消息失败:', error);
        this.setInitialGreeting();
      }
    },

    /**
     * 设置页面特定的初始问候语
     */
    setInitialGreeting() {
      const greetings = {
        home: 'Hi~欢迎来到OOTD智能穿搭助手！我能为你提供全方位的穿搭建议，包括风格分析、衣橱管理、单品推荐等。你可以浏览我们的AI风格分析功能、管理你的衣橱，或者在个人页面完善你的信息来获得更精准的推荐。有什么可以帮助你的吗？',
        style_analysis: '欢迎来到AI风格分析页面！这里我可以为你提供专业的风格分析和穿搭建议。你可以上传照片让我分析你的风格类型，或者告诉我你想尝试的风格，我会给你详细的分析和搭配建议。试试我们的智能AI分析和生成功能吧！',
        wardrobe: '欢迎来到你的智能衣橱！我可以根据你现有的衣服为你推荐OOTD搭配，帮你发现衣橱中的无限可能。告诉我你想要什么样的搭配风格，或者让我看看你的某件单品，我会为你提供专业的搭配建议和单品推荐。',
        profile: '欢迎来到个人中心！为了给你提供更精准的穿搭建议，我建议你完善个人信息，包括身材特点、喜好风格、生活场景等。这些信息将帮助我为你量身定制最适合的穿搭方案。有什么个人信息想要更新或者穿搭问题想要咨询的吗？'
      };
      
      const greeting = greetings[this.data.pageContext] || greetings.home;
      
      this.setData({
        messages: [{
          id: 1,
          type: 'ai',
          messageType: 'text',
          content: greeting,
          time: '刚刚'
        }],
        messageId: 2
      });
    },

    /**
     * 格式化时间
     */
    formatTime(date) {
      const now = new Date();
      const diff = now - date;
      
      if (diff < 60000) { // 1分钟内
        return '刚刚';
      } else if (diff < 3600000) { // 1小时内
        return `${Math.floor(diff / 60000)}分钟前`;
      } else if (diff < 86400000) { // 24小时内
        return `${Math.floor(diff / 3600000)}小时前`;
      } else {
        return `${date.getMonth() + 1}/${date.getDate()}`;
      }
    },

    /**
     * 清空对话
     */
    clearMessages() {
      this.setInitialGreeting();
    }
  }
});