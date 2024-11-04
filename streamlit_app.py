
# -*- coding: UTF-8 -*-
import streamlit as st
import pdfplumber
import io

import pdfplumber
import PyPDF2
import io

def extrair_texto_por_linha(pdf_file):
    linhas = []
    
    # Tentativa 1: pdfplumber
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for pagina in pdf.pages:
                texto = pagina.extract_text()
                if texto:
                    linhas.extend(texto.splitlines())
    except Exception as e:
        print(f"Erro ao usar pdfplumber: {e}")
    
    # Se pdfplumber falhar, tente PyPDF2
    if not linhas:
        try:
            pdf_file.seek(0)  # Reinicia o ponteiro do arquivo
            reader = PyPDF2.PdfReader(pdf_file)
            for page in reader.pages:
                texto = page.extract_text()
                if texto:
                    linhas.extend(texto.splitlines())
        except Exception as e:
            print(f"Erro ao usar PyPDF2: {e}")
    
    return linhas

def corrigir_caracteres(texto):
    correções = {
        'Ã£': 'ã', 'Ã¡': 'á', 'Ã©': 'é', 'Ã­': 'í', 'Ã³': 'ó', 'Ãº': 'ú', 'Ã§': 'ç',
        'Ã¢': 'â', 'Ãª': 'ê', 'Ã´': 'ô',
        'Ã': 'Á', 'Ã‰': 'É', 'Ã': 'Í', 'Ã"': 'Ó', 'Ãš': 'Ú', 'Ã‡': 'Ç',
        'Ã‚': 'Â', 'ÃŠ': 'Ê', 'Ã"': 'Ô',
        'confrontaçóes': 'confrontações', 'lmoveis': 'Imóveis', 'Cartorio': 'Cartório',
        'conÍrontando': 'confrontando', 'vêrtice': 'vértice', 'Debitos': 'Débitos',
        'TíTULO': 'TÍTULO', 'Amiqável': 'Amigável', 'matrÍcula': 'matrícula', 'Cedula':'Cédula',
        'condiçÕes': 'condições', 'condiçôes': 'condições', 'imovel': 'imóvel', 'lmóveis': 'Imóveis', 'Givil':'Civil', 
        'codigo': 'código', 'lnscrição':'Inscrição',  'lmovel': 'Imóvel', 'lnstituto': 'Instituto', 'Colonizaçáo1': 'Colonização',
        'ârea': 'área', 'PROPRETÁRn': 'PROPRIETÁRIO', 'lnformaçÕes': 'Informações', 'Doacão': 'Doação', 'Nâo':'Não', 'TÍtulos': 'Títulos',
        'confrontaçôes': 'confrontações', 'lnformações': 'Informações', 'proprio':'próprio', 'hipotese': 'hipótese', 'imoveis': 'imóveis',
        'construçáo': 'construção', 'TÍtulo': 'Título', 'imoveis': 'imóveis', 'hiootese': 'hipótese', 'hipotese': 'hipótese', 'medíndo': 'medindo',
        'Iado': 'lado', 'conÍorme': 'conforme', 'desiqnada': 'designada', 'nâoconstam': 'não constam','Cédular': 'Cedular', 'lmposto': 'Imposto',
        'Gedular': 'Cedular', 'grâos': 'grãos', 'cooPERATlvA': 'cooperativa', 'vâlida': 'válida', 'lnscriçâo': 'Inscrição',
        'cartorio':'cartório', 'Uniâo': 'União', 'Federacão': 'Federação', 'alé':'até', 'perÍmetro':'perímetro', 'lnicia-se': 'Inicia-se',
        'MATRICULA': 'MATRÍCULA', 'Area': 'Área', 'Dou fe': 'Dou fé', 'Colonizaçáo': 'Colonização', 'MarÍtimos': 'Marítimos', 'lmóvel':'Imóvel',
        'N.o': 'N.', 'Juridicas': 'Jurídicas', 

        # Adicione mais correções conforme necessário
    }
    for errado, correto in correções.items():
        texto = texto.replace(errado, correto)
    return texto

def cortar_texto(linhas, cortes):
    return [linhas[inicio:fim] for inicio, fim in cortes if 0 <= inicio < fim <= len(linhas)]

def main():
    st.set_page_config(page_title="Extrator de Texto de PDF", layout="wide")
    st.title("Extrator de Texto de PDF com Múltiplos Cortes")
    
    if 'linhas' not in st.session_state:
        st.session_state.linhas = []
    
    if 'cortes' not in st.session_state:
        st.session_state.cortes = []

    col1, col2 = st.columns([1, 1])

    with col1:
        pdf_file = st.file_uploader("Carregue o arquivo PDF", type=["pdf"])
        if pdf_file is not None and not st.session_state.linhas:
            with st.spinner('Extraindo texto do PDF...'):
                linhas = extrair_texto_por_linha(io.BytesIO(pdf_file.getvalue()))
                st.session_state.linhas = [corrigir_caracteres(linha) for linha in linhas]

        if st.session_state.linhas:
            texto_completo = "\n".join(f"{i}: {linha}" for i, linha in enumerate(st.session_state.linhas))
            st.text_area("Texto original:", value=texto_completo, height=400)

    with col2:
        if st.session_state.linhas:
            num_cortes = st.number_input("Quantos trechos deseja cortar?", min_value=1, max_value=10, value=len(st.session_state.cortes) or 1)
            
            novo_cortes = []
            for i in range(num_cortes):
                with st.expander(f"Trecho {i+1}", expanded=True):
                    inicio = st.number_input(f"Índice da linha inicial", min_value=0, max_value=len(st.session_state.linhas)-1, key=f"inicio_{i}", value=st.session_state.cortes[i][0] if i < len(st.session_state.cortes) else 0)
                    
                    fim_default = st.session_state.cortes[i][1] if i < len(st.session_state.cortes) else min(inicio+10, len(st.session_state.linhas))
                    fim_default = max(fim_default, inicio + 1)
                    
                    fim = st.number_input(f"Índice da linha final", min_value=inicio+1, max_value=len(st.session_state.linhas), key=f"fim_{i}", value=fim_default)
                    novo_cortes.append((inicio, fim))
            
            st.session_state.cortes = novo_cortes

            if st.button("Cortar Texto"):
                texto_cortado = cortar_texto(st.session_state.linhas, st.session_state.cortes)
                for i, trecho in enumerate(texto_cortado):
                    with st.expander(f"Trecho {i+1}", expanded=True):
                        # Removendo quebras de linha e juntando o texto
                        texto_sem_quebras = ' '.join(linha.strip() for linha in trecho)
                        st.text_area("Texto cortado:", value=texto_sem_quebras, height=150)
                
                # Preparando o texto para download (mantendo as quebras de linha aqui)
                texto_para_download = "\n\n".join([f"Trecho {i+1}:\n" + "\n".join(trecho) for i, trecho in enumerate(texto_cortado)])
                st.download_button(
                    label="Baixar trechos cortados",
                    data=texto_para_download.encode('utf-8'),
                    file_name="trechos_cortados.txt",
                    mime="text/plain"
                )

if __name__ == "__main__":
    main()
