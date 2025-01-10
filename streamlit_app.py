import streamlit as st
import pandas as pd
import json
import io
from typing import List, Dict, Any, Optional
from presidio_analyzer import PatternRecognizer, Pattern, RecognizerResult
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from docx import Document
from docx.shared import Pt

class SimpleAnalyzer:
    """Analisador simplificado baseado em padrões"""
    
    def __init__(self):
        self.recognizers = self._create_recognizers()
    
    def _create_recognizers(self) -> List[PatternRecognizer]:
        """Cria reconhecedores de padrões customizados para LGPD"""
        patterns = {
            # Documentos
            "CPF": r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}",
            "RG": r"\d{2}\.?\d{3}\.?\d{3}[-]?\d{1}|\d{2}\.?\d{3}\.?\d{3}",
            "CNH": r"\d{11}",
            "TITULO_ELEITOR": r"\d{4}\s?\d{4}\s?\d{4}",
            "PIS": r"\d{3}\.?\d{5}\.?\d{2}[-]?\d{1}",
            "PASSAPORTE": r"[A-Z]{2}\d{6}",
            
            # Dados Pessoais
            "NOME_COMPLETO": r"(?i)([A-ZÀ-Ú][a-zà-ú]+(?:\s+(?:dos?|das?|de|e|[A-ZÀ-Ú][a-zà-ú]+))+)",
            "NOME_PAIS": r"(?i)(?:pai|mãe|mae|genitor[a]?|father|mother)\s*:?\s*([A-ZÀ-Ú][a-zà-ú]+(?: (?:dos?|das?|de|e|[A-ZÀ-Ú][a-zà-ú]+))+)",
            "ESTADO_CIVIL": r"(?i)(solteiro|casado|divorciado|separado|viúvo|viuvo|união estável|uniao estavel)",
            "PROFISSAO": r"(?i)profiss[ãa]o\s*:?\s*([A-ZÀ-Ú][a-zà-ú]+(?: [A-ZÀ-Ú][a-zà-ú]+)*)",
            
            # Dados de Contato
            "EMAIL": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            "TELEFONE": r"(?:\+55\s?)?(?:\(?\d{2}\)?[-\s]?)?\d{4,5}[-\s]?\d{4}",
            "WHATSAPP": r"(?i)(?:whatsapp|wpp|zap)?\s*:?\s*(?:\+55\s?)?(?:\(?\d{2}\)?[-\s]?)?\d{4,5}[-\s]?\d{4}",
            
            # Dados Financeiros
            "CARTAO_CREDITO": r"\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}",
            "CONTA_BANCARIA": r"(?i)(?:ag[êe]ncia|conta)\s*:?\s*\d{1,4}[-.]?\d{1,10}",
            "RENDA": r"(?i)(?:sal[áa]rio|renda)\s*:?\s*R?\$?\s*\d+(?:\.\d{3})*(?:,\d{2})?",
            
            # Endereço
            "ENDERECO": r"(?i)(?:Rua|Av|Avenida|Alameda|Al|Praça|R|Travessa|Rod|Rodovia)\s+(?:[A-ZÀ-Ú][a-zà-ú]+\s*)+,?\s*\d+",
            "CEP": r"\d{5}[-]?\d{3}",
            "BAIRRO": r"(?i)(?:Bairro|B\.)\s*:?\s*[A-ZÀ-Ú][a-zà-ú]+(?: [A-ZÀ-Ú][a-zà-ú]+)*",
            
            # Dados Sensíveis
            "RACA": r"(?i)(branco|preto|pardo|amarelo|indígena|indigena|negro)",
            "RELIGIAO": r"(?i)(católico|catolico|evangélico|evangelico|espírita|espirita|umbanda|candomblé|candomble|judeu|muçulmano|muculmano|budista|ateu)",
            "ORIENTACAO_SEXUAL": r"(?i)(heterossexual|homossexual|bissexual|gay|lésbica|lesbica|trans(?:exual|gênero|genero)?)",
            
            # Datas
            "DATA": r"\d{2}[-/]\d{2}[-/]\d{4}|\d{2}\s+(?:de\s+)?(?:janeiro|fevereiro|março|marco|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\s+(?:de\s+)?\d{4}",
            "NASCIMENTO": r"(?i)(?:nascid[oa](?:\s+em)?|data\s+de\s+nascimento)\s*:?\s*\d{2}[-/]\d{2}[-/]\d{4}"
        }
        
        recognizers = []
        for entity_type, pattern in patterns.items():
            recognizer = PatternRecognizer(
                supported_language="pt",
                patterns=[
                    Pattern(
                        name=f"{entity_type}_pattern",
                        regex=pattern,
                        score=0.85
                    )
                ]
            )
            # Armazena o tipo de entidade como atributo
            recognizer.entity_type = entity_type
            recognizers.append(recognizer)
            
        return recognizers
    
    def analyze(self, text: str) -> List[RecognizerResult]:
        """Analisa texto em busca de padrões"""
        results = []
        for recognizer in self.recognizers:
            # Usa o entity_type armazenado em vez de supported_entity
            results.extend(recognizer.analyze(text=text, entities=[recognizer.entity_type]))
        return results

