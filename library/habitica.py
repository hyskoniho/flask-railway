import re
from datetime import datetime, timezone
from typing import List, Dict, Tuple, Optional, Any


def utc_now_iso_z() -> str:
    """Retorna timestamp UTC em formato ISO 8601 com sufixo Z."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_priority_from_line(line: str) -> float:
    """Extrai prioridade da linha da task no padrão do plugin Tasks."""
    if "🔺" in line:
        return 2.0
    if "⏫" in line:
        return 1.5
    if "🔼" in line:
        return 1.0
    return 0.1


def parse_date_from_line(line: str) -> Optional[str]:
    """Extrai a primeira data (YYYY-MM-DD) encontrada na linha."""
    date_match = re.search(r"\d{4}-\d{2}-\d{2}", line)
    return date_match.group(0) if date_match else None


def parse_tags_from_line(line: str) -> List[str]:
    """Extrai tags no formato #tag."""
    # Obsidian não aceita espaço em tag; internamente usamos espaço para manter
    # compatibilidade com tags do Habitica (ex.: "Check HP").
    return [tag.replace("-", " ") for tag in re.findall(r"#([\w-]+)", line)]


def normalize_tags_for_compare(tags: List[str]) -> List[str]:
    """Normaliza tags para comparação estável entre Obsidian e Habitica."""
    normalized = []
    for tag in tags:
        clean_tag = re.sub(r"\s+", " ", str(tag).replace("-", " ")).strip()
        if clean_tag:
            normalized.append(clean_tag)
    return sorted(normalized)


def parse_completed_from_line(line: str) -> bool:
    """Detecta conclusão por checkbox marcado ou data de conclusão."""
    checkbox_completed = re.search(r"- \[[xX]\]", line) is not None
    completed_date_match = re.search(r"✅\s*(\d{4}-\d{2}-\d{2})", line)
    return checkbox_completed or (completed_date_match is not None)


def clean_task_body(line: str) -> str:
    """Remove metadados da linha e retorna apenas o texto da task."""
    body = line
    body = re.sub(r"- \[[ xX]\]\s*", "", body)
    body = re.sub(r"TODO", "", body, flags=re.IGNORECASE)
    body = re.sub(r"📅\s*\d{4}-\d{2}-\d{2}", "", body)
    body = re.sub(r"[⏫🔼🔺]", "", body)
    body = re.sub(r"✅\s*\d{4}-\d{2}-\d{2}", "", body)
    body = re.sub(r"#([\w-]+)", "", body)
    return body.strip()


def parse_iso_date(date_value: str) -> datetime:
    """Converte datas ISO simples para datetime aceitando sufixo Z."""
    return datetime.fromisoformat(date_value.replace("Z", "+00:00"))


def compare_task_dates(d1: Optional[str], d2: Optional[str]) -> int:
    """Compara datas ISO; retorna 1 se d1>d2, -1 se d1<d2, 0 se empate."""
    if d1 and d2:
        dt1 = parse_iso_date(d1)
        dt2 = parse_iso_date(d2)
        if dt1 > dt2:
            return 1
        if dt1 < dt2:
            return -1
        return 0
    if d1 and not d2:
        return 1
    if d2 and not d1:
        return -1
    return 0


