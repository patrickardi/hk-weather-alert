# 下一场对话请先读此文件

同一项目，新开 OpenCode 会话。工作目录必须是：

`/Users/weidongli/Desktop/hk-weather-alert`

那是已连 GitHub 的完整最新版。不要用 `hackathon project`（空壳）或桌面根上的旧 `weather-card-probe`。

## GitHub

- 仓库：https://github.com/patrickardi/hk-weather-alert
- 账号：`wikky-coder`（write，不是 admin）
- `main` 已是 `app/` 结构
- 旧 main 备份：`backup/main-before-app-layout`
- GitHub 2026-10-12 留底：`backup/github-main-2026-10-12` 与标签 `archive/github-main-2026-10-12`（`0a6c78d`）
- **不要改、不要推、不要 force-push 任何 backup/ 或 archive/ 引用**
- 不要 force-push `main`

## 架构

`wire.py` 镜像上游 JSON（保留 `""`）→ `adapters.py` 唯一映射 → `engine.evaluate(PersonalContext, WeatherState)` → `render.py` HTML。

规则：`app/rules/*.yaml`。区名：`mapping.py`（屯門區 ≠ 屯門）。警告身份用 `code` 不是 dict 键。

## 已完成

- 三层边界；`python3 -m pytest` 43 个测试
- HTML 卡（DO/DONT/STATUS + 999），`python3 -m app.render`；fixture 卡：`python3 -m app.render --fixtures`
- 热线文案：`ContactInfo.label` 不含号码；CONTACT 按警告计算（T8+/红黑雨/山泥 → 2572 8427 24h；仅酷热 → 午夜前；否则 1823；999/992 常在）
- 块级结果：六块 `BlockOutcome`；庇护所永不写成「已开放」；101 湖山路降雨显示、庇护所省略
- `CANCEL` 过滤；warnsum×rhrread 交叉校验；三态个人字段；`Severity.rank`；`Rule.provenance`
- ALS 庇护所探针在 `/Users/weidongli/Desktop/hackathon项目/weather-card-probe/`
- `fixtures/warnsum_en_live.json` 为 `{}` 是无警告时的真值，不是坏文件
- `python3 -m app.probe --als` 可打村屋/屋邨/不存在地址（需网络）

## 已知缺陷

- 渲染只有 HTML，没有 Playwright JPEG
- 未接 GenAI 编码入口、中英并列输出、庇护所白名单命中后才显示 SHELTER
- 本地 `main` 落后 `origin/main` 4 个 commit（那些是 TextEdit RTF 规则文件 + 过期 AGENTS.md）；不要把备份分支的内容覆盖进来

## 不要做的

- 不要让 LLM 直接打 API 然后口播数字
- 不要把 `""` 当成 0/False
- 不要推荐强制 `b=1`
- 不要声称 Observatory 不服务少数族裔；`lang=id` 是 200+HTML
- 不要用机翻填印尼文
- 不要动 `backup/*` 或 `archive/*`

## 新对话怎么开

OpenCode 里对新 session，cwd 选本文件夹，第一句：「先读 HANDOFF.md 和 AGENTS.md，接着干。」
