import streamlit as st
import requests
import json
import re
import urllib.parse
from datetime import datetime
from streamlit_local_storage import LocalStorage

# ================= SECRETS & CONFIGURACÃO =================
NOTION_TOKEN = st.secrets.get("notion_token")
NOTION_DATABASE_ID = st.secrets.get("notion_database_id")

st.set_page_config(page_title="Portal de Vendas", page_icon="📶", layout="centered")
local_storage = LocalStorage()

if 'init' not in st.session_state:
    st.session_state.update({
        'init': True,
        'aba_ativa': "📝 Nova Venda",
        'vendedor_atual': "Moabe",
        'rascunhos_locais': [],
        'form_venda_cache': {},
        'planos_dinamicos': {
            "NIO Fibra": ["500 Mega", "800 Mega"],
            "TIM Ultrafibra": ["600 Mega", "800 Mega"],
            "Vivo": ["Padrão"],
            "Claro": ["Padrão"]
        }
    })

def gerar_protocolo():
    return f"ID-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

def gerar_chave():
    return f"key_{datetime.now().timestamp()}"

def salvar_local():
    try:
        dados = {"rascunhos": st.session_state['rascunhos_locais']}
        local_storage.setItem("pap_rascunhos_v7", json.dumps(dados), key=gerar_chave())
    except: pass

def carregar_local():
    try:
        rs = local_storage.getItem("pap_rascunhos_v7")
        if rs:
            dados = json.loads(rs) if isinstance(rs, str) else rs
            st.session_state['rascunhos_locais'] = dados.get('rascunhos', [])
    except: pass

if not st.session_state.get('memoria_ok'):
    carregar_local()
    st.session_state['memoria_ok'] = True

def validar_cpf(doc):
    d = re.sub(r'[^0-9]', '', str(doc))
    return len(d) in [11, 14]

def formatar_ficha(d):
    return f"""📄 *NOVA VENDA* 📄

👤 *CLIENTE*
Nome: {d['nome']}
Doc: {d['cpf']}
Mãe: {d.get('mae', 'Não informado')}
Email: {d.get('email', 'Não informado')}

📞 *CONTATOS*
WhatsApp: {d['whats1']}
Contato 2: {d.get('whats2', 'Não informado')}

📍 *ENDEREÇO*
CEP: {d['cep']}
{d['rua']}, Nº {d['numero']} - {d['bairro']}

📶 *SERVIÇO*
Operadora: {d['operadora']}
Plano: {d['plano']}
Protocolo: {d['protocolo']}"""

# ================= FUNÇÃO NOTION TILE UNIVERSAL =================
def enviar_tile_notion(titulo, conteudo_texto):
    if not NOTION_TOKEN or not NOTION_DATABASE_ID:
        return False, "Chaves do Notion ausentes nos Secrets."
    
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    # Busca dinamicamente qual o nome da coluna de título no Notion para não dar erro
    nome_coluna_titulo = "title"
    try:
        url_db = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}"
        r_db = requests.get(url_db, headers=headers, timeout=5)
        if r_db.status_code == 200:
            props = r_db.json().get("properties", {})
            for k, v in props.items():
                if v.get("type") == "title":
                    nome_coluna_titulo = k
                    break
    except: pass

    data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            nome_coluna_titulo: {
                "title": [{"text": {"content": titulo[:100]}}]
            }
        },
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": conteudo_texto}}]
                }
            }
        ]
    }
    
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=10)
        if resp.status_code == 200:
            return True, "Tile criada com sucesso!"
        else:
            msg = resp.json().get('message', resp.text)
            return False, f"Notion recusou: {msg}"
    except Exception as e:
        return False, f"Erro de conexão: {e}"

