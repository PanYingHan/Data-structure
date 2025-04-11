import os
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime
import gradio as gr
from gemini_utils import analyze_csv
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
import io

# 載入環境變數
load_dotenv()

# 註冊 macOS 內建中文字體
pdfmetrics.registerFont(TTFont('HeitiTC', '/System/Library/Fonts/STHeiti Light.ttc'))

# PDF 產出
def generate_pdf(text: str, prompt: str) -> str:
    filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    c = canvas.Canvas(filename, pagesize=A4)
    c.setFont("HeitiTC", 12)
    c.drawString(40, 800, f"🧠 您的需求：{prompt[:40]}")
    c.drawString(40, 780, "📝 分析結果：")
    y = 760
    for line in text.splitlines():
        if y < 50:
            c.showPage()
            c.setFont("HeitiTC", 12)
            y = 800
        c.drawString(40, y, line[:90])
        y -= 20
    c.save()
    return filename

# Gradio 主邏輯
def gradio_handler(csv_file, user_prompt):
    # 如果沒有上傳 CSV 檔案
    if not csv_file:
        response = "你沒有提供任何 CSV 內容和指令。請提供 CSV 數據以及你想讓我執行的分析。"
        pdf_path = 0
        return response, pdf_path

    # 如果有上傳 CSV 檔案
    df = pd.read_csv(csv_file.name)
    csv_text = df.to_csv(index=False)
    try:
        response = analyze_csv(user_prompt, csv_text)
    except Exception as e:
        response = f"⚠️ 分析錯誤：{str(e)}"
    pdf_path = generate_pdf(text=response, prompt=user_prompt)
    return response, pdf_path

# 預設指令
default_prompt = """請在此輸入您的需求"""

# Gradio UI
with gr.Blocks(css="""
#main-block {
    padding: 2rem;
    background-color:#ffc0cb;
    border-radius: 1rem;
}
.label-title {
    font-size: 1rem;
    font-weight: bold;
    margin-bottom: 0.5rem;
    color: #333;
}
.gr-box {
    padding: 1rem;
    border: 1px solid #ddd;
    border-radius: 0.75rem;
    background-color: #fff;
}
""") as demo:

    with gr.Column(elem_id="main-block"):
        gr.Markdown("## 上傳你的 CSV 檔案進行分析～")

        with gr.Row():
            with gr.Column():
                gr.Markdown("<div class='label-title'>📁 上傳 CSV 檔案</div>")
                csv_input = gr.File(type="filepath", file_types=[".csv"], interactive=True, elem_classes=["gr-box"])
            with gr.Column():
                gr.Markdown("<div class='label-title'>📝 輸入您的需求</div>")
                user_input = gr.Textbox(lines=10, value=default_prompt, elem_classes=["gr-box"])

        with gr.Column():
            gr.Markdown("<div class='label-title'>🤖 AI 分析結果</div>")
            output_text = gr.Textbox(interactive=False, elem_classes=["gr-box"])

        with gr.Column():
            gr.Markdown("<div class='label-title'>📄 下載 PDF 報表</div>")
            output_pdf = gr.File(interactive=False, elem_classes=["gr-box"])

        gr.Button("🚀 開始分析").click(
            fn=gradio_handler,
            inputs=[csv_input, user_input],
            outputs=[output_text, output_pdf]
        )

# 自動開啟 Chrome
from playwright.sync_api import sync_playwright
import threading

def open_browser_with_gradio():
    with sync_playwright() as p:
        chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        user_data_dir = "/tmp/gradio-chrome-profile"
        print("🚀 啟動 Google Chrome 並載入 Gradio 頁面...")
        browser = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            executable_path=chrome_path,
        )
        page = browser.pages[0]
        page.goto("http://127.0.0.1:7860", timeout=0)
        print("✅ Chrome 視窗已開啟")
        input("🔚 用完請按 Enter 關閉瀏覽器...")
        browser.close()

if __name__ == "__main__":
    threading.Thread(target=demo.launch, daemon=True).start()
    open_browser_with_gradio()

# 執行前請先執行：source venv/bin/activate
# 再執行：python csv_analysis.py
