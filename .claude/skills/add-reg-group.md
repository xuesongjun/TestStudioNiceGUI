---
name: add-reg-group
description: |
  在 YAML 配置中添加新的寄存器分组
---

# 添加寄存器分组

## 配置文件位置

`src/config/register_maps/default_regs.yaml`

## 格式

```yaml
register_groups:
  - name: GROUP_NAME           # 分组名称（英文大写）
    description: "分组描述"     # 中文描述
    base_address: 0xXXXXXXXX   # 基地址（十六进制）
    range:
      start: 0x00              # 起始偏移
      end: 0xXX                # 结束偏移
      step: 4                  # 步长（通常为4，32位寄存器）
    exclude_offsets: []         # 排除的偏移地址列表（校准寄存器）
```

## 示例

```yaml
  - name: NEW_REG_GROUP
    description: "新寄存器组描述"
    base_address: 0x20200000
    range:
      start: 0x00
      end: 0x3c
      step: 4
    exclude_offsets: [0x10, 0x14]  # 排除偏移 0x10 和 0x14 的寄存器
```

## 注意事项

- `exclude_offsets` 用于标记校准寄存器，不同设备值不同是正常的，对比时会跳过
- 地址使用十六进制格式
- `step` 通常为 4（32位寄存器按4字节对齐）
- 实际寄存器地址 = base_address + offset
