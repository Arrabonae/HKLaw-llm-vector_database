import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
import argparse
from langchain.vectorstores import Chroma
from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain.callbacks.base import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.embeddings import HuggingFaceEmbeddings
from database import loadOrdinance
from transformers import GPT2Tokenizer
from colorama import Fore, init


MAX_TOKENS = 3850
TOKENIZER = GPT2Tokenizer.from_pretrained("gpt2")


def truncate_tokens(query, chat_history, max_tokens):
    total_tokens = len(TOKENIZER.encode(query))
    truncated_history = []

    for message in reversed(chat_history):
        total_tokens += len(TOKENIZER.encode(message[0])) + len(TOKENIZER.encode(message[1]))
        if total_tokens <= max_tokens:
            truncated_history.insert(0, message)
        else:
            break

    return query, truncated_history


def main():
    parser = argparse.ArgumentParser(description="Chatbot using Langchain and OpenAI API")
    parser.add_argument("-v", "--verbose", action="store_true", default=False, help="Enable verbose mode")
    parser.add_argument("-m", "--model", default="gpt-3.5-turbo", help="Model selection (default: gpt-3.5-turbo, options: gpt-3.5-turbo, gpt-4)")
    parser.add_argument("-s", "--use-langchain-splitter", action="store_true", default=False, help="Use Langchain's own text splitter. \
                        The default is to use the splitter is specifically designed for Hong Kong Ordinances, splits the data into articles, \
                        preserving more metadata.")

    args = parser.parse_args()
    api_key = input("Please enter your OpenAI API key: ")
    verbose = args.verbose
    use_langchain_splitter = args.use_langchain_splitter
    model = args.model

    persist_directory = 'db'
    embeddings = HuggingFaceEmbeddings()

    if os.path.exists(persist_directory):
        print("Loading from existing database...")
        vectordb = Chroma(persist_directory=persist_directory, embedding_function=embeddings)
        vectordb.persist()
    else:
        print("Creating new database...")
        processed, meta = loadOrdinance(use_langchain_splitter)
        vectordb = Chroma.from_texts(texts=processed, embedding=embeddings, metadatas=meta, persist_directory=persist_directory)
        vectordb.persist()

    chat_history = []
    qa = ConversationalRetrievalChain.from_llm(ChatOpenAI(temperature=0, model_name=model, openai_api_key=api_key), vectordb.as_retriever(), return_source_documents=True, verbose=verbose)
    
    init(autoreset=True)
    print(Fore.CYAN + "Welcome to the Chatbot!")
    print(Fore.CYAN + "Type 'exit' to exit the chatbot or 'clear' to clear the chat history.")
    while True:
        query = input(Fore.RED + "You: ")
        if query.lower() == "exit":
            break
        if query.lower() == "clear":
            chat_history = []
            print("Chat history cleared.")
        else:
            query, truncated_history = truncate_tokens(query, chat_history, MAX_TOKENS)
            result = qa({"question": query, "chat_history": truncated_history})
            chat_history.append((query, result["answer"]))
            source = [doc.metadata['Ordinance'] + ' -> ' + doc.metadata['Article'] for doc in result['source_documents']]
            print(Fore.CYAN + f"Bot: {result['answer']} \n\n ({' | '.join(source)})")
            chat_history += [(query, result["answer"])]

if __name__ == "__main__":
    main()