class Anonimizador:
    def __init__(self):
        """Inicializa o anonimizador"""
        self.analyzer = SimpleAnalyzer()
        self.anonymizer = AnonymizerEngine()
        self.operator_config = self._get_operator_config()
    
    def _get_operator_config(self) -> Dict[str, OperatorConfig]:
        """Retorna configurações de anonimização para cada tipo de dado"""
        return {
            # Documentos - Mascaramento parcial
            "CPF": OperatorConfig("mask", {"chars_to_mask": 9, "masking_char": "*", "from_end": False}),
            "RG": OperatorConfig("mask", {"chars_to_mask": 7, "masking_char": "*", "from_end": False}),
            "CNH": OperatorConfig("mask", {"chars_to_mask": 8, "masking_char": "*", "from_end": False}),
            "TITULO_ELEITOR": OperatorConfig("mask", {"chars_to_mask": 8, "masking_char": "*", "from_end": False}),
            "PIS": OperatorConfig("mask", {"chars_to_mask": 9, "masking_char": "*", "from_end": False}),
            "PASSAPORTE": OperatorConfig("mask", {"chars_to_mask": 6, "masking_char": "*", "from_end": False}),
            
            # Dados Pessoais - Substituição total
            "NOME_COMPLETO": OperatorConfig("replace", {"new_value": "[NOME PROTEGIDO]"}),
            "NOME_PAIS": OperatorConfig("replace", {"new_value": "[FILIAÇÃO PROTEGIDA]"}),
            "ESTADO_CIVIL": OperatorConfig("replace", {"new_value": "[ESTADO CIVIL PROTEGIDO]"}),
            "PROFISSAO": OperatorConfig("replace", {"new_value": "[PROFISSÃO PROTEGIDA]"}),
            
            # Dados de Contato - Mascaramento parcial
            "EMAIL": OperatorConfig("mask", {"chars_to_mask": -1, "masking_char": "*", "from_end": False}),
            "TELEFONE": OperatorConfig("mask", {"chars_to_mask": 8, "masking_char": "*", "from_end": False}),
            "WHATSAPP": OperatorConfig("mask", {"chars_to_mask": 8, "masking_char": "*", "from_end": False}),
            
            # Dados Financeiros - Mascaramento total
            "CARTAO_CREDITO": OperatorConfig("mask", {"chars_to_mask": 12, "masking_char": "*", "from_end": False}),
            "CONTA_BANCARIA": OperatorConfig("replace", {"new_value": "[DADOS BANCÁRIOS PROTEGIDOS]"}),
            "RENDA": OperatorConfig("replace", {"new_value": "[INFORMAÇÃO FINANCEIRA PROTEGIDA]"}),
            
            # Endereço - Substituição
            "ENDERECO": OperatorConfig("replace", {"new_value": "[ENDEREÇO PROTEGIDO]"}),
            "CEP": OperatorConfig("mask", {"chars_to_mask": 5, "masking_char": "*", "from_end": False}),
            "BAIRRO": OperatorConfig("replace", {"new_value": "[BAIRRO PROTEGIDO]"}),
            
            # Dados Sensíveis - Substituição total
            "RACA": OperatorConfig("replace", {"new_value": "[DADO SENSÍVEL - RAÇA]"}),
            "RELIGIAO": OperatorConfig("replace", {"new_value": "[DADO SENSÍVEL - RELIGIÃO]"}),
            "ORIENTACAO_SEXUAL": OperatorConfig("replace", {"new_value": "[DADO SENSÍVEL - ORIENTAÇÃO SEXUAL]"}),
            
            # Datas - Substituição
            "DATA": OperatorConfig("replace", {"new_value": "[DATA PROTEGIDA]"}),
            "NASCIMENTO": OperatorConfig("replace", {"new_value": "[DATA DE NASCIMENTO PROTEGIDA]"}),
            
            # Padrão para outros tipos de dados
            "DEFAULT": OperatorConfig("replace", {"new_value": "[DADO PROTEGIDO]"})
        }
    
    def anonimizar_texto(self, texto: str) -> str:
        """Anonimiza texto"""
        if not isinstance(texto, str) or not texto.strip():
            return texto
            
        try:
            # Analisar texto
            resultados = self.analyzer.analyze(texto)
            
            # Anonimizar texto
            texto_anonimizado = self.anonymizer.anonymize(
                text=texto,
                analyzer_results=resultados,
                operators=self.operator_config
            )
            
            return texto_anonimizado.text
        except Exception as e:
            st.error(f"Erro ao anonimizar texto: {str(e)}")
            return texto

    def processar_csv(self, conteudo: str) -> pd.DataFrame:
        """Processa arquivo CSV"""
        df = pd.read_csv(pd.StringIO(conteudo))
        for coluna in df.columns:
            if df[coluna].dtype == 'object':
                df[coluna] = df[coluna].apply(lambda x: self.anonimizar_texto(str(x)) if pd.notna(x) else x)
        return df

    def processar_json(self, conteudo: str) -> dict:
        """Processa arquivo JSON"""
        dados = json.loads(conteudo)
        
        def anonimizar_dict(d: Any) -> Any:
            if isinstance(d, dict):
                return {k: anonimizar_dict(v) for k, v in d.items()}
            elif isinstance(d, list):
                return [anonimizar_dict(v) for v in d]
            elif isinstance(d, str):
                return self.anonimizar_texto(d)
            else:
                return d
                
        return anonimizar_dict(dados)

    def processar_pdf(self, pdf_bytes: bytes) -> bytes:
        """Processa arquivo PDF"""
        try:
            pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
            pdf_writer = PdfWriter()
            
            for pagina in pdf_reader.pages:
                texto = pagina.extract_text()
                if texto:
                    texto_anonimizado = self.anonimizar_texto(texto)
                    
                    packet = io.BytesIO()
                    c = canvas.Canvas(packet, pagesize=letter)
                    
                    # Ajuste as coordenadas Y para começar do topo
                    y = 750
                    for linha in texto_anonimizado.split('\n'):
                        if linha.strip():
                            c.drawString(50, y, linha)
                            y -= 15  # Ajuste o espaçamento entre linhas conforme necessário
                    
                    c.save()
                    packet.seek(0)
                    nova_pagina = PdfReader(packet).pages[0]
                    pdf_writer.add_page(nova_pagina)
                else:
                    pdf_writer.add_page(pagina)
            
            output = io.BytesIO()
            pdf_writer.write(output)
            return output.getvalue()
            
        except Exception as e:
            st.error(f"Erro ao processar PDF: {str(e)}")
            return pdf_bytes

    def processar_docx(self, docx_bytes: bytes) -> bytes:
        """Processa arquivo DOCX"""
        try:
            doc_temp = io.BytesIO(docx_bytes)
            doc = Document(doc_temp)
            doc_anonimizado = Document()
            
            # Copiar estilos
            for style in doc.styles:
                if style.type == 1:  # Paragraph style
                    try:
                        doc_anonimizado.styles.add_style(
                            style.name, style.type,
                            base_style=doc_anonimizado.styles['Normal']
                        )
                    except:
                        pass
                        # Processar parágrafos
            for para in doc.paragraphs:
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
            
            output = io.BytesIO()
            doc_anonimizado.save(output)
            return output.getvalue()
            
        except Exception as e:
            st.error(f"Erro ao processar DOCX: {str(e)}")
            return docx_bytes

