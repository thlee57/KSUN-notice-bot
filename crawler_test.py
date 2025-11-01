import requests
from bs4 import BeautifulSoup

# TODO 1: 이 주소를 실제 학교 공지사항 게시판 주소로 바꿔주세요!
url = 'https://www.kunsan.ac.kr/board/list.kunsan?boardId=BBS_0000008&menuCd=DOM_000000105001001000&contentsSid=211&cpath=' 

# TODO 2: 이 선택자는 잠시 후에 찾아서 채울 예정입니다.
selector = '#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a' 

try:
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(res.text, "lxml")
    
    # CSS 선택자로 가장 최신 글 제목 요소(element)를 하나만 찾기
    latest_post_element = soup.select_one(selector)
    
    # 요소가 성공적으로 찾아졌는지 확인
    if latest_post_element:
        # 요소에서 순수한 텍스트(제목)만 추출
        title = latest_post_element.get_text(strip=True)
        print("✅ 크롤링 성공!")
        print(f"가장 최신 공지사항 제목: {title}")
    else:
        print("❌ 요소를 찾지 못했습니다. CSS 선택자가 올바른지 확인해주세요.")

except Exception as e:
    print(f"오류가 발생했습니다: {e}")