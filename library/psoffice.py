import os, requests
from bs4 import BeautifulSoup

def extract_table_data(html_content: str) -> list[dict]:
    soup = BeautifulSoup(html_content, 'html.parser')

    thead = soup.find('thead')
    header_cells = thead.find_all('th')

    column_titles = []
    for th in header_cells[1:]:
        a_tag = th.find('a')
        if a_tag:
            day_text = a_tag.contents[0].strip()
            date_div = a_tag.find('div', class_='dataLinkDia')
            date_text = date_div.text.strip() if date_div else ''
            full_title = f'{day_text} {date_text}'
            column_titles.append(full_title)
        else:
            text = th.get_text(strip=True)
            if text:
                column_titles.append(text)

    tbody = soup.find('tbody')
    rows = tbody.find_all('tr')

    data = []
    for row in rows:
        row_dict = {}
        td_activity = row.find('td')
        if td_activity:
            aloc_div = td_activity.find('span', class_='ativTitulo')
            if aloc_div:
                aloc_text = aloc_div.get_text(separator=' ', strip=True)
                row_dict['Activity'] = aloc_text
            else:
                row_dict['Activity'] = ''
        else:
            row_dict['Activity'] = ''
        
        tds = row.find_all('td')[1:]

        num_day_columns = len(column_titles) - 2
        for i in range(num_day_columns):
            td = tds[i] if i < len(tds) else None
            val = ''
            if td:
                input_box = td.find('input', type='text')
                if input_box and input_box.has_attr('value'):
                    val = input_box['value']
            row_dict[column_titles[i]] = val
        
        total_td_idx = num_day_columns
        total_val = ''
        if total_td_idx < len(tds):
            total_input = tds[total_td_idx].find('input', type='text')
            if total_input and total_input.has_attr('value'):
                total_val = total_input['value']
        row_dict['Total'] = total_val
        
        ept_td_idx = num_day_columns + 1
        ept_val = ''
        if ept_td_idx < len(tds):
            ept_input = tds[ept_td_idx].find('input', type='text')
            if ept_input and ept_input.has_attr('value'):
                ept_val = ept_input['value']
        row_dict['EPT'] = ept_val

        data.append(row_dict)

    return data

def get_week(username: str, password: str) -> dict:
    s: requests.Session = requests.Session()
    
    login_url: str = 'https://psofficeapp.com.br/mosten/core/util/login.do'
    login_headers: dict = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6,el;q=0.5',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://psofficeapp.com.br',
        'Referer': 'https://psofficeapp.com.br/mosten/core/util/login.do',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0',
        'sec-ch-ua': '"Chromium";v="142", "Microsoft Edge";v="142", "Not_A Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
    }
    
    login_payload: dict = {
        'LoginName': username,
        'Password': password,
        'Remember': 'Y',
        'button_processLogin': 'Entrar',
        'dbContext': 'default',
        'processLogin_params': 'state%253DprocessLogin',
        'processLogin_encoding': 'u',
    }

    login_resp: requests.Response = s.post(login_url, headers=login_headers, data=login_payload)
    login_resp.raise_for_status()

    report_url: str = r'https://psofficeapp.com.br/mosten/psoffice/horas/horasnew.do?controller=com.mcfox.cron.controller.HorasNewController&state=Select&_sctx=2666266221961328081&_mn_cdg=horasminha&_nm_ctx=minhaPagina&tela=1'
    report_resp: requests.Response = s.get(report_url)

    report_resp.raise_for_status()
    return extract_table_data(report_resp.text.replace("\n", "").replace("\t", ""))


if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv(override=True)
    
    from pprint import pprint
    pprint(get_week(os.environ.get('PSO_LOGIN'), os.environ.get('PSO_PASS')))