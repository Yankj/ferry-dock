# 渡口 / Ferry Dock

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="brand/banner-dark.svg">
  <img src="brand/banner.svg" width="960" alt="渡口 / Ferry Dock — 手机上的文字，渡到电脑。">
</picture>

**手机上的文字，渡到电脑。**

[English](README.md) · [产品问答](PRFAQ.md) · [分发说明](docs/distribution.md) · [品牌资产](brand/README.md)

把手机文字送到电脑临时收件箱，或准确交回发起收集的任务。打开电脑页面，手机扫码、粘贴、发送。普通传输不需要 AI，也不用安装手机 App。

**当前预览：正在准备 `0.1.0-alpha.2`。** 黑白灰界面以透明层次组织内容，传输和请求接口保持不变。实际 Safari 浅色桌面收发及 **Copied** 标签已通过；深色／手机尺寸 GUI 检查因认证交互边界受阻，新版尚未重做系统粘贴检查，正式产物验收仍待完成。默认使用预构建应用或 CLI，无需安装 Git、Go 或 Node。**目前没有发布 GitHub Release 或原生包的公开下载链接**；[验证记录](docs/verification.md)与[分发说明](docs/distribution.md)区分当前结果和历史 alpha.1 快照。源码构建只面向开发者。

## 意见在手机，提案在电脑

你在电脑写提案，客户意见却在手机聊天里。把它发送到电脑，再复制进正在做的工作。

在 Agent 任务中，创建一个标注提案和所需反馈的请求。手机页面直接问这件事，私有读取句柄只拿回该请求的结果。并行任务不用猜“最新一条消息”属于谁。

请求收集是一个工具，不是 Agent 宿主。等待超时后可再查，Skill 本身不能唤醒暂停的任务。

## 打开本地预览

这份 `.app` 就是渡口本身，不是需要额外安装的桌面平台。**首次：ZIP 解压 → 打开 `Ferry Dock.app` → 扫码；以后：打开应用 → 扫码。** 它运行与 CLI 相同的 Go 核心，在系统浏览器打开界面；没有安装向导、注册、登录启动项，也不用另装 Go／Node、获取源码或修改全局 PATH。

1. 电脑页面自动创建临时会话并展示二维码。
2. 手机扫码，粘贴文字后点击 **Send to computer**。
3. 电脑点击 **Copy** 复制。

桌面模式的默认局域网路径在所有 IPv4 网卡的空闲端口监听，并把选定的私有 IPv4 用于手机链接。无法明确选择局域网地址时，会退回 loopback 监听并显示 **Local only**，真实手机不能访问该地址。二维码不能穿透访客 Wi-Fi 隔离、VPN、路由或防火墙。

关闭浏览器标签不会结束 Go 服务。再次打开应用会回到经过验证的同一实例；在电脑本地页面点击 **Quit Ferry Dock** 才会退出，并清空**全部**内存会话和请求。私有缓存目录或 `startup.log` 可能保留。共享服务时，一个任务结束只应取消自己的请求。

本地应用包不等于已签名／公证的公开发行版，也不代表下载后的 Gatekeeper 首启已通过。[分发说明](docs/distribution.md)区分生成产物、本机检查、首启验收与公开发布，本预览不提供关闭安全机制的绕过流程。

## 偏好 CLI？

解压匹配系统与架构的原生 CLI 包，在包的根目录用 macOS/Linux POSIX shell 运行：

```sh
./ferry-dock version
./ferry-dock desktop
```

Windows 在 PowerShell 中使用 `.\ferry-dock.exe`。生成或交叉编译出安装包，不代表每个平台都完成本机运行验收。CLI 无子命令时默认前台 `serve`；需要浏览器启动器和后台生命周期时，明确使用 `desktop`。

CLI 和应用内的可执行文件都支持 JSON `version` 及 `request` 命令。版本输出含 `version`、`commit`、`os`、`arch`、`defaultMode`。包内布局与高级 `serve --listen ... --public-url ...` 用法见[分发说明](docs/distribution.md)。

## 普通传输保持简单

