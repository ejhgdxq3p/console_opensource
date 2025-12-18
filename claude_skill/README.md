# MRI4ALL Console - Claude Skill

本文档是从MRI4ALL开源项目反推出的Claude Skill，用于指导基于此代码库的二次开发。

## 📁 文件结构

```
claude_skill/
├── README.md                    # 本文件 - 总览
├── architecture.md              # 系统架构设计
├── coding_standards.md          # 代码规范与风格
├── design_patterns.md           # 设计模式详解
├── module_guide.md              # 模块开发指南
├── sequence_development.md      # 序列开发指南
├── ui_development.md            # UI开发指南
├── service_development.md       # 服务开发指南
└── best_practices.md            # 最佳实践与常见陷阱
```

## 🎯 快速索引

| 我想... | 查看文档 |
|---------|----------|
| 了解整体架构 | [architecture.md](architecture.md) |
| 编写符合规范的代码 | [coding_standards.md](coding_standards.md) |
| 添加新的MRI序列 | [sequence_development.md](sequence_development.md) |
| 开发UI界面 | [ui_development.md](ui_development.md) |
| 创建新服务 | [service_development.md](service_development.md) |
| 理解设计模式 | [design_patterns.md](design_patterns.md) |

## 🔑 核心原则

1. **微服务架构** - UI、采集(ACQ)、重建(RECON)三个独立服务
2. **基于文件夹的队列** - 服务间通过文件系统进行任务传递
3. **插件式序列系统** - 序列自动注册，支持热插拔
4. **类型安全** - 使用Pydantic进行数据验证
5. **跨平台兼容** - 支持Linux(生产)和Windows(开发)

