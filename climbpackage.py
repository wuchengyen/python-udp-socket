import requests
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO


session = requests.Session()
# 建立 session 保持 cookie 狀態
url = "https://eservice.7-11.com.tw/e-tracking/search.aspx"
headers = {
    "User-Agent": "Mozilla/5.0"
}

# 頁面 URL
url = "https://eservice.7-11.com.tw/e-tracking/search.aspx"
headers = {
    "User-Agent": "Mozilla/5.0"
}

# 取得頁面與驗證碼
response = session.get(url, headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')

# 抓取 __VIEWSTATE 等隱藏欄位 (必要)
viewstate = soup.select_one("input[name='__VIEWSTATE']")["value"]
eventvalidation = soup.select_one("input[name='__EVENTVALIDATION']")["value"]
viewstategenerator = soup.select_one("input[name='__VIEWSTATEGENERATOR']")["value"]

# 抓取驗證碼圖片
captcha_img_url = "https://eservice.7-11.com.tw/e-tracking/ImageDraw.aspx"
captcha_response = session.get(captcha_img_url, headers=headers)

# 顯示驗證碼讓使用者輸入
image = Image.open(BytesIO(captcha_response.content))
image.show()

# 使用者手動輸入驗證碼
captcha_text = input("請輸入驗證碼：")

# 查詢參數 (包裹代碼請自行更換)
post_data = {
    '__VIEWSTATE': viewstate,
    '__VIEWSTATEGENERATOR': viewstategenerator,
    '__EVENTVALIDATION': eventvalidation,
    'txtItemNo': 'F72753672930',  # 包裹編號
    'txtChkNumber': captcha_text,  # 驗證碼
    'btnQuery': '查詢'
}

# 送出查詢
result = session.post(url, data=post_data, headers=headers)

# 解析結果
result_soup = BeautifulSoup(result.text, 'html.parser')
tracking_info = result_soup.find('table', {'id': 'gvResult'})

if tracking_info:
    print("包裹運送狀況：")
    rows = tracking_info.find_all('tr')
    for row in rows:
        cols = row.find_all(['th', 'td'])
        print(" | ".join(col.get_text(strip=True) for col in cols))
else:
    print("查無資料或驗證碼錯誤。")