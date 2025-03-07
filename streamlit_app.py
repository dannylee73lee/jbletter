import streamlit as st
from openai import OpenAI
from datetime import datetime, timedelta
import time
import base64
import os
import re
import requests

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

def fetch_real_time_news(api_key, query="AI digital transformation", days=7, language="en"):
    """
    NewsAPI를 사용하여 실시간 뉴스를 가져옵니다.
    무료 플랜은 최근 1개월(실제로는 더 짧을 수 있음) 데이터만 접근 가능합니다.
    """
    # 날짜 범위 계산 (API 제한으로 인해 기간을 줄임)
    end_date = datetime.now()
    # 무료 플랜 제한을 고려하여 기간을 줄임
    start_date = end_date - timedelta(days=min(days, 7))  # 최대 7일로 제한
    
    # NewsAPI 요청
    url = "https://newsapi.org/v2/everything"
    params = {
        'q': query,
        'from': start_date.strftime('%Y-%m-%d'),
        'to': end_date.strftime('%Y-%m-%d'),
        'sortBy': 'publishedAt',
        'language': language,
        'apiKey': api_key
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        news_data = response.json()
        return news_data['articles']
    else:
        raise Exception(f"뉴스 가져오기 실패: {response.status_code} - {response.text}")

def generate_newsletter(openai_api_key, news_api_key, news_query, language="en", custom_success_story=None, issue_num=1, highlight_settings=None):
    os.environ["OPENAI_API_KEY"] = openai_api_key  # OpenAI API 키 설정
    
    # OpenAI 클라이언트 초기화
    client = OpenAI(api_key=openai_api_key)
    
    date = datetime.now().strftime('%Y년 %m월 %d일')
    issue_number = issue_num

    # 현재 주차 계산 (이슈 번호를 주차로 사용)
    current_week = issue_num
    
    # AI 팁 주제 데이터베이스 - 여러 주제를 순환하여 제공
    ai_tip_topics = [
        "효과적인 프롬프트 작성의 기본 원칙 (Chain of Thought, Chain of Draft)",
        "특정 업무별 최적의 프롬프트 템플릿",
        "AI를 활용한 데이터 분석 프롬프트 기법",
        "창의적 작업을 위한 AI 프롬프트 전략",
        "AI와 협업하여 문제 해결하기",
        "다양한 AI 도구 활용법 비교",
        "업무 자동화를 위한 AI 프롬프트 설계",
        "AI를 활용한 의사결정 지원 기법"
    ]
    
    # 현재 주차에 해당하는 주제 선택 (순환)
    current_topic = ai_tip_topics[(current_week - 1) % len(ai_tip_topics)]
    
    # 하이라이트 설정 기본값
    if highlight_settings is None:
        highlight_settings = {
            "title": "중부Infra AT/DT 뉴스레터 개시",
            "subtitle": "AI, 어떻게 시작할지 막막하다면?",
            "link_text": "AT/DT 추진방향 →",
            "link_url": "#"
        }
    
    # 실시간 뉴스 가져오기
    news_info = ""
    try:
        # 무료 플랜은 최근 1주일 정도의 데이터만 접근 가능하므로 days=7로 설정
        news_articles = fetch_real_time_news(news_api_key, query=news_query, days=7, language=language)
        # 상위 5개 뉴스 선택
        top_news = news_articles[:5]
        
        # GPT-4에 전달할 뉴스 정보 준비
        news_info = "최근 7일 내 수집된 실제 뉴스 기사:\n\n"
        for i, article in enumerate(top_news):
            # 날짜 포맷 변환
            pub_date = datetime.fromisoformat(article['publishedAt'].replace('Z', '+00:00')).strftime('%Y년 %m월 %d일')
            news_info += f"{i+1}. 제목: {article['title']}\n"
            news_info += f"   날짜: {pub_date}\n"
            news_info += f"   요약: {article['description']}\n"
            news_info += f"   출처: {article['source']['name']}\n"
            news_info += f"   URL: {article['url']}\n\n"
    except Exception as e:
        news_info = f"실시간 뉴스를 가져오는 중 오류가 발생했습니다: {str(e)}"
        st.error(f"뉴스 API 오류: {str(e)}")
    
    prompts = {
        'main_news': f"""
        AIDT Weekly 뉴스레터의 '주요 소식' 섹션을 생성해주세요.
        오늘 날짜는 {date}입니다. 아래는 최근 7일 이내의 실제 뉴스 기사입니다:
        
        {news_info}
        
        위 뉴스 기사 중 가장 중요하고 관련성 높은 3가지 주요 소식을 선택하여 다음 형식으로 작성해주세요:
        
        ## [주제]의 [핵심 강점/특징]은 [주목할만합니다/확인됐습니다/중요합니다].
        
        간략한 내용을 1-2문장으로 작성하세요. 내용은 특정 기술이나 서비스, 기업의 최신 소식을 다루고, 
        핵심 내용만 포함해주세요. 그리고 왜 중요한지를 강조해주세요.
        
        구체적인 수치나 인용구가 있다면 추가해주세요.
        
        각 소식의 마지막에는 뉴스 기사의 발행일과 출처를 반드시 "[출처 제목](출처 URL)" 형식으로 포함하세요.
        
        모든 주제는 반드시 제공된 실제 뉴스 기사에서만 추출해야 합니다. 가상의 정보나 사실이 아닌 내용은 절대 포함하지 마세요.
        각 소식 사이에 충분한 공백을 두어 가독성을 높여주세요.
        """,


        'aidt_tips': f"""
        AIDT Weekly 뉴스레터의 '이번 주 AIDT 팁' 섹션을 생성해주세요.
        
        이번 주 팁 주제는 "{current_topic}"입니다.
        
        이 주제에 대해 다음 형식으로 실용적인 팁을 작성해주세요:
        
        ## 이번 주 팁: [주제에 맞는 구체적인 팁 제목]
        
        팁에 대한 배경과 중요성을 2-3문장으로 간결하게 설명해주세요. AI 기본기와 관련된 내용을 포함하세요.
        
        **핵심 프롬프트 예시:**
        - 첫 번째 프롬프트 템플릿 (구체적인 예시와 함께)
        - 두 번째 프롬프트 템플릿 (구체적인 예시와 함께)
        - 세 번째 프롬프트 템플릿 (구체적인 예시와 함께)
        
        이 팁을 활용했을 때의 업무 효율성 향상이나 결과물 품질 개선 등 구체적인 이점을 한 문장으로 작성해주세요.
        
        마지막에 "다음 주에는 다른 AI 기본기 팁을 알려드리겠습니다."라는 문장을 추가해주세요.
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
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AIDT Weekly - 제{issue_number}호</title>
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
                max-width: 600px;
                margin: 0 auto;
                background-color: #ffffff;
            }}
            .content {{
                padding: 20px;
            }}
            .header {{
                background-color: #333333;
                color: white;
                padding: 15px 20px;
                text-align: left;
            }}
            .title {{
                margin: 0;
                font-size: 20px;
                font-weight: bold;
            }}
            .issue-date {{
                margin-top: 5px;
                font-size: 10pt;
            }}
            .section {{
                margin-bottom: 25px;
                border-bottom: 1px solid #eee;
                padding-bottom: 20px;
            }}
            .section:last-child {{
                border-bottom: none;
            }}
            .section-title {{
                color: #ffffff;
                font-size: 16px;
                font-weight: bold;
                margin-bottom: 10px;
                background-color: #3e3e3e;
                padding: 8px 10px;
                border-radius: 4px;
            }}
            .section-icon {{
                margin-right: 8px;
            }}
            h2, h3 {{
                font-size: 14px;
                margin-bottom: 5px;
                color: #333333;
            }}
            .main-news h2 {{
                color: #ff5722;
                font-size: 14px;
                margin-top: 15px;
                margin-bottom: 5px;
                border-bottom: none;
                padding-bottom: 0;
            }}
            .main-news a {{
                color: #ff5722;
                text-decoration: none;
            }}
            .main-news a:hover {{
                text-decoration: underline;
            }}
            .main-news p, .success-case p, p, li {{
                font-size: 10pt;
                margin: 0 0 8px;
            }}
            ul {{
                padding-left: 20px;
                margin-top: 5px;
                margin-bottom: 8px;
            }}
            li {{
                margin-bottom: 3px;
            }}
            .footer {{
                background-color: #f1f1f1;
                padding: 10px;
                text-align: center;
                font-size: 9pt;
                color: #666;
            }}
            .section-container {{
                padding: 0 15px;
            }}
            .highlight-box {{
                background-color: #fff9f5;
                border: 1px solid #ffe0cc;
                border-radius: 5px;
                padding: 15px;
                margin: 10px 0;
            }}
            .highlight-title {{
                color: #ff5722;
                font-size: 16px;
                font-weight: bold;
                margin-bottom: 10px;
                text-align: center;
            }}
            .highlight-subtitle {{
                color: #666;
                font-size: 12px;
                text-align: center;
                margin-bottom: 15px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="title">중부Infra AT/DT Weekly</div>
                <div class="issue-info">제{issue_number}호 | {date}</div>
            </div>
            
            <div class="content">
                <div class="newsletter-intro">
                    <p>중부Infra AT/DT 뉴스레터는 모두가 AI발전 속도에 뒤쳐지지 않고 업무에 적용할 수 있도록 가장 흥미로운 AI 활용법을 전합니다.</p>
                </div>
                
                <div class="highlight-box">
                    <div class="highlight-title">{highlight_settings['title']}</div>
                    <div class="highlight-subtitle">{highlight_settings['subtitle']}</div>
                    <p style="text-align: right; margin-top: 5px; font-size: 9pt;"><a href="{highlight_settings['link_url']}" style="color: #ff5722;">{highlight_settings['link_text']}</a></p>
                </div>
                
                <div class="section">
                    <div class="section-title">주요 소식</div>
                    <div class="section-container main-news">
                        {newsletter_content['main_news']}
                    </div>
                </div>
                
                <div class="section">
                    <div class="section-title">이번 주 AIDT 팁</div>
                    <div class="section-container">
                        {newsletter_content['aidt_tips']}
                    </div>
                </div>
                
                <div class="section success-case">
                    <div class="section-title">성공 사례</div>
                    <div class="section-container">
                        {newsletter_content['success_story']}
                    </div>
                </div>
                
                <div class="section">
                    <div class="section-title">다가오는 이벤트</div>
                    <div class="section-container">
                        {newsletter_content['events']}
                    </div>
                </div>
                
                <div class="section">
                    <div class="section-title">질문 & 답변</div>
                    <div class="section-container">
                        {newsletter_content['qa']}
                    </div>
                </div>
            </div>
            
            <div class="footer">
                <p>© {datetime.now().year} AIDT Weekly | 뉴스레터 구독을 감사드립니다.</p>
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
    href = f'<a href="data:text/html;base64,{b64}" download="{filename}" style="display: inline-block; margin-top: 20px; padding: 10px 20px; background-color: #ff5722; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">뉴스레터 다운로드</a>'
    return href

def main():
    st.title("AIDT 뉴스레터 생성기")
    st.write("GPT-4와 실시간 뉴스 API를 활용하여 AI 디지털 트랜스포메이션 관련 뉴스레터를 자동으로 생성합니다.")
    
    # API 키 입력
    with st.expander("API 키 설정", expanded=True):
        st.info("NewsAPI.org에서 API 키를 발급받을 수 있습니다. (https://newsapi.org)")
        openai_api_key = st.text_input("OpenAI API 키 입력", type="password")
        news_api_key = st.text_input("News API 키 입력", type="password")
    
    # 뉴스레터 기본 설정
    with st.expander("뉴스레터 기본 설정", expanded=True):
        issue_number = st.number_input("뉴스레터 호수", min_value=1, value=1, step=1)
        
        # 뉴스 검색 설정
        news_query = st.text_input(
            "뉴스 검색어", 
            value="AI digital transformation OR artificial intelligence OR machine learning",
            help="뉴스 API 검색어를 입력하세요. OR, AND 등의 연산자를 사용할 수 있습니다."
        )
        
        st.info("⚠️ 참고: NewsAPI 무료 플랜은 약 7일 이내의 최신 뉴스만 조회할 수 있습니다. 더 오래된 뉴스를 조회하려면 유료 플랜으로 업그레이드해야 합니다.")
        
        language = st.selectbox(
            "뉴스 언어", 
            options=["en", "ko", "ja", "zh", "fr", "de"],
            format_func=lambda x: {"en": "영어", "ko": "한국어", "ja": "일본어", "zh": "중국어", "fr": "프랑스어", "de": "독일어"}[x],
            help="뉴스 검색 결과의 언어를 선택하세요."
        )
    
    # 하이라이트 박스 설정
    with st.expander("하이라이트 박스 설정"):
        highlight_title = st.text_input("하이라이트 제목", value="중부Infra AT/DT 뉴스레터 개시")
        highlight_subtitle = st.text_input("하이라이트 부제목", value="AI, 어떻게 시작할지 막막하다면?")
        highlight_link_text = st.text_input("링크 텍스트", value="AT/DT 추진방향 →")
        highlight_link_url = st.text_input("링크 URL", value="#")
    
    # 성공 사례 사용자 입력 옵션
    with st.expander("성공 사례 직접 입력"):
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
    
    # 뉴스레터 생성 버튼
    if st.button("뉴스레터 생성"):
        if not openai_api_key or not news_api_key:
            st.error("OpenAI API 키와 News API 키를 모두 입력하세요.")
        else:
            with st.spinner("뉴스레터 생성 중... (약 1-2분 소요될 수 있습니다)"):
                try:
                    # 하이라이트 설정 딕셔너리 생성
                    highlight_settings = {
                        "title": highlight_title,
                        "subtitle": highlight_subtitle,
                        "link_text": highlight_link_text,
                        "link_url": highlight_link_url
                    }
                    
                    html_content = generate_newsletter(
                        openai_api_key, 
                        news_api_key,
                        news_query,
                        language,
                        custom_success_story if use_custom_success else None, 
                        issue_number,
                        highlight_settings
                    )
                    filename = f"중부 ATDT Weekly-제{issue_number}호.html"
                    
                    st.success("✅ 뉴스레터가 성공적으로 생성되었습니다!")
                    st.markdown(create_download_link(html_content, filename), unsafe_allow_html=True)
                    
                    # 미리보기 표시 (iframe 사용) - HTML 태그가 그대로 보이는 문제 수정
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