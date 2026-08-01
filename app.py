import streamlit as st
import requests

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Bloco de Notas Nuvem", 
    page_icon="☁️", 
    layout="centered"
)

# ==========================================
# 2. GESTÃO DE CREDENCIAIS (Seguro para GitHub)
# ==========================================
# O código agora puxa as chaves de forma invisível.
try:
    NOTION_TOKEN = st.secrets["NOTION_TOKEN"]
    DATABASE_ID = st.secrets["DATABASE_ID"]
except FileNotFoundError:
    st.error("⚠️ Chaves de acesso não encontradas! Configure as Secrets no Streamlit Cloud.")
    st.stop()

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# ==========================================
# 3. FUNÇÕES DE COMUNICAÇÃO COM A API
# ==========================================
def enviar_nota(texto):
    url = "https://api.notion.com/v1/pages"
    dados = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "title": { 
                "title": [{"text": {"content": texto}}]
            }
        }
    }
    return requests.post(url, headers=HEADERS, json=dados)

def buscar_notas_recentes():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    payload = {
        "sorts": [{"timestamp": "created_time", "direction": "descending"}],
        "page_size": 5 
    }
    resposta = requests.post(url, headers=HEADERS, json=payload)
    if resposta.status_code == 200:
        return resposta.json().get("results", [])
    return []

# ==========================================
# 4. INTERFACE DO APLICATIVO
# ==========================================
st.title("☁️ Bloco de Notas Integrado")
st.markdown("**Nunca mais perca um texto.** Tudo o que você digita aqui vai direto para o Notion.")
st.divider()

# Área de Digitação Blindada
st.subheader("📝 Nova Anotação")

with st.form(key="form_notas", clear_on_submit=True):
    texto_nota = st.text_area(
        label="Conteúdo da Nota",
        placeholder="Digite suas ideias, listas ou textos importantes aqui...",
        height=200,
        label_visibility="collapsed"
    )
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        botao_salvar = st.form_submit_button("🚀 Enviar para Nuvem", use_container_width=True)

# Processamento do Envio
if botao_salvar:
    if not texto_nota.strip():
        st.warning("⚠️ O campo está vazio. Escreva algo antes de enviar!")
    else:
        with st.spinner("Sincronizando com o Notion... ⏳"):
            res = enviar_nota(texto_nota)
            
            if res.status_code == 200:
                st.success("✨ Nota salva com sucesso!")
                st.toast('Sincronização concluída!', icon='✅')
            else:
                st.error(f"❌ Erro ao salvar (Código: {res.status_code})")
                with st.expander("Ver detalhes do erro técnico"):
                    st.json(res.json())

st.divider()

# Histórico Recente de Notas
st.subheader("📂 Últimas 5 Notas Salvas")

with st.spinner("Carregando histórico..."):
    notas = buscar_notas_recentes()
    
    if not notas:
        st.info("Nenhuma nota encontrada neste Banco de Dados.")
    else:
        for nota in notas:
            try:
                texto_extraido = nota["properties"]["title"]["title"][0]["text"]["content"]
                data_crua = nota["created_time"]
                data_formatada = f"{data_crua[8:10]}/{data_crua[5:7]}/{data_crua[:4]}"
                
                with st.chat_message("user", avatar="📄"):
                    st.write(texto_extraido)
                    st.caption(f"🗓️ Salvo em: {data_formatada}")
            except (KeyError, IndexError):
                pass
