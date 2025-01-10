import streamlit as st
import pandas as pd
import json
import io
import re
from typing import List, Dict, Any, Optional
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from docx import Document
from docx.shared import Pt

class SimpleAnalyzer:
    """Analisador simplificado baseado em padrões"""
    
    def __init__(self):
        self.patterns = self._get_patterns()
        self.compiled_patterns = self._compile_patterns()
    
    def _get_patterns(self) -> Dict[str, str]:
        """Define os padrões de regex para cada tipo de dado"""
        return {
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
    
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compila os padrões regex"""
        return {entity_type: re.compile(pattern) for entity_type, pattern in self.patterns.items()}
    
    def analyze(self, text: str) -> List[Dict[str, Any]]:
        """Analisa texto em busca de padrões"""
        results = []
        for entity_type, pattern in self.compiled_patterns.items():
            matches = pattern.finditer(text)
            for match in matches:
                results.append({
                    'entity_type': entity_type,
                    'start': match.start(),
                    'end': match.end(),
                    'score': 0.85,
                    'text': match.group()
                })
        return sorted(results, key=lambda x: x['start'])

class Anonimizador:
    def __init__(self):
        """Inicializa o anonimizador"""
        self.analyzer = SimpleAnalyzer()
        self.operator_config = self._get_operator_config()
    
    def _get_operator_config(self) -> Dict[str, Dict[str, Any]]:
        """Retorna configurações de anonimização para cada tipo de dado"""
        return {
            # Documentos - Mascaramento parcial
            "CPF": {"type": "mask", "chars_to_mask": 9, "masking_char": "*", "from_end": False},
            "RG": {"type": "mask", "chars_to_mask": 7, "masking_char": "*", "from_end": False},
            "CNH": {"type": "mask", "chars_to_mask": 8, "masking_char": "*", "from_end": False},
            "TITULO_ELEITOR": {"type": "mask", "chars_to_mask": 8, "masking_char": "*", "from_end": False},
            "PIS": {"type": "mask", "chars_to_mask": 9, "masking_char": "*", "from_end": False},
            "PASSAPORTE": {"type": "mask", "chars_to_mask": 6, "masking_char": "*", "from_end": False},
            
            # Dados Pessoais - Substituição total
            "NOME_COMPLETO": {"type": "replace", "new_value": "[NOME PROTEGIDO]"},
            "NOME_PAIS": {"type": "replace", "new_value": "[FILIAÇÃO PROTEGIDA]"},
            "ESTADO_CIVIL": {"type": "replace", "new_value": "[ESTADO CIVIL PROTEGIDO]"},
            "PROFISSAO": {"type": "replace", "new_value": "[PROFISSÃO PROTEGIDA]"},
            
            # Dados de Contato - Mascaramento parcial
            "EMAIL": {"type": "mask", "chars_to_mask": -1, "masking_char": "*", "from_end": False},
            "TELEFONE": {"type": "mask", "chars_to_mask": 8, "masking_char": "*", "from_end": False},
            "WHATSAPP": {"type": "mask", "chars_to_mask": 8, "masking_char": "*", "from_end": False},
            
            # Dados Financeiros - Mascaramento total
            "CARTAO_CREDITO": {"type": "mask", "chars_to_mask": 12, "masking_char": "*", "from_end": False},
            "CONTA_BANCARIA": {"type": "replace", "new_value": "[DADOS BANCÁRIOS PROTEGIDOS]"},
            "RENDA": {"type": "replace", "new_value": "[INFORMAÇÃO FINANCEIRA PROTEGIDA]"},
            
            # Endereço - Substituição
            "ENDERECO": {"type": "replace", "new_value": "[ENDEREÇO PROTEGIDO]"},
            "CEP": {"type": "mask", "chars_to_mask": 5, "masking_char": "*", "from_end": False},
            "BAIRRO": {"type": "replace", "new_value": "[BAIRRO PROTEGIDO]"},
            
            # Dados Sensíveis - Substituição total
            "RACA": {"type": "replace", "new_value": "[DADO SENSÍVEL - RAÇA]"},
            "RELIGIAO": {"type": "replace", "new_value": "[DADO SENSÍVEL - RELIGIÃO]"},
            "ORIENTACAO_SEXUAL": {"type": "replace", "new_value": "[DADO SENSÍVEL - ORIENTAÇÃO SEXUAL]"},
            
            # Datas - Substituição
            "DATA": {"type": "replace", "new_value": "[DATA PROTEGIDA]"},
            "NASCIMENTO": {"type": "replace", "new_value": "[DATA DE NASCIMENTO PROTEGIDA]"},
            
            # Padrão para outros tipos de dados
            "DEFAULT": {"type": "replace", "new_value": "[DADO PROTEGIDO]"}
        }
    
    def _apply_mask(self, text: str, config: Dict[str, Any]) -> str:
        """Aplica mascaramento ao texto baseado na configuração"""
        chars_to_mask = config.get('chars_to_mask', len(text))
        masking_char = config.get('masking_char', '*')
        from_end = config.get('from_end', False)
        
        if from_end:
            return text[:-chars_to_mask] + masking_char * chars_to_mask
        return masking_char * chars_to_mask + text[chars_to_mask:]
    
    def _apply_replacement(self, text: str, config: Dict[str, Any]) -> str:
        """Aplica substituição ao texto baseado na configuração"""
        return config.get('new_value', '[DADO PROTEGIDO]')
    
    def anonimizar_texto(self, text: str) -> str:
        """Anonimiza texto"""
        if not isinstance(text, str) or not text.strip():
            return text
            
        try:
            # Analisa texto
            results = self.analyzer.analyze(text)
            if not results:
                return text
            
            # Ordena resultados pela posição inicial em ordem reversa
            results.sort(key=lambda x: x['start'], reverse=True)
            
            # Aplica anonimização
            modified_text = text
            for result in results:
                entity_type = result['entity_type']
                config = self.operator_config.get(entity_type, self.operator_config.get('DEFAULT'))
                
                if config['type'] == 'mask':
                    replacement = self._apply_mask(result['text'], config)
                else:  # replace
                    replacement = self._apply_replacement(result['text'], config)
                
                modified_text = (
                    modified_text[:result['start']] +
                    replacement +
                    modified_text[result['end']:]
                )
            
            return modified_text
            
        except Exception as e:
            st.error(f"Erro ao anonimizar texto: {str(e)}")
            return text

    def processar_csv(self, conteudo: str) -> pd.DataFrame:
        """Processa arquivo CSV"""
        try:
            df = pd.read_csv(pd.StringIO(conteudo))
            for coluna in df.columns:
                if df[coluna].dtype == 'object':
                    df[coluna] = df[coluna].apply(lambda x: self.anonimizar_texto(str(x)) if pd.notna(x) else x)
            return df
        except Exception as e:
            st.error(f"Erro ao processar CSV: {str(e)}")
            return pd.DataFrame()

    def processar_json(self, conteudo: str) -> dict:
        """Processa arquivo JSON"""
        try:
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
        except Exception as e:
            st.error(f"Erro ao processar JSON: {str(e)}")
            return {}

    def processar_pdf(self, pdf_bytes: bytes) -> bytes:
        """Processa arquivo PDF"""
        try:
            pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
            pdf_writer = PdfWriter()
            
            for pagina in pdf_reader.pages:
                texto = pagina.extract_text()
                if texto:
                    texto_anonimizado = self.anonimizar_texto(texto)
                    
                    # Criar nova página com texto anonimizado
                    packet = io.BytesIO()
                    c = canvas.Canvas(packet, pagesize=letter)
                    
                    y = 750  # Posição inicial Y
                    for linha in texto_anonimizado.split('\n'):
                        if linha.strip():
                            c.drawString(50, y, linha)
                            y -= 15  # Espaçamento entre linhas
                    
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
            # Abrir documento original
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
                    style=para.style.name if para.style else None
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
                
                if tabela.style:
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
    
    # Interface para anonimização de texto
    st.header("Anonimização de Texto")
    texto_input = st.text_area("Digite o texto a ser anonimizado:", height=150)
    if st.button("Anonimizar Texto") and texto_input:
        texto_anonimizado = anonimizador.anonimizar_texto(texto_input)
        st.text_area("Texto Anonimizado:", texto_anonimizado, height=150)
    
    # Interface para anonimização de arquivo
    st.header("Anonimização de Arquivo")
    arquivo = st.file_uploader(
        "Escolha um arquivo (.csv, .txt, .json, .pdf, .docx)",
        type=['csv', 'txt', 'json', 'pdf', 'docx']
    )
    
    if arquivo is not None:
        try:
            # Ler conteúdo do arquivo
            conteudo = arquivo.getvalue()
            
            # Processar diferentes tipos de arquivo
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
