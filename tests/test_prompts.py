"""
Testes automatizados para validação de prompts.
"""
import re
import pytest
import yaml
import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import validate_prompt_structure

PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "bug_to_user_story_v2.yml"
PROMPT_KEY = "bug_to_user_story_v2"


def load_prompts(file_path: str):
    """Carrega prompts do arquivo YAML."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


@pytest.fixture
def prompt():
    """Dados do prompt v2, lidos do YAML antes de cada teste."""
    return load_prompts(str(PROMPT_FILE))[PROMPT_KEY]


class TestPrompts:
    def test_prompt_has_system_prompt(self, prompt):
        """Verifica se o campo 'system_prompt' existe e não está vazio."""
        assert "system_prompt" in prompt, "O campo system_prompt não existe"
        assert prompt["system_prompt"].strip(), "O system_prompt está vazio"

    def test_prompt_has_role_definition(self, prompt):
        """Verifica se o prompt define uma persona (ex: "Você é um Product Manager")."""
        assert re.search(r"Você é (um|uma) \w+", prompt["system_prompt"]), (
            "O prompt não define uma persona com 'Você é um(a) ...'"
        )

    def test_prompt_mentions_format(self, prompt):
        """Verifica se o prompt exige formato Markdown ou User Story padrão."""
        text = prompt["system_prompt"].lower()

        assert re.search(r"como um.+eu quero.+para que", text), (
            "O prompt não exige o formato 'Como um..., eu quero..., para que...'"
        )
        assert "critérios de aceitação" in text, "O prompt não exige Critérios de Aceitação"

    def test_prompt_has_few_shot_examples(self, prompt):
        """Verifica se o prompt contém exemplos de entrada/saída (técnica Few-shot)."""
        text = prompt["system_prompt"]
        inputs = re.findall(r"^Relato de bug:", text, flags=re.MULTILINE)
        outputs = re.findall(r"^User Story:", text, flags=re.MULTILINE)

        assert len(inputs) >= 2, f"Esperado ao menos 2 exemplos de entrada, encontrados: {len(inputs)}"
        assert len(inputs) == len(outputs), "Cada exemplo de entrada precisa de uma saída"

    def test_prompt_no_todos(self, prompt):
        """Garante que você não esqueceu nenhum `[TODO]` no texto."""
        for field in ["description", "system_prompt", "user_prompt"]:
            # \b evita confundir com a palavra "todos" do português
            assert not re.search(r"\bTODO\b", prompt[field], flags=re.IGNORECASE), (
                f"O campo {field} ainda contém TODO"
            )

    def test_minimum_techniques(self, prompt):
        """Verifica (através dos metadados do yaml) se pelo menos 2 técnicas foram listadas."""
        techniques = prompt.get("techniques_applied", [])
        assert len(techniques) >= 2, f"Mínimo de 2 técnicas, encontradas: {len(techniques)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
