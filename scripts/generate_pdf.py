import os
import subprocess

def generate_pdf():
    docs_dir = "docs"
    output_md = os.path.join(docs_dir, "MLflow_Light_Manual.md")
    output_pdf = os.path.join(docs_dir, "MLflow_Light_Manual.pdf")
    
    # Ordem de leitura da documentação
    files_to_merge = [
        "README.md",
        os.path.join(docs_dir, "setup.md"),
        os.path.join(docs_dir, "architecture.md"),
        os.path.join(docs_dir, "usage_ml.md"),
        os.path.join(docs_dir, "usage_llm.md"),
        os.path.join(docs_dir, "usage_spans.md"),
        os.path.join(docs_dir, "usage_llm_judge.md"),
        os.path.join(docs_dir, "INSTRUCOES_AGENTES_IA.md"),
        os.path.join(docs_dir, "high_concurrency_guide.md"),
        os.path.join("examples", "README.md")
    ]
    
    print("📚 Consolidando os arquivos de documentação...")
    
    with open(output_md, "w", encoding="utf-8") as outfile:
        # Adiciona um título principal e índice
        outfile.write("<h1 align='center'>Manual Oficial: MLflow Light</h1>\n\n")
        outfile.write("<p align='center'><i>Visão Geral, Arquitetura, Setup, Guias de Uso (ML, LLM, Spans, Judge), Agentes de IA, Alta Concorrência e Códigos de Exemplo</i></p>\n\n")
        
        outfile.write("## Sumário\n")
        outfile.write("1. **Visão Geral e Repositório**\n")
        outfile.write("2. **Guia de Setup e Instalação**\n")
        outfile.write("3. **Arquitetura do Sistema**\n")
        outfile.write("4. **Guia de Uso: Modelos ML Tradicionais**\n")
        outfile.write("5. **Guia de Uso: LLMs e APIs (Gemini/OpenAI)**\n")
        outfile.write("6. **Guia de Uso: Spans e Árvores de Rastreamento (RAG/Agentes)**\n")
        outfile.write("7. **Guia de Uso: LLM as a Judge (Avaliações Automatizadas)**\n")
        outfile.write("8. **Instruções e Regras para Agentes Autônomos de IA**\n")
        outfile.write("9. **Guia de Alta Concorrência (Cloud Run/SQL)**\n")
        outfile.write("10. **Galeria de Códigos de Exemplo Prontos**\n\n")
        outfile.write("---\n\n")
        outfile.write("---\n\n")
        
        # Consolida os Markdowns
        for file_path in files_to_merge:
            if os.path.exists(file_path):
                print(f"Lendo {file_path}...")
                with open(file_path, "r", encoding="utf-8") as infile:
                    content = infile.read()
                    outfile.write(content)
                    outfile.write("\n\n---\n\n") # Separador de páginas/seções
            else:
                print(f"⚠️ Aviso: Arquivo {file_path} não encontrado, pulando...")

        # Adiciona os códigos de exemplo formatados
        print("Lendo códigos de exemplo...")
        outfile.write("# Galeria de Códigos de Exemplo\n\n")
        outfile.write("Abaixo estão os scripts de referência para você copiar e colar nos seus projetos.\n\n")
        
        for file in os.listdir("examples"):
            if file.endswith(".py") or file.endswith(".mjs"):
                file_path = os.path.join("examples", file)
                print(f"Injetando código: {file_path}")
                
                # Determina a linguagem para o highlight correto
                lang = "python" if file.endswith(".py") else "javascript"
                
                with open(file_path, "r", encoding="utf-8") as infile:
                    code_content = infile.read()
                    
                outfile.write(f"## {file}\n\n")
                outfile.write(f"```{lang}\n")
                outfile.write(code_content)
                outfile.write("\n```\n\n---\n\n")

    print(f"✅ Arquivo Markdown consolidado criado em: {output_md}")
    print("O arquivo foi gerado com sucesso. Para exportá-lo, abra o arquivo no VS Code e use a extensão 'Markdown PDF'.")

if __name__ == "__main__":
    generate_pdf()