同一手机页面可以继续发送，不必每次扫码。**End session** 清空当前会话，**New session** 创建新会话，默认 15 分钟到期。关闭浏览器、结束会话和退出整个服务是不同操作。

普通会话每条文字上限 64 KiB，每个会话最多 1 MiB、128 条消息，最多 16 个活动会话。接受的文字保留空白和 Unicode。收据表示服务接收成功，不代表用户已经查看或复制。

## 任务收集：请求、等待、读取

复用已运行的桌面实例与私有控制文件。macOS 默认路径为 `~/Library/Caches/ferry-dock/runtime/control.json`，`desktop` 也会返回 `controlPath`。不要打印文件正文，它包含进程管理权限。

将 `ferry_bin` 设置为预构建可执行文件的**绝对路径**。应用内路径为 `Ferry Dock.app/Contents/MacOS/ferry-dock`，CLI 包则使用解压出的 `ferry-dock`。下列 POSIX 示例假定桌面实例已就绪，并为当前任务创建新的私有目录：

```sh
ferry_bin="/absolute/path/to/ferry-dock"
control_path="$HOME/Library/Caches/ferry-dock/runtime/control.json"
umask 077
runtime_dir="$(mktemp -d)"
"$ferry_bin" version
"$ferry_bin" request create \
  --control "$control_path" \
  --task-id proposal-launch \
  --prompt "Launch proposal: paste the changes from your phone chat." \
  --handle "$runtime_dir/proposal.json" --ttl 15m --max-bytes 16384
```

请使用真实的程序和控制文件路径，包括自定义桌面 `--state-dir`。每次请求的句柄和默认 PNG 路径都必须尚不存在。Windows 需要当前用户私有目录、Windows 路径及 PowerShell 语法；这里展示的是 POSIX 示例。

在发起请求的会话中展示返回的二维码 PNG 或私密手机链接。创建输出不含进程管理密钥或读取密钥，但句柄仍有当前请求的权限，必须保密。

手机提交后，通过同一句柄等待并读取。尚未提交时，正常返回 pending／无输入：

```sh
"$ferry_bin" request wait --handle "$runtime_dir/proposal.json" --timeout 10s
"$ferry_bin" request read --handle "$runtime_dir/proposal.json"
```

一个请求接受一次响应，默认最多 16 KiB。`--ttl` 接受 `15m`、`900s` 这类整秒时长，省略时继承服务保留时间。服务端生成 `requestId`；`taskId` 只是关联标签，不能授予权限。每个请求的读取与投递能力独立。

用 `request status --handle ...` 查询，`request cancel --handle ...` 结束收集。单次等待最多十秒，超时返回 pending、不取消请求；在 `request wait` 中按 Ctrl+C 也只结束等待。该保证不适用于创建／取消等操作中断；`outcome_unknown` 需要核对结果，不能盲目重试。

读取包含稳定的 `input.id` 和 `trust: "untrusted_user_input"`。调用方必须校验请求／任务身份，跳过同一输入已经完成的业务动作；中断后无法确定修改结果时，先核对当前文件。不承诺 Agent 业务执行的通用 exactly-once。

原生包及应用的 `Contents/Resources/skills/` 均附带可选[本地 Skill](skills/ferry-dock/SKILL.md)。手动引用即可，不会全局安装、修改 Agent 配置、要求源码仓库或执行手机文字中的命令。

## 一个 Go 核心，明确的信任边界

应用启动器、CLI、网页与请求适配共用同一 Go 核心。应用是打包及默认启动方式的选择，不是另一套 Swift／Node 后端。详见[架构](docs/architecture.md)、[请求协议](docs/contracts/request-v1.md)与[运行时决策](docs/decisions/0001-runtime.md)。

**本地不等于加密。** 桌面模式可能在选定的可信局域网上监听手机流量；前台 `serve` 未配置时默认 loopback。当前没有 TLS 自动配置或端到端加密，网络观察者可能获取内容与权限密钥。电脑链接、控制文件、读取句柄和手机邀请都应保密，不要直接暴露到公网。

