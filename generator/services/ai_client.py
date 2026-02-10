import json
import requests
from django.conf import settings

def generate_test_cases(data: dict) -> str:
    """Generación normal (no streaming)"""
    requirement_text = data["requirement"]
    if data.get("context"):
        requirement_text = f"CONTEXTO:\n{data['context']}\nREQUERIMIENTO:\n{data['requirement']}"

    payload = {"requirement": requirement_text}
    response = requests.post(
        settings.FASTAPI_URL + "/generate",
        json=payload,
        timeout=200
    )
    response.raise_for_status()
    return response.json().get("test_cases", "")


def generate_test_cases_stream(data: dict):
    """
    Genera test cases en streaming, línea por línea, con saltos de línea intactos.
    """
    payload = {
        "requirement": data["requirement"],
        "context": data.get("context", ""),
        "stream": True
    }

    response = requests.post(
        settings.FASTAPI_URL + "/generate",
        json=payload,
        stream=True,
        timeout=600
    )
    response.raise_for_status()

    # Iterar línea por línea y mantener saltos de línea
    for line in response.iter_lines(decode_unicode=True):
        if line:
            yield line + "\n"



def generate_project_test_cases(project_content: str) -> str:
    print("recibido y enviando a /generate-project ....")

    response = requests.post(
        settings.FASTAPI_URL + "/generate-project",
        json={"project_content": project_content},
        timeout=600
    )

    print("status:", response.status_code)
    print("raw response:", response.text)

    response.raise_for_status()  # 🔴 SI FALLA, PARA AQUÍ

    data = response.json()
    print("test_cases recibidos:", data.get("test_cases", ""))

    return data.get("test_cases", "")

