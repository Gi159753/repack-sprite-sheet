# repack-sprite-sheet

把透明背景的 sprite sheet / sprite 序列图重新整理成更适合游戏引擎导入的规则网格。

这个仓库既可以作为 Codex skill 使用，也可以直接运行里面的 Python 脚本来处理图片。

## 适合做什么

- 拆分已有 sprite sheet
- 裁掉每帧多余透明边
- 保持动画顺序重新排版
- 统一输出帧画布大小
- 设置输出列数和 padding
- 按底部居中、居中或左上角对齐
- 输出透明 PNG
- 可选输出 JSON metadata，方便配置 Godot、Unity、Phaser 或自定义运行时 atlas

它不是生成新图片的工具，而是整理已有透明 sprite sheet 的后处理工具。

## 文件结构

```text
repack-sprite-sheet/
  SKILL.md
  agents/
    openai.yaml
  references/
    layout-notes.md
  scripts/
    repack_sprite_sheet.py
```

## 安装为 Codex skill

如果你使用 Codex，可以从 GitHub 安装这个 skill：

```bash
python3 /Users/lanjian/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo Gi159753/repack-sprite-sheet \
  --path . \
  --name repack-sprite-sheet
```

安装后重启 Codex，新的 skill 才会被识别。

注意：如果本机已经存在同名目录，例如：

```text
~/.codex/skills/repack-sprite-sheet
```

安装器会拒绝覆盖已有 skill。这是正常保护行为。需要先备份/删除旧目录，或者安装到别的测试目录。

## 直接运行脚本

脚本需要 Python 3 和 Pillow。

如果你在 Codex 环境中，可以优先使用 Codex 自带 Python runtime，因为通常已经带有 Pillow：

```bash
/Users/lanjian/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  scripts/repack_sprite_sheet.py input.png output.png --columns 6 --padding 2 --metadata output.json
```

普通 Python 环境也可以运行：

```bash
python3 scripts/repack_sprite_sheet.py input.png output.png --columns 6 --padding 2 --metadata output.json
```

如果提示缺少 Pillow：

```bash
python3 -m pip install pillow
```

## 常用示例

### 1. 固定网格切帧

原图本来就是规则 sprite sheet，例如每帧 64x64：

```bash
python3 scripts/repack_sprite_sheet.py input.png output.png \
  --detect grid \
  --source-frame-width 64 \
  --source-frame-height 64 \
  --columns 8 \
  --padding 2 \
  --metadata output.json
```

也可以省略 `--detect grid`，只要提供了 `--source-frame-width` 或 `--source-frame-height`，脚本会自动使用 grid 模式。

### 2. 自动识别透明间隔

适合每个 pose 之间有透明 gutter 的序列图：

```bash
python3 scripts/repack_sprite_sheet.py input.png output.png \
  --detect auto \
  --columns 5 \
  --padding 4 \
  --metadata output.json
```

`auto` 会先尝试根据透明行/列分割。如果只检测到一个整体，会退回到 connected components 检测。

### 3. 连通区域检测

适合图标、道具、独立小物件：

```bash
python3 scripts/repack_sprite_sheet.py input.png output.png \
  --detect components \
  --columns 6 \
  --padding 2 \
  --min-component-area 8 \
  --metadata output.json
```

不建议直接用 components 模式处理带武器、粒子、阴影、分离身体部件的角色动画，因为一个动作帧可能会被拆成多个碎片。

### 4. 输出固定帧尺寸

如果游戏引擎要求每帧必须是固定尺寸，例如 64x64：

```bash
python3 scripts/repack_sprite_sheet.py input.png output.png \
  --source-frame-width 64 \
  --source-frame-height 64 \
  --cell-width 64 \
  --cell-height 64 \
  --columns 8 \
  --align bottom-center \
  --metadata output.json
```

如果 `--cell-width` 或 `--cell-height` 小于裁切后的最大帧尺寸，脚本会报错，避免静默裁掉图像。

## 参数说明

```text
input                         输入图片路径
output                        输出 PNG 路径
--detect auto|grid|components 检测模式，默认 auto
--source-frame-width N        原始固定网格的单帧宽度
--source-frame-height N       原始固定网格的单帧高度
--source-columns N            原始网格列数，可选
--source-rows N               原始网格行数，可选
--columns N                   输出列数
--cell-width N                输出单帧格子宽度
--cell-height N               输出单帧格子高度
--padding N                   每帧周围透明 padding，默认 2
--align bottom-center|center|top-left
                              帧在输出格子内的对齐方式，默认 bottom-center
--alpha-threshold N           alpha 阈值，默认 0
--min-component-area N        components 模式最小区域面积，默认 4
--keep-empty                  grid 模式下保留完全透明的空帧
--metadata path.json          输出 JSON metadata
```

## 检测模式怎么选

优先级建议：

1. 原图是规则 sprite sheet：使用 grid 模式。
2. 原图每帧之间有透明间隔：先试 auto 模式。
3. 原图是很多分散的小图标/物件：可以用 components 模式。

如果你知道原始帧宽高，优先使用 `--source-frame-width` 和 `--source-frame-height`。这通常比自动检测更稳定，尤其是角色动画。

## 对齐方式怎么选

```text
bottom-center  角色、敌人、拾取物、站在地面上的对象
center         子弹、爆炸、特效、图标
top-left       需要保留左上角定位习惯的 UI 或特殊 atlas
```

角色动画一般建议用 `bottom-center`，这样脚底或接触点更稳定，导入引擎后不容易抖动。

## metadata 内容

使用 `--metadata output.json` 后，会输出类似这些信息：

- frame_count
- columns / rows
- cell_width / cell_height
- padding
- alignment
- 每帧的原始裁切区域
- 每帧在输出图中的 cell 区域
- 每帧可见 sprite 在输出图中的区域

这些信息可以辅助配置：

- Godot `SpriteFrames`
- Godot `AnimatedSprite2D`
- Godot `AtlasTexture`
- Unity Sprite Editor slicing
- Phaser atlas / spritesheet
- 自定义运行时 atlas

## 注意事项

- 只处理透明背景图片，输入会被转换为 RGBA。
- 默认会跳过完全透明的空帧；如果需要保留空帧用于动画 timing，请使用 `--keep-empty`。
- 默认会裁掉每帧周围多余透明边，再放进统一大小的输出 cell。
- 默认输出 cell 尺寸是最大裁切帧尺寸加上 padding。
- `components` 模式可能会把一个角色帧拆成多个部分，例如武器、影子、粒子、分离的头发或手臂。
- 如果动画帧有固定节奏要求，最好使用 grid 模式并保留正确的源帧顺序。
- 输出顺序默认按从左到右、从上到下保留。
- 如果目标引擎要求固定帧尺寸，请显式设置 `--cell-width` 和 `--cell-height`。
- 如果自动检测结果不符合预期，先改用 grid 模式，不要继续调大量自动检测参数。

## 输出验证建议

处理完成后建议检查：

- 输出 PNG 尺寸是否符合预期
- frame_count 是否正确
- cell_width / cell_height 是否适合引擎导入
- 动画顺序是否仍然正确
- 角色脚底、中心点或特效中心是否稳定
- 是否误删了空帧
- 是否有某一帧被裁掉

脚本运行成功时会打印类似：

```text
wrote output.png (448x128), 16 frames, 8 columns, cell 56x64
```

## License

如果你准备公开给别人使用，建议在仓库中补充一个明确的 LICENSE 文件。
