## KGAT 推荐系统（训练 + 后端 API + 前端）

本仓库是一个可复现的 KGAT（Knowledge Graph Attention Network）推荐系统项目，包含：

- **KGAT 原始训练/推理代码**：`kgat/`（PyTorch + DGL）
- **后端 API**：`backend/`（FastAPI + PostgreSQL）
- **前端界面**：`frontend/`（Vue2 + Vue CLI 4）

---

## 目录

- [快速复现](#快速复现)
- [关键配置](#关键配置)
- [后端 API 概览](#后端-api-概览)
- [可选：启用 KGAT 模型推荐](#可选启用-kgat-模型推荐)
- [可选：训练 KGAT 模型](#可选训练-kgat-模型)
- [可选：可视化与分析脚本](#可选可视化与分析脚本)
- [仓库结构](#仓库结构)
- [引用与致谢](#引用与致谢)

---

## 快速复现

**不训练 KGAT**跑通“数据库 → 导入数据 → 后端 API → 前端页面”。

### 0) 前置条件

- **Python**：建议 3.10+
- **Node.js**：建议 16.x
- **Docker Desktop（推荐）**：一键启动 PostgreSQL（可选 Redis/Neo4j）

### 1) 启动数据库（PostgreSQL）

```powershell
cd backend
docker compose -f docker-compose-db.yml up -d
docker compose -f docker-compose-db.yml ps
```

> 不用 Docker 也可以本地安装 PostgreSQL，然后按 `backend/README.md` 中的 SQL 创建库与用户。

### 2) 启动后端（FastAPI）

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

copy env.example .env
python scripts/init_database.py
python scripts/import_amazon_data.py --max-users 500 --max-kg-triples 5000 --skip-neo4j
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

验证：

- 健康检查：`GET /health` → `{"status":"healthy"}`
- Swagger：访问 `http://localhost:8000/docs`

### 3) 启动前端（Vue2）

```powershell
cd frontend
npm install
npm run serve
```

如果 Node 17+ 遇到 OpenSSL 报错，使用：

```bash
npm run serve:legacy
```

访问：

- 前端：`http://localhost:8080`
- 后端：`http://127.0.0.1:8000`

---

## 关键配置

### 后端 `.env`

在 `backend/` 下由模板生成：

```powershell
cd backend
copy env.example .env
```

默认：

- `USE_KGAT_MODEL=False`
- `USE_NEO4J=False`

### PostgreSQL

```sql
CREATE DATABASE kgat_recommendation;
CREATE USER postgres WITH PASSWORD 'kgat_password';
GRANT ALL PRIVILEGES ON DATABASE kgat_recommendation TO postgres;
\c kgat_recommendation
GRANT ALL ON SCHEMA public TO postgres;
```

`.env` 对应：

```env
DATABASE_URL=postgresql://postgres:kgat_password@localhost:5432/kgat_recommendation
```

### 前端代理

前端开发环境通过 `frontend/vue.config.js` 代理：

- `/api/*` → `http://127.0.0.1:8000/api/*`

这样前端页面里只需要请求 `/api/...`，无需处理跨域。

---

## 后端 API 概览

### 认证（JWT）

- `POST /api/auth/register`
- `POST /api/auth/login`（OAuth2 form：`username=...&password=...`）
- `GET /api/auth/me`

前端会把 token 存在 `localStorage`，并在 `frontend/src/main.js` 中通过 Axios 拦截器注入：

- `Authorization: Bearer <token>`

### 商品（RESTful）

- `GET /api/items/`（分页/搜索/分类筛选）
- `GET /api/items/{item_id}`

### 推荐

- `GET /api/recommendations/me?limit=...`
- `GET /api/recommendations/popular?limit=...`（无需登录）
- `POST /api/recommendations/record-interaction`

### 兼容接口（待补充数据库）

- `POST /api/product/getAllProduct`
- `POST /api/product/getProductByCategory`
- `POST /api/product/getProductBySearch`
- `POST /api/product/getDetails`
- `POST /api/product/getDetailsPicture`
- `POST /api/product/getPromoProduct`
- `POST /api/product/getHotProduct`
- `POST /api/product/getCategory`

对应实现主要在：`backend/app/api/product.py`（映射到 `items` 的查询）。

---

## 可选：启用 KGAT 模型推荐

默认后端使用轻量级算法（ItemCF）即可运行。若你已有训练好的 KGAT 模型，想在后端启用 KGAT：

### 1) 安装 KGAT 相关依赖

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements-kgat.txt
```

> Windows 上安装 `dgl` 可能需要额外 wheel 源（不同 CPU/GPU 版本不同）。如遇安装失败，请以 DGL 官方安装说明为准。

### 2) 配置 `.env`

```env
USE_KGAT_MODEL=True
USE_GPU=False
MODEL_PATH=trained_model/KGAT/amazon-book/.../model_epochXX.pth
```

### 3) 验证模型加载（可选）

```powershell
cd backend
python scripts/init_kgat_model.py
```

---

## 可选：训练 KGAT 模型

原始训练脚本在 `kgat/` 下，建议在虚拟环境中单独安装训练依赖（torch + dgl）。

示例（amazon-book）：

```powershell
cd kgat
python main_kgat.py --data_name amazon-book --n_epoch 50
```

训练输出通常在 `trained_model/` 下，模型路径会类似：

```
trained_model/KGAT/amazon-book/entitydim64_relationdim64_bi-interaction_64-32-16_lr0.0001_pretrain1/model_epoch{epoch}.pth
```

然后按上文把 `MODEL_PATH` 配进 `backend/.env` 即可让后端加载。

---

## 可选：可视化与分析脚本

仓库内包含一些可视化/解释脚本与输出示例：

- 脚本：`kgat/visualization/scripts/`
- 输出：`kgat/visualization/outputs/`

这些内容偏研究/分析用途，不影响运行前后端。

---

## 仓库结构

```
.
├── backend/           # FastAPI 后端
├── frontend/          # Vue2 前端
├── kgat/              # KGAT 原始训练/推理代码
├── datasets/          # 数据集（amazon-book 等）
├── trained_model/     # 训练产物（示例模型/日志）
```

---

## 引用与致谢

KGAT 来源论文（KDD 2019）：

```bibtex
@inproceedings{KGAT19,
  author    = {Xiang Wang and Xiangnan He and Yixin Cao and Meng Liu and Tat{-}Seng Chua},
  title     = {{KGAT:} Knowledge Graph Attention Network for Recommendation},
  booktitle = {{KDD}},
  pages     = {950--958},
  year      = {2019}
}
```


