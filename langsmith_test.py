import os
from dotenv import load_dotenv

# LangChain Core prompt
from langchain_core.prompts import ChatPromptTemplate
# Groq LLM via LangChain
from langchain_groq import ChatGroq


def main():
    # Load .env so LANGSMITH_* variables and GROQ_API_KEY are available
    load_dotenv()

    # Quick sanity print (do not print full keys)
    ls_enabled = os.getenv("LANGSMITH_TRACING") or os.getenv("LANGCHAIN_TRACING_V2")
    ls_key_prefix = (os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY") or "")[:8]
    project = os.getenv("LANGSMITH_PROJECT") or os.getenv("LANGCHAIN_PROJECT")
    print(f"LangSmith tracing: {ls_enabled}, key prefix: {ls_key_prefix}, project: {project}")

    # Initialize LLM (Groq) — make sure GROQ_API_KEY is set in .env
    llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0.1)

    # Minimal prompt → should appear as a run in LangSmith
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant."),
        ("user", "Say hello and mention 'LangSmith tracing is ON'.")
    ])

    chain = prompt | llm

    # Invoke once
    resp = chain.invoke({})
    print("Model response:")
    print(resp)

    print("If LangSmith is configured correctly, this run should be visible under your project dashboard.")


if __name__ == "__main__":
    main()
