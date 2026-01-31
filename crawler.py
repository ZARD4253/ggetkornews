from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import os
from xml.sax.saxutils import escape
import re

# --- 설정 ---
TARGET_URL = "https://game.naver.com/lounge/SD_Gundam_G_Generation_ETERNAL/board/22"
OUTPUT_DIR = "output"

options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

driver = webdriver.Chrome(options=options)

print(f"[{TARGET_URL}] 테이블형 공지 게시판 크롤링 시작...")

def detect_post_type(title):
    """제목에서 공지 타입을 감지하여 적절한 카드 스타일 반환"""
    title_lower = title.lower()
    
    if any(keyword in title for keyword in ['[긴급]', '긴급', '[중요]', '중요']):
        return {'type': 'urgent', 'icon': '🚨', 'label': '긴급'}
    elif any(keyword in title for keyword in ['[점검]', '점검', '유지보수', '업데이트']):
        return {'type': 'maintenance', 'icon': '🔧', 'label': '점검'}
    elif any(keyword in title for keyword in ['[이벤트]', '이벤트', 'EVENT']):
        return {'type': 'event', 'icon': '🎉', 'label': '이벤트'}
    elif any(keyword in title for keyword in ['[업데이트]', '신규', '추가', 'NEW']):
        return {'type': 'update', 'icon': '⭐', 'label': '업데이트'}
    elif any(keyword in title for keyword in ['[공지]', '안내']):
        return {'type': 'notice', 'icon': '📢', 'label': '공지'}
    else:
        return {'type': 'default', 'icon': '📄', 'label': '일반'}

