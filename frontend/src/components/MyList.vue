<!--
 * @Description: 列表组件，用于首页、全部商品页面的商品列表 - 使用本地图书封面
 -->
<template>
  <div id="myList" class="myList">
    <ul>
      <li v-for="item in list" :key="item.product_id">
        <el-popover placement="top">
          <p>确定删除吗？</p>
          <div style="text-align: right; margin: 10px 0 0">
            <el-button type="primary" size="mini" @click="deleteCollect(item.product_id)">确定</el-button>
          </div>
          <i class="el-icon-close delete" slot="reference" v-show="isDelete"></i>
        </el-popover>
        <router-link :to="{ path: '/goods/details', query: {productID:item.product_id} }">
          <img :src="getImageUrl(item.product_picture, item.product_id)" alt />
          <h2>{{item.product_name}}</h2>
          <h3>{{item.product_title}}</h3>
          <p>
            <span>{{item.product_selling_price}}元</span>
            <span
              v-show="item.product_price != item.product_selling_price"
              class="del"
            >{{item.product_price}}元</span>
          </p>
        </router-link>
      </li>
      <li v-show="isMore && list.length>=1" id="more">
        <router-link :to="{ path: '/goods', query: {categoryID:categoryID} }">
          浏览更多
          <i class="el-icon-d-arrow-right"></i>
        </router-link>
      </li>
    </ul>
  </div>
</template>
<script>
export default {
  name: "MyList",
  // list为父组件传过来的商品列表
  // isMore为是否显示"浏览更多"
  // isDelete为是否显示删除按钮
  props: ["list", "isMore", "isDelete"],
  data() {
    return {};
  },
  computed: {
    // 通过list获取当前显示的商品的分类ID，用于"浏览更多"链接的参数
    categoryID: function() {
      let categoryID = [];
      if (this.list != "") {
        for (let i = 0; i < this.list.length; i++) {
          const id = this.list[i].category_id;
          if (!categoryID.includes(id)) {
            categoryID.push(id);
          }
        }
      }
      return categoryID;
    }
  },
  methods: {
    // 获取图片URL - 支持本地图书封面、Data URI 和普通 URL
    getImageUrl(picture, productId) {
      if (!picture) {
        return this.getLocalBookImage(productId);
      }
      
      // 如果是本地图书路径
      if (picture.startsWith('/books/')) {
        return picture;
      }
      
      // 如果是 Data URI，直接返回
      if (picture.startsWith('data:')) {
        return picture;
      }
      
      // 如果是完整 URL
      if (picture.startsWith('http://') || picture.startsWith('https://')) {
        // 检查是否是不可访问的外部URL，使用本地图片替代
        if (picture.includes('placeholder') || picture.includes('via.placeholder') || picture.includes('picsum') || picture.includes('loremflickr') || picture.includes('unsplash')) {
          return this.getLocalBookImage(productId);
        }
        return picture;
      }
      
      // 相对路径，拼接后端地址
      return this.$target + picture;
    },
    
    // 获取本地图书封面图片路径（伪随机分配，同一商品始终显示同一图片）
    getLocalBookImage(productId) {
      // 使用简单哈希函数打乱图片顺序，避免尾号相同的商品显示相同图片
      const id = productId || 0;
      // 哈希公式：(id * 质数1 + 质数2) % 图片总数
      const hash = (id * 31 + id * 17 + 13) % 50;
      const imageIndex = hash + 1;
      const paddedIndex = imageIndex.toString().padStart(2, '0');
      return `/books/book_${paddedIndex}.jpg`;
    },
    
    deleteCollect(product_id) {
      this.$axios
        .post("/api/user/collect/deleteCollect", {
          user_id: this.$store.getters.getUser.user_id,
          product_id: product_id
        })
        .then(res => {
          switch (res.data.code) {
            case "001":
              // 删除成功
              // 删除删除列表中的该商品信息
              for (let i = 0; i < this.list.length; i++) {
                const temp = this.list[i];
                if (temp.product_id == product_id) {
                  this.list.splice(i, 1);
                }
              }
              // 提示删除成功信息
              this.notifySucceed(res.data.msg);
              break;
            default:
              // 提示删除失败信息
              this.notifyError(res.data.msg);
          }
        })
        .catch(err => {
          return Promise.reject(err);
        });
    }
  }
};
</script>
<style scoped>
.myList ul li {
  z-index: 1;
  float: left;
  width: 234px;
  height: 280px;
  padding: 10px 0;
  margin: 0 0 14.5px 13.7px;
  background-color: white;
  -webkit-transition: all 0.2s linear;
  transition: all 0.2s linear;
  position: relative;
}
.myList ul li:hover {
  z-index: 2;
  -webkit-box-shadow: 0 15px 30px rgba(0, 0, 0, 0.1);
  box-shadow: 0 15px 30px rgba(0, 0, 0, 0.1);
  -webkit-transform: translate3d(0, -2px, 0);
  transform: translate3d(0, -2px, 0);
}
.myList ul li img {
  display: block;
  width: 160px;
  height: 160px;
  background: url(../assets/imgs/placeholder.png) no-repeat 50%;
  margin: 0 auto;
  object-fit: contain;
}
.myList ul li h2 {
  margin: 25px 10px 0;
  font-size: 14px;
  font-weight: 400;
  color: #333;
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
  overflow: hidden;
}
.myList ul li h3 {
  margin: 5px 10px;
  height: 18px;
  font-size: 12px;
  font-weight: 400;
  color: #b0b0b0;
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
  overflow: hidden;
}
.myList ul li p {
  margin: 10px 10px 10px;
  text-align: center;
  color: #ff6700;
}
.myList ul li p .del {
  margin-left: 0.5em;
  color: #b0b0b0;
  text-decoration: line-through;
}
.myList #more {
  text-align: center;
  line-height: 280px;
}
.myList #more a {
  font-size: 18px;
  color: #333;
}
.myList #more a:hover {
  color: #ff6700;
}
.myList ul li .delete {
  position: absolute;
  top: 10px;
  right: 10px;
  display: none;
}
.myList ul li:hover .delete {
  display: block
}
.myList ul li .delete:hover {
  color: #ff6700;
}
</style>
