# Procedure Library

保存已经跑通、经过独立模型测试的标准流程和脚本，供本地与云端复用。注册入口是 `procedure-register`；每个验收通过的流程可以安装成单独的 Codex 技能。

需要 Python 3.10+ 和已登录的 Codex CLI 0.159.0+。工具本身只依赖 Python 标准库。macOS 优先使用 ChatGPT 桌面应用附带的兼容 CLI；`PROCEDURE_CODEX` 可显式指定可执行文件。模型执行和工具权限由当前环境提供；不绕过沙箱或审批。

本仓库也是一个插件，包含注册入口和所有已验收流程的技能入口。可从 GitHub marketplace 安装：

```bash
codex plugin marketplace add Vico304/procedure-library --ref main
codex plugin add procedure-library@procedure-library
```

安装后在新会话中使用“标准流程库”。注册修改源码副本，已安装插件缓存用于执行。新流程通过验收并推送后，刷新 marketplace 并重新安装更新插件。

```bash
git clone https://github.com/Vico304/procedure-library.git
cd procedure-library
python3 tools/procedure.py --help
python3 tools/procedure.py list
python3 tools/procedure.py models
```

注册与发布规范见 [docs/registration.md](docs/registration.md)。仓库中的 `procedures/` 保存已验收版本；草稿、实际参数、模型输出和原始测试报告放在被忽略的 `.local/` 中。

```bash
python3 tools/procedure.py init example-task --complexity routine
# 按任务补全 .local/drafts/example-task 中的规范、准备器与检查器。
python3 tools/procedure.py validate .local/drafts/example-task
python3 tools/procedure.py test .local/drafts/example-task
# 使用上一步真实输出的报告路径。
python3 tools/procedure.py promote .local/drafts/example-task --report REPORT_JSON
python3 tools/procedure.py install example-task --skills-dir SKILLS_DIRECTORY
```

`SKILLS_DIRECTORY` 是当前宿主加载技能的位置，例如云端仓库的 `.agents/skills`。通用注册技能可从 `skills/procedure-register` 复制到该目录。业务输入每次通过参数文件传入；不把机器路径存入流程定义。

跨项目使用同一个本地流程库时，可设置 `PROCEDURE_LIBRARY`，或在已安装的注册技能目录中创建 `.local/library.json`，用 `library_path` 指向本机副本。这个绑定文件不提交到公开仓库；云端使用自己的副本与绑定。

执行型号只使用以下两种，规则维护在 `tools/model-policy.json`：

| 复杂度 | 选型依据 | 默认执行配置 |
| --- | --- | --- |
| `routine` | 输入与步骤明确，固定操作或少量已知分支 | `gpt-6-luna` / `low` |
| `complex` | 较多分支判断、视觉理解或跨工具处理 | `gpt-6.1-terra` / `medium` |

登记 `complexity` 与一句 `complexity_reason`。`--effort` 可调整推理强度，再按实际配置验收。型号不可用时报告原因，不换成 5.6 或其他型号；变更模型或复杂度后重新验收该版本。旧版验收保留在 Git 历史，不作为新配置的依据。

```bash
python3 tools/procedure.py run procedures/example-task \
  --parameters PARAMETERS_JSON --workspace WORKSPACE_DIRECTORY
```

运行时固定使用验收记录中的模型与推理强度。模型只获得执行包、参数和必要输入，准备器与独立检查器由控制端执行。默认每个测试用例只有一次模型执行，失败就报告，不自动重试或更换模型。`--timeout` 可指定每次执行的时间预算。

正常执行也要通过独立检查器，退出码为零与模型自报成功都不单独作为验收依据。流程包、执行器或测试脚本改变后，既有验收记录会失效，需要重新测试。

在云端克隆后运行同样的命令。模型登录、CLI、外部工具和真实参数由云端环境配置；本地通过不代表外部工具或账号在云端也可用。当前实际验收环境记录在各流程的 `verification.json`。

```bash
python3 -m unittest discover -s tests -v
python3 tools/procedure.py audit
python3 tools/procedure.py build-plugin
```

插件 ZIP 生成到 `dist/`，只包含公开运行材料；不包含 `.local/`、Git 元数据或测试原始日志。插件技能引用统一流程包，避免把脚本和规则重复维护在多个入口中。云端也可独立安装流程技能，无须安装桌面插件。

公开检查拦截常见个人绝对路径、凭据文件和令牌形态；发布时还应核对是否已经将业务绑定参数化。仓库不保存原始会话、个人配置、真实参数文件或原始模型日志。
