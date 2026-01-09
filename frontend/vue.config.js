/*
 * @Description: 配置文件
 * @Author: hai-27
 * @Date: 2020-02-07 16:23:00
 * @LastEditors: hai-27
 * @LastEditTime: 2021-03-03 22:32:57
 */
module.exports = {
  publicPath: './',
  devServer: {
    open: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000', // KGAT后端地址
        changeOrigin: true, //允许跨域
        // 不需要重写路径，KGAT后端使用/api前缀
        // pathRewrite: {
        //   '^/api': ''
        // }
      }
    }
  }
}