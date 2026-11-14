"""
Script para fazer push de prompts otimizados ao LangSmith Prompt Hub.

Este script:
1. Lê os prompts otimizados de prompts/bug_to_user_story_v2.yml
2. Valida os prompts
3. Faz push PÚBLICO para o LangSmith Hub
4. Adiciona metadados (tags, descrição, técnicas utilizadas)

DICAS DE IMPLEMENTAÇÃO:

- O push é feito pelo cliente do LangSmith:

      from langsmith import Client
      from langchain_core.prompts import ChatPromptTemplate

      client = Client()
      prompt = ChatPromptTemplate.from_messages([
          ("system", system_prompt),
          ("user", user_prompt),
      ])
      url = client.push_prompt(
          f"{username}/bug_to_user_story_v2",
          object=prompt,
          is_public=True,
          description="...",
          tags=[...],
      )

- `username` vem de USERNAME_LANGSMITH_HUB no .env e precisa ser o seu handle
  do Hub. Se você ainda não tem um handle, veja as instruções no .env.example.

- A variável do template precisa ser {bug_report}, que é a chave de entrada
  usada no dataset de avaliação.

- Use `load_yaml` de utils.py para ler o arquivo .yml.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from langsmith import Client
from langchain_core.prompts import ChatPromptTemplate
from utils import load_yaml, check_env_vars, print_section_header

load_dotenv()

PROMPT_KEY = "bug_to_user_story_v2"
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / f"{PROMPT_KEY}.yml"

# Chave de entrada usada pelo dataset de avaliação
REQUIRED_VARIABLE = "bug_report"


def build_chat_prompt(prompt_data: dict) -> ChatPromptTemplate:
    """Monta o ChatPromptTemplate (system + user) a partir dos dados do YAML."""
    return ChatPromptTemplate.from_messages([
        ("system", prompt_data["system_prompt"]),
        ("user", prompt_data["user_prompt"]),
    ])


def push_prompt_to_langsmith(prompt_name: str, prompt_data: dict) -> bool:
    """
    Faz push do prompt otimizado para o LangSmith Hub (PÚBLICO).

    Args:
        prompt_name: Nome do prompt
        prompt_data: Dados do prompt

    Returns:
        True se sucesso, False caso contrário
    """
    techniques = prompt_data.get("techniques_applied", [])
    tags = list(dict.fromkeys(prompt_data.get("tags", []) + techniques))

    description = prompt_data.get("description", "").strip()
    if techniques:
        description = f"{description} | Técnicas: {', '.join(techniques)}"

    try:
        prompt = build_chat_prompt(prompt_data)

        url = Client().push_prompt(
            prompt_name,
            object=prompt,
            is_public=True,
            description=description,
            tags=tags,
        )

        print(f"   ✓ Push realizado: {prompt_name}")
        print(f"   ✓ {url}")
        return True

    except Exception as e:
        error_msg = str(e).lower()

        # O Hub recusa um commit idêntico ao último: o prompt já está publicado
        if "nothing to commit" in error_msg or "has not changed" in error_msg:
            print(f"   ✓ '{prompt_name}' já está atualizado no Hub (sem alterações)")
            return True

        print(f"   ❌ Erro ao fazer push de '{prompt_name}': {e}")
        print("\n   Verifique:")
        print("   - LANGSMITH_API_KEY está correta no .env")
        print("   - USERNAME_LANGSMITH_HUB é o seu handle do Hub (ele só existe")
        print("     depois de você tornar algum prompt público pela primeira vez)")
        return False


def validate_prompt(prompt_data: dict) -> tuple[bool, list]:
    """
    Valida estrutura básica de um prompt (versão simplificada).

    Args:
        prompt_data: Dados do prompt

    Returns:
        (is_valid, errors) - Tupla com status e lista de erros
    """
    errors = []

    if not isinstance(prompt_data, dict):
        return (False, ["Estrutura do prompt inválida (esperado um dicionário)"])

    for field in ["description", "system_prompt", "user_prompt", "version"]:
        if not str(prompt_data.get(field, "")).strip():
            errors.append(f"Campo obrigatório faltando ou vazio: {field}")

    system_prompt = str(prompt_data.get("system_prompt", ""))
    user_prompt = str(prompt_data.get("user_prompt", ""))

    if "TODO" in system_prompt or "TODO" in user_prompt:
        errors.append("O prompt ainda contém TODOs")

    if len(prompt_data.get("techniques_applied", [])) < 2:
        errors.append("Mínimo de 2 técnicas requeridas em techniques_applied")

    # As variáveis são conferidas no template já montado: isso também pega
    # chaves soltas que o LangChain interpretaria como variável por engano.
    if not errors:
        try:
            variables = set(build_chat_prompt(prompt_data).input_variables)
        except Exception as e:
            errors.append(f"Template inválido: {e}")
        else:
            if variables != {REQUIRED_VARIABLE}:
                errors.append(
                    f"O template deve ter exatamente a variável {{{REQUIRED_VARIABLE}}}, "
                    f"encontradas: {sorted(variables)}"
                )
            if f"{{{REQUIRED_VARIABLE}}}" not in user_prompt:
                errors.append(f"user_prompt deve conter a variável {{{REQUIRED_VARIABLE}}}")

    return (len(errors) == 0, errors)


def main():
    """Função principal"""
    print_section_header("PUSH DE PROMPTS OTIMIZADOS AO LANGSMITH HUB")

    if not check_env_vars(["LANGSMITH_API_KEY", "USERNAME_LANGSMITH_HUB"]):
        return 1

    username = os.getenv("USERNAME_LANGSMITH_HUB")

    prompts = load_yaml(str(PROMPT_PATH))
    if not prompts or PROMPT_KEY not in prompts:
        print(f"❌ Prompt '{PROMPT_KEY}' não encontrado em {PROMPT_PATH}")
        return 1

    prompt_data = prompts[PROMPT_KEY]
    prompt_name = f"{username}/{PROMPT_KEY}"

    print(f"Validando prompt: {PROMPT_KEY}")
    is_valid, errors = validate_prompt(prompt_data)
    if not is_valid:
        print("❌ Prompt inválido:")
        for error in errors:
            print(f"   - {error}")
        return 1
    print("   ✓ Prompt válido")

    print(f"\nFazendo push: {prompt_name}")
    if not push_prompt_to_langsmith(prompt_name, prompt_data):
        return 1

    print("\n✅ Push concluído!")
    print("\nPróximos passos:")
    print("1. Confira o prompt em https://smith.langchain.com/prompts")
    print("2. Execute a avaliação: python src/evaluate.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
