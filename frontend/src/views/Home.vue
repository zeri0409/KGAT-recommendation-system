<!--
 * @Description: 首页组件（集成KGAT推荐功能）- 使用本地图书封面
 -->
<template>
  <div class="home" id="home" name="home">
    <!-- 轮播图 -->
    <div class="block">
      <el-carousel height="460px">
        <el-carousel-item v-for="item in bannerList" :key="item.id">
          <img 
            style="width:100%; height:460px; object-fit:cover; cursor:pointer;" 
            :src="item.image" 
            :alt="item.title"
            @click="handleBannerClick(item)"
          />
        </el-carousel-item>
      </el-carousel>
    </div>
    <!-- 轮播图END -->
    
    <div class="main-box">
      <div class="main">
        
        <!-- ============ 未登录用户：热门商品显示在最前面 ============ -->
        <div class="recommend hot-section" v-if="!isLogin && hotList.length > 0">
          <div class="box-hd">
            <div class="title">
              <i class="el-icon-hot-water"></i> 热门商品
            </div>
            <div class="subtitle">大家都在看</div>
          </div>
          <div class="box-bd">
            <div class="recommend-list">
              <el-row :gutter="20">
                <el-col :span="6" v-for="item in hotList" :key="'hot-' + item.item_id">
                  <div class="recommend-item" @click="goToDetail(item.item_id)">
                    <div class="img-box">
                      <img :src="getImageUrl(item.image_url, item.item_id)" :alt="item.title" />
                    </div>
                    <div class="info">
                      <div class="name">{{ item.title || '商品' + item.item_id }}</div>
                      <div class="price" v-if="item.price">¥{{ item.price }}</div>
                    </div>
                  </div>
                </el-col>
              </el-row>
            </div>
          </div>
        </div>
        <!-- 未登录热门商品END -->

        <!-- ============ 为你推荐模块（已登录用户） ============ -->
        <div class="recommend" v-if="isLogin && recommendList.length > 0">
          <div class="box-hd">
            <div class="title">
              <i class="el-icon-star-on"></i> 为你推荐
            </div>
            <div class="subtitle">基于KGAT知识图谱的个性化推荐</div>
          </div>
          <div class="box-bd">
            <div class="recommend-list">
              <el-row :gutter="20">
                <el-col :span="6" v-for="item in recommendList" :key="'rec-' + item.item_id">
                  <div class="recommend-item" @click="goToDetail(item.item_id)">
                    <div class="img-box">
                      <img :src="getImageUrl(item.image_url, item.item_id)" :alt="item.title" />
                    </div>
                    <div class="info">
                      <div class="name">{{ item.title || '商品' + item.item_id }}</div>
                      <div class="price" v-if="item.price">¥{{ item.price }}</div>
                      <div class="score" v-if="item.score">
                        <el-rate 
                          v-model="item.score" 
                          disabled 
                          :max="5"
                          :colors="['#99A9BF', '#F7BA2A', '#FF9900']">
                        </el-rate>
                      </div>
                    </div>
                  </div>
                </el-col>
              </el-row>
            </div>
            <!-- 加载更多 -->
            <div class="load-more" v-if="hasMoreRecommend">
              <el-button type="text" @click="loadMoreRecommend" :loading="loadingMore">
                加载更多推荐
              </el-button>
            </div>
          </div>
        </div>
        <!-- 为你推荐模块END -->

        <!-- ============ 已登录用户：热门商品显示在为你推荐下方 ============ -->
        <div class="recommend hot-section" v-if="isLogin && hotList.length > 0">
          <div class="box-hd">
            <div class="title">
              <i class="el-icon-hot-water"></i> 热门商品
            </div>
            <div class="subtitle">大家都在看</div>
          </div>
          <div class="box-bd">
            <div class="recommend-list">
              <el-row :gutter="20">
                <el-col :span="6" v-for="item in hotList" :key="'hot-login-' + item.item_id">
                  <div class="recommend-item" @click="goToDetail(item.item_id)">
                    <div class="img-box">
                      <img :src="getImageUrl(item.image_url, item.item_id)" :alt="item.title" />
                    </div>
                    <div class="info">
                      <div class="name">{{ item.title || '商品' + item.item_id }}</div>
                      <div class="price" v-if="item.price">¥{{ item.price }}</div>
                    </div>
                  </div>
                </el-col>
              </el-row>
            </div>
          </div>
        </div>
        <!-- 已登录热门商品END -->

        <!-- 推荐商品 展示区域 -->
        <div class="phone">
          <div class="box-hd">
            <div class="title">推荐商品</div>
          </div>
          <div class="box-bd">
            <div class="list">
              <MyList :list="phoneList" :isMore="true"></MyList>
            </div>
          </div>
        </div>
        <!-- 推荐商品 展示区域END -->
      </div>
    </div>
  </div>
