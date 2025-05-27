---
applyTo: "**"
---

# Taipei City Dashboard 建置指南

## 项目架构

Taipei City Dashboard 由以下主要组件组成:

- 前端 Dashboard 可视化界面 (React + Vite)
- 后端 API 服务 (Go)
- 数据库服务 (PostgreSQL + PostGIS)
- AI 导航服务 (Python MCP)
- Redis 缓存服务

## Docker 环境

- 所有组件都应使用 Docker 容器化
- 配置文件应放在 `docker/.env` 中
- 数据库服务使用 `docker-compose-db.yaml` 管理
- 应用服务使用 `docker-compose.yaml` 管理

## 数据库配置

使用两个 PostgreSQL 数据库:

- `postgres-data`: 存储仪表盘数据
- `postgres-manager`: 存储仪表盘管理数据

数据库连接配置:

```yaml
DB_DASHBOARD_HOST=postgres-data  # Docker 网络中的主机名
DB_DASHBOARD_PORT=5432
DB_MANAGER_HOST=postgres-manager
DB_MANAGER_PORT=5432


MCP AI 導航服務
使用 Python 3.12
使用 uv 作為包管理工具
採用 MCP (Model Context Protocol) 架構
使用 asyncpg 進行非同步資料庫連線
在 Docker 環境中需連接到 br_dashboard 網路

後端開發
使用 Gin 框架開發 RESTful API
資料庫存取使用 GORM
遵循 Clean Architecture 原則
建置流程
準備環境變數: .env
啟動資料庫服務: docker-compose -f docker-compose-db.yaml up -d
建置並啟動應用服務: docker-compose up -d
AI 導航服務單獨建置: cd Dashboard-MCP/ai_nav && docker build -t ai_nav_img .
Docker 網路注意事項
所有容器應連接到 br_dashboard 網路
容器間通訊使用服務名稱作為主機名稱(如 postgres-data)
從宿主機存取服務需使用連接埠映射和 localhost
故障排查
資料庫連線問題: 檢查 .env 設定和網路設置
容器啟動問題: 查看 docker logs <container_name>
應用錯誤: 參考各服務的日誌輸出
CI/CD 流程
GitHub Actions 用於自動化測試
Docker 映像檔建置和部署流程遵循 GitOps 原則

請在每次執行完畢後更新此說明文件，確保此文件跟上專案最新進度。
```
