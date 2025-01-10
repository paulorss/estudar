import streamlit as st
import pandas as pd
import re
import json
import io
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from docx import Document
from docx.shared import Pt
from typing import Dict, List, Tuple

class Anonimizador:
    def __init__(self):
        self.patterns = {
            'CPF': (r'\d{3}[\.-]?\d{3}[\.-]?\d{3}[-]?\d{2}', '[CPF PROTEGIDO]'),
            'RG': (r'\d{2}[\.-]?\d{3}[\.-]?\d{3}[-]?\d{1}', '[RG PROTEGIDO]'),
            'NOME_COMPLETO': (r'[A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+)*', '[NOME PROTEGIDO]'),
            'NOME_PAI': (r'(?i)(?:pai|father|genitor)\s*:?\s*([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+)*)', '[FILIAÇÃO PROTEGIDA]'),
            'NOME_MAE': (r'(?i)(?:mãe|mae|mother|genitora)\s*:?\s*([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+)*)', '[FILIAÇÃO PROTEGIDA]'),
            'ESTADO_CIVIL': (r'(?i)(solteiro|casado|divorciado|separado|viúvo|viuvo|união estável|uniao estavel)', '[ESTADO CIVIL PROTEGIDO]'),
            'EMAIL': (r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '[EMAIL PROTEGIDO]'),
            'TELEFONE': (r'(?:\+55\s?)?(?:\(\d{2}\)|\d{2})[-\s]?\d{4,5}[-\s]?\d{4}', '[TELEFONE PROTEGIDO]'),
            'CARTAO_CREDITO': (r'\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}', '[CARTÃO PROTEGIDO]'),
            'DATA': (r'\d{2}[-/]\d{2}[-/]\d{4}', '[DATA PROTEGIDA]'),
            'ENDERECO': (r'(?i)(?:Rua|Av|Avenida|Alameda|Al|Praça|R)\s+(?:[A-ZÀ-Ú][a-zà-ú]+\s*)+,?\s*\d+', '[ENDEREÇO PROTEGIDO]'),
            'CEP': (r'\d{5}[-]?\d{3}', '[CEP PROTEGIDO]'),
            'CNH': (r'\d{11}', '[CNH PROTEGIDA]'),
            'TITULO_ELEITOR': (r'\d{12}', '[TÍTULO ELEITOR PROTEGIDO]'),
            'PIS': (r'\d{11}', '[PIS PROTEGIDO]'),
            'RACA': (r'(?i)(branco|preto|pardo|amarelo|indígena|indigena)', '[RAÇA PROTEGIDA]'),
            'RELIGIAO': (r'(?i)(católico|catolico|evangélico|evangelico|espírita|espirita|umbanda|candomblé|candomble|judeu|muçulmano|muculmano|budista|ateu)', '[RELIGIÃO PROTEGIDA]')
        }
        
    def anonimizar_texto(self, texto: str) -> str:
        if not isinstance(texto, str):
            return texto
            
        texto_anonimizado = texto
        for padrao, substituicao in self.patterns.values():
            texto_anonimizado = re.sub(padrao, substituicao, texto_anonimizado)
        return texto_anonimizado

    def processar_csv(self, conteudo: str) -> pd.DataFrame:
        df = pd.read_csv(pd.StringIO(conteudo))
        for coluna in df.columns:
            if df[coluna].dtype == 'object':
                df[coluna] = df[coluna].apply(self.anonimizar_texto)
        return df

    def processar_docx(self, docx_bytes: bytes) -> bytes:
        """Processa arquivo DOCX e retorna versão anonimizada"""
        try:
            # Criar documento temporário a partir dos bytes
            doc_temp = io.BytesIO(docx_bytes)
            doc = Document(doc_temp)
            
            # Criar novo documento para conteúdo anonimizado
            doc_anonimizado = Document()
            
            # Copiar estilos do documento original
            for style in doc.styles:
                if style.type == 1:  # Apenas estilos de parágrafo
                    try:
                        doc_anonimizado.styles.add_style(
                            style.name, style.type, 
                            base_style=doc_anonimizado.styles['Normal']
                        )
                    except:
                        pass  # Ignora se o estilo já existe
            
            # Processar parágrafos
            for para in doc.paragraphs:
                # Adicionar parágrafo com mesmo estilo
                novo_para = doc_anonimizado.add_paragraph(
                    self.anonimizar_texto(para.text),
                    style=para.style.name
                )
                
                # Copiar formatação de runs
                for idx, run in enumerate(para.runs):
                    if idx < len(novo_para.runs):
                        novo_run = novo_para.runs[idx]
                        novo_run.bold = run.bold
                        novo_run.italic = run.italic
                        novo_run.underline = run.underline
                        if run.font.size:
                            novo_run.font.size = run.font.size
            
            # Processar tabelas
            for tabela in doc.tables:
                nova_tabela = doc_anonimizado.add_table(
                    rows=len(tabela.rows),
                    cols=len(tabela.columns)
                )
                nova_tabela.style = tabela.style
                
                for i, linha in enumerate(tabela.rows):
                    for j, celula in enumerate(linha.cells):
                        nova_celula = nova_tabela.cell(i, j)
                        nova_celula.text = self.anonimizar_texto(celula.text)
            
            # Salvar documento anonimizado
            output = io.BytesIO()
            doc_anonimizado.save(output)
            return output.getvalue()
            
        except Exception as e:
            st.error(f"Erro ao processar DOCX: {str(e)}")
            return docx_bytes  # Retorna o documento original em caso de erro
        """Processa arquivo PDF e retorna versão anonimizada"""
        try:
            # Criar PDF reader e writer
            pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
            pdf_writer = PdfWriter()
            
            # Processar cada página
            for pagina in pdf_reader.pages:
                # Extrair texto da página
                texto = pagina.extract_text()
                if texto:
                    # Anonimizar o texto
                    texto_anonimizado = self.anonimizar_texto(texto)
                    
                    # Criar nova página com texto anonimizado
                    packet = io.BytesIO()
                    c = canvas.Canvas(packet, pagesize=letter)
                    
                    # Quebrar o texto em linhas para melhor formatação
                    linhas = texto_anonimizado.split('\n')
                    y = 750  # Posição inicial Y
                    for linha in linhas:
                        if linha.strip():  # Ignorar linhas vazias
                            c.drawString(50, y, linha)
                            y -= 15  # Espaçamento entre linhas
                    
                    c.save()
                    packet.seek(0)
                    
                    # Adicionar nova página ao PDF
                    nova_pagina = PdfReader(packet).pages[0]
                    pdf_writer.add_page(nova_pagina)
                else:
                    # Se não houver texto, manter a página original
                    pdf_writer.add_page(pagina)
            
            # Salvar PDF anonimizado
            output = io.BytesIO()
            pdf_writer.write(output)
            return output.getvalue()
            
        except Exception as e:
            st.error(f"Erro ao processar PDF: {str(e)}")
            return pdf_bytes  # Retorna o PDF original em caso de erro

    def processar_json(self, conteudo: str) -> dict:
        dados = json.loads(conteudo)
        
        def anonimizar_dict(d):
            if isinstance(d, dict):
                return {k: anonimizar_dict(v) for k, v in d.items()}
            elif isinstance(d, list):
                return [anonimizar_dict(v) for v in d]
            elif isinstance(d, str):
                return self.anonimizar_texto(d)
            else:
                return d
                
        return anonimizar_dict(dados)

