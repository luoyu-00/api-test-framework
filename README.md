# api-test-framework

接口自动化测试框架（pytest + requests + allure + GitHub Actions）。

面向 **零接口自动化经验、但有 Python 基础** 的同学：跑通它 → 换成真实被测系统 → 扩到 60 条用例 → 简历上就有了能扛住深挖的一条。

---

## 一、5 分钟跑起来（Windows · 零基础版）

> 项目里**已经预建好 `.venv` 虚拟环境并装完依赖**，你不装 Python 也能直接跑。  
> 想长期做测试开发，再去装一个自己的 Python（见 §1.4）。

### 1.1 先打开终端，并且进到项目目录

**最快的办法**：打开「文件资源管理器」，进入下面这个文件夹

```
D:\WorkBuddy\data\2026-11-18-20-27-37\测试转行实践\api-test-framework
```

在**地址栏**（显示路径的那个输入框）里删掉路径、输入 `powershell`，回车。  
终端会直接开在这个目录下，省掉 `cd`。

或者：`Win + R` → 输入 `powershell` → 回车，然后手动进目录：

```powershell
cd "D:\WorkBuddy\data\2026-11-18-20-27-37\测试转行实践\api-test-framework"
```

**怎么确认进对了**：执行 `dir`，应该能看到 `config.yaml`、`testcases`、`sut`、`.venv` 这几个名字。  
**看不到就是没进对**，后面所有命令都会报错，先解决这一步。

### 1.2 启动被测服务（这个窗口开着别关）

```powershell
.\.venv\Scripts\python.exe -m uvicorn sut.main:app --port 8000
```

看到这两行就是成功了：

```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

浏览器打开 <http://127.0.0.1:8000/docs> ，能看到接口列表 = 被测服务活了。

**这个窗口就是"被测系统"，一直开着。关掉它，测试立刻跑不了。**

### 1.3 另开一个终端，跑用例

回到项目目录，用 §1.1 的方法**再开一个** PowerShell 窗口，执行：

```powershell
.\.venv\Scripts\python.exe -m uvicorn sut.main:app --port 8000
```

看到这个就是成功了：

```
============================= 32 passed in 1.21s ==============================
```

### 1.4 关于 Python：你到底要不要自己装一个

| 你的目的                             | 做法                                                            |
| -------------------------------- | ------------------------------------------------------------- |
| 只想先把用例跑起来、看懂框架                   | **不用装**，用项目里预建的 `.venv` 就够了                                   |
| 要长期做测试开发、用 PyCharm / VS Code 写代码 | 去 python.org 装 Python 3.12，**安装时勾选 `Add python.exe to PATH`** |

装了真 Python 之后，重建一次环境（用你自己的解释器）：

```powershell
python -m venv .venv --clear
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

> ⚠️ Windows 商店里那个 `python` 是个"占位程序"，输入 `python` 会弹商店——那不是装了 Python。  
> 用 `python --version` 验证：**能打印版本号才是真装了**，弹商店就说明没装。

### 1.5 常见报错对照表

| 报错 / 现象                                           | 真正原因               | 解决                                                        |
| ------------------------------------------------- | ------------------ | --------------------------------------------------------- |
| `无法将".\.venv\Scripts\python.exe"项识别为 cmdlet...`   | 当前目录不是项目根目录        | 回 §1.1，`dir` 确认能看到 `config.yaml`                          |
| `ModuleNotFoundError: No module named 'api'`      | 在上一层目录跑了 pytest    | 必须在 `api-test-framework` 这一层执行                            |
| `ConnectionRefusedError` / `Max retries exceeded` | 被测服务没起，或端口被占       | 确认 §1.2 的窗口还开着；或换端口 `--port 8001` 并同步改 `config.yaml`      |
| 用例跑了但 `allure-results` 是空的                        | 正常，原始结果在，只是没生成图形报告 | 见 §1.6                                                    |
| PowerShell 提示"禁止运行脚本"                             | 执行策略限制             | 本节所有命令都是 `python.exe -m xxx` 形式，不会触犯策略；不要用 `activate.ps1` |

### 1.6 看图形化报告（第 2 周再做也不迟）

```powershell
allure serve allure-results
```

`allure` 命令行需要单独装：`scoop install allure`，或从  
<https://github.com/allure-framework/allure2/releases> 下 zip，解压后把 `bin` 目录加进 PATH。

每次 `pytest` 都会把原始结果写进 `allure-results/`（已 gitignore），所以随时可以重新生成报告。

### 1.7 如果你用的是 Git Bash 而不是 PowerShell

把 `.\` 换成 `./`，其余一样：

```bash
./.venv/Scripts/python.exe -m uvicorn sut.main:app --port 8000
./.venv/Scripts/python.exe -m pytest
```

### 1.8 换成真实被测系统

改 `config.yaml` 的 `local.base_url` 为真实若依地址（如 `http://127.0.0.1:8080`），账号密码同步改，再跑一次。  
能跑通 → 说明框架真的解耦了；跑不通的用例 → 说明契约模拟器掩盖了真实差异（这正是你要处理的）。

