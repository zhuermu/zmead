# 视频生成工具增强功能指南

## 概述

`generate_video_tool` 现已支持 Veo 3.1 的所有高级功能，包括图片转视频、插值、参考图片引导等。

## 支持的生成模式

### 1. 文本转视频（Text-to-Video）

最基础的模式，仅使用文本提示生成视频。

**使用场景：**
- 从零开始创建视频
- 描述性场景生成

**参数：**
```python
{
    "prompt": "A cute kitten playing with yarn",  # 或使用 product_info + style
    "style": "lifestyle",
    "duration": 4,
    "aspect_ratio": "16:9"
}
```

**AI 识别关键词：**
- "生成一个视频..."
- "创建视频展示..."

---

### 2. 图片转视频（Image-to-Video）

将静态图片转换为动态视频，为图片添加动画效果。

**使用场景：**
- 为广告素材添加动态效果
- 将产品图片转换为视频广告
- 动画化用户上传的图片

**方式 A：使用对话历史中的图片**
```python
{
    "use_context_image": True,  # 自动使用最近的图片
    "context_image_index": 0,   # 0=最新，1=倒数第二张
    "prompt": "Add smooth camera movement and zoom effects",
    "style": "dynamic",
    "duration": 4
}
```

**方式 B：直接提供图片**
```python
{
    "first_frame_b64": "base64_encoded_image_data",
    "prompt": "Animate this product image with professional camera movement",
    "style": "professional",
    "duration": 4
}
```

**AI 识别关键词：**
- "把这张图片做成视频"
- "给这个图片加动画"
- "animate this image"
- "make a video from that"
- "用刚才的图片生成视频"

**工具会自动：**
- 从对话历史中查找最近的图片（generated_images 或 attachments）
- 支持用户上传的图片和 AI 生成的图片
- 如果找不到图片，会提示用户

---

### 3. 插值（Interpolation）

指定视频的第一帧和最后一帧，Veo 自动生成平滑过渡。

**使用场景：**
- 精确控制视频的开始和结束画面
- 创建特定的动作序列
- 产品展示的特定角度转换

**参数：**
```python
{
    "first_frame_b64": "base64_start_image",
    "last_frame_b64": "base64_end_image",
    "prompt": "Smooth transition with dynamic camera movement",
    "duration": 8,  # 插值模式必须是 8 秒
    "aspect_ratio": "16:9"
}
```

**AI 识别关键词：**
- "从第一张图片过渡到第二张"
- "创建从...到...的视频"
- "interpolate between these images"

**限制：**
- 必须使用 8 秒时长
- 支持 16:9 和 9:16 宽高比

---

### 4. 参考图片引导（Reference-Guided）

使用最多 3 张参考图片来指导视频内容，保持主体外观一致。

**使用场景：**
- 保持品牌一致性（使用品牌素材作为参考）
- 保持角色外观（使用角色图片作为参考）
- 产品视频（使用产品图片作为参考）

**参数：**
```python
{
    "reference_images_b64": [
        "base64_image_1",  # 例如：产品图片
        "base64_image_2",  # 例如：模特图片
        "base64_image_3",  # 例如：配饰图片
    ],
    "prompt": "A fashion model wearing the dress and accessories from the reference images, walking on a runway",
    "style": "professional",
    "duration": 8,  # 参考图片模式必须是 8 秒
    "aspect_ratio": "16:9"  # 仅支持 16:9
}
```

**AI 识别关键词：**
- "使用这些图片作为参考"
- "保持这个产品的外观"
- "用这些素材生成视频"

**限制：**
- 最多 3 张参考图片
- 必须使用 8 秒时长
- 仅支持 16:9 宽高比

---

## 对话历史图片提取

工具会自动从对话历史中提取图片，支持：

1. **AI 生成的图片**：`generated_images` 字段
2. **用户上传的图片**：`attachments` 字段
3. **Data URL 格式**：从消息内容中提取 `data:image/...;base64,...`

**提取逻辑：**
- 从最新消息向前搜索
- 按时间倒序返回图片列表
- `context_image_index=0` 表示最新的图片

---

## 智能提示构建

工具会根据输入模式自动构建合适的提示：

### 文本转视频提示
```
Create a professional advertising video for {product_name}.
Product: {description}
Style: {style_description}
Requirements:
- High-quality, professional video production
- Clear product showcase
- Engaging and attention-grabbing
- Suitable for social media advertising
- No text overlays
```

