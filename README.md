# AI Frontier Radar

这是一个 GitHub Pages 静态网站，使用 GitHub Actions 每天自动刷新。

## 自动刷新

- 工作流文件：`.github/workflows/daily-update.yml`
- 生成脚本：`scripts/update_site.py`
- 定时：每天 00:00 UTC，即北京时间 08:00
- 也可以在 GitHub 仓库的 `Actions` 页面手动运行 `Daily AI news refresh`

## 重要说明

自动化脚本只抓取官方或可信公开页面。知乎、微博、抖音、微信公众号、小红书等社媒渠道需要人工核验或额外合规 API 接入，当前不会把未经核验的社媒信息写入正式资讯。

如果某些来源抓取失败，网站首页顶部会显示“部分来源抓取失败”，并列出失败渠道和错误原因。失败详情也会写入 `data/latest-news.json` 的 `failures` 字段。
