# Tapbeam

**手机发过来，电脑接着做。**

[English](README.md)

Tapbeam 是一个轻量本地中转服务：电脑启动，手机扫码，把文字发送到临时收件箱。手机免安装，不需要云账号或 AI 模型。

**当前为早期 alpha。** 首个切片只支持手机向电脑发送纯文本。文件传输、与当前任务关联的 Agent 输入尚未实现；目前没有二进制 release 或 npm 包。

## 立即尝试

源码构建需要 Go 1.26 或更新版本。构建后的程序内嵌网页，不依赖 Node 运行时或数据库。

```sh
git clone https://github.com/Yankj/tapbeam.git
cd tapbeam
go run ./cmd/tapbeam
```

默认监听 `127.0.0.1:8787`，仅供本机访问。手机使用时，显式提供电脑在可信局域网内的可达地址：

```sh
go run ./cmd/tapbeam -listen 0.0.0.0:8787 -public-url http://192.168.1.20:8787
```

将 `192.168.1.20` 替换成电脑的局域网 IP。设备之间需实际可达；访客 Wi-Fi 隔离、VPN 路由或防火墙都可能阻断连接。

1. 打开终端输出的**电脑链接**，页面自动创建会话并展示二维码。
2. 手机扫码，粘贴文字后点击 **Send to computer**。
3. 电脑点击 **Copy** 复制。

电脑链接具有收件箱管理权限，请保密；只向手机分享投递链接或二维码。结束时点击 **End session**，也可以等待默认 15 分钟到期；需要继续时点击 **New session**。数据保存在内存中，进程重启后清空。

构建可执行程序：

```sh
go build -o bin/tapbeam ./cmd/tapbeam
./bin/tapbeam -help
```

## 当前能力

- 临时纯文本会话，电脑管理权限与手机投递权限分离。
- 扫码进入、原文保真、增量收取和复制结果反馈。
- 关闭与到期失效、64 KiB 文本上限、1 MiB 收件箱上限和重复提交去重。
- 网页及二维码由本机服务提供，不调用外部二维码服务、统计或模型。

手机只能向当前会话投递，不能读取收件箱或管理会话。剪贴板能力取决于浏览器与权限；始终保留手动粘贴，不在后台监听剪贴板。

## 后续方向

先把普通传输做好。后续通过可选 CLI/Skill 或 MCP，让 Agent 在缺少手机信息时创建请求、展示二维码，并把结果交回原任务。这些适配层共用同一会话核心。文件和图片、更多输入类型及分发安装包都属于后续范围。

核心采用 Go，内嵌 HTML、CSS 和 JavaScript。[运行时决策](docs/decisions/0001-runtime.md) 公平比较 Node、Go 与 Rust；[性能预算](docs/performance.md) 定义测量方法与目标，不代表已取得的跑分。

## 使用边界

此 alpha 面向可信局域网，使用 HTTP，不能保护流量和能力密钥免受网络监听。不应直接暴露到公网。URL fragment 可减少密钥进入普通请求路径的机会，不能使链接变成可以随意公开的信息。详见[架构及威胁模型](docs/architecture.md)和[安全问题反馈](SECURITY.md)。

## 参与贡献

```sh
go fmt ./...
go vet ./...
go test ./...
go test -race ./...
```

[贡献指南](CONTRIBUTING.md) 说明评审与验证要求；[产品范围](docs/product.md) 记录最短操作链路。自动化检查通过，不代表真实 Android/iOS 扫码和剪贴板体验已验收。

## 参考与许可

启动及扫码体验参考 [DropLocal](https://github.com/shiyuanhai/droplocal/tree/16c9fe05e048b2c5ebbe2e75ccb4619620bd9653)，文本保真及增量收取参考 [Ferry](https://github.com/max1874/ferry/tree/5b7882947ef34ae422004ae81ccc2da509693fe1)。Tapbeam 核心为独立实现，不是两者的 fork。依赖归属及许可见[第三方声明](THIRD_PARTY_NOTICES.md)。

[MIT](LICENSE)。
