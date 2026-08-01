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
# 2. SEGURANÇA E CREDENCIAIS
# ==========================================
try:
    NOTION_TOKEN = st.secrets["NOTION_TOKEN"]
    DATABASE_ID = st.secrets["DATABASE_ID"]
except Exception:
    st.error("⚠️ Chaves de acesso não encontradas! Configure as Secrets no painel do Streamlit Cloud.")
    st.stop()

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# ==========================================
# 3. FUNÇÕES DO SISTEMA
# ==========================================
def enviar_nota(texto):
    """Envia a anotação para a nuvem do Notion."""
    url = "https://api.notion.com/v1/pages"
    dados = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "title": {"title": [{"text": {"content": texto}}]}
        }
    }
    return requests.post(url, headers=HEADERS, json=dados)

def buscar_notas_recentes():
    """Busca as 5 notas mais recentes do banco de dados."""
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
st.markdown("Suas anotações enviadas de forma segura para o Notion.")
st.divider()

# Formulário blindado contra perdas e travamentos
st.subheader("📝 Nova Anotação")

with st.form(key="form_notas", clear_on_submit=True):
    texto_nota = st.text_area(
        label="Conteúdo da Nota",
        placeholder="Escreva tudo o que precisar aqui...",
        height=200,
        label_visibility="collapsed"
    )
    
    botao_salvar = st.form_submit_button("🚀 Enviar para a Nuvem", use_container_width=True)

# Ações ao clicar no botão
if botao_salvar:
    if not texto_nota.strip():
        st.warning("⚠️ O campo de texto está vazio. Escreva algo!")
    else:
        with st.spinner("Sincronizando com os servidores... ⏳"):
            res = enviar_nota(texto_nota)
            
            if res.status_code == 200:
                st.success("✨ Nota salva com sucesso!")
                st.toast("Sincronização concluída!", icon="✅")
            else:
                st.error(f"❌ Erro ao salvar (Código: {res.status_code})")

st.divider()

# Visualização do Histórico
st.subheader("📂 Últimas 5 Notas")

with st.spinner("Carregando histórico da nuvem..."):
    notas = buscar_notas_recentes()
    
    if not notas:
        st.info("Nenhuma nota encontrada no momento.")
    else:
        for nota in notas:
            try:
                # Extrai apenas o texto útil da resposta da API
                texto_extraido = nota["properties"]["title"]["title"][0]["text"]["content"]
                st.info(texto_extraido, icon="📄")
            except (KeyError, IndexError):
                pass