也可以用参数临时切环境，不改文件：

```powershell
.\.venv\Scripts\python.exe -m pytest --env staging
```

---

## 二、为什么要一个"契约模拟器"

```
本地开发 ──→ 真实若依（8080）      业务真、缺陷真、但要装 MySQL/Redis
CI 流水线 ─→ sut/ 契约模拟器（8000） 秒级启动、无依赖、永远可复现
                    ↑
            同一套用例，同一套断言，只换 base_url
```

- 真实系统装一次要半天，CI 里每次拉起太重（MySQL 初始化 + Redis + Java 启动，3~5 分钟），流水线容易红。
- 契约模拟器把「被测服务的接口契约」固化下来，让**框架的质量**可以独立验证。
- 面试时这么讲：「我把测试环境做了分层——CI 用轻量契约服务保证流水线稳定性和可复现，业务验证在真实系统上做。这样测试失败一定是代码问题，不是环境问题。」这句话本身就是资深测试的思维。

> 注意：`sut/` 是**被测对象**，不是测试代码。不要为了让它通过而改它——那不是测试，那是造假。

---

## 三、目录结构与设计取舍

```
api-test-framework/
├─ config.yaml              # 环境配置（base_url / 账号 / 超时），用例零硬编码
├─ conftest.py              # 全局 fixture：配置、token、已登录 client、匿名 client
├─ common/
│  ├─ logger.py             # 双通道日志（控制台 + logs/run.log）
│  ├─ http_client.py        # requests 封装：鉴权注入、重试、耗时、敏感字段脱敏、allure 附件
│  ├─ assert_util.py        # 断言封装：失败信息带上下文，不是光秃秃的 assert
│  └─ data_loader.py        # YAML 数据驱动
├─ api/                     # 接口层（Page Object 的接口版）
│  ├─ base_api.py
│  └─ user_api.py           # LoginApi / UserApi
├─ testcases/               # 用例层：只写业务逻辑，不写 requests
│  ├─ conftest.py
│  ├─ test_login.py
│  └─ test_user.py
├─ data/login_data.yaml     # 参数化数据
├─ sut/main.py              # 被测服务（契约模拟器）
└─ .github/workflows/api-test.yml
```

**四个刻意的设计决定，每一个都是面试考点：**

| 决定                             | 为什么                           | 面试怎么答                                   |
| ------------------------------ | ----------------------------- | --------------------------------------- |
| 三层分离（common / api / testcases） | 接口改了只改 api 层，用例不动             | 「分层是为了降低维护成本，被测系统改一个字段，我只需要改一处」         |
| session 级 token，只登录一次          | 每条用例都登录会让 60 条用例多跑 60 次鉴权，慢且脏 | 「登录是前置条件不是测试目标，用 fixture 做 session 级复用」 |
| 用例自己造数、自己清数                    | 测试不能依赖"库里刚好有条数据"              | 「用例要可重复执行，造数和清理必须成对，否则第二次跑就红」           |
| 断言带响应全文                        | 失败时不用重跑就能定位                   | 「断言信息要能让下一个人直接看懂问题在哪」                   |

---

## 四、三周怎么走

### 第 1 周：把技术跑通（不追求用例数量）

| 天    | 做什么                                                                | 交付             |
| ---- | ------------------------------------------------------------------ | -------------- |
| D1   | ✅ 装环境跑通 32 条用例（已完成）                                                | 截图：32 passed   |
| D2   | 筛选练习：`-k login`、`-m smoke`、`-x`、`--lf` 各跑一次，说清四者区别              | 笔记：什么时候用哪个     |
| D3   | 给 `UserApi` 加 `list_by_status()`，补 3 条状态过滤用例（status=0 / status=1 / status 非法值） | 用例 35 条        |
| D4   | **扩契约**：先在 `sut/main.py` 加 `/system/role/list`，再写 `RoleApi` + 5 条用例（练习"先定契约再写用例"） | 用例 40 条        |
| D5   | 建 GitHub 仓库推送，让 Actions 第一次变绿，点开 gh-pages 里的 allure 报告             | 截图 + 可访问的报告链接 |
| D6-7 | 通读 `assert_util.py`，把 3 条用例的断言从"只验 code"升级为"验业务字段"                   | 提交记录           |

> 注意：D3/D4 的用例必须打**现有 mock 已支持的端点**。想测角色、部门，先在 `sut/main.py` 里补对应端点——
> 这不是"改被测系统作弊"，而是你在扮演"造被测环境"的人，真实项目里测试环境也常常要你自己搭。

### 第 2 周：换真实系统 + 铺量到 40 条

| 天      | 做什么                                   | 交付      |
| ------ | ------------------------------------- | ------- |
| D8-9   | Docker 部署真实若依（见下方命令），把 `base_url` 指过去 | 环境跑通截图  |
| D10    | **处理验证码**（这是你第一个真实的工程问题）              | 见下方"坑位" |
| D11-13 | 按模块扩用例：登录 15 条、用户管理 25 条              | 用例 40 条 |
| D14    | 全量跑一遍，把失败的分成"真 bug / 用例写错 / 环境问题"三类   | 分类记录    |

