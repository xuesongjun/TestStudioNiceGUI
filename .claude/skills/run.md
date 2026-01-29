---
name: run
description: |
  启动 Test Studio 应用
---

# 启动 Test Studio

## 操作步骤

1. 激活虚拟环境
2. 运行 `python src/main.py`
3. 应用启动后可通过浏览器访问 http://localhost:8081

## 命令

```bash
cd c:\workspace\test_studio
.\venv\Scripts\activate && python src/main.py
```

## 注意事项

- 确保虚拟环境 `venv` 已安装所有依赖
- 默认端口为 8081，如端口被占用需修改 `src/main.py` 中的 `ui.run(port=8081)`
- 应用基于 NiceGUI 框架，启动后自动打开浏览器
