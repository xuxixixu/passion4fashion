Page({
  data: {
    initialPosition: {
      x: 300,
      y: 400
    }
  },

  onLoad() {
    console.log('AI助手测试页面加载');
    
    // 获取系统信息来设置悬浮球初始位置
    tt.getSystemInfo({
      success: (res) => {
        this.setData({
          initialPosition: {
            x: res.windowWidth - 80, // 距离右边80rpx
            y: res.windowHeight / 2   // 垂直居中
          }
        });
      }
    });
  },

  onShow() {
    console.log('AI助手测试页面显示');
  },

  onHide() {
    console.log('AI助手测试页面隐藏');
  },

  onUnload() {
    console.log('AI助手测试页面卸载');
  }
});