"""
Script para fazer pull de prompts do LangSmith Prompt Hub.

Este script:
1. Conecta ao LangSmith usando credenciais do .env
2. Faz pull dos prompts do Hub
3. Salva localmente em prompts/bug_to_user_story_v1.yml

SIMPLIFICADO: Usa serialização nativa do LangChain para extrair prompts.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from langchain import hub
from utils import save_yaml, check_env_vars, print_section_header

load_dotenv()

# Raiz do repositório: permite rodar o script de qualquer diretório
REPO_ROOT = Path(__file__).resolve().parent.parent

# Prompts de baixa qualidade publicados pelo professor no LangSmith Hub.
# Formato: (identificador no Hub, arquivo local de destino, chave raiz do YAML)
PROMPTS_TO_PULL = [
    (
        "leonanluppi/bug_to_user_story_v1",
        "prompts/bug_to_user_story_v1.yml",
        "bug_to_user_story_v1",
    ),
]


def extract_messages(prompt_template) -> dict:
    """
    Extrai system_prompt e user_prompt de um ChatPromptTemplate do LangChain.

    A serialização nativa do LangChain guarda cada mensagem como um
    *MessagePromptTemplate. Aqui percorremos as mensagens e separamos o
    conteúdo por tipo (system / human), preservando as variáveis ({bug_report}).

    Args:
        prompt_template: Objeto retornado por hub.pull()

    Returns:
        Dicionário com as chaves 'system_prompt' e 'user_prompt'
    """
    system_parts = []
    user_parts = []

    for message in getattr(prompt_template, "messages", []):
        template = getattr(getattr(message, "prompt", None), "template", None)

        if template is None:
            # Mensagens fixas (não-template) expõem o texto em .content
            template = getattr(message, "content", None)

        if not template:
            continue

        message_type = getattr(message, "__class__").__name__.lower()

        if "system" in message_type:
            system_parts.append(template)
        else:
            user_parts.append(template)

    return {
        "system_prompt": "\n\n".join(system_parts),
        "user_prompt": "\n\n".join(user_parts),
    }


def pull_prompts_from_langsmith() -> bool:
    """
    Faz pull de cada prompt configurado em PROMPTS_TO_PULL e salva em YAML.

    Returns:
        True se todos os prompts foram baixados com sucesso, False caso contrário
    """
    all_ok = True

    for hub_name, output_path, yaml_key in PROMPTS_TO_PULL:
        print(f"📥 Fazendo pull de: {hub_name}")

        try:
            prompt_template = hub.pull(hub_name)
        except Exception as e:
            print(f"   ❌ Erro ao fazer pull: {e}")
            print("   Verifique LANGSMITH_API_KEY no .env e o nome do prompt.\n")
            all_ok = False
            continue

        messages = extract_messages(prompt_template)

        if not messages["system_prompt"] and not messages["user_prompt"]:
            print("   ❌ Prompt baixado não contém mensagens reconhecíveis.\n")
            all_ok = False
            continue

        prompt_data = {
            yaml_key: {
                "description": "Prompt para converter relatos de bugs em User Stories",
                "system_prompt": messages["system_prompt"],
                "user_prompt": messages["user_prompt"],
                "version": "v1",
                "source": hub_name,
                "input_variables": sorted(prompt_template.input_variables),
                "tags": ["bug-analysis", "user-story", "product-management"],
            }
        }

        destination = str(REPO_ROOT / output_path)

        if save_yaml(prompt_data, destination):
            print(f"   ✓ Salvo em: {output_path}")
            print(f"   ✓ Variáveis de entrada: {prompt_template.input_variables}\n")
        else:
            print(f"   ❌ Falha ao salvar em {output_path}\n")
            all_ok = False

    return all_ok


def main():
    """Função principal"""
    print_section_header("PULL DE PROMPTS DO LANGSMITH HUB")

    if not check_env_vars(["LANGSMITH_API_KEY"]):
        return 1

    if not pull_prompts_from_langsmith():
        print("❌ Nem todos os prompts foram baixados com sucesso.")
        return 1

    print("✅ Pull concluído com sucesso!\n")
    print("Próximos passos:")
    print("1. Analise o prompt em prompts/bug_to_user_story_v1.yml")
    print("2. Refatore-o em prompts/bug_to_user_story_v2.yml")
    print("3. Publique com: python src/push_prompts.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