### 图片动画提示
```
Animate this image with {style_description}.
Requirements:
- Maintain the original image quality and composition
- Add natural, realistic motion
- Create smooth, professional animation
- Suitable for advertising use
- No text overlays or watermarks
```

---

## 使用示例

### 示例 1：用户上传图片后生成视频

**用户：** "帮我把这张产品图做成视频"

**AI 应该调用：**
```python
generate_video_tool({
    "use_context_image": True,
    "prompt": "Professional product showcase with smooth camera movement",
    "style": "professional",
    "duration": 4,
    "aspect_ratio": "16:9"
})
```

### 示例 2：使用之前生成的图片

**用户：** "用刚才生成的第二张图片做个视频"

**AI 应该调用：**
```python
generate_video_tool({
    "use_context_image": True,
    "context_image_index": 1,  # 第二张图片
    "prompt": "Add dynamic motion and energy to this image",
    "style": "energetic",
    "duration": 4
})
```

### 示例 3：参考图片引导

**用户：** "用这三张图片作为参考，生成一个时尚走秀视频"

**AI 应该调用：**
```python
generate_video_tool({
    "use_context_image": False,
    "reference_images_b64": [image1_b64, image2_b64, image3_b64],
    "prompt": "A fashion model walking on a runway wearing the dress and accessories from the reference images, professional lighting, cinematic",
    "style": "professional",
    "duration": 8,
    "aspect_ratio": "16:9"
})
```

---

## 技术实现细节

### 对话历史传递

`react_agent.py` 现在会将对话历史传递给工具：

```python
conversation_history = self._messages_to_history(state.messages)

tool_result = await self._execute_tool(
    tool_name=plan.action,
    parameters=plan.action_input or {},
    available_tools=loaded_tools,
    user_id=state.user_id,
    conversation_history=conversation_history,  # 新增
)
```

### 图片提取逻辑

```python
def _extract_image_from_context(
    self,
    context: dict[str, Any] | None,
    index: int = 0,
) -> str | None:
    """从对话历史中提取图片。
    
    搜索顺序：
    1. generated_images（AI 生成的图片）
    2. attachments（用户上传的图片）
    3. content 中的 data URL
    
    返回第 index 个图片的 base64 数据。
    """
```

---

## 参数参考

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `product_info` | object | 否 | - | 产品信息（name, description, features） |
| `prompt` | string | 否 | - | 直接文本提示（优先级高于 product_info） |
| `style` | string | 否 | "dynamic" | 视频风格：dynamic, calm, energetic, professional, lifestyle |
| `duration` | number | 否 | 4 | 视频时长：4, 6, 8 秒 |
| `aspect_ratio` | string | 否 | "16:9" | 宽高比：16:9, 9:16 |
| `first_frame_b64` | string | 否 | - | 第一帧图片（base64） |
| `last_frame_b64` | string | 否 | - | 最后一帧图片（base64，需配合 first_frame） |
| `reference_images_b64` | array | 否 | - | 参考图片数组（最多3张） |
| `use_context_image` | boolean | 否 | false | 是否使用对话历史中的图片 |
| `context_image_index` | number | 否 | 0 | 使用第几张历史图片（0=最新） |
| `negative_prompt` | string | 否 | - | 负面提示（要避免的内容） |

---

## 注意事项

1. **时长限制：**
   - 插值模式：必须 8 秒
   - 参考图片模式：必须 8 秒
   - 其他模式：4, 6, 或 8 秒

2. **宽高比限制：**
   - 参考图片模式：仅支持 16:9
   - 其他模式：16:9 或 9:16

3. **参考图片数量：**
   - 最多 3 张
   - 超过 3 张会自动截取前 3 张

4. **对话历史：**
   - 工具会自动搜索最近的图片
   - 如果找不到图片且 `use_context_image=true`，会记录警告但继续执行

5. **异步处理：**
   - 视频生成是异步的，需要轮询
   - 工具内部已处理轮询逻辑（最多 5 分钟）
   - 超时会返回 timeout 状态

---

## 测试

运行测试脚本：
```bash
cd ai-orchestrator
python test_video_generation.py
```

注意：需要有效的 Gemini API 密钥才能实际生成视频。
