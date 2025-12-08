# Scripts 目录

这个目录存放了一些辅助脚本，它们不是核心功能的一部分，但可能在特定场景下有用：

## 演示脚本

- `improved_contact_processor.py` - 展示如何改进现有Excel文件的联系人数据
- `local_demo.py` - 本地联系人提取功能演示
- `test_design_leads.py` - 设计业务商机处理器测试（非pytest）
- `test_filter.py` - 智能公告过滤器测试（非pytest）

## 分析工具

- `analyze_ccgp.py` - 政府采购网页面结构分析工具（早期开发时的调试工具）

## 注意事项

这些脚本：
- 不会被主程序调用
- 不是正式的单元测试
- 可能需要手动修改路径或参数才能运行
- 仅供学习和参考使用

建议通过 `python main.py` 来使用系统的正式功能。