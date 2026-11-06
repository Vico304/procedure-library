---
name: procedure-directory-copy-verify
description: "复制目录并核对文件与目录结构一致性 适用于：将目录复制到指定新位置并验证完整性；重复复制已相同的目录；复制前检查目标冲突"
metadata:
  version: "0.2.0"
---

# 复制目录并核对文件与目录结构一致性

读取 [输入契约](../../procedures/directory-copy-verify/procedure.json) 和 [流程说明](../../procedures/directory-copy-verify/procedure.md)，确认本次任务适用并取得所需参数。真实路径等绑定写入本地临时 JSON，不修改已验收流程。

运行入口使用登记的模型和推理强度启动独立执行器，并检查真实产物：

```text
python3 <插件根>/tools/procedure.py run <插件根>/procedures/directory-copy-verify --parameters <参数文件> --workspace <本次工作目录>
```

插件根是本 SKILL.md 所在目录的上两级目录。额外写入目录仅在当前授权覆盖时通过 `--write-root <目录>` 显式传入。收到失败、缺少输入或前提不满足时报告停点与运行记录，不静默换模型、扩大范围或自行修订流程。当前主模型负责必要判断，业务步骤由该入口执行。
