from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

def configure_model(model_name):
    model_mapper = {
        "gpt-4o-mini": ChatOpenAI(model=model_name),
        "deepseek-r1:7b": ChatOllama(model=model_name)
    }
    return model_mapper[model_name]
