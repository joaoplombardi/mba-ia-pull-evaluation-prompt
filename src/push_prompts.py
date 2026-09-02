"""
Script para fazer push de prompts otimizados ao LangSmith Prompt Hub.

Este script:
1. Lê os prompts otimizados de prompts/bug_to_user_story_v2.yml
2. Valida os prompts
3. Faz push PÚBLICO para o LangSmith Hub
4. Adiciona metadados (tags, descrição, técnicas utilizadas)

SIMPLIFICADO: Código mais limpo e direto ao ponto.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from langchain import hub
from langchain_core.prompts import ChatPromptTemplate
from utils import load_yaml, check_env_vars, print_section_header

load_dotenv()

# Raiz do repositório: permite rodar o script de qualquer diretório
REPO_ROOT = Path(__file__).resolve().parent.parent

PROMPTS_FILE = "prompts/bug_to_user_story_v2.yml"
PROMPT_KEY = "bug_to_user_story_v2"


def get_hub_username() -> tuple:
    """
    Retorna o username do LangSmith Hub e se o workspace já tem handle.

    O handle é o identificador público do workspace no Prompt Hub. Sem ele o
    LangSmith recusa prompts públicos e o prefixo "owner/". Consultamos a API
    para saber se o handle existe e usamos USERNAME_LANGSMITH_HUB como fallback.

    Returns:
        (username, has_handle) - nome a usar e se o handle existe de fato
    """
    env_username = os.getenv("USERNAME_LANGSMITH_HUB", "").strip()

    try:
        from langsmith import Client

        handle = (Client()._get_settings().tenant_handle or "").strip()
    except Exception as e:
        print(f"⚠️  Não foi possível consultar o handle do workspace: {e}")
        handle = ""

    if handle:
        if env_username and env_username != handle:
            print(
                f"⚠️  USERNAME_LANGSMITH_HUB ('{env_username}') difere do handle "
                f"do workspace ('{handle}'); usando o handle real."
            )
        return (handle, True)

    return (env_username, False)


def build_readme(prompt_data: dict) -> str:
    """
    Monta o README publicado junto do prompt no LangSmith Hub.

    Args:
        prompt_data: Dados do prompt lidos do YAML

    Returns:
        Texto em Markdown com os metadados do prompt
    """
    techniques = prompt_data.get("techniques_applied", [])
    changelog = prompt_data.get("changelog", [])

    lines = [
        f"# {PROMPT_KEY}",
        "",
        prompt_data.get("description", ""),
        "",
        f"**Versão:** {prompt_data.get('version', 'v2')}",
        "",
        "## Técnicas de Prompt Engineering aplicadas",
        "",
    ]

    lines += [f"- {technique}" for technique in techniques]

    if changelog:
        lines += ["", "## Changelog de otimização", ""]
        lines += [f"- {entry}" for entry in changelog]

    return "\n".join(lines)


def validate_prompt(prompt_data: dict) -> tuple:
    """
    Valida estrutura básica de um prompt (versão simplificada).

    Args:
        prompt_data: Dados do prompt

    Returns:
        (is_valid, errors) - Tupla com status e lista de erros
    """
    errors = []

    for field in ("description", "system_prompt", "user_prompt", "version"):
        if not prompt_data.get(field):
            errors.append(f"Campo obrigatório ausente ou vazio: {field}")

    system_prompt = (prompt_data.get("system_prompt") or "").strip()
    user_prompt = (prompt_data.get("user_prompt") or "").strip()

    if "TODO" in system_prompt or "TODO" in user_prompt:
        errors.append("O prompt ainda contém marcadores [TODO]")

    if "{bug_report}" not in user_prompt:
        errors.append("user_prompt deve conter a variável {bug_report}")

    if "{bug_report}" in system_prompt:
        errors.append(
            "system_prompt não deve conter {bug_report} "
            "(o bug pertence ao user prompt)"
        )

    techniques = prompt_data.get("techniques_applied", [])
    if len(techniques) < 2:
        errors.append(
            f"Mínimo de 2 técnicas requeridas em techniques_applied, "
            f"encontradas: {len(techniques)}"
        )

    return (len(errors) == 0, errors)


def push_prompt_to_langsmith(prompt_name: str, prompt_data: dict, is_public: bool = True) -> bool:
    """
    Faz push do prompt otimizado para o LangSmith Hub (PÚBLICO).

    Args:
        prompt_name: Nome do prompt
        prompt_data: Dados do prompt
        is_public: Publica o prompt como público (exige handle no Hub)

    Returns:
        True se sucesso, False caso contrário
    """
    try:
        chat_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", prompt_data["system_prompt"]),
                ("human", prompt_data["user_prompt"]),
            ]
        )

        tags = [str(tag) for tag in prompt_data.get("tags", [])]
        readme = build_readme(prompt_data)
        description = prompt_data.get("description", "")

        try:
            url = hub.push(
                prompt_name,
                chat_prompt,
                new_repo_is_public=is_public,
                new_repo_description=description,
                readme=readme,
                tags=tags,
            )
            print(f"   ✓ Novo commit publicado: {url}")

        except Exception as e:
            # O Hub recusa commits idênticos ao último. Isso não é uma falha:
            # o prompt já está publicado com este conteúdo, e ainda queremos
            # sincronizar metadados e visibilidade abaixo.
            if "has not changed" not in str(e) and "409" not in str(e):
                raise

            print("   ℹ️  Conteúdo idêntico ao último commit; nada a versionar.")

        # hub.push só aplica is_public na CRIAÇÃO do repositório.
        # Em re-pushes garantimos explicitamente que o prompt siga público.
        try:
            from langsmith import Client

            Client().update_prompt(
                prompt_name,
                description=description,
                readme=readme,
                tags=tags,
                is_public=is_public,
            )
            visibilidade = "PÚBLICO" if is_public else "privado"
            print(f"   ✓ Metadados sincronizados (visibilidade: {visibilidade})")
        except Exception as e:
            print(f"   ⚠️  Não foi possível atualizar metadados/visibilidade: {e}")

        return True

    except Exception as e:
        print(f"   ❌ Erro ao fazer push: {e}")
        return False


def main():
    """Função principal"""
    print_section_header("PUSH DE PROMPTS OTIMIZADOS PARA O LANGSMITH HUB")

    if not check_env_vars(["LANGSMITH_API_KEY"]):
        return 1

    username, has_handle = get_hub_username()

    if not username:
        print("❌ USERNAME_LANGSMITH_HUB não configurada no .env")
        print("   Crie seu handle em https://smith.langchain.com/prompts")
        print("   e preencha a variável no .env.")
        return 1

    prompts_file = load_yaml(str(REPO_ROOT / PROMPTS_FILE))
    if not prompts_file:
        return 1

    prompt_data = prompts_file.get(PROMPT_KEY)
    if not prompt_data:
        print(f"❌ Chave '{PROMPT_KEY}' não encontrada em {PROMPTS_FILE}")
        return 1

    print(f"📄 Arquivo: {PROMPTS_FILE}")
    print(f"👤 Username: {username}\n")

    is_valid, errors = validate_prompt(prompt_data)
    if not is_valid:
        print("❌ Prompt inválido:")
        for error in errors:
            print(f"   - {error}")
        return 1

    techniques = prompt_data.get("techniques_applied", [])
    print("✓ Validação OK")
    print(f"✓ Técnicas aplicadas ({len(techniques)}):")
    for technique in techniques:
        print(f"   - {technique}")
    print()

    if has_handle:
        prompt_name = f"{username}/{PROMPT_KEY}"
    else:
        # Sem handle no Hub o LangSmith não aceita prompts públicos nem o
        # prefixo de owner: publicamos no workspace e avisamos o usuário.
        prompt_name = PROMPT_KEY
        print("⚠️  Este workspace ainda não tem handle no LangSmith Prompt Hub.")
        print("   O prompt será publicado como PRIVADO, sem prefixo de owner.")
        print("   Para publicá-lo como PÚBLICO, crie o handle em")
        print("   https://smith.langchain.com/prompts (botão de tornar público)")
        print("   e rode este script novamente.\n")

    print(f"📤 Publicando: {prompt_name}")

    if not push_prompt_to_langsmith(prompt_name, prompt_data, is_public=has_handle):
        return 1

    print("\n✅ Push concluído com sucesso!\n")
    print("Próximos passos:")
    print(f"1. Confira o prompt em: https://smith.langchain.com/prompts/{PROMPT_KEY}")
    print("2. Execute a avaliação: python src/evaluate.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