def main():
    st.title("Anonimizador de Dados - LGPD")
    
    st.markdown("""
    ### Dados detectados e anonimizados:
    
    **Documentos:**
    - CPF
    - RG
    - CNH
    - Título de Eleitor
    - PIS
    - Cartão de Crédito
    
    **Dados Pessoais:**
    - Nomes Completos
    - Nome do Pai
    - Nome da Mãe
    - Estado Civil
    - Email
    - Telefone
    - Endereço
    - CEP
    - Data de Nascimento
    
    **Dados Sensíveis (Art. 5º LGPD):**
    - Raça/Etnia
    - Religião
    """)
    
    anonimizador = Anonimizador()
    
    # Área para entrada de texto
    st.header("Anonimização de Texto")
    texto_input = st.text_area("Digite o texto a ser anonimizado:", height=150)
    if st.button("Anonimizar Texto") and texto_input:
        texto_anonimizado = anonimizador.anonimizar_texto(texto_input)
        st.text_area("Texto Anonimizado:", texto_anonimizado, height=150)
    
    # Upload de arquivo
    st.header("Anonimização de Arquivo")
    arquivo = st.file_uploader("Escolha um arquivo (.csv, .txt, .json, .pdf)", type=['csv', 'txt', 'json', 'pdf'])
    
    if arquivo is not None:
        try:
            conteudo = arquivo.getvalue()
            
            if arquivo.name.endswith('.csv'):
                conteudo_texto = conteudo.decode('utf-8')
                resultado = anonimizador.processar_csv(conteudo_texto)
                csv = resultado.to_csv(index=False)
                st.download_button(
                    "Download CSV Anonimizado",
                    csv,
                    "anonimizado.csv",
                    "text/csv"
                )
            elif arquivo.name.endswith('.json'):
                conteudo_texto = conteudo.decode('utf-8')
                resultado = anonimizador.processar_json(conteudo_texto)
                json_str = json.dumps(resultado, ensure_ascii=False, indent=2)
                st.download_button(
                    "Download JSON Anonimizado",
                    json_str,
                    "anonimizado.json",
                    "application/json"
                )
            elif arquivo.name.endswith('.docx'):
                docx_anonimizado = anonimizador.processar_docx(conteudo)
                st.download_button(
                    "Download DOCX Anonimizado",
                    docx_anonimizado,
                    "anonimizado.docx",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
                pdf_anonimizado = anonimizador.processar_pdf(conteudo)
                st.download_button(
                    "Download PDF Anonimizado",
                    pdf_anonimizado,
                    "anonimizado.pdf",
                    "application/pdf"
                )
            else:  # .txt
                conteudo_texto = conteudo.decode('utf-8')
                texto_anonimizado = anonimizador.anonimizar_texto(conteudo_texto)
                st.download_button(
                    "Download TXT Anonimizado",
                    texto_anonimizado,
                    "anonimizado.txt",
                    "text/plain"
                )
            
            st.success("Arquivo processado com sucesso!")
            
        except Exception as e:
            st.error(f"Erro ao processar arquivo: {str(e)}")

if __name__ == "__main__":
    main()