try:
    driver.get(TARGET_URL)
    print("⏳ 게시판 로딩 대기 중...")

    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "post_board_detail__1JkwM"))
        )
        print("✅ 게시글 행(tr) 요소 감지됨!")
    except Exception as e:
        print(f"⚠️ 대기 시간 초과, 바로 파싱 시도합니다. ({e})")

    time.sleep(3)
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    items = []

    rows = soup.find_all('tr', class_='post_board_detail__1JkwM')
    print(f"📊 총 {len(rows)}개의 게시글 행 발견")

    if len(rows) == 0:
        print("❌ 게시글을 찾지 못했습니다. 페이지 소스 일부를 출력합니다:")
        print("="*80)
        print(soup.prettify()[:3000])
        print("="*80)
        raise Exception("게시글 요소를 찾을 수 없습니다. 구조를 확인하세요.")

    for row in rows:
        title_tag = row.find('a', class_='post_board_title__3NYcf')
        if not title_tag:
            continue

        title = title_tag.get_text().strip()
        href = title_tag['href']
        full_link = "https://game.naver.com" + href if href.startswith('/') else href

        author_tag = row.find('span', class_='name_text__27mv1')
        author = author_tag.get_text().strip() if author_tag else "알 수 없음"

        date_tag = row.find('span', class_='post_board_information__28nF0')
        pub_date = date_tag.get_text().strip() if date_tag else "날짜 없음"

        # 공지 타입 감지
        post_info = detect_post_type(title)

        items.append({
            'title': title,
            'link': full_link,
            'author': author,
            'pubDate': pub_date,
            'type': post_info['type'],
            'icon': post_info['icon'],
            'label': post_info['label']
        })

        print(f"📄 [{pub_date}] {title}")
        print(f"   👤 작성자: {author}")
        print(f"   🔗 링크: {full_link}\n")

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    if items:
        # === RSS 생성 (기존과 동일) ===
        with open(f"{OUTPUT_DIR}/feed.xml", "w", encoding="utf-8") as f:
            now = time.strftime("%a, %d %b %Y %H:%M:%S +0900")
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write('<rss version="2.0">\n')
            f.write('  <channel>\n')
            f.write('    <title>SD Gundam G Generation Eternal - 공식 공지사항</title>\n')
            f.write(f'    <link>{TARGET_URL}</link>\n')
            f.write(f'    <lastBuildDate>{now}</lastBuildDate>\n')
            f.write('    <description>공식 공지 게시판(board/22)의 모든 글을 크롤링한 피드입니다.</description>\n')

            for item in items:
                escaped_title = escape(item['title'])
                escaped_author = escape(item['author'])
                f.write('    <item>\n')
                f.write(f'      <title>{escaped_title}</title>\n')
                f.write(f'      <link>{item["link"]}</link>\n')
                f.write(f'      <description>작성자: {escaped_author} | {escaped_title}</description>\n')
                f.write(f'      <pubDate>{now}</pubDate>\n')
                f.write('    </item>\n')

            f.write('  </channel>\n')
            f.write('</rss>\n')

        # === 건담 스타일 HTML 생성 (우클릭 방지 코드 추가) ===
        with open(f"{OUTPUT_DIR}/index.html", "w", encoding="utf-8") as f:
            f.write("""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SD건담 G 제네레이션 이터널 - 공식 공지사항</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            user-select: none;
            -webkit-user-select: none;
            -moz-user-select: none;
            -ms-user-select: none;
        }
        
        body {
            font-family: 'Pretendard', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;
            background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%);
            min-height: 100vh;
            padding: 20px;
            color: #fff;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            margin-bottom: 50px;
            padding: 40px 20px;
            background: linear-gradient(135deg, rgba(211, 47, 47, 0.1) 0%, rgba(25, 118, 210, 0.1) 100%);
            border-radius: 20px;
            border: 2px solid rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
        }
        
        .header h1 {
            font-size: 2.5em;
            background: linear-gradient(135deg, #ff6b6b 0%, #4ecdc4 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 10px;
            font-weight: 800;
            text-shadow: 0 0 30px rgba(255, 107, 107, 0.3);
        }
        
        .header .subtitle {
            color: #a0aec0;
            font-size: 1.1em;
            margin-bottom: 10px;
        }
        
        .header .updated {
            color: #718096;
            font-size: 0.9em;
            font-family: 'Courier New', monospace;
        }
        
        .cards-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 25px;
            margin-bottom: 40px;
        }
        
        .card {
            position: relative;
            background: linear-gradient(135deg, rgba(30, 30, 60, 0.8) 0%, rgba(20, 20, 40, 0.9) 100%);
            border-radius: 16px;
            padding: 0;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            cursor: pointer;
        }
        
        .card:hover {
            transform: translateY(-8px) scale(1.02);
            border-color: rgba(255, 255, 255, 0.3);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4),
                        0 0 30px rgba(255, 255, 255, 0.1);
        }
        
        .card-header {
            padding: 20px;
            position: relative;
            overflow: hidden;
        }
        
        .card-header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 100%;
            opacity: 0.1;
            background: linear-gradient(135deg, transparent 0%, rgba(255,255,255,0.1) 100%);
        }
        
        /* 카드 타입별 그라데이션 */
        .card.urgent .card-header {
            background: linear-gradient(135deg, #ff0844 0%, #ff6b6b 100%);
        }
        
        .card.maintenance .card-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        
        .card.event .card-header {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }
        
        .card.update .card-header {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        }
        
        .card.notice .card-header {
            background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        }
        
        .card.default .card-header {
            background: linear-gradient(135deg, #757f9a 0%, #d7dde8 100%);
        }
        
        .card-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 6px 14px;
            background: rgba(255, 255, 255, 0.2);
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 700;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.3);
        }
        
        .card-body {
            padding: 20px;
        }
        
        .card-title {
            font-size: 1.15em;
            font-weight: 700;
            color: #fff;
            margin-bottom: 15px;
            line-height: 1.5;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }
        
        .card-meta {
            display: flex;
            gap: 20px;
            margin-bottom: 15px;
            font-size: 0.9em;
            color: #a0aec0;
        }
        
        .card-meta span {
            display: flex;
            align-items: center;
            gap: 6px;
        }
        
        .card-link {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 20px;
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.1) 0%, rgba(255, 255, 255, 0.05) 100%);
            color: #fff;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 600;
            font-size: 0.95em;
            border: 1px solid rgba(255, 255, 255, 0.2);
            transition: all 0.3s ease;
        }
        
        .card-link:hover {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.2) 0%, rgba(255, 255, 255, 0.1) 100%);
            transform: translateX(5px);
            border-color: rgba(255, 255, 255, 0.4);
        }
        
        /* 카드 장식 효과 */
        .card::before {
            content: '';
            position: absolute;
            top: -50%;
            right: -50%;
            width: 200%;
            height: 200%;
            background: linear-gradient(45deg, transparent 0%, rgba(255,255,255,0.03) 50%, transparent 100%);
            transform: rotate(45deg);
            pointer-events: none;
        }
        
        /* 반응형 */
        @media (max-width: 768px) {
            .cards-grid {
                grid-template-columns: 1fr;
                gap: 20px;
            }
            
            .header h1 {
                font-size: 2em;
            }
            
            .header {
                padding: 30px 15px;
            }
            
            .card-meta {
                flex-direction: column;
                gap: 10px;
            }
        }
        
        /* 로딩 애니메이션 */
        @keyframes shimmer {
            0% { background-position: -1000px 0; }
            100% { background-position: 1000px 0; }
        }
        
        .loading {
            animation: shimmer 2s infinite;
            background: linear-gradient(90deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.1) 50%, rgba(255,255,255,0.05) 100%);
            background-size: 1000px 100%;
        }
    </style>
</head>
<body oncontextmenu="return false" onselectstart="return false" ondragstart="return false">
    <div class="container">
        <div class="header">
            <h1>🤖 SD건담 G 제네레이션 이터널</h1>
            <p class="subtitle">📡 공식 공지사항 게시판</p>
            <p class="updated">Last Update: """ + time.strftime("%Y-%m-%d %H:%M:%S") + """</p>
        </div>
        
        <div class="cards-grid">
""")
            
            for item in items:
                card_type = item['type']
                f.write(f"""
            <div class="card {card_type}">
                <div class="card-header">
                    <div class="card-badge">{item['icon']} {item['label']}</div>
                </div>
                <div class="card-body">
                    <div class="card-title">{item['title']}</div>
                    <div class="card-meta">
                        <span>👤 {item['author']}</span>
                        <span>📅 {item['pubDate']}</span>
                    </div>
                    <a class="card-link" href="{item['link']}" target="_blank">
                        📄 원문 보기 →
                    </a>
                </div>
            </div>
""")

            f.write("""
        </div>
    </div>
    
    <script>
        // 카드 클릭 시 링크로 이동
        document.querySelectorAll('.card').forEach(card => {
            card.addEventListener('click', (e) => {
                if (e.target.tagName !== 'A') {
                    const link = card.querySelector('.card-link');
                    if (link) window.open(link.href, '_blank');
                }
            });
        });
        
        // ===== 보안 기능 =====
        
        // 1. 우클릭 메뉴(Context Menu) 방지
        document.addEventListener('contextmenu', function(e) {
            e.preventDefault();
            return false;
        }, false);
        
        // 2. 드래그 및 텍스트 선택 방지
        document.addEventListener('selectstart', function(e) {
            e.preventDefault();
            return false;
        }, false);
        
        document.addEventListener('dragstart', function(e) {
            e.preventDefault();
            return false;
        }, false);
        
        // 3. 복사(Ctrl+C), 잘라내기(Ctrl+X), 전체선택(Ctrl+A) 막기
        document.addEventListener('keydown', function(e) {
            if (e.ctrlKey && (e.keyCode === 67 || e.keyCode === 88 || e.keyCode === 65)) {
                e.preventDefault();
                return false;
            }
        }, false);
        
        // 4. 개발자 도구 (F12, Ctrl+Shift+I/J/C, Ctrl+U) 막기
        document.onkeydown = function(e) {
            // F12
            if (e.keyCode === 123) {
                return false;
            }
            // Ctrl+Shift+I, Ctrl+Shift+J, Ctrl+Shift+C
            if (e.ctrlKey && e.shiftKey && (e.keyCode === 73 || e.keyCode === 74 || e.keyCode === 67)) {
                return false;
            }
            // Ctrl+U (페이지 소스 보기)
            if (e.ctrlKey && e.keyCode === 85) {
                return false;
            }
        };
    </script>
</body>
</html>""")

        print(f"\n🎉 성공! {len(items)}개의 공지글 저장 완료 → {OUTPUT_DIR}/index.html")
        print("🔗 GitHub Pages에 배포하면 자동 갱신 사이트 완성!")
        print("🔒 우클릭 방지 및 복사 방지 보안 기능 적용됨")

    else:
        print("\n🚫 게시글을 하나도 찾지 못했습니다. 클래스명을 다시 확인해 주세요.")

except Exception as e:
    print(f"❌ 최종 에러 발생: {e}")
    raise e

finally:
    driver.quit()
