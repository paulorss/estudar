import streamlit as st
import pandas as pd
import json
import io
from typing import List, Dict, Any, Optional
import spacy
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry, PatternRecognizer, Pattern, EntityRecognizer
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from docx import Document
from docx.shared import Pt

class PresidioConfig:
    """Configuração do Presidio com suporte a reconhecedores customizados para LGPD"""
    
    @staticmethod
    def get_custom_patterns() -> Dict[str, Pattern]:
        return {
            "CPF": Pattern(
                name="cpf_pattern",
                regex=r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}",
                score=0.9
            ),
            "RG": Pattern(
                name="rg_pattern",
                regex=r"\d{2}\.?\d{3}\.?\d{3}-?\d{1}",
                score=0.9
            ),
            "CNH": Pattern(
                name="cnh_pattern",
                regex=r"\d{11}",
                score=0.8
            ),
            "ESTADO_CIVIL": Pattern(
                name="estado_civil_pattern",
                regex=r"(?i)(solteiro|casado|divorciado|separado|viúvo|viuvo|união estável|uniao estavel)",
                score=0.7
            ),
            "NOME_PAIS": Pattern(
                name="nome_pais_pattern",
                regex=r"(?i)(pai|mae|mãe|father|mother|genitor|genitora)\s*:?\s*([A-ZÀ-Ú][a-zà-ú]+ (?:[A-ZÀ-Ú][a-zà-ú]+ )?[A-ZÀ-Ú][a-zà-ú]+)",
                score=0.8
            )
        }
    
    @staticmethod
    def get_operator_config() -> Dict[str, OperatorConfig]:
        return {
            "PERSON": OperatorConfig("replace", {"new_value": "[NOME PROTEGIDO]"}),
            "CPF": OperatorConfig("mask", {"chars_to_mask": 9, "masking_char": "*", "from_end": False}),
            "RG": OperatorConfig("mask", {"chars_to_mask": 7, "masking_char": "*", "from_end": False}),
            "CNH": OperatorConfig("mask", {"chars_to_mask": 8, "masking_char": "*", "from_end": False}),
            "ESTADO_CIVIL": OperatorConfig("replace", {"new_value": "[ESTADO CIVIL PROTEGIDO]"}),
            "NOME_PAIS": OperatorConfig("replace", {"new_value": "[FILIAÇÃO PROTEGIDA]"}),
            "EMAIL_ADDRESS": OperatorConfig("mask", {"chars_to_mask": -1, "masking_char": "*", "from_end": False}),
            "PHONE_NUMBER": OperatorConfig("mask", {"chars_to_mask": 8, "masking_char": "*", "from_end": False}),
            "CREDIT_CARD": OperatorConfig("mask", {"chars_to_mask": 12, "masking_char": "*", "from_end": False}),
            "LOCATION": OperatorConfig("replace", {"new_value": "[LOCALIZAÇÃO PROTEGIDA]"}),
            "DATE_TIME": OperatorConfig("replace", {"new_value": "[DATA PROTEGIDA]"}),
            "NRP": OperatorConfig("replace", {"new_value": "[DOCUMENTO PROTEGIDO]"}),
            "DEFAULT": OperatorConfig("replace", {"new_value": "[DADO PROTEGIDO]"})
        }

class Anonimizador:
    def __init__(self):
        """Inicializa o anonimizador com Presidio"""
        # Configurar analisador
        registry = RecognizerRegistry()
        self.add_custom_recognizers(registry)
        
        # Inicializar engines
        self.analyzer = AnalyzerEngine(registry=registry)
        self.anonymizer = AnonymizerEngine()
        
        # Carregar configurações
        self.operator_config = PresidioConfig.get_operator_config()
    
    def add_custom_recognizers(self, registry: RecognizerRegistry) -> None:
        """Adiciona reconhecedores customizados ao registro"""
        patterns = PresidioConfig.get_custom_patterns()
        for entity_type, pattern in patterns.items():
            recognizer = PatternRecognizer(
                supported_entity=entity_type,
                patterns=[pattern]
            )
            registry.add_recognizer(recognizer)
    
    def anonimizar_texto(self, texto: str) -> str:
        """Anonimiza texto usando Presidio"""
        if not isinstance(texto, str) or not texto.strip():
            return texto
            
        try:
            # Analisar texto
            resultados = self.analyzer.analyze(
                text=texto,
                language='pt'
            )
            
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
                df[coluna] = df[coluna].apply(self.anonimizar_texto)
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
                    y = 750  # Posição inicial Y
                    for linha in texto_anonimizado.split('\n'):
                        if linha.strip():
                            c.drawString(50, y, linha)
                            y -= 15
                    
                    c.save()
                    packet.seek(0)
                    nova_pagina = PdfReader(packet).pages[0]
                    pdf_writer.add_page(nova_pagina)
                else:
                    pdf_writer.add_page(pagina)
            
            # Salvar PDF anonimizado
            output = io.BytesIO()
            pdf_writer.write(output)
            return output.getvalue()
            
        except Exception as e:
            st.error(f"Erro ao processar PDF: {str(e)}")
            return pdf_bytes

    def processar_docx(self, docx_bytes: bytes) -> bytes:
        """Processa arquivo DOCX"""
        try:
            # Criar documento
            doc_temp = io.BytesIO(docx_bytes)
            doc = Document(doc_temp)
            doc_anonimizado = Document()
            
            # Copiar estilos
            for style in doc.styles:
                if style.type == 1:
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
                
                # Copiar formatação
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
            
            # Salvar documento
            output = io.BytesIO()
            doc_anonimizado.save(output)
            return output.getvalue()
            
        except Exception as e:
            st.error(f"Erro ao processar DOCX: {str(e)}")
            return docx_bytes

def main():
    st.title("Anonimizador de Dados - LGPD com Presidio")
    
    st.markdown("""
    ### Dados detectados e anonimizados:
    
    **Documentos:**
    - CPF (mascaramento parcial)
    - RG (mascaramento parcial)
    - CNH (mascaramento parcial)
    - Cartões de crédito (mascaramento parcial)
    
    **Dados Pessoais:**
    - Nomes completos
    - Nome dos pais
    - Estado civil
    - E-mails (mascaramento)
    - Telefones (mascaramento)
    - Endereços
    - Datas
    
    **Dados Sensíveis (Art. 5º LGPD):**
    - Detecção automática de dados sensíveis via Presidio
    """)
    
    # Inicializar anonimizador
    anonimizador = Anonimizador()
    
    # Interface para entrada de texto
    st.header("Anonimização de Texto")
    texto_input = st.text_area("Digite o texto a ser anonimizado:", height=150)
    if st.button("Anonimizar Texto") and texto_input:
        texto_anonimizado = anonimizador.anonimizar_texto(texto_input)
        st.text_area("Texto Anonimizado:", texto_anonimizado, height=150)
    
    # Interface para upload de arquivo
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
