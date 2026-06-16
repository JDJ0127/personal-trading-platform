# 腾讯云 CloudBase 静态托管部署

1.0 版本推荐只部署前端静态看板，后端继续在本地或后续服务器生成 JSON 报告。这样可以先验证平台稳定性和策略可靠性，避免过早引入在线后端运维。

## 准备

1. 注册并登录腾讯云账号。
2. 开通 CloudBase，并创建一个环境。
3. 在 CloudBase 控制台复制环境 ID，后续命令记为 `CLOUDBASE_ENV_ID`。
4. 如果绑定中国大陆节点和自定义域名，按腾讯云要求完成 ICP 备案。

## 首次部署

```bash
CLOUDBASE_ENV_ID=<your-env-id> npm run deploy:cloudbase
```

脚本会执行：

1. `npm run build`
2. `tcb hosting deploy dist -e <your-env-id>`

如果 CLI 要求登录，按终端提示完成腾讯云授权后重新执行部署命令。

## 数据更新流程

当前 1.0 的数据文件位于 `src/data/`。后端任务更新 JSON 后，重新执行：

```bash
npm run build
CLOUDBASE_ENV_ID=<your-env-id> npm run deploy:cloudbase
```

后续如果要自动每日更新，可以再把 BaoStock 同步、模拟盘任务、JSON 导出迁移到 CloudBase 云函数/定时触发器，或迁移到一台轻量服务器。

## 上线检查

- 首页能打开。
- 左侧导航能切换各模块。
- 数据中心显示行情覆盖率。
- 回放验证能看到回放日期、权益曲线和账户指标。
- 浏览器控制台无明显资源 404 或 JavaScript 错误。
