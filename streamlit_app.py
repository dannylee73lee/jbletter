import streamlit as st
from openai import OpenAI
from datetime import datetime
import time
import base64
import os
import re

def convert_markdown_to_html(text):
    """마크다운 텍스트를 HTML로 변환합니다."""
    # 제목 변환 (# 제목)
    text = re.sub(r'^# (.*)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.*)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^### (.*)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    
    # 굵은 텍스트 (**텍스트**)
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    
    # 기울임 텍스트 (*텍스트*)
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    
    # 링크 변환 ([텍스트](URL))
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', text)
    
    # 글머리 기호 (- 항목)
    text = re.sub(r'^\- (.*?)$', r'<li>\1</li>', text, flags=re.MULTILINE)
    
    # 색상 표시 강조 - 주요 소식에서 사용할 수 있는 색상 강조 기능
    text = re.sub(r'\[강조\](.*?)\[\/강조\]', r'<span style="color:#e74c3c; font-weight:bold;">\1</span>', text)
    
    # 줄바꿈을 <br>과 <p>로 변환
    paragraphs = text.split('\n\n')
    for i, paragraph in enumerate(paragraphs):
        if not paragraph.startswith('<h') and not paragraph.startswith('<li'):
            # 이미 HTML 태그가 아닌 경우만 <p> 태그로 감싸기
            if '<li>' in paragraph:
                # 리스트 항목이 있는 경우 <ul> 태그로 감싸기
                paragraph = f'<ul>{paragraph}</ul>'
            else:
                paragraph = f'<p>{paragraph}</p>'
        paragraphs[i] = paragraph.replace('\n', '<br>')
    
    return ''.join(paragraphs)

def generate_newsletter(api_key, issue_number, custom_success_story=None):
    os.environ["OPENAI_API_KEY"] = api_key  # API 키 설정
    
    # 클라이언트 초기화
    client = OpenAI(api_key=api_key)
    
    date = datetime.now().strftime('%Y년 %m월 %d일')
    
    prompts = {
        'main_news': """
        AIDT Weekly 뉴스레터의 '주요 소식' 섹션을 생성해주세요.
        형식:
        
        ## [주제]의 [핵심 강점/특징]은 [주목할만합니다/확인됐습니다/중요합니다].
        
        간략한 내용을 1-2문장으로 작성하세요. 내용은 특정 기술이나 서비스, 기업의 최신 소식을 다루고, 
        핵심 내용만 포함해주세요. 그리고 왜 중요한지를 강조해주세요.
        
        구체적인 수치나 인용구가 있다면 추가해주세요. 예를 들어 "이에 관련하여 [전문가 이름]은 [의견/평가]라고 이야기 합니다."
        
        마지막에는 추가 정보를 볼 수 있는 곳을 언급해주세요. 예: "[출처]에서 전체 내용을 확인할 수 있습니다."
        
        ## [두 번째 주제]의 [핵심 강점/특징]은 [주목할만합니다/확인됐습니다].
        
        간략한 내용을 1-2문장으로 작성하세요. 내용은 특정 기술이나 서비스, 기업의 최신 소식을 다루고, 
        핵심 내용만 포함해주세요. 그리고 왜 중요한지를 강조해주세요.
        
        구체적인 수치나 인용구가 있다면 추가해주세요.
        
        ## [세 번째 주제]가 [중요한 이벤트/변화]를 준비/출시합니다.
        
        간략한 내용을 1-2문장으로 작성하세요. 기술이나 서비스의 출시 예정일이나 영향력을 언급하세요.
        각 소식 사이에 충분한 공백을 두어 가독성을 높여주세요.
        """,
        'aidt_tips': """
        AIDT Weekly 뉴스레터의 'AI 활용 팁' 섹션을 생성해주세요.
        형식:
        
        ## 이번 주 팁: 팁 제목
        
        팁에 대한 설명을 2-3문장으로 간결하게 작성해주세요.
        
        **핵심 단계:**
        - 첫 번째 단계
        - 두 번째 단계
        - 세 번째 단계
        
        이 팁을 활용했을 때의 이점을 한 문장으로 작성해주세요.
        """,
        'success_story': """
        AIDT Weekly 뉴스레터의 '성공 사례' 섹션을 생성해주세요.
        한국 기업 사례 1개와 외국 기업 사례 1개를 생성해야 합니다.
        각 사례는 제목과 3개의 단락으로 구성되어야 합니다.
        각 단락은 3~4줄로 구성하고, 구체적인 내용과 핵심 정보를 포함해야 합니다.
        단락 사이에는 한 줄을 띄워서 가독성을 높여주세요.
        
        형식:
        
        ## [한국 기업명]의 AI 혁신 사례
        
        첫 번째 단락에서는 기업이 직면한 문제와 배경을 상세히 설명합니다. 구체적인 수치나 상황을 포함하여 3~4줄로 작성해주세요. 이 부분에서는 독자가 왜 이 기업이 AI 솔루션을 필요로 했는지 이해할 수 있도록 해주세요.
        
        두 번째 단락에서는 기업이 도입한 AI 솔루션을 상세히 설명합니다. 어떤 기술을 사용했는지, 어떻게 구현했는지, 특별한 접근 방식은 무엇이었는지 등을 포함하여 3~4줄로 작성해주세요.
        
        세 번째 단락에서는 AI 도입 후 얻은 구체적인 성과와 결과를 설명합니다. 가능한 한 정량적인 수치(비용 절감, 효율성 증가, 고객 만족도 향상 등)를 포함하여 3~4줄로 작성해주세요.
        
        ## [외국 기업명]의 AI 혁신 사례
        
        첫 번째 단락에서는 기업이 직면한 문제와 배경을 상세히 설명합니다. 구체적인 수치나 상황을 포함하여 3~4줄로 작성해주세요. 이 부분에서는 독자가 왜 이 기업이 AI 솔루션을 필요로 했는지 이해할 수 있도록 해주세요.
        
        두 번째 단락에서는 기업이 도입한 AI 솔루션을 상세히 설명합니다. 어떤 기술을 사용했는지, 어떻게 구현했는지, 특별한 접근 방식은 무엇이었는지 등을 포함하여 3~4줄로 작성해주세요.
        
        세 번째 단락에서는 AI 도입 후 얻은 구체적인 성과와 결과를 설명합니다. 가능한 한 정량적인 수치(비용 절감, 효율성 증가, 고객 만족도 향상 등)를 포함하여 3~4줄로 작성해주세요.
        """,
        'events': f"""
        AIDT Weekly 뉴스레터의 '다가오는 이벤트' 섹션을 생성해주세요.
        현재 날짜는 {date}입니다.
        형식:
        
        ## 컨퍼런스/웨비나 제목
        - 날짜/시간: [날짜 정보]
        - 장소/형식: [장소 또는 온라인 여부]
        - 내용: 한 문장으로 간략한 설명
        
        ## 다른 이벤트 제목
        - 날짜/시간: [날짜 정보]
        - 장소/형식: [장소 또는 온라인 여부]
        - 내용: 한 문장으로 간략한 설명
        """,
        'qa': """
        AIDT Weekly 뉴스레터의 'Q&A' 섹션을 생성해주세요.
        형식:
        
        ## 간단명료한 질문?
        
        답변을 2-3문장으로 간결하게 작성해주세요. 불필요한 설명은 제외하고 핵심 정보만 포함해주세요.
        """
    }
    
    newsletter_content = {}
    
    for section, prompt in prompts.items():
        try:
            # 사용자가 입력한 성공 사례가 있으면 생성 건너뛰기
            if section == 'success_story' and custom_success_story:
                newsletter_content[section] = convert_markdown_to_html(custom_success_story)
                continue
                
            response = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "AI 디지털 트랜스포메이션 뉴스레터 콘텐츠 생성 전문가. 간결하고 핵심적인 내용만 포함한 뉴스레터를 작성합니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            newsletter_content[section] = convert_markdown_to_html(response.choices[0].message.content)
        except Exception as e:
            newsletter_content[section] = f"<p>콘텐츠 생성 오류: {e}</p>"
    
    # 날짜 형식 업데이트
    formatted_date = datetime.now().strftime('%Y년 %m월 %d일')
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>중부 AT/DT Weekly - 제{issue_number}호</title>
        <style>
            body {{
                font-family: 'Segoe UI', Arial, sans-serif;
                line-height: 1.5;
                color: #333;
                margin: 0;
                padding: 0;
                background-color: #f9f9f9;
            }}
            .container {{
                max-width: 800px;
                margin: 0 auto;
                background-color: #ffffff;
            }}
            .content {{
                padding: 20px;
            }}
            .header {{
                text-align: center;
                padding: 20px 0;
            }}
            .title {{
                color: #4285f4;
                font-size: 32px;
                font-weight: bold;
                margin: 0;
            }}
            .issue-info {{
                margin-top: 10px;
                font-size: 16px;
                color: #333;
            }}
            .divider {{
                height: 1px;
                background-color: #4285f4;
                margin: 20px 0;
            }}
            .section {{
                margin-bottom: 30px;
                border-bottom: 1px solid #eee;
                padding-bottom: 20px;
            }}
            .section:last-child {{
                border-bottom: none;
            }}
            .section-title {{
                display: flex;
                align-items: center;
                margin-bottom: 15px;
            }}
            .section-icon {{
                margin-right: 10px;
                font-size: 20px;
            }}
            h2, h3 {{
                font-size: 16px;
                margin-bottom: 5px;
                color: #333333;
            }}
            .main-news h2 {{
                color: #4285f4;
                font-size: 16px;
                margin-top: 15px;
                margin-bottom: 5px;
            }}
            .main-news a {{
                color: #4285f4;
                text-decoration: none;
            }}
            .main-news a:hover {{
                text-decoration: underline;
            }}
            .main-news p, .success-case p, p, li {{
                font-size: 14px;
                margin: 0 0 10px;
            }}
            ul {{
                padding-left: 20px;
                margin-top: 5px;
                margin-bottom: 10px;
            }}
            li {{
                margin-bottom: 5px;
            }}
            .footer {{
                background-color: #f1f1f1;
                padding: 15px;
                text-align: center;
                font-size: 12px;
                color: #666;
            }}
            .section-container {{
                padding: 0 15px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="title">중부 AT/DT Weekly</div>
                <div class="issue-info">제{issue_number}호 | {formatted_date}</div>
            </div>
            
            <div class="divider"></div>
            
            <div class="content">
                <div class="section">
                    <div class="section-title">
                        <span class="section-icon">🔔</span>
                        <h2 style="color: white; margin: 0; font-weight: bold;">주요 소식</h2>
                    </div>
                    <div class="section-container main-news">
                        {newsletter_content['main_news']}
                    </div>
                </div>
                
                <div class="section">
                    <div class="section-title">
                        <span class="section-icon">💡</span>
                        <h2 style="color: white; margin: 0; font-weight: bold;">이번 주 팁</h2>
                    </div>
                    <div class="section-container">
                        {newsletter_content['aidt_tips']}
                    </div>
                </div>
                
                <div class="section success-case">
                    <div class="section-title">
                        <span class="section-icon">🏆</span>
                        <h2 style="color: white; margin: 0; font-weight: bold;">성공 사례</h2>
                    </div>
                    <div class="section-container">
                        {newsletter_content['success_story']}
                    </div>
                </div>
                
                <div class="section">
                    <div class="section-title">
                        <span class="section-icon">📅</span>
                        <h2 style="color: white; margin: 0; font-weight: bold;">다가오는 이벤트</h2>
                    </div>
                    <div class="section-container">
                        {newsletter_content['events']}
                    </div>
                </div>
                
                <div class="section">
                    <div class="section-title">
                        <span class="section-icon">❓</span>
                        <h2 style="color: white; margin: 0; font-weight: bold;">질문 & 답변</h2>
                    </div>
                    <div class="section-container">
                        {newsletter_content['qa']}
                    </div>
                </div>
            </div>
            
            <div class="footer">
                <p>© {datetime.now().year} 중부 AT/DT Weekly | 뉴스레터 구독을 감사드립니다.</p>
                <p>문의사항이나 제안이 있으시면 언제든지 연락해 주세요.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html_content

def create_download_link(html_content, filename):
    """HTML 콘텐츠를 다운로드할 수 있는 링크를 생성합니다."""
    b64 = base64.b64encode(html_content.encode()).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="{filename}" style="display: inline-block; margin-top: 20px; padding: 10px 20px; background-color: #4285f4; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">뉴스레터 다운로드</a>'
    return href

def main():
    st.title("중부 AT/DT Weekly 뉴스레터 생성기")
    st.write("GPT-4를 활용하여 디지털 트랜스포메이션 관련 뉴스레터를 자동으로 생성합니다.")
    
    # OpenAI API 키 입력
    api_key = st.text_input("OpenAI API 키 입력", type="password")
    
    # 호수 입력
    issue_number = st.number_input("뉴스레터 호수", min_value=1, value=1, step=1)
    
    # 성공 사례 사용자 입력 옵션
    use_custom_success = st.checkbox("성공 사례를 직접 입력하시겠습니까?")
    
    custom_success_story = None
    if use_custom_success:
        st.write("아래에 성공 사례를 마크다운 형식으로 입력하세요. 한국 기업과 외국 기업 사례 각 1개씩 포함해주세요.")
        st.write("각 사례는 3개의 단락으로 구성하고, 단락당 3-4줄로 작성해주세요.")
        st.write("예시 형식:")
        st.code("""
## 삼성전자의 AI 혁신 사례

첫 번째 단락 내용을 여기에 작성하세요. 3-4줄로 구성하세요.

두 번째 단락 내용을 여기에 작성하세요. 3-4줄로 구성하세요.

세 번째 단락 내용을 여기에 작성하세요. 3-4줄로 구성하세요.

## Google의 AI 혁신 사례

첫 번째 단락 내용을 여기에 작성하세요. 3-4줄로 구성하세요.

두 번째 단락 내용을 여기에 작성하세요. 3-4줄로 구성하세요.

세 번째 단락 내용을 여기에 작성하세요. 3-4줄로 구성하세요.
        """)
        
        custom_success_story = st.text_area("성공 사례 직접 입력", height=400)
    
    if st.button("뉴스레터 생성"):
        if not api_key:
            st.error("API 키를 입력하세요.")
        else:
            with st.spinner("뉴스레터 생성 중... (약 1-2분 소요될 수 있습니다)"):
                try:
                    html_content = generate_newsletter(api_key, issue_number, custom_success_story if use_custom_success else None)
                    filename = f"중부_ATDT_Weekly_{issue_number}호_{datetime.now().strftime('%Y%m%d')}.html"
                    
                    st.success("✅ 뉴스레터가 성공적으로 생성되었습니다!")
                    st.markdown(create_download_link(html_content, filename), unsafe_allow_html=True)
                    
                    # 미리보기 표시 (iframe 사용)
                    st.subheader("생성된 뉴스레터")
                    
                    # HTML 특수 문자 처리와 Content-Security-Policy 추가
                    safe_html = html_content.replace('"', '\\"')
                    iframe_html = f"""
                    <iframe 
                        srcdoc="{safe_html}" 
                        width="100%" 
                        height="600" 
                        frameborder="0"
                        sandbox="allow-scripts"
                    ></iframe>
                    """
                    st.markdown(iframe_html, unsafe_allow_html=True)
                    
                except Exception as e:
                    st.error(f"오류가 발생했습니다: {e}")

if __name__ == "__main__":
    main()