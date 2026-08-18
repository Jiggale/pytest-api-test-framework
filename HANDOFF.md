# 项目接手说明（Handoff）—— 给 WorkBuddy / 后续维护者

> 本文档面向**接手本项目的人**（如 WorkBuddy 或新同事），说明项目背景、改造点、CI 配置、已知坑和日常操作。
> 普通简历/作品介绍请看 `README.md`，本文件偏"维护者视角"。

---

## 0. 一句话定位

这是一个**接口自动化测试框架**学习作品：基于开源 `pytestDemo` 重写，核心改造是**离线可跑（Mock）** + **GitHub Actions 自动跑用例并发布 Allure 报告到 Pages**。

- 仓库：`https://github.com/Jiggale/pytest-api-test-framework`
- 在线报告：`https://Jiggale.github.io/pytest-api-test-framework/`
- 原作者 demo 仓库：`https://github.com/wintests/flaskDemo`（被测试的真实接口服务，本项目已不依赖它）

---

## 1. 项目来源与改造史（重要背景）

原 `pytestDemo` 依赖作者私有的 `192.168.89.128:9999` 虚拟机 + MySQL + Redis，
**离开作者环境根本跑不起来**。本项目在原 demo 基础上做了如下改造（**未改动原 `pytestDemo` 目录，只在副本 `pytestDemo-mine` 里改**）：

| 改造项 | 文件 | 说明 |
| --- | --- | --- |
| 离线 Mock | `core/mock_data.py`（新增） | `MockBackend` 内存契约 mock + SQL 联动 |
| Mock 接入请求 | `core/rest_client.py` | 修 `files/cookies` 误用 `params` bug；`request` 增加 mock 分支 |
| 数据库路由 | `common/mysql_operate.py` | `USE_MOCK` 时 `MysqlDb` 不连真库，`exec_sql` 路由到内存假库 |
| 透传开关 | `api/user.py` | 读 `setting.ini` 的 `USE_MOCK` 透传 `RestClient` |
| 数据修正 | `data/api_test_data.yml` | 修原 demo 把 `1004` 写成 `"1004"` 的字符串笔误 |
| 配置开关 | `config/setting.ini` | 新增 `[mock] USE_MOCK = true` |
| 依赖升级 | `requirements.txt` | pytest>=8 / allure-pytest / requests-mock 等 |
| 一键推送 | `push_to_github.bat` | 填好用户名邮箱的容错版推送脚本 |
| CI | `.github/workflows/ci.yml` | 见下文 |
| 忽略项 | `.gitignore` | 排除 report/ log/ __pycache__/ allure-results/ 等 |

> ⚠️ 注意：`api_root_url = http://192.168.89.128:9999` 和 `mock_data.py` 里的 `192.168.89.128` 字符串**必须保留**——
> 那是 Mock 后端用来 strip 路径前缀的"特征串"，删了用例就跑不通。**这不是残留 bug，是设计需要。**

---

## 2. 目录结构

```
pytestDemo-mine/
├── api/              # 接口封装层：把 HTTP 接口封装成 Python 方法
├── common/           # 工具类（数据库、配置读取等）
├── config/           # 配置（setting.ini）
├── core/             # 核心：requests 封装、Mock 后端、断言工具
├── data/             # 测试数据（YAML）
├── operation/        # 关键字封装层：把多个接口组合成业务关键字
├── testcases/        # 测试用例（api_test / scenario_test）
├── .github/workflows/ci.yml
├── push_to_github.bat
├── pytest.ini
├── requirements.txt
├── README.md         # 面向读者/面试官的作品说明
├── HANDOFF.md        # 本文件（维护者视角）
└── Developer         # 空占位文件，可删
```

---

## 3. 本地运行

```powershell
# 1. 建虚拟环境（推荐 conda / venv 隔离）
conda create -n pytest_study python=3.12 -y
conda activate pytest_study

# 2. 装依赖
pip install -r requirements.txt

# 3. （可选）本地看 Allure 报告需先装 allure 命令行
#    macOS/Linux: brew install allure  或下载 release zip
#    Windows: 下载 https://github.com/allure-framework/allure2/releases 解压并加入 PATH

# 4. 跑用例（离线 mock 模式，use_mock 默认 true）
pytest testcases -q --alluredir=allure-results

# 5. 看报告
allure serve ./allure-results
```

> 注意：原 demo 的 `pytest.ini` 里可能已配置 `--alluredir` 等选项，直接 `pytest` 也能跑。
> 在 CI 里我们显式指定 `pytest testcases -q --alluredir=allure-results`。

---

## 4. CI 配置说明（`.github/workflows/ci.yml`）

两个 job：

