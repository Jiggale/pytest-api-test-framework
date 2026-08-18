# 接口自动化测试框架（pytest + requests + YAML + Allure）

> 面向测试工程师岗位的作品项目：在开源 demo 基础上重写为**可离线运行、可上 CI** 的接口自动化框架。

## 项目亮点

- **分层架构**：`api`（接口封装）→ `operation`（关键字/业务封装）→ `testcases`（用例），数据用 YAML 驱动，职责清晰。
- **离线可跑**：内置 `MockBackend` 内存契约 mock，**无需部署被测服务**即可全量跑通用例，对学习/面试演示非常友好。
- **CI/CD**：GitHub Actions 每次 push 自动跑用例，并把 Allure 报告部署到 GitHub Pages。
- **报告可视化**：[Allure 在线报告](https://Jiggale.github.io/pytest-api-test-framework/)（首次访问需等待 Pages 部署完成）。

## 技术栈

| 类别 | 选型 |
| --- | --- |
| 语言 | Python 3.10+ |
| 测试框架 | pytest |
| HTTP 客户端 | requests |
| 数据驱动 | PyYAML |
| 报告 | Allure (`allure-pytest`) |
| Mock | requests-mock + 自研 `MockBackend`（状态化契约 mock） |
| CI | GitHub Actions |
| 部署 | GitHub Pages（Allure 报告） |

## 项目结构

```
.
├── api/              # 接口封装层：把 HTTP 接口封装成 Python 方法
├── common/           # 工具类（数据库、配置读取等）
├── core/             # 核心：requests 封装、Mock 后端、断言工具
├── config/           # 配置文件（setting.ini）
├── data/             # 测试数据（YAML）
├── operation/        # 关键字封装层：把多个接口组合成业务关键字
├── testcases/        # 测试用例
├── .github/workflows # CI 配置
├── push_to_github.bat# 一键推送脚本
├── pytest.ini        # pytest 配置
└── requirements.txt  # 依赖清单
```

## 本地运行

### 1. 创建虚拟环境并安装依赖

```powershell
# 推荐使用 conda / venv 隔离环境
pip install -r requirements.txt
```

### 2. 切换为离线 mock 模式

`config/setting.ini` 中：

```ini
[mock]
USE_MOCK = true
```

### 3. 执行用例

```powershell
pytest
```

### 4. 查看 Allure 报告

```powershell
allure serve ./report
```

## CI 流程

`.github/workflows/ci.yml` 在 `push` 到 `main` 分支时自动触发：

1. 装 Python 与依赖
2. 跑 `pytest --alluredir=allure-results`
3. 用 `actions/upload-pages-artifact` + `actions/deploy-pages` 把报告发布到 GitHub Pages

## 简历/面试可讲的几点

- **为什么分层**：接口变更时只改 `api` 层，用例层零修改；关键字复用降低重复代码。
- **为什么加 Mock**：真实环境依赖 Flask + MySQL + Redis，CI 跑不起来；通过状态化 mock 让"测试与被测解耦"，符合契约测试思想。
- **为什么数据驱动**：YAML 把用例和测试数据分离，方便非工程师维护测试场景。
- **CI 价值**：push 即回归，避免"本地能跑线上炸"。
