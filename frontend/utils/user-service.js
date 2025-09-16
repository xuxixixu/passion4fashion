/**
 * 用户服务管理
 * 处理用户登录、信息存储等功能
 */

class UserService {
  constructor() {
    this.userId = null;
    this.userInfo = null;
    this.init();
  }

  /**
   * 初始化用户服务
   */
  init() {
    try {
      // 从本地存储获取用户信息
      this.userId = tt.getStorageSync('userId');
      this.userInfo = tt.getStorageSync('userInfo');
      
      // 如果没有用户ID，生成一个临时ID
      if (!this.userId) {
        this.userId = this.generateTempUserId();
        tt.setStorageSync('userId', this.userId);
      }
    } catch (error) {
      console.error('用户服务初始化失败:', error);
      this.userId = this.generateTempUserId();
    }
  }

  /**
   * 生成临时用户ID
   */
  generateTempUserId() {
    return 'temp_' + Date.now() + '_' + Math.floor(Math.random() * 1000);
  }

  /**
   * 获取当前用户ID
   */
  getUserId() {
    return this.userId;
  }

  /**
   * 获取用户信息
   */
  getUserInfo() {
    return this.userInfo;
  }

  /**
   * 设置用户信息
   */
  setUserInfo(userInfo) {
    this.userInfo = userInfo;
    try {
      tt.setStorageSync('userInfo', userInfo);
    } catch (error) {
      console.error('保存用户信息失败:', error);
    }
  }

  /**
   * 用户登录
   */
  async login(loginData) {
    try {
      const response = await tt.request({
        url: 'https://your-backend-url.com/api/auth/login',
        method: 'POST',
        header: {
          'Content-Type': 'application/json'
        },
        data: loginData
      });

      if (response.statusCode === 200 && response.data.success) {
        this.userId = response.data.data.user_id;
        this.userInfo = response.data.data.user_info;
        
        // 保存到本地存储
        tt.setStorageSync('userId', this.userId);
        tt.setStorageSync('userInfo', this.userInfo);
        tt.setStorageSync('token', response.data.data.token);
        
        return response.data;
      } else {
        throw new Error(response.data.message || '登录失败');
      }
    } catch (error) {
      console.error('登录失败:', error);
      throw error;
    }
  }

  /**
   * 用户登出
   */
  logout() {
    try {
      // 清除本地存储的用户信息，但保留会话ID以保持历史记录
      tt.removeStorageSync('token');
      tt.removeStorageSync('userInfo');
      // 注意：不删除userId和conversationId，以保持历史记录
      
      this.userInfo = null;
      // userId保持不变，用于历史记录连续性
    } catch (error) {
      console.error('登出失败:', error);
    }
  }

  /**
   * 检查用户是否已登录
   */
  isLoggedIn() {
    const token = tt.getStorageSync('token');
    return !!token && !!this.userInfo;
  }

  /**
   * 获取认证token
   */
  getToken() {
    return tt.getStorageSync('token');
  }

  /**
   * 清除所有用户数据（包括历史记录）
   */
  clearAllData() {
    try {
      tt.clearStorageSync();
      this.userId = this.generateTempUserId();
      this.userInfo = null;
      tt.setStorageSync('userId', this.userId);
    } catch (error) {
      console.error('清除数据失败:', error);
    }
  }
}

// 创建单例实例
const userService = new UserService();

export default userService;