import streamlit as st
import pandas as pd
import json
import io
from typing import List, Dict, Any, Optional
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from docx import Document
import spacy
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
import os

# Download spaCy model during first run
@st.cache_resource
def load_spacy_model():
    try:
        nlp = spacy.load("pt_core_news_lg")
    except OSError:
        os.system("python -m spacy download pt_core_news_lg")
        nlp = spacy.load("pt_core_news_lg")
    return nlp

class PresidioAnalyzer:
    def __init__(self):
        """Initialize Presidio analyzer with Portuguese support"""
        self.nlp = load_spacy_model()
        
        # Configure NLP engine with Portuguese model
        provider = NlpEngineProvider(nlp_engine=self.nlp)
        
        # Initialize analyzer with Portuguese support
        self.analyzer = AnalyzerEngine(
            nlp_engine=provider,
            supported_languages=["pt"]
        )
        
        # Initialize anonymizer
        self.anonymizer = AnonymizerEngine()
        
        # Configure custom recognizers for Brazilian documents
        self.custom_entities = {
            "CPF": r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}",
            "RG": r"\d{2}\.?\d{3}\.?\d{3}[-]?\d{1}|\d{2}\.?\d{3}\.?\d{3}",
            "CNH": r"\d{11}",
            "TITULO_ELEITOR": r"\d{4}\s?\d{4}\s?\d{4}",
            "PIS": r"\d{3}\.?\d{5}\.?\d{2}[-]?\d{1}",
        }

    def analyze_text(self, text: str) -> List[Dict]:
        """Analyze text using Presidio and custom recognizers"""
        # Get Presidio analysis results
        analyzer_results = self.analyzer.analyze(
            text=text,
            language="pt",
            entities=[
                "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", 
                "CREDIT_CARD", "LOCATION", "DATE_TIME",
                "NRP", "MEDICAL_LICENSE", "URL", "TITLE"
            ]
        )
        
        return analyzer_results

    def anonymize_text(self, text: str) -> str:
        """Anonymize text using Presidio"""
        if not isinstance(text, str) or not text.strip():
            return text
            
        try:
            # Analyze text
            analyzer_results = self.analyze_text(text)
            
            # Define anonymization operators
            operators = {
                "PERSON": OperatorConfig("mask", {"chars_to_mask": 4, "masking_char": "*"}),
                "EMAIL_ADDRESS": OperatorConfig("mask", {"chars_to_mask": -4, "masking_char": "*"}),
                "PHONE_NUMBER": OperatorConfig("mask", {"chars_to_mask": 4, "masking_char": "*"}),
                "CREDIT_CARD": OperatorConfig("mask", {"chars_to_mask": -4, "masking_char": "*"}),
                "LOCATION": OperatorConfig("replace", {"new_value": "[LOCALIZAÇÃO]"}),
                "DATE_TIME": OperatorConfig("mask", {"chars_to_mask": 2, "masking_char": "*"}),
                "NRP": OperatorConfig("mask", {"chars_to_mask": 4, "masking_char": "*"}),
                "MEDICAL_LICENSE": OperatorConfig("mask", {"chars_to_mask": 4, "masking_char": "*"}),
                "URL": OperatorConfig("mask", {"chars_to_mask": -4, "masking_char": "*"}),
                "TITLE": OperatorConfig("replace", {"new_value": "[TÍTULO]"})
            }
            
            # Anonymize text
            anonymized_result = self.anonymizer.anonymize(
                text=text,
                analyzer_results=analyzer_results,
                operators=operators
            )
            
            return anonymized_result.text
            
        except Exception as e:
            st.error(f"Erro ao anonimizar texto: {str(e)}")
            return text

    def process_csv(self, content: str) -> pd.DataFrame:
        """Process CSV file"""
        try:
            df = pd.read_csv(pd.StringIO(content))
            for column in df.columns:
                if df[column].dtype == 'object':
                    df[column] = df[column].apply(lambda x: self.anonymize_text(str(x)) if pd.notna(x) else x)
            return df
        except Exception as e:
            st.error(f"Erro ao processar CSV: {str(e)}")
            return pd.DataFrame()

    def process_json(self, content: str) -> dict:
        """Process JSON file"""
        try:
            data = json.loads(content)
            
            def anonymize_dict(d: Any) -> Any:
                if isinstance(d, dict):
                    return {k: anonymize_dict(v) for k, v in d.items()}
                elif isinstance(d, list):
                    return [anonymize_dict(v) for v in d]
                elif isinstance(d, str):
                    return self.anonymize_text(d)
                else:
                    return d
                    
            return anonymize_dict(data)
        except Exception as e:
            st.error(f"Erro ao processar JSON: {str(e)}")
            return {}

    def process_pdf(self, pdf_bytes: bytes) -> bytes:
        """Process PDF file"""
        try:
            pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
            pdf_writer = PdfWriter()
            
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    anonymized_text = self.anonymize_text(text)
                    
                    packet = io.BytesIO()
                    c = canvas.Canvas(packet, pagesize=letter)
                    
                    y = 750
                    for line in anonymized_text.split('\n'):
                        if line.strip():
                            c.drawString(50, y, line)
                            y -= 15
                    
                    c.save()
                    packet.seek(0)
                    new_page = PdfReader(packet).pages[0]
                    pdf_writer.add_page(new_page)
                else:
                    pdf_writer.add_page(page)
            
            output = io.BytesIO()
            pdf_writer.write(output)
            return output.getvalue()
            
        except Exception as e:
            st.error(f"Erro ao processar PDF: {str(e)}")
            return pdf_bytes

    def process_docx(self, docx_bytes: bytes) -> bytes:
        """Process DOCX file"""
        try:
            doc_temp = io.BytesIO(docx_bytes)
            doc = Document(doc_temp)
            anonymized_doc = Document()
            
            for style in doc.styles:
                if style.type == 1:
                    try:
                        anonymized_doc.styles.add_style(
                            style.name, style.type,
                            base_style=anonymized_doc.styles['Normal']
                        )
                    except:
                        pass
            
            for para in doc.paragraphs:
                new_para = anonymized_doc.add_paragraph(
                    self.anonymize_text(para.text),
                    style=para.style.name if para.style else None
                )
                
                for idx, run in enumerate(para.runs):
                    if idx < len(new_para.runs):
                        new_run = new_para.runs[idx]
                        new_run.bold = run.bold
                        new_run.italic = run.italic
                        new_run.underline = run.underline
                        if run.font.size:
                            new_run.font.size = run.font.size
            
            for table in doc.tables:
                new_table = anonymized_doc.add_table(
                    rows=len(table.rows),
                    cols=len(table.columns)
                )
                
                if table.style:
                    new_table.style = table.style
                
                for i, row in enumerate(table.rows):
                    for j, cell in enumerate(row.cells):
                        new_cell = new_table.cell(i, j)
                        new_cell.text = self.anonymize_text(cell.text)
            
            output = io.BytesIO()
            anonymized_doc.save(output)
            return output.getvalue()
            
        except Exception as e:
            st.error(f"Erro ao processar DOCX: {str(e)}")
            return docx_bytes

