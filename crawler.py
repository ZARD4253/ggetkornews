from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import os
from xml.sax.saxutils import escape

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

try:
    driver.get(TARGET_URL)
    print("⏳ 게시판 로딩 대기 중...")

    # ✅ 테이블 행(tr) 요소가 나타날 때까지 대기
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "post_board_detail__1JkwM"))
        )
        print("✅ 게시글 행(tr) 요소 감지됨!")
    except Exception as e:
        print(f"⚠️ 대기 시간 초과, 바로 파싱 시도합니다. ({e})")

    time.sleep(3)  # 추가 로딩 대기
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    items = []

    # ✅ 핵심: tr.post_board_detail__1JkwM 찾기
    rows = soup.find_all('tr', class_='post_board_detail__1JkwM')
    print(f"📊 총 {len(rows)}개의 게시글 행 발견")

    if len(rows) == 0:
        print("❌ 게시글을 찾지 못했습니다. 페이지 소스 일부를 출력합니다:")
        print("="*80)
        print(soup.prettify()[:3000])
        print("="*80)
        raise Exception("게시글 요소를 찾을 수 없습니다. 구조를 확인하세요.")

    for row in rows:
        # 1. 제목 + 링크
        title_tag = row.find('a', class_='post_board_title__3NYcf')
        if not title_tag:
            continue

        title = title_tag.get_text().strip()
        href = title_tag['href']
        full_link = "https://game.naver.com" + href if href.startswith('/') else href

        # 2. 작성자
        author_tag = row.find('span', class_='name_text__27mv1')
        author = author_tag.get_text().strip() if author_tag else "알 수 없음"

        # 3. 작성일 — 첫 번째 .post_board_information__28nF0
        date_tag = row.find('span', class_='post_board_information__28nF0')
        pub_date = date_tag.get_text().strip() if date_tag else "날짜 없음"

        items.append({
            'title': title,
            'link': full_link,
            'author': author,
            'pubDate': pub_date
        })

        print(f"📄 [{pub_date}] {title}")
        print(f"   👤 작성자: {author}")
        print(f"   🔗 링크: {full_link}\n")

    # 저장
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    if items:
        # === RSS 생성 ===
        with open(f"{OUTPUT_DIR}/feed.xml", "w", encoding="utf-8") as f:
            now = time.strftime("%a, %d %b %Y %H:%M:%S +0900")
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write('<rss version="2.0">\n')
            f.write('  <channel>\n')
            f.write('    <title>SD Gundam G Generation Eternal - 공식 공지사항</title>\n')
            f.write(f'    <link>{TARGET_URL}</link>\n')
            f.write(f'    <lastBuildDate>{now}</lastBuildDate>\n')
            f.write('    <description>공식 공지 게시판(board/5)의 모든 글을 크롤링한 피드입니다.</description>\n')

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

        # === HTML 생성 (index.html) ===
        with open(f"{OUTPUT_DIR}/index.html", "w", encoding="utf-8") as f:
            f.write("""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SD건담 G 제네레이션 이터널 - 공식 공지사항</title>
    <style>
        body { font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif; padding: 20px; background: #f5f5f7; margin: 0; }
        .container { max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 3px 10px rgba(0,0,0,0.08); }
        h1 { color: #d32f2f; text-align: center; margin-bottom: 10px; font-size: 1.8em; }
        .subtitle { text-align: center; color: #777; margin-bottom: 30px; font-size: 0.95em; }
        .updated { text-align: center; color: #999; margin-bottom: 30px; font-size: 0.9em; }
        .post-item { margin-bottom: 25px; padding: 20px; border-radius: 8px; background: #fafafa; border-left: 4px solid #d32f2f; transition: transform 0.2s; }
        .post-item:hover { transform: translateX(5px); background: #fff5f5; }
        .post-title { font-weight: 600; font-size: 1.15em; color: #1a1a1a; margin-bottom: 8px; line-height: 1.4; }
        .post-meta { color: #666; font-size: 0.88em; margin-bottom: 12px; display: flex; gap: 15px; }
        .post-meta span { display: flex; align-items: center; gap: 4px; }
        .post-link { display: inline-block; padding: 8px 20px; background: #d32f2f; color: white; text-decoration: none; border-radius: 20px; font-weight: 500; font-size: 0.95em; }
        .post-link:hover { background: #b71c1c; }
        @media (max-width: 768px) {
            .container { margin: 10px; padding: 20px; }
            h1 { font-size: 1.5em; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📢 SD건담 G 제네레이션 이터널</h1>
        <p class="subtitle">공식 공지사항 게시판 (board/5)</p>
        <p class="updated">최근 업데이트: """ + time.strftime("%Y-%m-%d %H:%M:%S") + """</p>
""")
            for item in items:
                f.write(f"""
        <div class="post-item">
            <div class="post-title">{item['title']}</div>
            <div class="post-meta">
                <span>👤 {item['author']}</span>
                <span>📅 {item['pubDate']}</span>
            </div>
            <a class="post-link" href="{item['link']}" target="_blank">📄 원문 보기</a>
        </div>""")

            f.write("""
    </div>
</body>
</html>""")

        print(f"\n🎉 성공! {len(items)}개의 공지글 저장 완료 → {OUTPUT_DIR}/index.html")
        print("🔗 GitHub Pages에 배포하면 자동 갱신 사이트 완성!")

    else:
        print("\n🚫 게시글을 하나도 찾지 못했습니다. 클래스명을 다시 확인해 주세요.")

except Exception as e:
    print(f"❌ 최종 에러 발생: {e}")
    raise e

finally:
    driver.quit()
