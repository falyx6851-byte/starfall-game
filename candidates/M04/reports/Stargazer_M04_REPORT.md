# Stargazer M04 外观精修候选

## 范围
- 基于 **M03 已通过的披肩结构基线** 继续精修，不回退到 H01 / M02 重做整块披肩。
- 仅修改 **mesh 08 Asymmetric shoulder mantle**，其余头盔、胸甲、肩甲、身体、武器、背后长披风、骨架、原动画与场景保持不变。
- 只使用原有贴图与材质体系；未增加布料物理系统，未修改全局共用材质参数。

## 本轮实际改动
1. 保留 M03 的肩甲包覆范围、肩部支撑关系与胸前扣点连接。
2. 对靠近脖子与扣点之间偏高的跨接区域做了局部压低与顺滑整理。
3. 在 **M03 布面之上** 增加了 3 组方向明确的大褶皱（扣点下落、肩部转折、后侧下垂）与 1 组较浅的过渡脊线。
4. 恢复深青色布面，并沿真实下摆自由边缘增加了 **克制的窄金边**；金边单独成局部几何，未把胸前边线扩成三角金属片。

## 结构保护复查
DesignPose / 0 秒 / Y=1.90 截面复查：
- 肩甲最外缘 X = **-0.51493**
- M03 披布最外缘 X = **-0.53219**
- M04 披布最外缘 X = **-0.59050**

该侧 X 越负越靠外。M04 仍位于肩甲外侧，且没有比 M03 更缩回内侧。

## 动作抽查
已复查：
- DesignPose
- Idle
- Run
- Attack1：0.13 / 0.16 / 0.32 秒

当前结论：
- 包覆关系在本轮外观精修后 **没有退化到肩甲内侧**。
- 仍然保留既有待办：**抬臂时整片上翻，动态偏硬**。本轮没有把上色或加褶皱当作“自然动作已解决”。

## 交付文件
- `Stargazer_M04.glb`
- `Stargazer_M04_PREVIEW.html`
- `Stargazer_M04_M03_COMPARE.jpg`
- `Stargazer_M04_VIEWS.jpg`
- `Stargazer_M04_POSES.jpg`
- `Stargazer_M04_MANTLE_SOURCE.py`
- `Stargazer_M04_Sample.zip`

## 校验摘要
- PASS · All non-mantle meshes byte-identical to M03 baseline
- PASS · Nodes/hierarchy unchanged
- PASS · Animations unchanged
- PASS · Materials unchanged
- PASS · Texture image bytes unchanged
- PASS · Mantle uses 2 local primitives: gold trim + cloth · [1, 2]
- PASS · Coverage at Y=1.90 remains outside the shoulder · {"shoulderMinX": -0.5149328489066818, "M03MinX": -0.5321883136501618, "M04MinX": -0.590504304069516, "M03Outside": -0.017255464743480053, "M04Outside": -0.07557145516283426}
- PASS · M04 did not reduce M03 coverage at Y=1.90 · {"shoulderMinX": -0.5149328489066818, "M03MinX": -0.5321883136501618, "M04MinX": -0.590504304069516, "M03Outside": -0.017255464743480053, "M04Outside": -0.07557145516283426}
- PASS · Preview and delivered GLB exist · {"previewBytes": 12081358, "glbBytes": 8408324}

> 本轮停在披肩外观验收，不自动推进到其他身体部件或正式游戏整合。
