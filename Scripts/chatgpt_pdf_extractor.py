import os
import logging
from pathlib import Path

import openai
from dotenv import load_dotenv
from openai import OpenAI


# Configuração de log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Caminhos fixos (editáveis) ===
PDF_PATH = Path(r"C:\Users\Milson Yuji Aoki\OneDrive - Universidade Federal do ABC\Dev_yuji\ACADEMICO\UFABC\2° QUAD\BECM\3 - Danilo Marcondes\Danilo Marcondes .pdf")
OUTPUT_PATH = Path(r"C:\Users\Milson Yuji Aoki\OneDrive - Universidade Federal do ABC\Dev_yuji\ACADEMICO\UFABC\2° QUAD\BECM\3 - Danilo Marcondes\danilo marcondes.txt")

def load_api_key(env_var: str = "OPENAI_API_KEY") -> None:
    """Carrega a chave da API do .env e configura o cliente OpenAI."""
    load_dotenv()
    key = os.getenv(env_var)
    if not key:
        logger.error(f"{env_var} não encontrado no .env.")
        raise EnvironmentError(f"{env_var} não definido.")
    openai.api_key = key

def upload_file_to_openai(client: OpenAI, file_path: Path) -> str:
    """Envia o arquivo PDF para a OpenAI e retorna o ID do arquivo."""
    logger.info(f"Enviando arquivo para OpenAI: {file_path}")
    try:
        with open(file_path, "rb") as file:
            file_obj = client.files.create(file=file, purpose="assistants")
        logger.info(f"Arquivo enviado com id: {file_obj.id}")
        return file_obj.id
    except Exception as e:
        logger.error(f"Falha ao enviar arquivo: {e}")
        raise

def request_response_for_file(client: OpenAI, file_id: str, prompt: str, model: str = "gpt-4o") -> str:
    """Solicita ao modelo que processe o PDF enviado."""
    logger.info("Solicitando resposta da OpenAI para arquivo enviado")
    try:
        # Cria um assistant para processar o arquivo
        assistant = client.beta.assistants.create(
            name="PDF Extractor",
            instructions="Você é um assistente que extrai texto de documentos PDF.",
            model=model,
            tools=[{"type": "file_search"}]
        )
        
        # Cria uma thread
        thread = client.beta.threads.create()
        
        # Adiciona mensagem com o arquivo
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=prompt,
            attachments=[{"file_id": file_id, "tools": [{"type": "file_search"}]}]
        )
        
        # Executa o assistant
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id
        )
        
        # Aguarda a conclusão
        import time
        while run.status in ['queued', 'in_progress']:
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        
        if run.status == 'completed':
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            response_message = messages.data[0]
            # Extrai o texto do conteúdo da mensagem
            for content in response_message.content:
                if content.type == 'text':
                    return content.text.value
            # Se não encontrou texto, retorna uma representação string
            return str(response_message.content[0])
        else:
            raise Exception(f"Run falhou com status: {run.status}")
            
    except Exception as e:
        logger.error(f"Erro na chamada à API: {e}")
        raise

def save_text(content: str, output_path: Path) -> None:
    """Salva o texto processado no arquivo TXT."""
    logger.info(f"Salvando resposta em: {output_path}")
    output_path.write_text(content, encoding="utf-8")

def main():
    if not PDF_PATH.exists():
        logger.error(f"PDF não encontrado: {PDF_PATH}")
        raise FileNotFoundError(str(PDF_PATH))

    load_api_key()
    client = OpenAI(api_key=openai.api_key)

    prompt = "Extraia o conteúdo completo deste documento exatamente como está, sem mudanças."
    file_id = upload_file_to_openai(client, PDF_PATH)
    result_text = request_response_for_file(client, file_id, prompt)
    save_text(result_text, OUTPUT_PATH)
    logger.info("Processo concluído com sucesso.")

if __name__ == "__main__":
    main()