# ================= TEMA CLARO E LIMPO =================
st.markdown("""
    <style>
    .stApp { background-color: #F9FAFB; color: #111827; font-family: 'Segoe UI', system-ui, sans-serif; }
    h1, h2, h3, h4, label { color: #111827 !important; }
    .stTextInput>div>div>input, .stSelectbox>div>div>select, .stTextArea>div>div>textarea {
        background-color: #FFFFFF !important; color: #111827 !important;
        border: 1px solid #D1D5DB !important; border-radius: 8px !important; padding: 12px !important; font-size: 16px !important;
    }
    .stButton>button {
        background-color: #2563EB; color: #FFFFFF !important; border: none; border-radius: 8px; 
        width: 100%; padding: 14px; font-weight: 600; font-size: 15px;
    }
    .alert-ok { background-color: #ECFDF5; border: 1px solid #A7F3D0; color: #065F46; padding: 16px; border-radius: 8px; font-weight: 600; text-align: center; margin-bottom: 15px; }
    .alert-err { background-color: #FEF2F2; border: 1px solid #FECACA; color: #991B1B; padding: 16px; border-radius: 8px; font-weight: 600; text-align: center; margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)

st.title("Portal de Atendimento")

col1, col2 = st.columns(2)
if col1.button("📝 Fazer Pedido"): st.session_state['aba_ativa'] = "📝 Nova Venda"; st.rerun()
if col2.button("📂 Rascunhos Salvos"): st.session_state['aba_ativa'] = "📂 Rascunhos"; st.rerun()

st.markdown("<hr>", unsafe_allow_html=True)

# ================= FORMULÁRIO DE VENDA =================
if st.session_state['aba_ativa'] == "📝 Nova Venda":
    cache = st.session_state.get('form_venda_cache', {})
    
    ops = ["Selecione"] + list(st.session_state['planos_dinamicos'].keys())
    op_idx = ops.index(cache.get('f_operadora')) if cache.get('f_operadora') in ops else 0
    operadora = st.selectbox("Operadora", ops, index=op_idx)
    
    planos_disponiveis = st.session_state['planos_dinamicos'].get(operadora, []) if operadora != "Selecione" else []

    with st.form("form_venda"):
        st.subheader("Dados do Cliente")
        nome = st.text_input("Nome Completo", value=cache.get('f_nome', ''))
        cpf = st.text_input("CPF ou CNPJ", value=cache.get('f_cpf', ''))
        mae = st.text_input("Nome da Mãe", value=cache.get('f_mae', ''))
        email = st.text_input("E-mail", value=cache.get('f_email', ''))
        
        c_w1, c_w2 = st.columns(2)
        whats1 = c_w1.text_input("WhatsApp Principal", value=cache.get('f_whats1', ''))
        whats2 = c_w2.text_input("2º Contato (Opcional)", value=cache.get('f_whats2', ''))

        st.subheader("Endereço")
        cep = st.text_input("CEP", value=cache.get('f_cep', ''))
        rua = st.text_input("Rua / Avenida", value=cache.get('f_rua', ''))
        
        c_n, c_b = st.columns([1, 2])
        numero = c_n.text_input("Número", value=cache.get('f_numero', ''))
        bairro = c_b.text_input("Bairro", value=cache.get('f_bairro', ''))

        lista_p = ["Selecione"] + planos_disponiveis
        pl_idx = lista_p.index(cache.get('f_plano')) if cache.get('f_plano') in lista_p else 0
        plano = st.selectbox("Plano Desejado", lista_p, index=pl_idx)

        st.markdown("<br>", unsafe_allow_html=True)
        col_b1, col_b2 = st.columns(2)
        btn_salvar = col_b1.form_submit_button("💾 Salvar Rascunho")
        btn_gerar = col_b2.form_submit_button("⚡ Enviar e Gerar Ficha")

        if btn_salvar:
            if not nome:
                st.markdown('<div class="alert-err">Informe o nome para guardar o rascunho.</div>', unsafe_allow_html=True)
            else:
                novo_rascunho = {
                    "id": gerar_chave(), "f_nome": nome, "f_cpf": cpf, "f_mae": mae,
                    "f_email": email, "f_whats1": whats1, "f_whats2": whats2, "f_cep": cep,
                    "f_rua": rua, "f_numero": numero, "f_bairro": bairro,
                    "f_operadora": operadora, "f_plano": plano
                }
                st.session_state['rascunhos_locais'].insert(0, novo_rascunho)
                salvar_local()
                st.markdown('<div class="alert-ok">Rascunho salvo no celular!</div>', unsafe_allow_html=True)

        if btn_gerar:
            if not nome or not cpf or operadora == "Selecione" or plano == "Selecione":
                st.markdown('<div class="alert-err">Preencha Nome, CPF, Operadora e Plano.</div>', unsafe_allow_html=True)
            elif not validar_cpf(cpf):
                st.markdown('<div class="alert-err">CPF/CNPJ incorreto.</div>', unsafe_allow_html=True)
            else:
                dados_ficha = {
                    "protocolo": gerar_protocolo(), "nome": nome, "cpf": cpf, "mae": mae,
                    "email": email, "whats1": whats1, "whats2": whats2, "cep": cep,
                    "rua": rua, "numero": numero, "bairro": bairro,
                    "operadora": operadora, "plano": plano
                }
                
                texto_final = formatar_ficha(dados_ficha)
                titulo_tile = f"{nome} - {operadora} ({plano})"
                
                with st.spinner("Criando tile no Notion..."):
                    ok_n, msg_n = enviar_tile_notion(titulo_tile, texto_final)
                
                if ok_n:
                    st.markdown('<div class="alert-ok">✅ Venda enviada ao Notion! Ficha gerada abaixo:</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="alert-err">⚠️ {msg_n}</div>', unsafe_allow_html=True)

                st.code(texto_final, language="text")
                
                link_wpp = f"https://api.whatsapp.com/send?text={urllib.parse.quote_plus(texto_final)}"
                st.markdown(f'<a href="{link_wpp}" target="_blank"><button style="background-color: #25D366; color: #FFF; width: 100%; border: none; padding: 14px; border-radius: 8px; font-weight: bold; font-size: 16px; text-align: center; display: block; text-decoration: none;">📲 Enviar Ficha para o Backoffice</button></a>', unsafe_allow_html=True)

# ================= RASCUNHOS =================
elif st.session_state['aba_ativa'] == "📂 Rascunhos":
    st.subheader("Rascunhos no Aparelho")
    if not st.session_state['rascunhos_locais']:
        st.info("Nenhum rascunho salvo.")
    else:
        for r in list(st.session_state['rascunhos_locais']):
            st.markdown(f"**{r.get('f_nome')}** - {r.get('f_operadora')} | Tel: {r.get('f_whats1')}")
            c_a1, c_a2 = st.columns(2)
            if c_a1.button("Carregar", key=f"load_{r['id']}"):
                st.session_state['form_venda_cache'] = r
                st.session_state['rascunhos_locais'] = [x for x in st.session_state['rascunhos_locais'] if x['id'] != r['id']]
                salvar_local()
                st.session_state['aba_ativa'] = "📝 Nova Venda"
                st.rerun()
            if c_a2.button("Excluir", key=f"del_{r['id']}"):
                st.session_state['rascunhos_locais'] = [x for x in st.session_state['rascunhos_locais'] if x['id'] != r['id']]
                salvar_local()
                st.rerun()
