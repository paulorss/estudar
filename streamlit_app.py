import streamlit as st
import pandas as pd
from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig, RecognizerResult
import json
import re
from typing import List, Dict
import io

# Padrões específicos LGPD
PATTERNS = {
    # Padrões para nomes e estado civil
    "NOME_COMPLETO": r"(?i)([A-ZÀ-Ú][a-zà-ú]+ (?:[A-ZÀ-Ú][a-zà-ú]+ )?[A-ZÀ-Ú][a-zà-ú]+)",
    "NOME_PAI": r"(?i)(pai|father|genitor)\s*:?\s*([A-ZÀ-Ú][a-zà-ú]+ (?:[A-ZÀ-Ú][a-zà-ú]+ )?[A-ZÀ-Ú][a-zà-ú]+)",
    "NOME_MAE": r"(?i)(mãe|mae|mother|genitora)\s*:?\s*([A-ZÀ-Ú][a-zà-ú]+ (?:[A-ZÀ-Ú][a-zà-ú]+ )?[A-ZÀ-Ú][a-zà-ú]+)",
    "ESTADO_CIVIL": r"(?i)(solteiro|casado|divorciado|separado|viúvo|viuvo|união estável|uniao estavel)",
    "CPF": r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}",
    "RG": r"\d{2}\.?\d{3}\.?\d{3}-?\d{1}",
    "CNH": r"\d{11}",
    "TITULO_ELEITOR": r"\d{12}",
    "PIS": r"\d{11}",
    "CARTAO_SUS": r"\d{15}",
    "RACA": r"(?i)(branco|preto|pardo|amarelo|indígena)",
    "RELIGIAO": r"(?i)(católico|evangélico|espírita|umbanda|candomblé|judeu|muçulmano|budista|ateu)",
    "ORIENTACAO_SEXUAL": r"(?i)(heterossexual|homossexual|bissexual|gay|lésbica)",
    "BIOMETRICOS": r"(?i)(digital|retina|íris|face|voz)",
    "SAUDE": r"(?i)(diagnóstico|doença|condição|tratamento|medicamento|CID)",
    "GENETICOS": r"(?i)(DNA|genoma|gene|genético)",
    "FILIACAO_SINDICAL": r"(?i)(sindicato|sindical|filiação)",
    "DADOS_CRIANCA": r"(?i)(menor|criança|adolescente)"
}

def create_custom_recognizers() -> List[PatternRecognizer]:
    """Cria reconhecedores customizados para dados sensíveis LGPD"""
    recognizers = []
    
    for name, pattern in PATTERNS.items():
        recognizer = PatternRecognizer(
            supported_entity=name,
            patterns=[Pattern(name=name, regex=pattern, score=0.85)]
        )
        recognizers.append(recognizer)
    
    return recognizers

def setup_presidio():
    """Configura e retorna os motores do Presidio com reconhecedores LGPD"""
    analyzer = AnalyzerEngine()
    anonymizer = AnonymizerEngine()
    
    # Adiciona reconhecedores customizados
    custom_recognizers = create_custom_recognizers()
    for recognizer in custom_recognizers:
        analyzer.registry.add_recognizer(recognizer)
    
    return analyzer, anonymizer

def get_operator_config():
    """Retorna configurações de anonimização específicas para cada tipo de dado"""
    name_operator = OperatorConfig("replace", {"new_value": "[NOME PROTEGIDO]"})
    parent_operator = OperatorConfig("replace", {"new_value": "[FILIAÇÃO PROTEGIDA]"})
    marital_operator = OperatorConfig("replace", {"new_value": "[ESTADO CIVIL PROTEGIDO]"})
    return {
        "CPF": OperatorConfig("mask", {"chars_to_mask": 9, "masking_char": "*", "from_end": False}),
        "RG": OperatorConfig("mask", {"chars_to_mask": 7, "masking_char": "*", "from_end": False}),
        "CNH": OperatorConfig("mask", {"chars_to_mask": 8, "masking_char": "*", "from_end": False}),
        "TITULO_ELEITOR": OperatorConfig("mask", {"chars_to_mask": 8, "masking_char": "*", "from_end": False}),
        "PIS": OperatorConfig("mask", {"chars_to_mask": 7, "masking_char": "*", "from_end": False}),
        "CARTAO_SUS": OperatorConfig("mask", {"chars_to_mask": 11, "masking_char": "*", "from_end": False}),
        "RACA": OperatorConfig("replace", {"new_value": "[DADO SENSÍVEL - RAÇA]"}),
        "RELIGIAO": OperatorConfig("replace", {"new_value": "[DADO SENSÍVEL - RELIGIÃO]"}),
        "ORIENTACAO_SEXUAL": OperatorConfig("replace", {"new_value": "[DADO SENSÍVEL - ORIENTAÇÃO SEXUAL]"}),
        "BIOMETRICOS": OperatorConfig("replace", {"new_value": "[DADO SENSÍVEL - BIOMÉTRICO]"}),
        "SAUDE": OperatorConfig("replace", {"new_value": "[DADO SENSÍVEL - SAÚDE]"}),
        "GENETICOS": OperatorConfig("replace", {"new_value": "[DADO SENSÍVEL - GENÉTICO]"}),
        "FILIACAO_SINDICAL": OperatorConfig("replace", {"new_value": "[DADO SENSÍVEL - FILIAÇÃO SINDICAL]"}),
        "DADOS_CRIANCA": OperatorConfig("replace", {"new_value": "[DADO SENSÍVEL - MENOR DE IDADE]"}),
        "PHONE_NUMBER": OperatorConfig("mask", {"chars_to_mask": 8, "masking_char": "*", "from_end": False}),
        "EMAIL_ADDRESS": OperatorConfig("mask", {"chars_to_mask": -1, "masking_char": "*", "from_end": False}),
        "CREDIT_CARD": OperatorConfig("mask", {"chars_to_mask": 12, "masking_char": "*", "from_end": False}),
        "LOCATION": OperatorConfig("replace", {"new_value": "[LOCALIZAÇÃO]"}),
        "PERSON": OperatorConfig("replace", {"new_value": "[NOME]"}),
        "NOME_COMPLETO": name_operator,
        "NOME_PAI": parent_operator,
        "NOME_MAE": parent_operator,
        "ESTADO_CIVIL": marital_operator,
        "DEFAULT": OperatorConfig("replace", {"new_value": "[DADO SENSÍVEL]"})
    }