### 第 3 周：补到 60 条 + 收尾

| 天      | 做什么                                             | 交付       |
| ------ | ----------------------------------------------- | -------- |
| D15-17 | 补到 60 条（角色 12、部门 8，或继续深挖用户管理）                   | 60 条     |
| D18    | 覆盖率自查：每个接口是否都有 正例 / 反例 / 边界 / 鉴权 四类             | 自查表      |
| D19    | 写 `README` + 补 allure 环境信息 + 让报告能公开访问（gh-pages） | 报告链接     |
| D20-21 | 复盘：写 800 字《我如何从零搭一套接口自动化》，把踩的坑写清楚               | 文章（面试素材） |

### Docker 部署真实若依（D8 用）

```bash
# 目录里放好 ry_20250416.sql、quartz.sql（若依源码 sql/ 目录下）
docker run -d --name ry-mysql -p 3306:3306 \
  -e MYSQL_ROOT_PASSWORD=password -e MYSQL_DATABASE=ry-vue \
  -v $PWD/sql:/docker-entrypoint-initdb.d mysql:5.7 --character-set-server=utf8mb4

docker run -d --name ry-redis -p 6379:6379 redis:6

# 后端：源码 mvn package 出 jar 后在 target/ 下执行
java -jar ruoyi-admin.jar
# 前端：npm install && npm run dev
```

嫌重就换单容器方案（`halohub/halo:2.x`，内置 H2，一条 `docker run` 就起），接口换成 `/apis/content.halo.run/v1alpha1/posts` 即可，框架一行不用改。

---

## 五、坑位清单（这些坑本身就是面试素材）

1. **登录验证码**：若依默认开验证码，自动化会卡在第一步。  
   处理：测试环境把 `sys.account.captchaEnabled` 设为 `false`（或改 `application.yml`），**并写进测试计划的风险章节**。  
   面试答：「验证码是防人的，不是防接口的。测试环境关闭是标准做法，生产环境我们评估过——真正的风险是短信轰炸，那要靠限流，不是靠验证码。」
2. **脏数据**：`auto_test` 用户跑 50 次就有 50 个。→ 用例名带时间戳，fixture 里删。
3. **断言太死**：`assert resp.json() == {...}` 全字段比对，接口多返回一个 `createTime` 就红。→ 只断言你关心的字段。
4. **依赖执行顺序**：pytest 默认按文件名排，不等于业务顺序。→ 用 fixture 表达依赖，不要靠文件名。
5. **CI 里没有真实 SUT**：不要在 workflow 里装 MySQL。→ 用契约模拟器，或用 `docker compose` 的 service containers。
6. **allure 报告地址**：`allure serve` 只能本机看。→ 用 gh-pages 部署，简历里放可访问链接，面试官能自己点开看。这是作品集和"我做过"的分界线。

---

## 六、扩到 60 条的清单（防止瞎写）

每个接口至少四类：

- **正例**：合法参数 → 成功，且落库/可查（不只是看 code=200）
- **反例**：必填缺失、类型错误、超长、特殊字符、重复
- **边界**：长度 0/1/最大/最大+1，分页 0/1/最大/最大+1，数值上下界
- **鉴权**：无 token、过期 token、伪造 token、低权限 token 访问高权限接口

| 模块     | 正例 | 反例 | 边界 | 鉴权 | 小计     |
| ------ | -- | -- | -- | -- | ------ |
| 登录     | 2  | 6  | 3  | 2  | 13     |
| 用户管理   | 8  | 10 | 8  | 2  | 28     |
| 角色管理   | 4  | 4  | 3  | 1  | 12     |
| 部门/字典  | 4  | 3  | 2  | 1  | 10     |
| **合计** |    |    |    |    | **63** |

---

## 七、这套东西最后变成简历上的什么

> **接口自动化测试框架（个人项目 · 2026.11–2027.01）**  
> 基于 pytest + requests + allure 搭建三层架构（配置层/接口层/用例层），实现 token 自动注入、失败重试、敏感字段脱敏、请求响应全链路日志；  
> 覆盖登录鉴权与用户管理 63 条用例（正例/反例/边界/鉴权四类），用 fixture 实现数据自造自清，支持重复执行不产生脏数据；  
> 接入 GitHub Actions，push 触发全量回归并发布 allure 报告至 gh-pages，单次执行 28s。  
> 仓库：github.com/xxx/api-test-framework　报告：xxx.github.io/api-test-framework

面试官会顺着问的四个问题，提前准备好答案：

1. 为什么用 session 级 token，不用 function 级？
2. 用例之间怎么保证互不影响？
3. 接口改了字段，你要改几个文件？
4. 这个框架哪里还能改进？（答：数据与用例未完全分离、缺 schema 校验、缺并发、报告没接失败重试留痕）
