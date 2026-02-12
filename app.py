from flask import Flask, request, jsonify, render_template
from zhipuai import ZhipuAI
import base64
import os
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

# 智谱客户端
client = ZhipuAI(api_key=os.getenv('ZHIPU_API_KEY'))

def ocr_and_generate(image_base64):
    """OCR识别 + 生成相似题"""
    
    # 1. 第一步：OCR 提取原题文字
    ocr_response = client.chat.completions.create(
        model="glm-4v-flash",
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "这张图片里是一道初高中题目。请把题目原文完整提取出来，包括题干、选项（如果有）、图片描述（如果有）。只输出文字，不要额外解释。"
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}"
                    }
                }
            ]
        }]
    )
    original_text = ocr_response.choices[0].message.content
    
    # 2. 第二步：生成相似题
    generate_response = client.chat.completions.create(
        model="glm-4-flash",  # 纯文本模型，免费
        messages=[{
            "role": "user",
            "content": f"""你是一个出题老师。根据下面这道题，**创作一道全新的、难度相似的题目**。

要求：
- 考察相同的知识点
- 难度相当
- 题型一致（选择题/填空题/解答题）
- 完全原创，不能和原题一样
- 如果是选择题，必须给出4个选项并标注正确答案
- 如果是解答题，给出完整解析

原题：
{original_text}

请按以下格式返回：
【原题文字】
（这里放OCR提取的原文）

【相似新题】
（这里放你出的新题）

【答案】
（新题的答案）

【解析】
（简要解析）"""
        }],
        temperature=0.7  # 适度随机，保证每次出的题不一样
    )
    
    result = generate_response.choices[0].message.content
    
    return {
        "original": original_text,
        "generated": result
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    # ⚠️ 修改2：支持两种上传方式（文件上传 + base64 JSON）
    if request.content_type and 'application/json' in request.content_type:
        # 处理「换一道题」的 JSON 请求
        data = request.get_json()
        image_base64 = data.get('image_base64')
        if not image_base64:
            return jsonify({"error": "没有图片数据"}), 400
        try:
            result = ocr_and_generate(image_base64)
            return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        # 处理文件上传
        if 'image' not in request.files:
            return jsonify({"error": "没有上传文件"}), 400
        
        file = request.files['image']
        image_data = file.read()
        image_base64 = base64.b64encode(image_data).decode()
        
        try:
            result = ocr_and_generate(image_base64)
            return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))  # 👈 Render 会自动传入 PORT
    app.run(host='0.0.0.0', port=port, debug=False)  # 👈 debug 必须 False
