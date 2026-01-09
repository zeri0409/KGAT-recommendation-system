/*
 * 入口文件
 */
import Vue from 'vue'
import App from './App.vue'
import router from './router'
import store from './store'

import ElementUI from 'element-ui';
import 'element-ui/lib/theme-chalk/index.css';
Vue.use(ElementUI);

// 全局函数及变量
import Global from './Global';
Vue.use(Global);

import Axios from 'axios';
Vue.prototype.$axios = Axios;

// 全局请求拦截器 - 添加JWT Token
Axios.interceptors.request.use(
  config => {
    // 从localStorage获取token
    const token = localStorage.getItem('token');
    if (token) {
      // 添加Authorization头
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  error => {
    // 跳转error页面
    router.push({ path: "/error" });
    return Promise.reject(error);
  }
);

// 全局响应拦截器 - 适配KGAT后端响应格式
Axios.interceptors.response.use(
  res => {
    // KGAT后端使用HTTP状态码，不是data.code
    // 如果响应成功，直接返回
    return res;
  },
  error => {
    // 处理HTTP错误
    if (error.response) {
      const status = error.response.status;
      if (status === 401) {
        // 401表示没有登录或token过期
        localStorage.removeItem('token');
        store.dispatch("setUser", "");
        Vue.prototype.notifyError("请先登录");
        // 修改vuex的showLogin状态,显示登录组件
        store.dispatch("setShowLogin", true);
      } else if (status === 403) {
        // 403表示权限不足
        Vue.prototype.notifyError("权限不足");
      } else if (status >= 500) {
        // 500表示服务器异常
        router.push({ path: "/error" });
      } else if (status === 400) {
        // 400错误（如注册失败、验证错误等）不在这里显示，让组件自己处理
        // 这样可以避免重复显示错误消息
      } else {
        // 其他错误
        const data = error.response && error.response.data ? error.response.data : {};
        const msg = data.detail || data.msg || "请求失败";
        Vue.prototype.notifyError(msg);
      }
    } else {
      // 网络错误
      router.push({ path: "/error" });
    }
    return Promise.reject(error);
  }
);

// 全局拦截器,在进入需要用户权限的页面前校验是否已经登录
router.beforeResolve((to, from, next) => {
  const loginUser = store.state.user.user;
  const token = localStorage.getItem('token');
  
  // 判断路由是否设置相应校验用户权限
  if (to.meta.requireAuth) {
    // 检查是否有token和用户信息
    if (!token || !loginUser) {
      // 如果有token但没有用户信息，尝试获取用户信息
      if (token && !loginUser) {
        Axios.get("/api/auth/me", {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }).then(res => {
          // 保存用户信息
          let user = JSON.stringify(res.data);
          localStorage.setItem("user", user);
          store.dispatch("setUser", res.data);
          next();
        }).catch(() => {
          // token无效，清除并显示登录
          localStorage.removeItem('token');
          store.dispatch("setShowLogin", true);
          if (from.name == null) {
            next("/");
            return;
          }
          next(false);
        });
        return;
      }
      
      // 没有登录，显示登录组件
      store.dispatch("setShowLogin", true);
      if (from.name == null) {
        //此时，是在页面没有加载，直接在地址栏输入链接，进入需要登录验证的页面
        next("/");
        return;
      }
      // 终止导航
      next(false);
      return;
    }
  }
  next();
});

// 相对时间过滤器,把时间戳转换成时间
// 格式: 2020-02-25 21:43:23
Vue.filter('dateFormat', (dataStr) => {
  var time = new Date(dataStr);
  function timeAdd0 (str) {
    if (str < 10) {
      str = '0' + str;
    }
    return str;
  }
  var y = time.getFullYear();
  var m = time.getMonth() + 1;
  var d = time.getDate();
  var h = time.getHours();
  var mm = time.getMinutes();
  var s = time.getSeconds();
  return y + '-' + timeAdd0(m) + '-' + timeAdd0(d) + ' ' + timeAdd0(h) + ':' + timeAdd0(mm) + ':' + timeAdd0(s);
});

//全局组件
import MyMenu from './components/MyMenu';
Vue.component(MyMenu.name, MyMenu);
import MyList from './components/MyList';
Vue.component(MyList.name, MyList);
import MyLogin from './components/MyLogin';
Vue.component(MyLogin.name, MyLogin);
import MyRegister from './components/MyRegister';
Vue.component(MyRegister.name, MyRegister);

Vue.config.productionTip = false;

new Vue({
  router,
  store,
  render: h => h(App)
}).$mount('#app')
