<!--
 * @Description: 用户注册组件
 -->
<template>
  <div id="register">
    <el-dialog title="注册" width="300px" center :visible.sync="isRegister">
      <el-form
        :model="RegisterUser"
        :rules="rules"
        status-icon
        ref="ruleForm"
        class="demo-ruleForm"
      >
        <el-form-item prop="name">
          <el-input
            prefix-icon="el-icon-user-solid"
            placeholder="请输入账号"
            v-model="RegisterUser.name"
          ></el-input>
        </el-form-item>
        <el-form-item prop="pass">
          <el-input
            prefix-icon="el-icon-view"
            type="password"
            placeholder="请输入密码"
            v-model="RegisterUser.pass"
          ></el-input>
        </el-form-item>
        <el-form-item prop="confirmPass">
          <el-input
            prefix-icon="el-icon-view"
            type="password"
            placeholder="请再次输入密码"
            v-model="RegisterUser.confirmPass"
          ></el-input>
        </el-form-item>
        <el-form-item>
          <el-button size="medium" type="primary" @click="Register" style="width:100%;">注册</el-button>
        </el-form-item>
      </el-form>
    </el-dialog>
  </div>
</template>
<script>
export default {
  name: "MyRegister",
  props: ["register"],
  data() {
    // 用户名的校验方法
    let validateName = (rule, value, callback) => {
      if (!value) {
        return callback(new Error("请输入用户名"));
      }
      // KGAT后端要求：用户名最小长度3，最大长度50
      // 简化验证，只检查长度
      if (value.length >= 3 && value.length <= 50) {
        // 不检查用户名是否存在，注册时后端会返回错误
        this.$refs.ruleForm.validateField("checkPass");
        return callback();
      } else {
        return callback(new Error("用户名长度应在3-50个字符之间"));
      }
    };
    // 密码的校验方法
    let validatePass = (rule, value, callback) => {
      if (value === "") {
        return callback(new Error("请输入密码"));
      }
      // KGAT后端要求：密码最小长度6
      if (value.length >= 6) {
        this.$refs.ruleForm.validateField("checkPass");
        return callback();
      } else {
        return callback(new Error("密码长度至少6个字符"));
      }
    };
    // 确认密码的校验方法
    let validateConfirmPass = (rule, value, callback) => {
      if (value === "") {
        return callback(new Error("请输入确认密码"));
      }
      // 校验是否以密码一致
      if (this.RegisterUser.pass != "" && value === this.RegisterUser.pass) {
        this.$refs.ruleForm.validateField("checkPass");
        return callback();
      } else {
        return callback(new Error("两次输入的密码不一致"));
      }
    };
    return {
      isRegister: false, // 控制注册组件是否显示
      RegisterUser: {
        name: "",
        pass: "",
        confirmPass: ""
      },
      // 用户信息校验规则,validator(校验方法),trigger(触发方式),blur为在组件 Input 失去焦点时触发
      rules: {
        name: [{ validator: validateName, trigger: "blur" }],
        pass: [{ validator: validatePass, trigger: "blur" }],
        confirmPass: [{ validator: validateConfirmPass, trigger: "blur" }]
      }
    };
  },
  watch: {
    // 监听父组件传过来的register变量，设置this.isRegister的值
    register: function(val) {
      if (val) {
        this.isRegister = val;
      }
    },
    // 监听this.isRegister变量的值，更新父组件register变量的值
    isRegister: function(val) {
      if (!val) {
        this.$refs["ruleForm"].resetFields();
        this.$emit("fromChild", val);
      }
    }
  },
  methods: {
    Register() {
      // 通过element自定义表单校验规则，校验用户输入的用户信息
      this.$refs["ruleForm"].validate(valid => {
        //如果通过校验开始注册
        if (valid) {
          this.$axios
            .post("/api/auth/register", {
              username: this.RegisterUser.name,
              password: this.RegisterUser.pass
            })
            .then(res => {
              // KGAT后端注册成功返回用户信息
              if (res.data.user_id) {
                // 隐藏注册组件
                this.isRegister = false;
                // 弹出通知框提示注册成功信息
                this.notifySucceed("注册成功，请登录");
                // 自动显示登录框
                this.$store.dispatch("setShowLogin", true);
              } else {
                // 弹出通知框提示注册失败信息
                this.notifyError("注册失败");
              }
            })
            .catch(err => {
              // 处理错误响应
              if (err.response && err.response.data) {
                const data = err.response.data;
                let msg = data.detail || data.msg || "注册失败";
                
                // 如果是用户名已存在，提供更友好的提示
                if (msg === "用户名已存在" || msg.includes("用户名已存在")) {
                  msg = "用户名已存在，请尝试其他用户名";
                  // 不清空用户名输入框，让用户修改
                  // 只清空密码输入框
                  this.RegisterUser.pass = "";
                  this.RegisterUser.confirmPass = "";
                } else {
                  // 其他错误，清空所有输入框
                  this.$refs["ruleForm"].resetFields();
                }
                
                this.notifyError(msg);
              } else {
                // 网络错误或其他错误
                this.$refs["ruleForm"].resetFields();
                this.notifyError("注册失败，请检查网络连接");
              }
              return Promise.reject(err);
            });
        } else {
          return false;
        }
      });
    }
  }
};
</script>
<style>
</style>