本地运行／不调用模型，描述的是渡口服务。通过可选 Skill 把 CLI 结果交给 Agent 后，云模型传输与留存取决于该宿主。普通非 AI 传输仍不需要 AI 账号。

## 限制与恢复

| 情况 | 处理方式 |
| --- | --- |
| 显示 Local only | 手机无法访问 loopback；高级配置需使用已确认的局域网地址，不要关闭网络保护。 |
| 浏览器标签已关闭 | 重新打开应用；服务一直运行到 **Quit Ferry Dock** 或进程退出。 |
| 服务已就绪，但浏览器打开失败 | 重试打开，或使用已知的私有控制路径；浏览器报错不会撤销服务启动。 |
| Paste 或 Copy 不可用 | 使用系统手动粘贴或选中可见文字复制；浏览器权限各不相同。 |
| 等待返回 pending | 保留句柄再查询；超时没有取消收集。 |
| 创建／取消返回 `outcome_unknown` | 使用已保存句柄核对。若创建时未保存句柄，应说明不确定、等待未知请求到期，不能盲目再次创建。 |
| 桌面启动报告未知服务 | 尚未验证其身份，不应杀进程或覆盖共享状态来强行启动。 |
| 服务已退出／重启 | 原内存数据已丢失；句柄不是备份。 |

当前不含文件、照片、音频、远控、连续剪贴板同步、持久历史、云中继、npm/npx、MCP 或浏览器插件。[产品形态](docs/product-shape.md)记录窄范围决策。

## 验证与贡献

历史 alpha.1 修订在实际 Safari 27.0.1 的 loopback 检查中，通过普通收发、系统真实复制粘贴、任务提交与读取、390×844 布局样本、UI Quit，以及新二进制同标签页 A→B 切换不串投。其八个归档通过结构／哈希检查，两次完整构建的十个输出文件逐字节一致；Mac arm64 应用包通过 `--no-open`、私有状态目录下的默认参数分派、生命周期、CLI、安全与清理检查，这不等于 Finder 零参数首启。上述结果不代表 alpha.2 视觉修订已验收。收据见[分发说明](docs/distribution.md)、[验证记录](docs/verification.md)及[主张／证据](docs/claims-evidence.md)。Finder／默认缓存发现、默认浏览器自动打开、手机局域网／扫码、Gatekeeper、实际 Codex 宿主及 Windows/Linux 本机验收仍为 **NOT_RUN**。

[此前 macOS arm64／Go 1.27.3 loopback 基线](docs/performance-baseline.md)与[原始样本](docs/benchmarks/2026-10-28-macos-arm64.json)测的是特定旧 CLI／核心二进制，不代表应用启动、浏览器打开、手机操作或 Agent 速度。[预算](docs/performance.md)仍是工程目标。

<details>
<summary>开发者：从源码构建</summary>

Git 和 Go 1.26+ 是开发前提，不是预览用户的运行依赖。请使用与预览 manifest 匹配的源码版本；本地预览可能领先于公开 `main`。构建／下载依赖可能需要互联网。在该源码目录下使用 macOS/Linux POSIX shell：

```sh
go build -o bin/ferry-dock ./cmd/ferry-dock
./bin/ferry-dock version
./bin/ferry-dock desktop
```

Windows 开发者应构建 `bin/ferry-dock.exe` 并调用 `.\bin\ferry-dock.exe`。源码构建默认显示开发元数据，除非构建参数提供了发行身份；打包脚本会明确记录 dirty 源码状态。

```sh
go fmt ./...
go vet ./...
go test ./...
go test -race ./...
```

详见[贡献指南](CONTRIBUTING.md)与[打包说明](docs/distribution.md)。

</details>

启动／扫码设计参考 [DropLocal](https://github.com/shiyuanhai/droplocal/tree/16c9fe05e048b2c5ebbe2e75ccb4619620bd9653)，原文保真／增量收取参考 [Ferry](https://github.com/max1874/ferry/tree/5b7882947ef34ae422004ae81ccc2da509693fe1)。应用为独立实现，[第三方声明](THIRD_PARTY_NOTICES.md)保留依赖归属。

[MIT](LICENSE)。
