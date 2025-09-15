from pathlib import Path
import sys

# Ensure project root is in path
ROOT = Path(__file__).parent
sys.path.append(str(ROOT))

from agents.sql_agent import load_metadata_yaml, build_fewshot_block_from_examples  # type: ignore


def build_prompt(question: str,
                 examples_path: str = "data/examples.jsonl",
                 template_path: str = "prompts/sql_prompt.txt",
                 top_k: int = 1) -> str:
    fewshot_text, _ = build_fewshot_block_from_examples(examples_path, question, top_k=top_k)
    schema_context = load_metadata_yaml()

    template_file = Path(template_path)
    if template_file.exists():
        template = template_file.read_text(encoding="utf-8")
        prompt = template.replace("{fewshot}", fewshot_text).replace("{question}", question)
    else:
        prompt = (
            "You are a SQL assistant for a SQLite database. "
            "Return exactly one SELECT statement only, enclosed in a ```sql``` block, with no explanations. "
            "Use accurate table/column names from the schema. Avoid destructive queries. "
            "Do NOT include LIMIT unless the user explicitly asks for it.\n" + fewshot_text + "\n"
            f"User question: {question}"
        )

    return schema_context + prompt


if __name__ == "__main__":
    q = "What is the Inventory Level of S001 at P0005 on 2022-01-01?"
    prompt = build_prompt(q)
    print(prompt)


