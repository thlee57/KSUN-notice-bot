import asyncio
import json
import logging
import requests
import threading
import os

from bs4 import BeautifulSoup
from urllib.parse import urljoin
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, 
    CommandHandler, 
    ContextTypes, 
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

MAIN_MENU, SELECTING_FACULTY, SELECTING_DEPARTMENT, DELETING_KEYWORD, SUBSCRIBE_MENU, KEYWORD_MENU, AWAITING_KEYWORD, = range(7)


# 로깅 설정 
logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler = logging.FileHandler('bot.log', encoding='utf-8')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)


# 설정 정보
MY_TOKEN = os.getenv("MY_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

BOARDS = {
    '공지사항': {
        'url': 'https://www.kunsan.ac.kr/board/list.kunsan?boardId=BBS_0000008&menuCd=DOM_000000105001001000&contentsSid=211&cpath=',
        'selector': '#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'
    },
    '학사/장학': {
        'url': 'https://www.kunsan.ac.kr/board/list.kunsan?boardId=BBS_0000009&menuCd=DOM_000000105001002000&contentsSid=212&cpath=',
        'selector': '#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'
    },
    '채용/모집/공고': {
        'url': 'https://www.kunsan.ac.kr/board/list.kunsan?boardId=BBS_0000010&menuCd=DOM_000000105001003000&contentsSid=213&cpath=',
        'selector': '#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'
    }
}

DEPARTMENTS = {
    '컴퓨터소프트웨어특성화대학': {
        '컴퓨터정보공학과': {'url': 'https://www.kunsan.ac.kr/cie/board/list.kunsan?boardId=BBS_0000758&menuCd=DOM_000011204001000000&contentsSid=4535&cpath=%2Fcie',
                     'selector': '#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'},
        '인공지능융합학과': {'url': 'https://www.kunsan.ac.kr/ai/board/list.kunsan?boardId=BBS_0000368&menuCd=DOM_000012505001000000&contentsSid=6143&cpath=%2Fai',
                     'selector': '#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'},
        '임베디드소프트웨어학과': {'url': 'https://www.kunsan.ac.kr/car/board/list.kunsan?boardId=BBS_0000334&menuCd=DOM_000008009001000000&contentsSid=5212&cpath=%2Fcar',
                     'selector': '#content > div.bbs_list01 > table > tbody > tr:nth-child(6) > td.tit > a'},
        '소프트웨어학과': {'url': 'https://www.kunsan.ac.kr/sw/board/list.kunsan?boardId=BBS_0000442&menuCd=DOM_000009605001000000&contentsSid=2976&cpath=%2Fsw',
                     'selector': '#content > div.bbs_list01 > table > tbody > tr:nth-child(3) > td.tit > a'},
        'IT융합통신공학과': {'url': 'https://www.kunsan.ac.kr/radio/board/list.kunsan?boardId=BBS_0000340&menuCd=DOM_000008104001000000&contentsSid=2656&cpath=%2Fradio',
                     'selector': '#content > div.bbs_list01 > table > tbody > tr:nth-child(5) > td.tit > a'},
    },
    '해양·바이오특성화대학': {
        '생명과학과': {'url': 'https://www.kunsan.ac.kr/biology/board/list.kunsan?boardId=BBS_0000649&menuCd=DOM_000007005007000000&contentsSid=3822&cpath=%2Fbiology',
                  'selector': '#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'},
        '해양수산공공인재학과': {'url': 'https://www.kunsan.ac.kr/marine/board/list.kunsan?boardId=BBS_0000395&menuCd=DOM_000008905001000000&contentsSid=2840&cpath=%2Fmarine',
                  'selector': '#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'},
        '해양생명과학과': {'url': 'https://www.kunsan.ac.kr/aquaculture/board/list.kunsan?boardId=BBS_0001228&menuCd=DOM_000009305010000000&contentsSid=7533&cpath=%2Faquaculture',
                  'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'},
        '해양생물자원학과': {'url': 'https://www.kunsan.ac.kr/mbiotec/board/list.kunsan?boardId=BBS_0000407&menuCd=DOM_000009105001000000&contentsSid=2878&cpath=%2Fmbiotec',
                  'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'},
        '수산생명의학과': {'url': 'https://www.kunsan.ac.kr/dalm/board/list.kunsan?boardId=BBS_0000414&menuCd=DOM_000009205001000000&contentsSid=2898&cpath=%2Fdalm',
                  'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'},
        '식품영양학과': {'url': 'https://www.kunsan.ac.kr/foodnutr/board/list.kunsan?boardId=BBS_0000314&menuCd=DOM_000007705001000000&contentsSid=2567&cpath=%2Ffoodnutr',
                  'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'},
        '기관공학과': {'url': 'https://www.kunsan.ac.kr/marineengineering/board/list.kunsan?boardId=BBS_0000427&menuCd=DOM_000009405001000000&contentsSid=2934&cpath=%2Fmarineengineering',
                  'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'},
        '식품생명공학과': {'url': 'https://www.kunsan.ac.kr/foodscience/board/list.kunsan?boardId=BBS_0000320&menuCd=DOM_000007805001000000&contentsSid=2590&cpath=%2Ffoodscience',
                  'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'}
     },
     '경영특성화대학': {
        '경영학부': {'url':'https://www.kunsan.ac.kr/business/board/list.kunsan?boardId=BBS_0000188&menuCd=DOM_000006306001000000&contentsSid=2210&cpath=%2Fbusiness',
                  'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'},
        '국제물류학과': {'url':'https://www.kunsan.ac.kr/logistics/board/list.kunsan?boardId=BBS_0000212&menuCd=DOM_000006605001000000&contentsSid=2277&cpath=%2Flogistics',
                   'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'},  
        '무역학과': {'url':'https://www.kunsan.ac.kr/trade/board/list.kunsan?boardId=BBS_0000178&menuCd=DOM_000006205001000000&contentsSid=2177&cpath=%2Ftrade',
                 'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'},  
        '회계학부': {'url':'https://www.kunsan.ac.kr/accounting/board/list.kunsan?boardId=BBS_0000195&menuCd=DOM_000006405001000000&contentsSid=2231&cpath=%2Faccounting',
                 'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'},  
        '금융부동산경제학과': {'url':'https://www.kunsan.ac.kr/economics/board/list.kunsan?boardId=BBS_0000170&menuCd=DOM_000006105001000000&contentsSid=2151&cpath=%2Feconomics',
                      'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'},  
        '벤처창업학과': {'url':'https://www.kunsan.ac.kr/startup/board/list.kunsan?boardId=BBS_0000434&menuCd=DOM_000009505001000000&contentsSid=2953&cpath=%2Fstartup',
                   'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'},   
     },
    '자율전공대학': {
        '자율전공학부': {'url':'https://www.kunsan.ac.kr/CLS/board/list.kunsan?boardId=BBS_0001082&menuCd=DOM_000012610004000000&contentsSid=6429&cpath=%2FCLS',
                   'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'},  
        '미술학과': {'url':'https://www.kunsan.ac.kr/finearts/board/list.kunsan?boardId=BBS_0000119&menuCd=DOM_000004705001000000&contentsSid=1646&cpath=%2Ffinearts',
                 'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'},  
        '음악과': {'url':'https://www.kunsan.ac.kr/music/board/list.kunsan?boardId=BBS_0000147&menuCd=DOM_000004905001000000&contentsSid=1706&cpath=%2Fmusic',
                'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'},  
        '조선공학과': {'url':'https://www.kunsan.ac.kr/naoe/board/list.kunsan?boardId=BBS_0000382&menuCd=DOM_000008704001000000&contentsSid=2797&cpath=%2Fnaoe',
                  'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'},  
        '글로벌융합학부': {'url':'https://www.kunsan.ac.kr/board/list.kunsan?boardId=BBS_0001206&menuCd=&contentsSid=7396&cpath=',
                    'selector':'#content > div.bbs_list01 > table > tbody > tr > td'},  
     },
    '융합과학공학대학': {
        '전자공학과': {'url':'https://www.kunsan.ac.kr/electronic/board/list.kunsan?boardId=BBS_0000389&menuCd=DOM_000008805001000000&contentsSid=2821&cpath=%2Felectronic',
                  'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'},
        '전기공학과': {'url':'https://www.kunsan.ac.kr/electrical/board/list.kunsan?boardId=BBS_0000325&menuCd=DOM_000007904001000000&contentsSid=2605&cpath=%2Felectrical',
                  'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'},
        '신소재공학과': {'url':'https://www.kunsan.ac.kr/mse/board/list.kunsan?boardId=BBS_0000359&menuCd=DOM_000008404001000000&contentsSid=2723&cpath=%2Fmse',
                   'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'},
        '화학공학과': {'url':'https://www.kunsan.ac.kr/nanochemeng/board/list.kunsan?boardId=BBS_0000362&menuCd=DOM_000008505001000000&contentsSid=2740&cpath=%2Fnanochemeng',
                  'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'},
        '환경공학과': {'url':'https://www.kunsan.ac.kr/environment/board/list.kunsan?boardId=BBS_0000354&menuCd=DOM_000008305001000000&contentsSid=2699&cpath=%2Fenvironment',
                  'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'},
        '토목공학과': {'url':'https://www.kunsan.ac.kr/gscivil/board/list.kunsan?boardId=BBS_0000347&menuCd=DOM_000008205001000000&contentsSid=2681&cpath=%2Fgscivil',
                  'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'},
        '해양건설공학과': {'url':'https://www.kunsan.ac.kr/constructionengineering/index.kunsan',
                    'selector':'#content > div.m_con.main04 > div > div > div > div > ul > li > a'},
        '첨단과학기술학부': {'url':'https://www.kunsan.ac.kr/cdscience/board/list.kunsan?boardId=BBS_0001103&menuCd=DOM_000013106001000000&contentsSid=6638&cpath=%2Fcdscience',
                     'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'},
        '수학과': {'url':'https://www.kunsan.ac.kr/math/board/list.kunsan?boardId=BBS_0000249&menuCd=DOM_000007104001000000&contentsSid=2387&cpath=%2Fmath',
                'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'},
     },
    '인문콘텐츠융합대학': {
        '국어국문학과': {'url':'https://www.kunsan.ac.kr/korean/board/list.kunsan?boardId=BBS_0000462&menuCd=DOM_000001111001000000&contentsSid=5204&cpath=%2Fkorean',
                   'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(3) > td.tit > a'},
        '영어영문학과': {'url':'https://www.kunsan.ac.kr/knuenglish/board/list.kunsan?boardId=BBS_0000080&menuCd=DOM_000004403001000000&contentsSid=1529&cpath=%2Fknuenglish',
                   'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'},
        '일어일문학과': {'url':'https://www.kunsan.ac.kr/japanese/board/list.kunsan?boardId=BBS_0000096&menuCd=DOM_000005805001000000&contentsSid=2079&cpath=%2Fjapanese',
                   'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'},
        '중어중문학과': {'url':'https://www.kunsan.ac.kr/chinese/board/list.kunsan?boardId=BBS_0001069&menuCd=DOM_000005909001000000&contentsSid=6301&cpath=%2Fchinese',
                   'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'},
        '역사학과': {'url':'https://www.kunsan.ac.kr/history/board/list.kunsan?boardId=BBS_0000108&menuCd=DOM_000004503001000000&contentsSid=1564&cpath=%2Fhistory',
                 'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'},
        '철학과': {'url':'https://www.kunsan.ac.kr/philosophy/board/list.kunsan?boardId=BBS_0000129&menuCd=DOM_000004605001000000&contentsSid=1618&cpath=%2Fphilosophy',
                'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'},
        '교직과': {'url':'https://www.kunsan.ac.kr/teaching/board/list.kunsan?boardId=BBS_0000220&menuCd=DOM_000006705001000000&contentsSid=2298&cpath=%2Fteaching',
                'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'},
     },
    'ICC특성화대학부': {
        '미디어문화학부': {'url':'https://www.kunsan.ac.kr/mediaculture/board/list.kunsan?boardId=BBS_0000766&menuCd=DOM_000005711001000000&contentsSid=4617&cpath=%2Fmediaculture',
                    'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(2) > td.tit > a'},
        '아동학부': {'url':'https://www.kunsan.ac.kr/child_family/board/list.kunsan?boardId=BBS_0000262&menuCd=DOM_000007305001000000&contentsSid=2422&cpath=%2Fchild_family',
                 'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'},
        '사회복지학부': {'url':'https://www.kunsan.ac.kr/nkssw/board/list.kunsan?boardId=BBS_0000161&menuCd=DOM_000005104001000000&contentsSid=1770&cpath=%2Fnkssw',
                   'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'},
        '법행정경찰학부': {'url':'https://www.kunsan.ac.kr/LPAP/board/list.kunsan?boardId=BBS_0001010&menuCd=DOM_000012305001000000&contentsSid=6038&cpath=%2FLPAP',
                    'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(2) > td.tit > a'},
        '간호학부': {'url':'https://www.kunsan.ac.kr/nursing/board/list.kunsan?boardId=BBS_0000305&menuCd=DOM_000007605001000000&contentsSid=2536&cpath=%2Fnursing',
                 'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'},
        '체육학부': {'url':'https://www.kunsan.ac.kr/ksports/board/list.kunsan?boardId=BBS_0001038&menuCd=DOM_000007505007000000&contentsSid=6177&cpath=%2Fksports',
                 'selector':'#content > div.bbs_list01 > table > tbody > tr > td.tit > a'},
        '산업디자인학부': {'url':'https://www.kunsan.ac.kr/kssandi/board/list.kunsan?boardId=BBS_0001096&menuCd=DOM_000006005009000000&contentsSid=6557&cpath=%2Fkssandi',
                    'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'},
        '의류학부': {'url':'https://www.kunsan.ac.kr/clothing/board/list.kunsan?boardId=BBS_0000270&menuCd=DOM_000007409001000000&contentsSid=6190&cpath=%2Fclothing',
                 'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'},
        '해양경찰학부': {'url':'https://www.kunsan.ac.kr/mpolice/board/list.kunsan?boardId=BBS_0000400&menuCd=DOM_000009005001000000&contentsSid=2857&cpath=%2Fmpolice',
                   'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(2) > td.tit > a'},
        '기계공학부': {'url':'https://www.kunsan.ac.kr/kunsanwheel/board/list.kunsan?boardId=BBS_0000456&menuCd=DOM_000009905001000000&contentsSid=3032&cpath=%2Fkunsanwheel',
                  'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(3) > td.tit > a'},
        '건축공학부': {'url':'https://architecture.kunsan.ac.kr/archives/category/news',
                  'selector':'#post-10425 > header > h1 > a'},
        '공간디자인융합기술학부': {'url':'https://www.kunsan.ac.kr/interiorhousing/board/list.kunsan?boardId=BBS_0000449&menuCd=DOM_000009705001000000&contentsSid=2997&cpath=%2Finteriorhousing',
                        'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'},
        '이차전지·에너지학부': {'url':'https://www.kunsan.ac.kr/energy/board/list.kunsan?boardId=BBS_0001099&menuCd=DOM_000013005001000000&contentsSid=6590&cpath=%2Fenergy',
                       'selector':'#content > div.bbs_list01 > table > tbody > tr:nth-child(1) > td.tit > a'},
    }

}



SUBSCRIPTION_FILE = 'subscriptions.json'
LAST_POSTS_FILE = 'last_posts.json'
KEYWORD_FILE = 'keywords.json'
DEPARTMENT_FILE = 'departments.json'

# 파일 관리 함수 
def load_json(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f: return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError): return {}

def save_json(filename, data):
    with open(filename, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=4)

# 웹 크롤링 함수
def get_latest_notice(url, selector):
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(res.text, "lxml")
        post = soup.select_one(selector)
        if not post: return None, None
        title = post.get_text(strip=True)
        link = urljoin(url, post['href'])
        return title, link
    except Exception as e:
        logger.error(f"크롤링 오류 ({url}): {e}")
        return None, None
    
# 핸들러 & 서버 시작 함수
class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/health"):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"ok")
        else:
            self.send_response(404)
            self.end_headers()

    # 불필요한 로그 억제 (선택)
    def log_message(self, format, *args):
        return

def start_health_server():
    port = int(os.getenv("PORT", "8080"))
    server = HTTPServer(("0.0.0.0", port), _HealthHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()


# 텔레그램 명령어 처리 함수
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("소속 학부/학과 공지설정", callback_data='set_department')],
        [InlineKeyboardButton("게시판 구독 관리", callback_data='menu_subscribe')],
        [InlineKeyboardButton("키워드 설정", callback_data='menu_keyword')],
        [InlineKeyboardButton("최신 공지 확인", callback_data='check_now')],
        [InlineKeyboardButton("내 알림설정", callback_data='my_settings')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    
    if update.message:
        await update.message.reply_text(
            "안녕하세요! 👋\n국립군산대학교 맞춤형 공지 알림 봇입니다.\n"
            "아래 메뉴에서 원하는 기능을 선택하세요.",
            reply_markup=reply_markup
        )
    
    else:
        await update.callback_query.edit_message_text(
            "메인 메뉴입니다. 원하는 기능을 선택하세요.",
            reply_markup=reply_markup
        )
    
    return MAIN_MENU


# 백그라운드 자동 알림 함수 
async def auto_check_notices(context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    last_posts = load_json(LAST_POSTS_FILE)
    subscriptions = load_json(SUBSCRIPTION_FILE)
    keywords_db = load_json(KEYWORD_FILE)
    departments_db = load_json(DEPARTMENT_FILE) 

    
    for board_name, board_info in BOARDS.items():
        url, selector = board_info['url'], board_info['selector']
        new_title, new_link = get_latest_notice(url, selector)
        if not new_title: continue

        old_title, _ = last_posts.get(board_name, (None, None))

        if new_title != old_title:
            logger.info(f"[{board_name}] 새 공지 발견! -> {new_title}")
            last_posts[board_name] = (new_title, new_link) 
            
            message = f"🔔 [{board_name}] 새 글!\n\n<a href='{new_link}'>{new_title}</a>"

            
            for chat_id, user_subs in subscriptions.items():
                if board_name in user_subs:
                    user_keywords = keywords_db.get(chat_id, [])
                    if not user_keywords or any(k in new_title for k in user_keywords):
                        try: await bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
                        except Exception as e: logger.error(f"{chat_id} (전체공지) 전송 실패: {e}")
    
    
    for chat_id, user_dept_info in departments_db.items():
        if not isinstance(user_dept_info, dict): continue 
        faculty_name = user_dept_info.get('faculty')
        major_name = user_dept_info.get('major')

        if not faculty_name or not major_name: continue

       
        try:
            dept_info = DEPARTMENTS[faculty_name][major_name]
            dept_url = dept_info['url']
            dept_selector = dept_info['selector']
        except KeyError:
            logger.warning(f"DEPARTMENTS 딕셔너리에서 {faculty_name} - {major_name} 정보를 찾을 수 없음.")
            continue
            
        # 해당 학과 게시판 크롤링
        dept_new_title, dept_new_link = get_latest_notice(dept_url, dept_selector)
        if not dept_new_title: continue

        # last_posts.json에서 이 학과의 마지막 글 확인 (학과 이름으로 저장)
        dept_key = f"dept_{major_name}" # 고유 키 생성 
        dept_old_title, _ = last_posts.get(dept_key, (None, None))

        if dept_new_title != dept_old_title:
            logger.info(f"[{major_name}] 새 학과 공지 발견! -> {dept_new_title}")
            last_posts[dept_key] = (dept_new_title, dept_new_link) # 최신 글로 업데이트 저장
            
            # 학과 공지 알림 메시지 생성
            dept_message = f"🎓 [{major_name}] 새 학과 공지!\n\n<a href='{dept_new_link}'>{dept_new_title}</a>"
            
            # 해당 학과를 설정한 사용자에게 알림 발송 (키워드 필터링 적용)
            user_keywords = keywords_db.get(chat_id, [])
            if not user_keywords or any(k in dept_new_title for k in user_keywords):
                try: await bot.send_message(chat_id=chat_id, text=dept_message, parse_mode='HTML')
                except Exception as e: logger.error(f"{chat_id} (학과공지) 전송 실패: {e}")

    save_json(LAST_POSTS_FILE, last_posts)


async def check_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  
    
    chat_id = str(query.message.chat_id)
    
    subscriptions = load_json(SUBSCRIPTION_FILE)
    keywords_db = load_json(KEYWORD_FILE)
    departments_db = load_json(DEPARTMENT_FILE)

    user_subs = subscriptions.get(chat_id, [])
    user_dept_info = departments_db.get(chat_id)

    if not user_subs:
        await query.message.reply_text("구독 중인 게시판이 없습니다. 메인 메뉴에서 [게시판 구독 관리]를 먼저 설정해주세요.")
        await asyncio.sleep(2)
        await start(update, context)
        return MAIN_MENU

    await query.message.reply_text("구독 중인 게시판의 최신 공지를 확인중입니다..")
    found_any = False 

    for board_name in user_subs:
        board_info = BOARDS.get(board_name)
        if not board_info:
            continue

        title, link = get_latest_notice(board_info['url'], board_info['selector'])

        if title == "NETWORK_ERROR": # 네트워크 오류
             await context.bot.send_message(chat_id=chat_id, text=f"⚠️ [{board_name}] 서버 접속 실패!")
             continue
        
        if title and link:
            message = f"🔔 [{board_name}] 현재 최신 글\n\n<a href='{link}'>{title}</a>"
            await context.bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
            found_any = True

    if isinstance(user_dept_info, dict): 
        faculty_name = user_dept_info.get('faculty')
        major_name = user_dept_info.get('major')

        if faculty_name and major_name: 
            try:
                dept_info = DEPARTMENTS[faculty_name][major_name]
                dept_url = dept_info['url']
                dept_selector = dept_info['selector']

                title, link = get_latest_notice(dept_url, dept_selector)

                if title == "NETWORK_ERROR": 
                     await context.bot.send_message(chat_id=chat_id, text=f"⚠️ [{major_name}] 서버 접속 실패!")
                     
                elif title and link:
                    message = f"🎓 [{major_name}] 현재 최신 글\n\n<a href='{link}'>{title}</a>"
                    await context.bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
                    found_any = True

            except KeyError: # DEPARTMENTS 딕셔너리에 학과 정보가 없는 경우
                logger.warning(f"{chat_id}: 설정된 학과 정보 ({faculty_name}-{major_name})를 DEPARTMENTS에서 찾을 수 없음.")
            except Exception as e: # 기타 크롤링 오류
                 logger.error(f"{chat_id}: 학과 공지 확인 중 오류: {e}")

    # --- 3. 아무 공지도 못 찾았을 경우 메시지 ---
    if not found_any:
        await query.message.reply_text(f"현재 설정된 게시판에서 최신 공지를 가져오는 데 실패했거나, 게시판에 글이 없습니다.")

    await asyncio.sleep(2)
    await start(update, context)

    return MAIN_MENU

# --- 봇 시작 및 스케줄링 ---
async def post_init(application: Application):
    application.job_queue.run_repeating(auto_check_notices, interval=600, first=10, data=load_json(LAST_POSTS_FILE))
    await application.bot.send_message(chat_id=ADMIN_CHAT_ID, text="✅알림봇을 시작합니다. /start 버튼을 눌러주세요.")
    logger.info("봇이 성공적으로 시작되었습니다.")

# 메인 메뉴 버튼 처리
async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = str(query.message.chat_id)

    if data == 'menu_subscribe':
        # --- 게시판 구독 버튼 생성 로직 수정 ---
        db = load_json(SUBSCRIPTION_FILE)
        user_subs = db.get(chat_id, [])
        
        keyboard = []
        for board_name in BOARDS.keys():
            # 구독 중이면 체크 표시, 아니면 빈 네모 표시
            prefix = "✅ " if board_name in user_subs else "⬜️ "
            keyboard.append([InlineKeyboardButton(prefix + board_name, callback_data=f"sub_{board_name}")])
            
        keyboard.append([InlineKeyboardButton("↩️ 메인 메뉴로", callback_data='sub_back')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text="[게시판 구독 관리]\n구독 상태를 변경할 게시판을 선택하세요:", reply_markup=reply_markup)
        
        return SUBSCRIBE_MENU

    elif data == 'menu_keyword':
        # 키워드 관리 버튼을 보여줌
        keyboard = [
            [InlineKeyboardButton("키워드 추가", callback_data='key_add')],
            [InlineKeyboardButton("키워드 삭제", callback_data='key_remove')],
            [InlineKeyboardButton("↩️ 메인 메뉴로", callback_data='key_back')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text="[키워드 설정]\n원하는 작업을 선택하세요:", reply_markup=reply_markup)
        
        return KEYWORD_MENU 

    elif data == 'set_department':
        keyboard = []
        # DEPARTMENTS 딕셔너리에서 학부 이름 가져와 버튼 만들기
        for faculty_name in DEPARTMENTS.keys():
            keyboard.append([InlineKeyboardButton(faculty_name, callback_data=f"faculty_{faculty_name}")])
        keyboard.append([InlineKeyboardButton("↩️ 메인 메뉴로", callback_data='main_menu')]) # 콜백 데이터 통일
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text="소속 학부(대학)를 선택하세요:", reply_markup=reply_markup)
        return SELECTING_FACULTY # 상태를 '학부 선택 중'으로 변경

# 학부 선택 상태 처리
async def faculty_selection_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    logger.info(f"Faculty selection handler entered. Callback data: {query.data}") # 로그 추가

    if data == 'main_menu': # '메인 메뉴로' 버튼 처리
        logger.info("Going back to main menu...")
        await start(update, context) # 메인 메뉴 보여주기
        return MAIN_MENU

    elif data.startswith("faculty_"):
        faculty_name = data.split("_", 1)[1]
        logger.info(f"Faculty selected: {faculty_name}")
        # 사용자가 선택한 학부 이름을 임시로 저장 (학과 선택 시 사용)
        context.user_data['selected_faculty'] = faculty_name

        keyboard = []
        # 해당 학부의 학과 목록을 가져와 버튼으로 만듦
        try:
            majors = list(DEPARTMENTS[faculty_name].keys())
            for i in range(0, len(majors), 2): # 한 줄에 최대 2개씩 버튼 배치
                 row = [InlineKeyboardButton(m, callback_data=f"dept_{m}") for m in majors[i:i+2]]
                 keyboard.append(row)
        except KeyError:
             logger.error(f"DEPARTMENTS 딕셔너리에서 '{faculty_name}' 학부 정보를 찾을 수 없음.")
             await query.edit_message_text(text="오류: 학과 정보를 불러올 수 없습니다. 관리자에게 문의하세요.")
             await start(update, context) # 안전하게 메인 메뉴로
             return MAIN_MENU

        keyboard.append([InlineKeyboardButton("↩️ 학부 선택으로", callback_data='dept_back')]) # 뒤로가기 버튼
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            await query.edit_message_text(text=f"[{faculty_name}]\n소속 학과(부)를 선택하세요:", reply_markup=reply_markup)
        except Exception as e:
            logger.warning(f"학과 선택 메시지 수정 실패: {e}")
            # 메시지 수정 실패 시 새 메시지로 보내는 등의 예외 처리 추가 가능

        logger.info("Moving to department selection state.")
        return SELECTING_DEPARTMENT # 상태를 '학과 선택 중'으로 변경
    else:
         logger.warning(f"Unexpected callback data in faculty selection: {data}")
         await start(update, context) # 예상치 못한 입력 시 메인 메뉴로
         return MAIN_MENU

# 학과 선택 상태 처리
async def department_selection_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = str(query.message.chat_id)
    logger.info(f"Department selection handler entered. Callback data: {query.data}") # 로그 추가

    if data == 'dept_back': # '학부 선택으로' 버튼
        logger.info("Going back to faculty selection...")
        # 학부 선택 버튼 다시 보여주기 (main_menu_handler의 set_department 로직 재사용)
        keyboard = []
        for faculty_name in DEPARTMENTS.keys():
            keyboard.append([InlineKeyboardButton(faculty_name, callback_data=f"faculty_{faculty_name}")])
        keyboard.append([InlineKeyboardButton("↩️ 메인 메뉴로", callback_data='main_menu')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            await query.edit_message_text(text="소속 학부(대학)를 선택하세요:", reply_markup=reply_markup)
        except Exception as e:
            logger.warning(f"학부 선택 메시지 수정 실패: {e}")
        return SELECTING_FACULTY # 이전 상태(학부 선택)로 돌아가기

    elif data.startswith("dept_"):
        major_name = data.split("_", 1)[1]
        faculty_name = context.user_data.get('selected_faculty', '알 수 없음') # 임시 저장된 학부 이름 가져오기
        logger.info(f"Department selected: {major_name} (Faculty: {faculty_name})")

        db = load_json(DEPARTMENT_FILE)
        current_dept = db.get(chat_id)
        action_text = ""

        # 이미 설정된 학과를 다시 누르면 설정 해제 (토글 기능)
        if isinstance(current_dept, dict) and current_dept.get('major') == major_name:
             del db[chat_id]
             action_text = f"🗑️ '{major_name}' 학과 설정이 해제되었습니다."
             logger.info(f"{chat_id}: 학과 설정 해제 - {major_name}")
        else:
             db[chat_id] = {'faculty': faculty_name, 'major': major_name}
             action_text = f"✅ 학과가 '{major_name}'로 설정되었습니다."
             logger.info(f"{chat_id}: 학과 설정 완료 - {major_name}")

        save_json(DEPARTMENT_FILE, db)
        await query.answer(action_text, show_alert=True) # 팝업으로 결과 표시

        # 설정 변경 후 학과 선택 메뉴 버튼 새로고침 (선택 상태 표시)
        keyboard = []
        try:
            majors = list(DEPARTMENTS[faculty_name].keys())
            current_major = db.get(chat_id, {}).get('major') # 업데이트된 정보 다시 로드
            for i in range(0, len(majors), 2):
                 row = []
                 for m in majors[i:i+2]:
                      prefix = "✅ " if m == current_major else "⬜️ "
                      row.append(InlineKeyboardButton(prefix + m, callback_data=f"dept_{m}"))
                 keyboard.append(row)
        except KeyError: # 학부 정보가 없는 예외 처리
             logger.error(f"학과 버튼 재생성 실패: DEPARTMENTS에서 '{faculty_name}' 학부 정보를 찾을 수 없음.")
             await start(update, context) # 에러 시 메인 메뉴로
             return MAIN_MENU

        keyboard.append([InlineKeyboardButton("↩️ 학부 선택으로", callback_data='dept_back')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            # 버튼만 새로고침 시도
            await query.edit_message_reply_markup(reply_markup=reply_markup)
        except Exception as e:
             logger.warning(f"학과 선택 메뉴 버튼 새로고침 실패: {e}")
             # 새로고침 실패 시 메시지 자체를 수정할 수도 있음
             # await query.edit_message_text(text=f"[{faculty_name}]\n소속 학과(부)를 선택하세요:", reply_markup=reply_markup)

        return SELECTING_DEPARTMENT # 현재 상태 유지하며 버튼만 새로고침
    else:
        logger.warning(f"Unexpected callback data in department selection: {data}")
        await start(update, context) # 예상치 못한 입력 시 메인 메뉴로
        return MAIN_MENU

async def subscribe_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = str(query.message.chat_id)

    if data == 'sub_back':
        await start(update, context) # start 함수가 메인 메뉴 보여줌
        return MAIN_MENU
    
    elif data.startswith("sub_"):
        board_name = data.split("_", 1)[1]
        
        db = load_json(SUBSCRIPTION_FILE)
        user_subs = db.get(chat_id, [])
        
        action_text = "" # 팝업 메시지
        if board_name not in user_subs:
            user_subs.append(board_name)
            action_text = f"✅ '{board_name}' 구독 완료!"
        else:
            user_subs.remove(board_name)
            action_text = f"🗑️ '{board_name}' 구독 취소!"
            
        db[chat_id] = user_subs
        save_json(SUBSCRIPTION_FILE, db)
        await query.answer(text=action_text) # 상태 변경 팝업 알림

        # --- 버튼 목록 새로고침 로직 ---
        keyboard = []
        for name in BOARDS.keys():
            prefix = "✅ " if name in user_subs else "⬜️ "
            keyboard.append([InlineKeyboardButton(prefix + name, callback_data=f"sub_{name}")])
        keyboard.append([InlineKeyboardButton("↩️ 메인 메뉴로", callback_data='sub_back')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        # edit_message_reply_markup을 사용해 버튼만 업데이트 (더 부드러움)
        await query.edit_message_reply_markup(reply_markup=reply_markup)
        
        # 상태는 그대로 구독 메뉴 유지
        return SUBSCRIBE_MENU

# '내 설정 확인' 버튼 처리
async def my_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = str(query.message.chat_id)
    
    # --- 1. 내 구독 목록 보여주기 (기존 my_subscriptions 함수 로직) ---
    chat_id = str(query.message.chat_id)
    db_subs = load_json(SUBSCRIPTION_FILE)
    user_subs = db_subs.get(chat_id, [])

    if user_subs:
        sub_message = "현재 구독 중인 게시판:\n- " + "\n- ".join(user_subs)
    else:
        sub_message = "구독 중인 게시판이 없습니다."
    
    # 2. 내 키워드 목록 보여주기 (기존 my_keywords 함수 로직)
    db_keys = load_json(KEYWORD_FILE)
    user_keywords = db_keys.get(chat_id, [])

    if user_keywords:
        key_message = "현재 등록된 키워드:\n- " + "\n- ".join(user_keywords)
    else:
        key_message = "등록된 키워드가 없습니다."

    # 3. 내 학과 설정 정보 추가
    db_dept = load_json(DEPARTMENT_FILE)
    user_dept_info = db_dept.get(chat_id)
    
    if isinstance(user_dept_info, dict) and 'major' in user_dept_info:
        dept_message = f"설정된 학과: {user_dept_info['major']}"
    else:
        dept_message = "설정된 학과가 없습니다."

   
    full_message = f"⚙️ **내 알림 설정** ⚙️\n\n{sub_message}\n\n{key_message}\n\n{dept_message}"
    await query.edit_message_text(text=full_message, parse_mode='Markdown')
    await asyncio.sleep(3)
    await start(update, context)
    
    return MAIN_MENU 

    

async def keyword_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = str(query.message.chat_id) 

    if data == 'key_back':
        await start(update, context)
        return MAIN_MENU

    elif data == 'key_add':
        await query.edit_message_text(text="추가할 키워드를 입력하세요. (취소하려면 /start 입력)")
        return AWAITING_KEYWORD
    
    elif data == 'key_remove':
        # 🔽 --- 키워드 삭제 로직 변경 --- 🔽
        db = load_json(KEYWORD_FILE)
        user_keywords = db.get(chat_id, [])

        if not user_keywords:
            await query.edit_message_text(text="삭제할 키워드가 없습니다.")
            await asyncio.sleep(2)
            await start(update, context)
            return MAIN_MENU
        else:
            keyboard = []
            for keyword in user_keywords:
                # 각 키워드를 삭제 버튼으로 만듦 (콜백 데이터: 'delkey_키워드')
                keyboard.append([InlineKeyboardButton(f"🗑️ {keyword}", callback_data=f"delkey_{keyword}")])
            keyboard.append([InlineKeyboardButton("↩️ 키워드 메뉴로", callback_data='key_back_from_delete')]) # 뒤로가기 버튼 추가
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text="삭제할 키워드를 선택하세요:", reply_markup=reply_markup)
            
            return DELETING_KEYWORD
        
# (keyword_menu_handler 와 비슷한 위치에 추가)

# 키워드 삭제 버튼 클릭 처리
async def delete_keyword_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = str(query.message.chat_id)

    if data == 'key_back_from_delete':
         # 키워드 메뉴 버튼을 다시 보여줌 (keyword_menu_handler 호출 대신 직접 생성)
        keyboard = [
            [InlineKeyboardButton("키워드 추가", callback_data='key_add')],
            [InlineKeyboardButton("키워드 삭제", callback_data='key_remove')],
            [InlineKeyboardButton("↩️ 메인 메뉴로", callback_data='key_back')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text="[키워드 설정]\n원하는 작업을 선택하세요:", reply_markup=reply_markup)
        return KEYWORD_MENU

    elif data.startswith("delkey_"):
        keyword_to_delete = data.split("_", 1)[1]
        
        db = load_json(KEYWORD_FILE)
        user_keywords = db.get(chat_id, [])

        if keyword_to_delete in user_keywords:
            user_keywords.remove(keyword_to_delete)
            db[chat_id] = user_keywords
            save_json(KEYWORD_FILE, db)
            await query.answer(text=f"🗑️ '{keyword_to_delete}' 삭제 완료!")

            # 삭제 후 키워드 목록 버튼 다시 보여주기 (업데이트된 목록)
            if not user_keywords:
                 await query.edit_message_text(text="모든 키워드가 삭제되었습니다.")
                 await asyncio.sleep(2)
                 await start(update, context) # 메인 메뉴로
                 return MAIN_MENU
            else:
                keyboard = []
                for keyword in user_keywords:
                    keyboard.append([InlineKeyboardButton(f"🗑️ {keyword}", callback_data=f"delkey_{keyword}")])
                keyboard.append([InlineKeyboardButton("↩️ 키워드 메뉴로", callback_data='key_back_from_delete')])
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(text="삭제할 키워드를 선택하세요:", reply_markup=reply_markup)
                return DELETING_KEYWORD 

# 키워드 입력 대기 상태에서 텍스트를 받았을 때
async def save_keyword_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.message.chat_id)
    keyword = update.message.text
    
    # --- (기존 /addkeyword 명령어에 있던 로직 수행) ---
    db = load_json(KEYWORD_FILE)
    user_keywords = db.get(chat_id, [])
    if keyword not in user_keywords:
        user_keywords.append(keyword)
        db[chat_id] = user_keywords
        save_json(KEYWORD_FILE, db)
        await update.message.reply_text(f"✅ 키워드 '{keyword}'(이)가 추가되었습니다.")
    else:
        await update.message.reply_text(f"이미 등록된 키워드입니다: '{keyword}'")

    await start(update, context)
    return MAIN_MENU


# 봇 통계 확인 (관리자용)
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.chat_id) != ADMIN_CHAT_ID:
        await update.message.reply_text("권한이 없습니다.")
        return

    subs_db = load_json(SUBSCRIPTION_FILE)
    keys_db = load_json(KEYWORD_FILE)
    
    total_subscribers = len(subs_db)
    total_keywords = sum(len(k) for k in keys_db.values())

    # 게시판별 구독자 수 집계
    board_counts = {}
    for chat_id, boards in subs_db.items():
        for board in boards:
            board_counts[board] = board_counts.get(board, 0) + 1
    
    sorted_boards = sorted(board_counts.items(), key=lambda item: item[1], reverse=True)
    board_stats = "\n".join([f"- {board}: {count}명" for board, count in sorted_boards])
    if not board_stats:
        board_stats = "없음"

    message = (
        f"📊 **봇 통계** 📊\n\n"
        f"총 구독자 수: **{total_subscribers}명**\n"
        f"등록된 총 키워드 수: **{total_keywords}개**\n\n"
        f"**게시판별 구독자 수:**\n{board_stats}"
    )
    await update.message.reply_text(message, parse_mode='Markdown')

# 전체 공지 발송 (관리자용)
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.chat_id) != ADMIN_CHAT_ID:
        await update.message.reply_text("권한이 없습니다.")
        return

    if not context.args:
        await update.message.reply_text("보낼 메시지를 입력해주세요. 예: /broadcast 중요 공지입니다!")
        return

    message_to_send = " ".join(context.args)
    subs_db = load_json(SUBSCRIPTION_FILE)
    
    sent_count = 0
    for chat_id in subs_db.keys(): # 구독자 모두에게 발송
        try:
            await context.bot.send_message(chat_id=chat_id, text=f"📢 **관리자 공지** 📢\n\n{message_to_send}", parse_mode='Markdown')
            sent_count += 1
        except Exception as e:
            logger.error(f"Failed to send broadcast to {chat_id}: {e}")
    
    await update.message.reply_text(f"✅ {sent_count}명에게 공지를 발송했습니다.")






def main():
    logger.info("알림봇을 시작합니다.")
    application = Application.builder().token(MY_TOKEN).build()
    
    conv_handler = ConversationHandler(
        # 1. 진입점: /start 명령어로만 대화 시작
        entry_points=[CommandHandler("start", start)],
        
        # 2. 상태별 버튼/텍스트 처리
        states={
            # 2-1. 메인 메뉴 상태에서 받을 수 있는 입력
            MAIN_MENU: [
                CallbackQueryHandler(main_menu_handler, pattern='^menu_|^set_department'),
                CallbackQueryHandler(check_now, pattern='^check_now'),
                CallbackQueryHandler(my_settings, pattern='^my_settings'),
            ],
            # 2-2. 게시판 구독 메뉴 상태
            SUBSCRIBE_MENU: [
                CallbackQueryHandler(subscribe_menu_handler, pattern='^sub_')
            ],
            # 2-3. 키워드 메뉴 상태
            KEYWORD_MENU: [
                CallbackQueryHandler(keyword_menu_handler, pattern='^key_'),
                CallbackQueryHandler(delete_keyword_button_handler, pattern='^delkey_|^key_back_from_delete')
            ],
            # 2-4. 키워드 입력을 기다리는 상태
            AWAITING_KEYWORD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_keyword_handler)
            ],
            # 2-5. 키워드 삭제 버튼을 보여주는 상태
            DELETING_KEYWORD: [
                CallbackQueryHandler(delete_keyword_button_handler, pattern='^delkey_|^key_back_from_delete')
            ],
            # 2-6. 학부 선택을 기다리는 상태
            SELECTING_FACULTY: [
                CallbackQueryHandler(faculty_selection_handler, pattern='^faculty_|^main_menu')
            ],
            # 2-7. 학과 선택을 기다리는 상태
            SELECTING_DEPARTMENT: [
                CallbackQueryHandler(department_selection_handler, pattern='^dept_|^dept_back')
            ],
        },
        
        # 3. 예외 처리: 
        fallbacks=[CommandHandler("start", start)],
        # 대화 타임아웃 등 기타 설정
    )

    # 봇에 ConversationHandler를 등록 (기존 핸들러들 대신)
    application.add_handler(conv_handler)
    
    # 관리자용 명령어는 ConversationHandler 밖에 별도로 등록
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("broadcast", broadcast))

    # 봇 자동 실행 작업 등록
    application.post_init = post_init
    
    # 봇 실행
    application.run_polling()


if __name__ == "__main__":
    start_health_server()
    main()