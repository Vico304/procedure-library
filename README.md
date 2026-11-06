# Procedure Library

保存已经跑通、经过独立模型测试的标准流程和脚本，供本地与云端复用。注册入口是 `procedure-register`；每个验收通过的流程可以安装成单独的 Codex 技能。

需要 Python 3.10+ 和已登录的 Codex CLI。工具本身只依赖 Python 标准库。模型执行和工具权限由当前 Codex 环境提供；不绕过沙箱或审批。

```bash
git clone https://github.com/Vico304/procedure-library.git
cd procedure-library
python3 tools/procedure.py --help
python3 tools/procedure.py list
python3 tools/procedure.py models
```

注册与发布规范见 [docs/registration.md](docs/registration.md)。仓库中的 `procedures/` 保存已验收版本；草稿、实际参数、模型输出和原始测试报告放在被忽略的 `.local/` 中。

```bash
python3 tools/procedure.py init example-task --model MODEL_NAME --effort low
# 按任务补全 .local/drafts/example-task 中的规范、准备器与检查器。
python3 tools/procedure.py validate .local/drafts/example-task
python3 tools/procedure.py test .local/drafts/example-task
# 使用上一步真实输出的报告路径。
python3 tools/procedure.py promote .local/drafts/example-task --report REPORT_JSON
python3 tools/procedure.py install example-task --skills-dir SKILLS_DIRECTORY
```

`SKILLS_DIRECTORY` 是当前宿主加载技能的位置，例如云端仓库的 `.agents/skills`。通用注册技能可从 `skills/procedure-register` 复制到该目录。业务输入每次通过参数文件传入；不把机器路径存入流程定义。

跨项目使用同一个本地流程库时，可设置 `PROCEDURE_LIBRARY`，或在已安装的注册技能目录中创建 `.local/library.json`，用 `library_path` 指向本机副本。这个绑定文件不提交到公开仓库；云端使用自己的副本与绑定。

`MODEL_NAME` 从目标执行环境的 `models` 输出中选择，并选择其支持的推理强度。桌面应用和独立 CLI 的可用型号可能不同；型号不可用时保留失败记录，由注册者调整明确配置后重新测试，不自动替换。

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
```

公开检查拦截常见个人绝对路径、凭据文件和令牌形态；发布时还应核对是否已经将业务绑定参数化。仓库不保存原始会话、个人配置、真实参数文件或原始模型日志。