</template>
<script>
export default {
  data() {
    return {
      // 轮播图数据 - 本地活动图片
      bannerList: [
        {
          id: 1,
          image: '/carousel/banner_01.jpg',
          title: '新书上架',
          link: '/goods'
        },
        {
          id: 2,
          image: '/carousel/banner_02.jpg',
          title: '限时优惠',
          link: '/goods'
        },
        {
          id: 3,
          image: '/carousel/banner_03.jpg',
          title: '热门推荐',
          link: '/goods'
        },
        {
          id: 4,
          image: '/carousel/banner_04.png',
          title: '会员专享',
          link: '/goods'
        }
      ],
      phoneList: "", // 推荐商品列表
      // 推荐相关数据
      recommendList: [], // 个性化推荐列表
      hotList: [], // 热门商品列表
      recommendPage: 1, // 推荐分页
      hasMoreRecommend: true, // 是否有更多推荐
      loadingMore: false // 加载更多状态
    };
  },
  computed: {
    // 判断用户是否登录
    isLogin() {
      return this.$store.getters.getUser;
    }
  },
  watch: {
    // 监听登录状态变化，重新获取推荐
    isLogin(newVal) {
      if (newVal) {
        this.fetchRecommendations();
      } else {
        this.recommendList = [];
      }
    }
  },
  created() {
    // 获取推荐商品数据
    this.getPromo("book", "phoneList");
    
    // 始终获取热门商品（无论是否登录）
    this.fetchHotProducts();
    
    // 如果已登录，获取个性化推荐
    if (this.isLogin) {
      this.fetchRecommendations();
    }
  },
  methods: {
    // 点击轮播图跳转
    handleBannerClick(item) {
      if (item.link) {
        this.$router.push(item.link);
      }
    },
    
    // 获取图片URL - 支持本地图书封面
    getImageUrl(imageUrl, itemId) {
      // 如果图片URL以 /books/ 开头，说明是本地图片
      if (imageUrl && imageUrl.startsWith('/books/')) {
        return imageUrl;
      }
      
      // 如果是 Data URI 或完整 URL
      if (imageUrl) {
        if (imageUrl.startsWith('data:')) {
          return imageUrl;
        }
        if (imageUrl.startsWith('http://') || imageUrl.startsWith('https://')) {
          // 检查是否是不可访问的外部URL，使用本地图片替代
          if (imageUrl.includes('placeholder') || imageUrl.includes('via.placeholder') || imageUrl.includes('picsum') || imageUrl.includes('loremflickr') || imageUrl.includes('unsplash')) {
            return this.getLocalBookImage(itemId);
          }
          return imageUrl;
        }
        // 相对路径，拼接后端地址
        return this.$target + imageUrl;
      }
      
      // 没有图片URL，使用本地图书封面
      return this.getLocalBookImage(itemId);
    },
    
    // 获取本地图书封面图片路径（伪随机分配，同一商品始终显示同一图片）
    getLocalBookImage(itemId) {
      // 使用简单哈希函数打乱图片顺序，避免尾号相同的商品显示相同图片
      const id = itemId || 0;
      // 哈希公式：(id * 质数1 + 质数2) % 图片总数
      const hash = (id * 31 + id * 17 + 13) % 50;
      const imageIndex = hash + 1;
      const paddedIndex = imageIndex.toString().padStart(2, '0');
      return `/books/book_${paddedIndex}.jpg`;
    },
    
    // 获取各类商品数据方法封装
    getPromo(categoryName, val, api) {
      api = api != undefined ? api : "/api/product/getPromoProduct";
      this.$axios
        .post(api, {
          categoryName
        })
        .then(res => {
          this[val] = res.data.Product;
        })
        .catch(err => {
          return Promise.reject(err);
        });
    },
    
    // ============ 推荐相关方法 ============
    
    // 获取个性化推荐
    async fetchRecommendations() {
      try {
        const res = await this.$axios.get("/api/recommendations/me", {
          params: { limit: 8 }
        });
        
        if (res.data && res.data.recommendations) {
          this.recommendList = res.data.recommendations;
          this.hasMoreRecommend = res.data.recommendations.length >= 8;
        }
      } catch (error) {
        console.error("获取推荐失败:", error);
      }
    },
    
    // 获取热门商品（始终获取，无论是否登录）
    async fetchHotProducts() {
      try {
        const res = await this.$axios.get("/api/recommendations/popular", {
          params: { limit: 8 }
        });
        
        if (res.data && res.data.recommendations) {
          this.hotList = res.data.recommendations;
        }
      } catch (error) {
        console.error("获取热门商品失败:", error);
      }
    },
    
    // 加载更多推荐
    async loadMoreRecommend() {
      this.loadingMore = true;
      this.recommendPage++;
      
      try {
        const res = await this.$axios.get("/api/recommendations/me", {
          params: { 
            limit: 8,
            offset: (this.recommendPage - 1) * 8
          }
        });
        
        if (res.data && res.data.recommendations) {
          if (res.data.recommendations.length > 0) {
            this.recommendList = [...this.recommendList, ...res.data.recommendations];
          }
          this.hasMoreRecommend = res.data.recommendations.length >= 8;
        }
      } catch (error) {
        console.error("加载更多推荐失败:", error);
      } finally {
        this.loadingMore = false;
      }
    },
    
    // 跳转到商品详情页
    goToDetail(itemId) {
      this.$router.push({
        path: "/goods/details",
        query: { productID: itemId }
      });
    }
  }
};
</script>
<style scoped>
@import "../assets/css/index.css";