def parse_obsidian_tasks(obsidian: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Extrai tasks do dicionário Obsidian (caminho->conteúdo).
    Retorna lista de tasks no formato:
    {
        'body': str,
        'date': Optional[str],
        'createdAt': str,
        'priority': float,
        'completed': bool,
        'source': 'obsidian',
        'tags': List[str],
        'file_path': str,
        'raw_line': str
    }
    """
    tasks = []
    # Regex para linhas de task no formato do plugin Tasks: "- [ ] TODO ...", "- [x] TODO ..."
    task_line_re = re.compile(r"^- \[[ xX]\].*TODO.*", re.MULTILINE)

    for file_path, content in obsidian.items():
        lines = content.splitlines()
        for line in lines:
            if task_line_re.match(line):
                priority = parse_priority_from_line(line)
                date = parse_date_from_line(line)
                created_at = utc_now_iso_z()
                completed = parse_completed_from_line(line)
                tags = parse_tags_from_line(line)
                body = clean_task_body(line)

                task = {
                    "body": body,
                    "date": date,
                    "createdAt": created_at,
                    "priority": priority,
                    "completed": completed,
                    "source": "obsidian",
                    "tags": tags,
                    "file_path": file_path,
                    "raw_line": line,
                }
                tasks.append(task)
    return tasks


def parse_habitica_tasks(habitica: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normaliza as tasks do Habitica para o formato interno usado no matching.
    Retorna lista de tasks no formato:
    {
        'body': str,
        'date': Optional[str],
        'createdAt': str,
        'priority': float,
        'completed': bool,
        'source': 'habitica',
        'tags': List[str],
        'id': str,
        'raw': dict (original)
    }
    """
    tasks = []
    for task in habitica:
        body = task.get("text", "").strip()
        date = task.get("date") or None
        created_at = task.get("createdAt") or utc_now_iso_z()
        priority = float(task.get("priority", 0.1))
        completed = bool(task.get("completed", False))
        tags = task.get("tags", [])
        task_id = task.get("id")

        tasks.append({
            "body": body,
            "date": date,
            "createdAt": created_at,
            "priority": priority,
            "completed": completed,
            "source": "habitica",
            "tags": tags,
            "id": task_id,
            "raw": task,
        })
    return tasks


def tasks_are_identical(t1: Dict[str, Any], t2: Dict[str, Any]) -> bool:
    """
    Verifica se duas tasks são idênticas (considerando body como chave primária).
    """
    return (
        t1["body"] == t2["body"] and
        t1.get("date") == t2.get("date") and
        t1.get("priority") == t2.get("priority") and
        t1.get("completed") == t2.get("completed") and
        normalize_tags_for_compare(t1.get("tags", [])) == normalize_tags_for_compare(t2.get("tags", []))
    )


def tasks_are_similar(t1: Dict[str, Any], t2: Dict[str, Any]) -> bool:
    """
    Verifica se duas tasks têm o mesmo body mas propriedades diferentes.
    """
    return (
        t1["body"] == t2["body"] and not tasks_are_identical(t1, t2)
    )


def compare_tasks(t1: Dict[str, Any], t2: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Compara duas tasks e retorna (melhor, pior) segundo regras:
    1. Prioridade maior vence
    2. Data mais recente vence
    3. Completed True vence
    4. Empate: t1 vence
    """
    # Prioridade
    if t1["priority"] != t2["priority"]:
        return (t1, t2) if t1["priority"] > t2["priority"] else (t2, t1)

    # Data
    date_cmp = compare_task_dates(t1.get("date"), t2.get("date"))
    if date_cmp > 0:
        return (t1, t2)
    if date_cmp < 0:
        return (t2, t1)

    # Completed
    if t1["completed"] != t2["completed"]:
        return (t1, t2) if t1["completed"] else (t2, t1)

    # Empate
    return (t1, t2)


def format_task_for_obsidian(task: Dict[str, Any]) -> str:
    """
    Formata uma task para o formato do plugin Tasks no Obsidian.
    Exemplo:
    - [ ] TODO Comprar Monitor Portátil #tag1 #tag2 📅 2024-06-01 ⏫
    """
    checkbox = "[x]" if task["completed"] else "[ ]"
    parts = [f"- {checkbox} TODO {task['body']}"]

    # Tags
    if task.get("tags"):
        # Para Obsidian, converter espaços para "-" no momento da escrita.
        parts.append(" ".join(f"#{str(tag).strip().replace(' ', '-')}" for tag in task["tags"] if str(tag).strip()))

    # Date
    if task.get("date"):
        parts.append(f"📅 {task['date']}")

    # Priority icon
    priority_icon_map = {1.5: "⏫", 1.0: "🔼", 2.0: "🔺"}
    priority_icon = priority_icon_map.get(float(task["priority"]), "")
    if priority_icon:
        parts.append(priority_icon)

    # Completed date (if completed and has date)
    if task["completed"] and task.get("date"):
        parts.append(f"✅ {task['date']}")

    return " ".join(parts)


def format_task_for_habitica_create(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formata uma task para criação no Habitica (JSON para API).
    """
    data = {
        "text": task["body"],
        "type": "todo",
        "priority": task["priority"],
        "completed": task["completed"],
    }
    if task.get("date"):
        data["date"] = task["date"]
    if task.get("tags"):
        data["tags"] = task["tags"]
    return data


def format_task_for_habitica_edit(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formata uma task para edição no Habitica (JSON para API).
    Deve conter o id da task.
    """
    data = format_task_for_habitica_create(task)
    data["id"] = task["id"]
    return data


def format_task_for_obsidian_edit(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formata uma task para edição no Obsidian.
    Retorna dict com:
    {
        "file_path": str,
        "new_text": str (linha da task atualizada)
    }
    """
    new_text = format_task_for_obsidian(task)
    return {
        "file_path": task["file_path"],
        "new_text": new_text,
        "old_raw_line": task.get("raw_line", ""),
    }


def sync_tasks(obsidian: Dict[str, str], habitica: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Função principal que recebe obsidian e habitica e retorna:
    {
        "create_obsidian": List[str],  # linhas de tasks para criar no obsidian
        "create_habitica": List[Dict],  # json para criar no habitica
        "edit_habitica": List[Dict],    # json para editar no habitica
        "edit_obsidian": List[Dict],    # dicts com file_path e new_text para editar obsidian
    }
    """
    obsidian_tasks = parse_obsidian_tasks(obsidian)
    habitica_tasks = parse_habitica_tasks(habitica)

    # Indexar por body para matching
    obsidian_map = {t["body"]: t for t in obsidian_tasks}
    habitica_map = {t["body"]: t for t in habitica_tasks}

    create_obsidian = []
    create_habitica = []
    edit_habitica = []
    edit_obsidian = []

    all_bodies = set(obsidian_map.keys()).union(habitica_map.keys())

    for body in all_bodies:
        o_task = obsidian_map.get(body)
        h_task = habitica_map.get(body)

        if o_task and not h_task:
            # Existe só no Obsidian -> criar no Habitica
            create_habitica.append(format_task_for_habitica_create(o_task))

        elif h_task and not o_task:
            # Existe só no Habitica -> criar no Obsidian
            create_obsidian.append(format_task_for_obsidian(h_task))

        elif o_task and h_task:
            # Existe nos dois -> comparar detalhes
            if tasks_are_identical(o_task, h_task):
                # Idênticos, nada a fazer
                continue
            else:
                # Diferentes, considerar dados do Habitica como verdade.
                # Preserva metadados do Obsidian para permitir edição no arquivo correto.
                merged_for_obsidian = {**h_task, "file_path": o_task["file_path"], "raw_line": o_task.get("raw_line", "")}
                edit_obsidian.append(format_task_for_obsidian_edit(merged_for_obsidian))
                # Editar Habitica para refletir Habitica (não precisa, mas vamos garantir)
                # Na verdade, Habitica é verdade, então só editar Habitica se for diferente? 
                # Mas já sabemos que são diferentes, então editar Habitica para manter dados dele mesmo não faz sentido.
                # Então só editar Habitica se quisermos sincronizar dados do Obsidian para Habitica, mas regra diz não.
                # Portanto, só editar Obsidian.
                # Se quiser editar Habitica para manter dados dele mesmo, não faz sentido.
                # Então pular editar Habitica.

    return {
        "create_obsidian": create_obsidian,
        "create_habitica": create_habitica,
        "edit_habitica": edit_habitica,
        "edit_obsidian": edit_obsidian,
    }


# Exemplo de uso:
if __name__ == "__main__":
    obsidian_example = {
        "notes/tarefas.md": """
- [ ] TODO Comprar Monitor Portátil #compras 📅 2024-06-01 ⏫
- [x] TODO Pagar conta de luz #financeiro ✅ 2024-05-15
"""
    }

    habitica_example = [
        {
            "_id": "3c3db523-5524-4b12-987a-b8305cbe0666",
            "type": "todo",
            "text": "Comprar Monitor Portátil",
            "notes": "Link de compra do Arzopa Z1FC [aqui](https://br.arzopa.com/products/z1fc-16-1-fhd-144hz-monitor-portatil?variant=46761341059316&country=BR&currency=BRL&utm_medium=product_sync&utm_source=google&utm_content=sag_organic&utm_campaign=sag_organic&gad_source=1&gad_campaignid=23619325366&gbraid=0AAAABCVlpRcG_CZf8syxUIdh04BcDf3ac&gclid=EAIaIQobChMIys6Xl6eGkwMVbF9IAB0W0ALOEAQYAiABEgI_yvD_BwE).\n",
            "tags": [],
            "value": -5.2738783997395196,
            "priority": 2,
            "attribute": "str",
            "challenge": {},
            "group": {"completedBy": {}, "assignedUsers": []},
            "reminders": [],
            "byHabitica": False,
            "completed": False,
            "collapseChecklist": False,
            "checklist": [],
            "createdAt": "2026-03-04T13:05:31.950Z",
            "updatedAt": "2026-03-09T10:56:48.213Z",
            "userId": "bbb3a114-5769-4a47-a975-51d89bd5206d",
            "id": "3c3db523-5524-4b12-987a-b8305cbe0666",
        }
    ]

    result = sync_tasks(obsidian_example, habitica_example)

    print("Criar no Obsidian (texto):")
    for t in result["create_obsidian"]:
        print(t)
    print("\nCriar no Habitica (json):")
    for t in result["create_habitica"]:
        print(t)
    print("\nEditar no Habitica (json):")
    for t in result["edit_habitica"]:
        print(t)
    print("\nEditar no Obsidian (json):")
    for t in result["edit_obsidian"]:
        print(t)