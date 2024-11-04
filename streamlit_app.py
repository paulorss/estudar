
# -*- coding: UTF-8 -*-
import streamlit as st
import PyPDF2
import re
import random

def extract_articles(text):
    start_index = text.find("Art. ")
    if start_index == -1:
        return []
    
    text = text[start_index:]
    articles = []
    matches = re.finditer(r'Art\. \d+º?\.?', text)
    positions = [match.start() for match in matches]
    positions.append(len(text))
    
    for i in range(len(positions) - 1):
        article = text[positions[i]:positions[i+1]].strip()
        if article:
            articles.append(article)
    
    return articles

def create_question_from_article(article):
    words = article.split()
    long_word_positions = []
    
    for i, word in enumerate(words):
        if len(word) >= 6 and not word.isupper() and not any(char.isdigit() for char in word):
            long_word_positions.append(i)
    
    if not long_word_positions:
        return article, "", article
    
    start_pos = random.choice(long_word_positions)
    num_words = min(random.randint(1, 3), len(words) - start_pos)
    omitted_words = " ".join(words[start_pos:start_pos + num_words])
    
    question_text = " ".join(words[:start_pos]) + " ________________________ " + \
                   " ".join(words[start_pos + num_words:])
    
    original_text = article
    
    return question_text, omitted_words, original_text

def main():
    st.title("Estudo de Artigos PDF")
    
    input_method = st.radio("Escolha o método de entrada:", 
                           ["Inserir texto", "Upload de PDF"])
    
    text_content = ""
    
    if input_method == "Inserir texto":
        text_content = st.text_area("Cole o texto aqui:", height=200)
    else:
        uploaded_file = st.file_uploader("Faça upload do arquivo PDF", type=['pdf'])
        if uploaded_file:
            try:
                pdf_reader = PyPDF2.PdfReader(uploaded_file)
                for page in pdf_reader.pages:
                    text_content += page.extract_text()
            except Exception as e:
                st.error(f"Erro ao processar o PDF: {str(e)}")
    
    if text_content:
        articles = extract_articles(text_content)
        
        if not articles:
            st.warning("Nenhum artigo foi encontrado no texto.")
            return
        
        if 'current_article' not in st.session_state:
            st.session_state.current_article = 0
            st.session_state.show_answer = False
            st.session_state.questions = [create_question_from_article(art) for art in articles]
        
        # Adiciona o slider para navegar entre os artigos
        st.session_state.current_article = st.slider("Selecione o artigo", 0, len(articles) - 1, st.session_state.current_article)
        
        # Adiciona os botões de navegação
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Anterior") and st.session_state.current_article > 0:
                st.session_state.current_article -= 1
                st.session_state.show_answer = False
                st.session_state.user_answer = ""
        
        with col2:
            if st.button("Reiniciar"):
                st.session_state.current_article = 0
                st.session_state.show_answer = False
                st.session_state.questions = [create_question_from_article(art) for art in articles]
                st.session_state.user_answer = ""
        
        with col3:
            if st.button("Próximo") and st.session_state.current_article < len(articles) - 1:
                st.session_state.current_article += 1
                st.session_state.show_answer = False
                st.session_state.user_answer = ""
        
        # Mostra o artigo com o trecho omitido
        question_text, omitted_words, original_text = st.session_state.questions[st.session_state.current_article]
        st.write(f"Artigo {st.session_state.current_article + 1} de {len(articles)}")
        st.markdown(f"<div style='text-align: justify;'>{question_text}</div>", unsafe_allow_html=True)
        
        # Campo para resposta do usuário
        if 'user_answer' not in st.session_state:
            st.session_state.user_answer = ""
        user_answer = st.text_area("Digite as palavras que faltam:", value=st.session_state.user_answer, height=100)
        st.session_state.user_answer = user_answer
        
        # Botão para verificar resposta
        if st.button("Verificar Resposta"):
            st.session_state.show_answer = True
        
        # Expander para mostrar a resposta completa
        with st.expander("Resposta"):
            if st.session_state.show_answer:
                st.write("Palavras que faltavam:", omitted_words)
                st.markdown(f"<div style='text-align: justify;'>{original_text}</div>", unsafe_allow_html=True)
                
                # Compara a resposta normalizando os textos
                user_normalized = " ".join(user_answer.strip().lower().split())
                correct_normalized = " ".join(omitted_words.strip().lower().split())
                
                if user_normalized == correct_normalized:
                    st.success("Correto!")
                else:
                    st.error("Incorreto. Compare sua resposta com o texto original.")

if __name__ == "__main__":
    main()
