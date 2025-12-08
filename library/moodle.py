import requests

def buildSession(username: str, password: str) -> tuple[str, str, str]:
    url: str = 'https://moodle.unisantos.br'

    response: requests.Response = requests.get(url)
    session: requests.Session = requests.Session()
    
    login_page: str = session.get(response.url).text
    end: str = login_page.split('id="loginForm"')[1].split('action="')[1].split('"')[0]

    login_data: dict = {
        'UserName': rf'ADSERVER\{username}',
        'RawUserName': username,
        'Password': password, 
        'AuthMethod': 'FormsAuthentication',
    }
    
    saml: str = session.post(f"https://adfs.unisantos.br{end}", data=login_data).text.split('value="')[1].split('"')[0]
    auth: dict = {"RelayState": url, "SAMLResponse": saml}
    auth_response: requests.Response = session.post(fr"{url}/auth/saml2/sp/saml2-acs.php/moodle.unisantos.br", data=auth)

    sesskey: str = session.get(r"https://moodle.unisantos.br/my/").text.split('"sesskey":"')[1].split('"')[0]
    id: str = session.get(r"https://moodle.unisantos.br/user/profile.php").text.split('"contextInstanceId":')[1].split(',')[0]
    cookies: dict = str(session.cookies.get_dict()).replace("'", '"')

    return cookies, sesskey, id