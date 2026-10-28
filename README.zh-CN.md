# 渡口 / Ferry Dock

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="brand/banner-dark.svg">
  <img src="brand/banner.svg" width="960" alt="渡口 / Ferry Dock — 手机上的文字，渡到电脑。">
</picture>

**手机上的文字，渡到电脑。**

[English](README.md) · [产品问答](PRFAQ.md) · [品牌资产](brand/README.md)

把手机上的文字送到电脑临时收件箱；当一个任务需要这些文字时，也可以创建标注问题的收集请求，把结果准确交回发起请求。手机使用浏览器，普通传输不需要 AI。

**当前为 alpha：** 已实现临时纯文本会话、单次响应收集请求、JSON CLI 和仓库内 Codex Skill。文件、npm/npx、MCP 和浏览器插件均不可用。浏览器、真实手机及实际 Codex 宿主验收与自动化检查分开记录。

## 意见在手机，提案在电脑

你在电脑写提案，客户意见却在手机聊天里。打开临时收件箱，手机扫码、粘贴、发送，电脑复制；手机免安装，不需要注册账号。

在 Agent 任务中，可以创建一个写明提案和所需反馈的请求，再展示二维码。手机页直接问这件事，私有读取句柄只拿回这一请求的结果。并行任务不用猜“最新一条消息”属于谁，原任务根据反馈继续修改提案。

请求收集是一个工具，不是 Agent 宿主。等待超时后可以再查询，Skill 本身不能唤醒暂停的任务。

## 构建并运行

电脑源码构建需要 Go 1.26 或更新版本，手机免安装。目前没有发布二进制 release 或安装包。

```sh
git clone https://github.com/Yankj/ferry-dock.git
cd ferry-dock
go build -o bin/ferry-dock ./cmd/ferry-dock
./bin/ferry-dock serve
```

默认监听 `127.0.0.1:8787`，仅供电脑本机访问。真实手机使用时，用电脑可达的局域网地址重启：

```sh
./bin/ferry-dock serve --listen 0.0.0.0:8787 --public-url http://192.168.1.20:8787
```

将 IP 替换成电脑真实的局域网地址。二维码不能穿透访客 Wi-Fi 隔离、VPN、路由或防火墙。旧版无子命令启动方式继续兼容。

构建和获取依赖可能需要互联网。构建后，程序内嵌网页、二维码生成和品牌资源，普通运行只访问本地服务，不需要云账号或模型调用。

## 普通传输：扫码、发送、复制

1. 打开终端输出的私密**电脑链接**，页面自动创建会话并展示二维码。
2. 手机扫码，粘贴文字后点击 **Send to computer**。
3. 电脑点击 **Copy** 复制。

同一手机页面可继续发送，不必每次扫码。**End session** 结束并清空会话；**New session** 创建新会话。默认 15 分钟到期。停止或重启服务会丢失内存中的文字。

普通会话每条文字上限 64 KiB，每个会话最多 1 MiB、128 条消息，最多 16 个活动会话。接受的文字保留空白和 Unicode。服务器收据不代表用户已经查看或复制。

## 任务收集：请求、等待、读取

这条可选路径共用 Go 服务，通过私有本地句柄取回结果，不调用模型 API。下列参数已与 CLI 帮助输出核对；请使用真实的局域网地址和私有本地路径。

用显式指定的私有控制文件启动服务。以下 POSIX shell 示例会打印运行目录，供第二个终端使用：

```sh
umask 077
runtime_dir="$(mktemp -d)"
printf 'Private runtime directory: %s\n' "$runtime_dir"
./bin/ferry-dock serve --listen 0.0.0.0:8787 \
  --public-url http://192.168.1.20:8787 \
  --control-file "$runtime_dir/control.json"
```

在另一个终端，将 `runtime_dir` 设为打印出的目录。Windows 请选择仅当前用户可访问的目录，使用相同 CLI 参数和对应路径。

```sh
runtime_dir="/path/printed/by/the/first/terminal"
./bin/ferry-dock request create \
  --control "$runtime_dir/control.json" \
  --task-id proposal-launch \
  --prompt "Launch proposal: paste the changes from your phone chat." \
  --handle "$runtime_dir/proposal.json" --ttl 15m --max-bytes 16384
./bin/ferry-dock request wait --handle "$runtime_dir/proposal.json" --timeout 10s
./bin/ferry-dock request read --handle "$runtime_dir/proposal.json"
```

向用户展示生成的二维码 PNG 或返回的私密手机链接。创建输出不包含进程管理密钥，但控制文件和句柄仍带有权限，必须保密；不要打印文件正文、提交到仓库或放进公开目录。