def analyze_text(analyzer, text):
    """Analisa o texto em busca de informações sensíveis"""
    return analyzer.analyze(
        text=text,
        language='pt',
        return_decision_process=True
    )

def anonymize_text(anonymizer, text, analyzer_results):
    """Anonimiza o texto com base nos resultados da análise"""
    operator_config = get_operator_config()
    
    return anonymizer.anonymize(
        text=text,
        analyzer_results=analyzer_results,
        operators=operator_config
    )

def process_file(file, analyzer, anonymizer):
    """Processa diferentes tipos de arquivos"""
    if file.name.endswith('.csv'):
        return process_csv(file, analyzer, anonymizer)
    elif file.name.endswith('.txt'):
        return process_txt(file, analyzer, anonymizer)
    elif file.name.endswith('.json'):
        return process_json(file, analyzer, anonymizer)
    else:
        raise ValueError("Formato de arquivo não suportado")

def process_csv(file, analyzer, anonymizer):
    """Processa arquivo CSV"""
    df = pd.read_csv(file)
    for column in df.columns:
        if df[column].dtype == 'object':  # processa apenas colunas de texto
            df[column] = df[column].apply(lambda x: anonymize_text(
                anonymizer,
                str(x),
                analyze_text(analyzer, str(x))
            ).text if pd.notnull(x) else x)
    return df

def process_txt(file, analyzer, anonymizer):
    """Processa arquivo TXT"""
    content = file.getvalue().decode('utf-8')
    analysis_results = analyze_text(analyzer, content)
    anonymized_content = anonymize_text(anonymizer, content, analysis_results)
    return anonymized_content.text

def process_json(file, analyzer, anonymizer):
    """Processa arquivo JSON"""
    content = json.loads(file.getvalue().decode('utf-8'))
    
    def anonymize_dict(d):
        if isinstance(d, dict):
            return {k: anonymize_dict(v) for k, v in d.items()}
        elif isinstance(d, list):
            return [anonymize_dict(v) for v in d]
        elif isinstance(d, str):
            analysis_results = analyze_text(analyzer, d)
            return anonymize_text(anonymizer, d, analysis_results).text
        else:
            return d
    
    return anonymize_dict(content)

def main():
    st.title("Anonimizador de Dados - LGPD")
    
    st.markdown("""
    ### Dados Pessoais Identificáveis:
    - Nomes completos
    - Nome do pai
    - Nome da mãe
    - Estado civil
    
    ### Dados Sensíveis Detectados (Art. 5º da LGPD):
    - Origem racial ou étnica
    - Convicção religiosa
    - Opinião política
    - Filiação sindical
    - Dados referentes à saúde
    - Vida sexual ou orientação sexual
    - Dados genéticos ou biométricos
    - Dados de crianças e adolescentes
    
    ### Documentos e Identificadores:
    - CPF
    - RG
    - CNH
    - Título de Eleitor
    - PIS/PASEP
    - Cartão SUS
    - E-mails
    - Telefones
    - Cartões de crédito
    """)
    
    # Configuração do Presidio
    analyzer, anonymizer = setup_presidio()
    
    # Interface para entrada de texto
    st.header("Anonimização de Texto")
    text_input = st.text_area("Digite o texto a ser anonimizado:", height=150)
    if st.button("Anonimizar Texto") and text_input:
        analysis_results = analyze_text(analyzer, text_input)
        anonymized_text = anonymize_text(anonymizer, text_input, analysis_results)
        st.text_area("Texto Anonimizado:", anonymized_text.text, height=150)
    
    # Interface para upload de arquivo
    st.header("Anonimização de Arquivo")
    uploaded_file = st.file_uploader("Escolha um arquivo (.csv, .txt, .json)", 
                                   type=['csv', 'txt', 'json'])
    
    if uploaded_file is not None:
        try:
            result = process_file(uploaded_file, analyzer, anonymizer)
            
            # Download do arquivo processado
            if isinstance(result, pd.DataFrame):
                csv = result.to_csv(index=False)
                st.download_button(
                    label="Download CSV Anonimizado",
                    data=csv,
                    file_name="anonimizado.csv",
                    mime="text/csv"
                )
            elif isinstance(result, str):
                st.download_button(
                    label="Download TXT Anonimizado",
                    data=result,
                    file_name="anonimizado.txt",
                    mime="text/plain"
                )
            else:  # JSON
                json_str = json.dumps(result, ensure_ascii=False, indent=2)
                st.download_button(
                    label="Download JSON Anonimizado",
                    data=json_str,
                    file_name="anonimizado.json",
                    mime="application/json"
                )
            
            st.success("Arquivo processado com sucesso!")
            
        except Exception as e:
            st.error(f"Erro ao processar arquivo: {str(e)}")

if __name__ == "__main__":
    main()