### job 1：`test`
- 检出 → 装 Python 3.12 → `pip install -r requirements.txt` → `pytest testcases -q --alluredir=allure-results`
- 把 `allure-results` 上传为 artifact（供下一个 job 用）
- **只负责跑用例，不部署**

### job 2：`allure-report`
- 依赖 `test`（`needs: test`）
- 仅在 `push` 到 `main`/`master` 时运行（`if: github.event_name == 'push' ...`）
- 下载 artifact → **装 Allure 命令行（下载 zip 方式，见坑 #1）** → `allure generate` → `actions/deploy-pages` 发布
- 挂 `environment: github-pages`

顶部声明：

```yaml
permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: pages
  cancel-in-progress: false
```

仓库必须：
- **Settings → Environments** 新建一个名为 `github-pages` 的 environment（名字必须一致）
- **Settings → Pages** 的 Source 选 **GitHub Actions**

---

## 5. 踩过的坑（接手前必读）

### 坑 1：`allure: command not found`（CI 报告生成失败）
- ❌ 原写法：`sudo apt-get install -y allure` —— Ubuntu 仓库里的 `allure` 是 Java 旧版且不一定可用，导致命令找不到。
- ✅ 现写法：下载 release zip 解压并软链到 `/usr/local/bin/allure` + 校验 `allure --version`。
```yaml
curl -o allure.zip -L https://github.com/allure-framework/allure2/releases/download/2.30.0/allure-2.30.0.zip
unzip allure.zip -d /opt/
sudo ln -sf /opt/allure-2.30.0/bin/allure /usr/local/bin/allure
allure --version
```

### 坑 2：Pages 404
- 原因一：`allure-report` job 没成功部署（见坑 1）。
- 原因二：Pages Source 没选 `GitHub Actions`。
- 解决：先确保 CI 跑绿 → 确认 Pages Source=GitHub Actions → 若仍 404，去 Actions 手动 **Re-run** `allure-report` job。

### 坑 3：第三方 deploy action 与官方 environment 不兼容
- ❌ 早期用过 `peaceiris/actions-gh-pages@v4`（推 `gh-pages` 分支），与 Pages Source=GitHub Actions 冲突。
- ✅ 改用官方 `actions/deploy-pages@v4` + `actions/configure-pages` + `actions/upload-pages-artifact`，配合 `github-pages` environment。

### 坑 4：`push_to_github.bat` 占位符
- 早期模板里是 `YOUR_GITHUB_USERNAME` / `YOUR_EMAIL`，会导致远程地址错误 + git 身份错乱。
- 现已填好 `Jiggale` / `1255039164@qq.com`，且脚本改为"远程已存在则 `set-url` 而非 `add`"，更容错。

### 坑 5：PowerShell 下 `cd /d` 报错
- 这是 CMD 语法，在 PowerShell 里要用 `Set-Location` 或 `cd`（不带 `/d`）。bat 文件本身在 CMD 下运行正常。

### 坑 6：git 中文日志乱码
- 终端 GBK 编码导致 `git log` 中文 commit message 显示为乱码（`鎺ュ彛...`），**内容本身正常**，不影响功能。

---

## 6. 日常维护操作

### 改代码后推送到 GitHub
```powershell
git add .
git commit -m "你的改动说明"
git push        # 自动触发 CI，报告自动更新
```

### 想手动触发 CI（不 push）
- 进仓库 **Actions → API Test CI → Run workflow**（我们在 ci.yml 里加了 `workflow_dispatch`）。

### 想本地看报告而不想装 allure
- 用 artifact 下载：Actions 里某个 run 的 `allure-results` artifact 下载后，本地 `allure serve` 即可。

### 想换被测试的真实服务（去掉 mock）
- `config/setting.ini` 里 `USE_MOCK = false`，并把 `api_root_url` / MySQL 配置指向真实服务。
- 注意：真实服务依赖 `flaskDemo`，需要另行部署 Flask + MySQL + Redis。

---

## 7. 已知遗留项（TODO）

- [ ] `Developer` 空文件可删除（无实际用途）。
- [ ] `testcases/` 下混有 `*.pyc`，应在 `.gitignore` 已忽略，确认未入库。
- [ ] 报告里 `scenario_test` 有 2 个灰色（skipped/xfailed）用例，属预期，非 bug。
- [ ] 如需多 Python 版本矩阵测试，可在 `test` job 加 `matrix: python-version`。
- [ ] 如想接邮件/钉钉通知，可在 `allure-report` job 后加通知 step。

---

## 8. 负责人 & 联系

- GitHub 账号：`Jiggale`
- 首次搭建：2026-08-18
- 最后稳定状态：CI 全绿，Allure 报告 100% 通过（20 cases）。