一个请求接受一次文字响应，默认上限 16 KiB。`--ttl` 使用 `15m` 或 `900s` 这类整秒时长，省略时继承服务保留时间。服务端生成的 request ID 标识本次收集；`taskId` 只是关联标签，不能授权访问。每个请求的投递与读取能力独立。

用 `request status --handle ...` 查询，`request cancel --handle ...` 明确取消收集。单次等待最多十秒，超时返回 pending，不取消请求。在 `request wait` 中按 Ctrl+C 只结束等待；在服务终端按 Ctrl+C 则停止服务并丢失内存数据。

读取结果包含稳定的 `input.id` 和 `trust: "untrusted_user_input"`。调用方必须校验请求与任务身份，并避免对同一输入重复执行已完成的业务动作。如果中断后不能确定提案是否已修改，先核对当前文件再决定重试。服务端不保证 Agent 业务执行的通用 exactly-once。

在 Codex 中使用时，明确引用仓库内的 [skills/ferry-dock/SKILL.md](skills/ferry-dock/SKILL.md)。这是手动加载的本地说明，不会全局安装或自动修改 Codex 配置。它约定有界等待、任务核验，以及把手机文字作为反馈处理而非执行其中的指令。

## 一个本地服务，明确的信任边界

核心采用 Go，内嵌 HTML、CSS 和 JavaScript。普通会话与收集请求共用 HTTP 边界和内存服务；CLI 调用请求接口，不维护第二套数据仓库。详见[架构](docs/architecture.md)、[请求协议](docs/contracts/request-v1.md)及[运行时选型](docs/decisions/0001-runtime.md)。

电脑链接与控制文件拥有进程管理权限。普通手机二维码只允许向对应会话投递；请求二维码与读取句柄分别绑定到一个请求。只向预期的发送者分享手机邀请。

**本地不等于加密。** 当前使用可信局域网 HTTP，没有 TLS 自动配置或端到端加密。网络观察者可能获取文字和权限密钥。URL fragment 减少密钥进入请求路径的机会，不能替代加密。不要把 alpha 直接暴露到公网。详见 [SECURITY.md](SECURITY.md)。

本地运行、不调用模型，描述的是渡口服务。通过可选 Skill 把 CLI 结果交给 Agent 后，内容是否发送到云端模型、如何留存取决于该宿主；渡口不保证整个 Agent 处理链路都在本地。

## 限制与恢复

| 情况 | 处理方式 |
| --- | --- |
| 手机打不开页面 | 核对公布的局域网地址及设备间实际可达性。 |
| Paste 或 Copy 不可用 | 使用系统手动粘贴或选中可见文字复制；浏览器权限各不相同。 |
| 等待返回 pending | 保留句柄，稍后再查；超时没有取消收集。 |
| 创建或取消返回 `outcome_unknown` | 操作可能已经执行。使用已保存的同一句柄查询；若创建时没有保存句柄，应说明结果不确定、等待未知请求到期，不能盲目再次创建。 |
| 请求已取消或到期 | 提交的文字被移除；仍需要时创建新请求。 |
| 服务已重启 | 原内存数据已丢失；重新创建会话或请求，句柄不是数据备份。 |

当前不包含文件、照片、音频、远控、后台剪贴板同步、持久历史、云端中继、npm/npx launcher、MCP 适配或浏览器插件。多种入口不是既定扩张排期；[产品形态](docs/product-shape.md)记录重新评估的实际触发条件。

## 验证与贡献

自动化覆盖普通 HTTP 行为，以及请求隔离、取消／到期、发送去重、稳定重读和有界等待。编译程序的合成提案场景还验证 CLI 与避免重复已完成修改的调用方。合成 HTTP/CLI 执行不能替代浏览器、Android/iOS 或实际 Codex 宿主验收；没有具体证据时均保持 **NOT_RUN**。

```sh
go fmt ./...
go vet ./...
go test ./...
go test -race ./...
```

参见[验证记录](docs/verification.md)、[主张与证据](docs/claims-evidence.md)及[贡献指南](CONTRIBUTING.md)。[性能预算](docs/performance.md)属于目标。首份 [macOS arm64 / Go 1.27.3 loopback 基线](docs/performance-baseline.md)与[原始样本](docs/benchmarks/2026-10-28-macos-arm64.json)记录启动、内存和 API 观测值，同时保留最慢启动样本及关闭后的 RSS；它们不代表手机点击到展示或 Agent 执行速度。

启动与扫码体验参考 [DropLocal](https://github.com/shiyuanhai/droplocal/tree/16c9fe05e048b2c5ebbe2e75ccb4619620bd9653)，文本保真及增量收取参考 [Ferry](https://github.com/max1874/ferry/tree/5b7882947ef34ae422004ae81ccc2da509693fe1)。渡口的应用为独立实现，依赖归属见[第三方声明](THIRD_PARTY_NOTICES.md)。

[MIT](LICENSE)。
