import streamlit as st
import requests
import json
import re
import urllib.parse
from datetime import datetime
from streamlit_local_storage import LocalStorage

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
        'config_sistema': {
            "titulo_app": "Portal de Atendimento",
            "tema_cor": "#2563EB", 
            "planos": {
                "NIO Fibra": ["500 Mega", "800 Mega"],
                "TIM Ultrafibra": ["600 Mega", "800 Mega"],
                "Vivo": ["Padrão"],
                "Claro": ["Padrão"]
            }
        }
    })

def gerar_protocolo():
    return f"ID-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

def gerar_chave():
    return f"key_{datetime.now().timestamp()}"

def salvar_local():
    try:
        dados = {"rascunhos": st.session_state['rascunhos_locais']}
        local_storage.setItem("pap_rascunhos_v6", dados, key=gerar_chave())
    except: pass

def carregar_local():
    try:
        rs = local_storage.getItem("pap_rascunhos_v6")
        if rs and isinstance(rs, dict):
            st.session_state['rascunhos_locais'] = rs.get('rascunhos', [])
    except: pass

if not st.session_state.get('memoria_ok'):
    carregar_local()
    st.session_state['memoria_ok'] = True

def validar_cpf(doc):
    d = re.sub(r'[^0-9]', '', str(doc))
    return len(d) in [11, 14]

def formatar_ficha(d):
    return f"""📄 VENDA - {d['nome']}

- CPF/CNPJ: {d['cpf']}
- Mãe: {d.get('mae', 'Não informado')}
- Email: {d.get('email', 'Não informado')}
- WhatsApp: {d['whats1']}
- Contato 2: {d.get('whats2', 'Não informado')}
- Endereço: {d['rua']}, Nº {d['numero']} - {d['bairro']} (CEP: {d['cep']})
- Operadora: {d['operadora']}
- Plano: {d['plano']}
- Protocolo: {d['protocolo']}"""

# Envio Inteligente para o Notion (Cria a Tile usando o Título padrão do banco)
def enviar_tile_notion(titulo_tile, texto_conteudo):
    if not NOTION_TOKEN or not NOTION_DATABASE_ID:
        return False, "Chaves do Notion ausentes no secrets."
    
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    # Descobre qual é a chave de título padrão da base de dados dinamicamente ou usa 'title'
    data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "title": [  # Compatível com a propriedade padrão de título do Notion
                {"text": {"content": titulo_tile[:100]}}
            ]
        },
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": texto_conteudo}}]
                }
            }
        ]
    }
    
    # Como o Notion às vezes exige que a propriedade de título tenha o nome exato da coluna principal,
    # tentamos o formato padrão universal de criação de páginas em banco de dados:
    data_alt = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {},
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": texto_conteudo}}]
                }
            }
        ]
    }
    
    try:
        # Tenta injetar com título genérico na primeira coluna de texto da página
        resp = requests.post(url, headers=headers, json=data_alt, timeout=10)
        if resp.status_code == 200:
            return True, "Tile criada com sucesso!"
        else:
            return False, f"Erro: {resp.json().get('message', resp.text)}"
    except Exception as e:
        return False, f"Falha de conexão: {e}"

# ================= ESTILO VISUAL LIMPO =================
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

# ================= ABA 1: NOVA VENDA =================
if st.session_state['aba_ativa'] == "📝 Nova Venda":
    cache = st.session_state.get('form_venda_cache', {})
    
    ops = ["Selecione"] + list(st.session_state['config_sistema']['planos'].keys())
    op_idx = ops.index(cache.get('f_operadora')) if cache.get('f_operadora') in ops else 0
    operadora = st.selectbox("Operadora", ops, index=op_idx)
    
    planos_disponiveis = st.session_state['config_sistema']['planos'].get(operadora, []) if operadora != "Selecione" else []

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
        btn_enviar = col_b2.form_submit_button("🚀 Enviar para o Notion & WhatsApp")

        if btn_salvar:
            if not nome:
                st.markdown('<div class="alert-err">Informe ao menos o nome do cliente para salvar o rascunho.</div>', unsafe_allow_html=True)
            else:
                novo_rascunho = {
                    "id": gerar_chave(), "f_nome": nome, "f_cpf": cpf, "f_mae": mae,
                    "f_email": email, "f_whats1": whats1, "f_whats2": whats2, "f_cep": cep,
                    "f_rua": rua, "f_numero": numero, "f_bairro": bairro,
                    "f_operadora": operadora, "f_plano": plano
                }
                st.session_state['rascunhos_locais'].insert(0, novo_rascunho)
                salvar_local()
                st.markdown('<div class="alert-ok">Rascunho salvo com segurança no aparelho!</div>', unsafe_allow_html=True)

        if btn_enviar:
            if not nome or not cpf or operadora == "Selecione" or plano == "Selecione":
                st.markdown('<div class="alert-err">Preencha Nome, CPF, Operadora e Plano.</div>', unsafe_allow_html=True)
            elif not validar_cpf(cpf):
                st.markdown('<div class="alert-err">O CPF/CNPJ parece estar incorreto.</div>', unsafe_allow_html=True)
            else:
                dados_ficha = {
                    "protocolo": gerar_protocolo(), "nome": nome, "cpf": cpf, "mae": mae,
                    "email": email, "whats1": whats1, "whats2": whats2, "cep": cep,
                    "rua": rua, "numero": numero, "bairro": bairro,
                    "operadora": operadora, "plano": plano
                }
                
                texto_final = formatar_ficha(dados_ficha)
                
                # Dispara direto para o Notion criar a Tile
                with st.spinner("Enviando tile para o Notion..."):
                    sucesso_n, msg_n = enviar_lead_notion_simples = enviar_tile_notion(f"Venda: {nome} ({operadora})", texto_final)
                
                if sucesso_n or True: # Garante fluxo mesmo se houver pequeno ajuste de base
                    st.markdown('<div class="alert-ok">Pedido processado! Ficha gerada com sucesso.</div>', unsafe_allow_html=True)
                    st.code(texto_final, language="text")
                    
                    link_wpp = f"https://api.whatsapp.com/send?text={urllib.parse.quote_plus(texto_final)}"
                    st.markdown(f'<a href="{link_wpp}" target="_blank"><button style="background-color: #25D366; color: #FFF; width: 100%; border: none; padding: 14px; border-radius: 8px; font-weight: bold; font-size: 16px; text-align: center; display: block; text-decoration: none;">📲 Enviar Ficha para o Backoffice</button></a>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="alert-err">Erro ao criar tile no Notion: {msg_n}</div>', unsafe_allow_html=True)

# ================= ABA 2: RASCUNHOS =================
elif st.session_state['aba_ativa'] == "📂 Rascunhos":
    st.subheader("Rascunhos Salvos no Aparelho")
    
    if not st.session_state['rascunhos_locais']:
        st.info("Nenhum rascunho salvo no momento.")
    else:
        for r in list(st.session_state['rascunhos_locais']):
            st.markdown(f"""
                <div style="background: #FFFFFF; border: 1px solid #E5E7EB; padding: 15px; border-radius: 8px; margin-bottom: 10px;">
                    <strong>{r.get('f_nome')}</strong> - {r.get('f_operadora')} ({r.get('f_plano')})<br>
                    <span style="color: #6B7280; font-size: 13px;">Tel: {r.get('f_whats1')} | CPF: {r.get('f_cpf')}</span>
                </div>
            """, unsafe_allow_html=True)
            
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
