"""
Testes automatizados para validação de prompts.
"""
import pytest
import yaml
import re
import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import validate_prompt_structure

PROMPTS_FILE = str(Path(__file__).parent.parent / "prompts" / "bug_to_user_story_v2.yml")
PROMPT_KEY = "bug_to_user_story_v2"


def load_prompts(file_path: str):
    """Carrega prompts do arquivo YAML."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def prompt():
    """Retorna o bloco do prompt otimizado (v2) do arquivo YAML."""
    data = load_prompts(PROMPTS_FILE)

    assert data is not None, f"Arquivo vazio ou inválido: {PROMPTS_FILE}"
    assert PROMPT_KEY in data, f"Chave '{PROMPT_KEY}' não encontrada em {PROMPTS_FILE}"

    return data[PROMPT_KEY]


@pytest.fixture(scope="module")
def full_text(prompt):
    """Concatena system_prompt e user_prompt em minúsculas para buscas textuais."""
    return f"{prompt.get('system_prompt', '')}\n{prompt.get('user_prompt', '')}".lower()


class TestPrompts:
    def test_prompt_has_system_prompt(self, prompt):
        """Verifica se o campo 'system_prompt' existe e não está vazio."""
        assert "system_prompt" in prompt, "Campo 'system_prompt' não existe no YAML"

        system_prompt = prompt["system_prompt"]

        assert isinstance(system_prompt, str), "'system_prompt' deve ser uma string"
        assert system_prompt.strip(), "'system_prompt' está vazio"
        assert len(system_prompt.strip()) > 200, (
            "'system_prompt' é curto demais para um prompt otimizado "
            f"({len(system_prompt.strip())} caracteres)"
        )

        # O user_prompt também precisa existir e ser o único portador do bug
        user_prompt = prompt.get("user_prompt", "")
        assert user_prompt.strip(), "'user_prompt' está vazio"
        assert "{bug_report}" in user_prompt, (
            "'user_prompt' deve conter a variável {bug_report}"
        )
        assert "{bug_report}" not in system_prompt, (
            "'{bug_report}' não deve ser duplicado no 'system_prompt' "
            "(esse era justamente o defeito da v1)"
        )

    def test_prompt_has_role_definition(self, prompt):
        """Verifica se o prompt define uma persona (ex: "Você é um Product Manager")."""
        system_prompt = prompt.get("system_prompt", "")

        assert re.search(
            r"você\s+(é|atua como)\s+(um|uma|o|a)?", system_prompt, re.IGNORECASE
        ), "O prompt não define uma persona com 'Você é ...' / 'Você atua como ...'"

        personas = [
            "product owner",
            "product manager",
            "po sênior",
            "analista de produto",
            "especialista",
        ]
        assert any(p in system_prompt.lower() for p in personas), (
            f"Nenhuma persona reconhecida encontrada. Esperado uma de: {personas}"
        )

    def test_prompt_mentions_format(self, full_text):
        """Verifica se o prompt exige formato Markdown ou User Story padrão."""
        assert "markdown" in full_text, (
            "O prompt não menciona o formato Markdown da resposta"
        )

        # Template padrão de user story: Como um... eu quero... para que...
        for part in ("como um", "eu quero", "para que"):
            assert part in full_text, (
                f"O prompt não exige o formato padrão de User Story "
                f"(trecho ausente: '{part}')"
            )

        # Critérios de aceitação no padrão Dado/Quando/Então
        assert "critérios de aceitação" in full_text, (
            "O prompt não exige uma seção de Critérios de Aceitação"
        )
        for part in ("dado", "quando", "então"):
            assert part in full_text, (
                f"O prompt não exige critérios no padrão Dado/Quando/Então "
                f"(trecho ausente: '{part}')"
            )

    def test_prompt_has_few_shot_examples(self, prompt):
        """Verifica se o prompt contém exemplos de entrada/saída (técnica Few-shot)."""
        system_prompt = prompt.get("system_prompt", "")
        lower = system_prompt.lower()

        assert "exemplo" in lower, "O prompt não contém uma seção de exemplos"

        entradas = len(re.findall(r"^\s*entrada:", system_prompt, re.MULTILINE | re.IGNORECASE))
        saidas = len(re.findall(r"^\s*saída:", system_prompt, re.MULTILINE | re.IGNORECASE))

        assert entradas >= 2, (
            f"Few-shot exige pelo menos 2 exemplos de entrada, encontrados: {entradas}"
        )
        assert saidas >= 2, (
            f"Few-shot exige pelo menos 2 exemplos de saída, encontrados: {saidas}"
        )
        assert entradas == saidas, (
            f"Cada entrada deve ter uma saída correspondente "
            f"(entradas: {entradas}, saídas: {saidas})"
        )

        # A técnica precisa estar declarada nos metadados
        techniques = " ".join(prompt.get("techniques_applied", [])).lower()
        assert "few-shot" in techniques or "few shot" in techniques, (
            "Few-shot Learning não está declarada em 'techniques_applied'"
        )

    def test_prompt_no_todos(self, prompt):
        """Garante que você não esqueceu nenhum `[TODO]` no texto."""
        blocos = {
            "description": str(prompt.get("description", "")),
            "system_prompt": prompt.get("system_prompt", ""),
            "user_prompt": prompt.get("user_prompt", ""),
        }

        marcadores = [
            "[TODO]",
            "TODO",
            "FIXME",
            "TBD",
            "<preencher>",
            "[preencher]",
            "[INSERIR",
        ]

        for nome, texto in blocos.items():
            for marcador in marcadores:
                assert marcador not in texto, (
                    f"Marcador '{marcador}' encontrado em '{nome}' — "
                    "o prompt não está finalizado"
                )

    def test_minimum_techniques(self, prompt):
        """Verifica (através dos metadados do yaml) se pelo menos 2 técnicas foram listadas."""
        techniques = prompt.get("techniques_applied", [])

        assert isinstance(techniques, list), (
            "'techniques_applied' deve ser uma lista no YAML"
        )
        assert len(techniques) >= 2, (
            f"Mínimo de 2 técnicas requeridas, encontradas: {len(techniques)}"
        )
        assert all(str(t).strip() for t in techniques), (
            "Há técnicas vazias em 'techniques_applied'"
        )

        # Valida também pelo helper oficial do projeto (src/utils.py)
        is_valid, errors = validate_prompt_structure(prompt)
        assert is_valid, f"Estrutura do prompt inválida: {errors}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
