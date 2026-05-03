import requests

GET_WEBHOOK = "https://primary-production-fb02.up.railway.app/webhook/acessar-arvore"
POST_WEBHOOK = "https://primary-production-fb02.up.railway.app/webhook/editar-arvore"

def get_tree():
    try:
        response = requests.get(GET_WEBHOOK, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to fetch family tree: {str(e)}")

def update_tree(data):
    try:
        response = requests.post(POST_WEBHOOK, json=data, timeout=10)
        response.raise_for_status()
        try:
            return response.json()
        except ValueError:
            return {"status": "success", "message": response.text}
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to update family tree: {str(e)}")