/* 推荐模块样式 */
.recommend {
  margin-bottom: 30px;
}

.recommend .box-hd {
  display: flex;
  align-items: baseline;
  padding-bottom: 15px;
  border-bottom: 2px solid #ff6700;
}

.recommend .box-hd .title {
  font-size: 22px;
  font-weight: 400;
  color: #333;
}

.recommend .box-hd .title i {
  color: #ff6700;
  margin-right: 5px;
}

.recommend .box-hd .subtitle {
  margin-left: 15px;
  font-size: 12px;
  color: #999;
}

.recommend .box-bd {
  padding: 20px 0;
}

.recommend-list {
  margin: 0 -10px;
}

.recommend-item {
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s ease;
  margin-bottom: 20px;
}

.recommend-item:hover {
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
  transform: translateY(-3px);
  border-color: #ff6700;
}

.recommend-item .img-box {
  width: 100%;
  height: 180px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f5f5;
  overflow: hidden;
}

.recommend-item .img-box img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.recommend-item .info {
  padding: 15px;
}

.recommend-item .info .name {
  font-size: 14px;
  color: #333;
  height: 40px;
  line-height: 20px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.recommend-item .info .price {
  font-size: 18px;
  color: #ff6700;
  font-weight: bold;
  margin-top: 10px;
}

.recommend-item .info .score {
  margin-top: 8px;
}

.load-more {
  text-align: center;
  padding: 20px 0;
}

.load-more .el-button {
  font-size: 14px;
  color: #ff6700;
}

/* 热门商品模块特殊样式 */
.hot-section .box-hd {
  border-bottom-color: #e74c3c;
}

.hot-section .box-hd .title i {
  color: #e74c3c;
}

.hot-section .recommend-item:hover {
  border-color: #e74c3c;
}

.hot-section .recommend-item .info .price {
  color: #e74c3c;
}
</style>