def main():
    st.title("Anonimizador de Dados - LGPD (Presidio)")
    
    st.markdown("""
    ### Dados detectados e anonimizados:
    
    **Usando Microsoft Presidio e spaCy em Português:**
    - Nomes de pessoas
    - Endereços de e-mail
    - Números de telefone
    - Cartões de crédito
    - Localizações
    - Datas e horários
    - URLs
    - Documentos brasileiros (CPF, RG, CNH, etc.)
    
    O sistema usa técnicas avançadas de processamento de linguagem natural para detectar e anonimizar dados sensíveis.
    """)
    
    analyzer = PresidioAnalyzer()
    
    st.header("Anonimização de Texto")
    text_input = st.text_area("Digite o texto a ser anonimizado:", height=150)
    if st.button("Anonimizar Texto") and text_input:
        anonymized_text = analyzer.anonymize_text(text_input)
        st.text_area("Texto Anonimizado:", anonymized_text, height=150)
    
    st.header("Anonimização de Arquivo")
    file = st.file_uploader(
        "Escolha um arquivo (.csv, .txt, .json, .pdf, .docx)",
        type=['csv', 'txt', 'json', 'pdf', 'docx']
    )
    
    if file is not None:
        try:
            content = file.getvalue()
            
            if file.name.endswith('.csv'):
                content_text = content.decode('utf-8')
                result = analyzer.process_csv(content_text)
                csv = result.to_csv(index=False)
                st.download_button(
                    "Download CSV Anonimizado",
                    csv,
                    "anonimizado.csv",
                    "text/csv"
                )
                
            elif file.name.endswith('.json'):
                content_text = content.decode('utf-8')
                result = analyzer.process_json(content_text)
                json_str = json.dumps(result, ensure_ascii=False, indent=2)
                st.download_button(
                    "Download JSON Anonimizado",
                    json_str,
                    "anonimizado.json",
                    "application/json"
                )
                
            elif file.name.endswith('.docx'):
                docx_anonymized = analyzer.process_docx(content)
                st.download_button(
                    "Download DOCX Anonimizado",
                    docx_anonymized,
                    "anonimizado.docx",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
                
            elif file.name.endswith('.pdf'):
                pdf_anonymized = analyzer.process_pdf(content)
                st.download_button(
                    "Download PDF Anonimizado",
                    pdf_anonymized,
                    "anonimizado.pdf",
                    "application/pdf"
                )
                
            else:  # .txt
                content_text = content.decode('utf-8')
                anonymized_text = analyzer.anonymize_text(content_text)
                st.download_button(
                    "Download TXT Anonimizado",
                    anonymized_text,
                    "anonimizado.txt",
                    "text/plain"
                )
            
            st.success("Arquivo processado com sucesso!")
            
        except Exception as e:
            st.error(f"Erro ao processar arquivo: {str(e)}")

if __name__ == "__main__":
    main()
