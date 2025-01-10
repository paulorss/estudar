import streamlit as st
import pandas as pd
import re
import json
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
    arquivo = st.file_uploader("Escolha um arquivo (.csv, .txt, .json)", type=['csv', 'txt', 'json'])
    
    if arquivo is not None:
        try:
            conteudo = arquivo.getvalue().decode('utf-8')
            
            if arquivo.name.endswith('.csv'):
                resultado = anonimizador.processar_csv(conteudo)
                csv = resultado.to_csv(index=False)
                st.download_button(
                    "Download CSV Anonimizado",
                    csv,
                    "anonimizado.csv",
                    "text/csv"
                )
            elif arquivo.name.endswith('.json'):
                resultado = anonimizador.processar_json(conteudo)
                json_str = json.dumps(resultado, ensure_ascii=False, indent=2)
                st.download_button(
                    "Download JSON Anonimizado",
                    json_str,
                    "anonimizado.json",
                    "application/json"
                )
            else:  # .txt
                texto_anonimizado = anonimizador.anonimizar_texto(conteudo)
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