def main():
    st.title("Anonimizador de Dados - LGPD")
    
    st.markdown("""
    ### Dados detectados e anonimizados:
    
    **Documentos:**
    - CPF (mascaramento parcial)
    - RG (mascaramento parcial)
    - CNH (mascaramento parcial)
    - Título de Eleitor (mascaramento parcial)
    - PIS (mascaramento parcial)
    - Passaporte (mascaramento parcial)
    
    **Dados Pessoais:**
    - Nomes completos
    - Nome dos pais
    - Estado civil
    - Profissão
    
    **Dados de Contato:**
    - E-mails (mascaramento)
    - Telefones (mascaramento)
    - WhatsApp (mascaramento)
    
    **Dados Financeiros:**
    - Cartões de crédito (mascaramento)
    - Contas bancárias
    - Informações de renda
    
    **Endereço:**
    - Endereços completos
    - CEP (mascaramento)
    - Bairro
    
    **Dados Sensíveis:**
    - Raça/Cor
    - Religião
    - Orientação Sexual
    
    **Datas:**
    - Datas em geral
    - Data de nascimento
    """)
    
    anonimizador = Anonimizador()
    
    st.header("Anonimização de Texto")
    texto_input = st.text_area("Digite o texto a ser anonimizado:", height=150)
    if st.button("Anonimizar Texto") and texto_input:
        texto_anonimizado = anonimizador.anonimizar_texto(texto_input)
        st.text_area("Texto Anonimizado:", texto_anonimizado, height=150)
    
    st.header("Anonimização de Arquivo")
    arquivo = st.file_uploader(
        "Escolha um arquivo (.csv, .txt, .json, .pdf, .docx)",
        type=['csv', 'txt', 'json', 'pdf', 'docx']
    )
    
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
                
            elif arquivo.name.endswith('.pdf'):
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
