# Visual Quality Checklist: Portal Redesign

**Purpose**: 确保首页重构符合 Frontiers/MDPI 的商业级视觉标准。
**Reference**: specs/003-portal-redesign/spec.md

## 视觉一致性 (Visual Identity)
- [ ] CHK001 **字体**: 标题 (Headings) 是否使用了衬线体 (Serif)？导航和正文是否使用了无衬线体 (Sans)？
- [ ] CHK002 **配色**: 顶栏是否为深蓝/黑 (`slate-900`)？CTA 按钮是否为醒目的品牌蓝？
- [ ] CHK003 **间距**: 板块之间是否留有足够的呼吸感 (`py-16` 或 `py-20`)？避免紧凑布局。

## 交互体验 (UX)
- [ ] CHK004 **导航**: 鼠标悬停在 "Journals" 上时，Mega Menu 是否能平滑展开？
- [ ] CHK005 **搜索**: 在搜索框输入关键词并回车，是否能正确跳转到 `/search` 页？
- [ ] CHK006 **响应式**: 在手机模式下，导航栏是否正确折叠为汉堡菜单？
- [ ] CHK007 **轮播**: 期刊轮播图是否支持手势滑动 (Touch Swipe)？

## 内容完整性
- [ ] CHK008 **统计**: 是否展示了 Impact Factor 或 Citation 等增强信任感的数字？
- [ ] CHK009 **入口**: 是否包含明显的 "Submit" 和 "Login" 入口？
