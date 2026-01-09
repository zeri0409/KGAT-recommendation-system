/*
 * @Description: 全局变量
 */
exports.install = function (Vue) {
  // KGAT后端地址
  Vue.prototype.$target = "http://127.0.0.1:8000/api/"; // 本地KGAT后端地址
  // 封装提示成功的弹出框
  Vue.prototype.notifySucceed = function (msg) {
    this.$notify({
      title: "成功",
      message: msg,
      type: "success",
      offset: 100
    });
  };
  // 封装提示失败的弹出框
  Vue.prototype.notifyError = function (msg) {
    this.$notify.error({
      title: "错误",
      message: msg,
      offset: 100
    });
  };
}