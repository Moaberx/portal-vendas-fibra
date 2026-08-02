import streamlit as st
import requests
import json
import re
import urllib.parse
from datetime import datetime
from streamlit_local_storage import LocalStorage

# ================= CONFIGURAÇÕES E CONSTANTES =================
URL_BACKEND_GOOGLE = "https://script.google.com/macros/s/AKfycbyTF3qUfRvMKh5JcyxJ_rbo8fSc04n24s8y8X7wtS0nP1qVjv2nUbpQLZHmAWmpXhKJ/exec"

try:
    NOTION_TOKEN = st.secrets.get("notion_token")
    NOTION_DATABASE_ID = st.secrets.get("notion_database_id")
except Exception:
    NOTION_TOKEN = None
    NOTION_DATABASE_ID = None

st.set_page_config(page_title="Portal de Vendas", page_icon="📶", layout="centered")
local_storage = LocalStorage()

if 'init' not in st.session_state:
    st.session_state.update({
        'init': True,
        'aba_ativa': "📝 Nova Venda",
        'rascunhos_locais': [],
        'form_venda_cache': {},
        'planos_dinamicos': {
            "NIO Fibra": ["500 Mega", "800 Mega"],
            "TIM Ultrafibra": ["600 Mega", "800 Mega"],
            "Vivo": ["Padrão"],
            "Claro": ["Padrão"]
        }
    })

# ================= FUNÇÕES AUXILIARES E DE MEMÓRIA =================
def gerar_chave():
    return f"key_{datetime.now().timestamp()}"

def salvar_local():
    try:
        dados = {"rascunhos": st.session_state['rascunhos_locais']}
        local_storage.setItem("pap_rascunhos_v9", json.dumps(dados), key=gerar_chave())
    except: pass

def carregar_local():
    try:
        rs = local_storage.getItem("pap_rascunhos_v9")
        if rs:
            dados = json.loads(rs) if isinstance(rs, str) else rs
            if isinstance(dados, dict):
                st.session_state['rascunhos_locais'] = dados.get('rascunhos', [])
    except: pass

if not st.session_state.get('memoria_ok'):
    carregar_local()
    st.session_state['memoria_ok'] = True

def blindar_texto(texto):
    if not isinstance(texto, str): return texto
    texto_limpo = texto.strip()
    if texto_limpo.startswith(('=', '+', '-', '@')): return f"'{texto_limpo}"
    return texto_limpo

def buscar_cep(cep):
    cep_limpo = re.sub(r'[^0-9]', '', str(cep))
    if len(cep_limpo) == 8:
        try:
            r = requests.get(f"https://viacep.com.br/ws/{cep_limpo}/json/", timeout=4)
            if r.status_code == 200 and "erro" not in r.json():
                return r.json()
        except: pass
    return None

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
Plano: {d['plano']}"""

# ================= APIS COM TRATAMENTO DE FALHAS (RESILIÊNCIA) =================
def api_google(payload):
    try:
        r = requests.post(URL_BACKEND_GOOGLE, json=payload, timeout=10)
        return True if r.status_code in [200, 201] else False
    except: 
        return False

def criar_tile_notion(titulo, texto_livre):
    if not NOTION_TOKEN or not NOTION_DATABASE_ID:
        return False, "Chaves Notion ausentes"
    
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "title": { "title": [{"text": {"content": titulo[:100]}}] }
        },
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": texto_livre}}]
                }
            }
        ]
    }
    
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=8)
        return (True, "OK") if resp.status_code == 200 else (False, resp.text)
    except Exception as e:
        return False, str(e)

# ================= ESTILO LIMPO =================
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
        width: 100%; padding: 14px; font-weight: 600; font-size: 15px; transition: 0.3s;
    }
    .stButton>button:hover { background-color: #1D4ED8; }
    .alert-ok { background-color: #ECFDF5; border: 1px solid #A7F3D0; color: #065F46; padding: 12px; border-radius: 6px; font-weight: 600; text-align: center; margin-bottom: 10px; }
    .alert-err { background-color: #FEF2F2; border: 1px solid #FECACA; color: #991B1B; padding: 12px; border-radius: 6px; font-weight: 600; text-align: center; margin-bottom: 10px; }
    .alert-warn { background-color: #FFFBEB; border: 1px solid #FDE68A; color: #92400E; padding: 12px; border-radius: 6px; font-weight: 600; text-align: center; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

st.title("Portal de Vendas")

col1, col2, col3 = st.columns(3)
if col1.button("📝 Fazer Pedido"): st.session_state['aba_ativa'] = "📝 Nova Venda"; st.rerun()
if col2.button("📞 Contato / Alerta"): st.session_state['aba_ativa'] = "📞 Contato Rápido"; st.rerun()
if col3.button("📂 Rascunhos"): st.session_state['aba_ativa'] = "📂 Rascunhos"; st.rerun()

st.markdown("<hr>", unsafe_allow_html=True)

# ================= ABA 1: NOVA VENDA =================
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
        c_cep, c_btn = st.columns([2, 1])
        cep = c_cep.text_input("CEP", value=cache.get('f_cep', ''))
        buscar_clicado = c_btn.form_submit_button("🔍 Buscar CEP")
        
        rua_val = cache.get('f_rua', '')
        bairro_val = cache.get('f_bairro', '')
        
        if buscar_clicado:
            dados_cep = buscar_cep(cep)
            if dados_cep:
                rua_val = dados_cep.get("logradouro", "")
                bairro_val = dados_cep.get("bairro", "")

        rua = st.text_input("Rua / Avenida", value=rua_val)
        c_n, c_b = st.columns([1, 2])
        numero = c_n.text_input("Número", value=cache.get('f_numero', ''))
        bairro = c_b.text_input("Bairro", value=bairro_val)

        lista_p = ["Selecione"] + planos_disponiveis
        pl_idx = lista_p.index(cache.get('f_plano')) if cache.get('f_plano') in lista_p else 0
        plano = st.selectbox("Plano Desejado", lista_p, index=pl_idx)

        st.markdown("<br>", unsafe_allow_html=True)
        col_b1, col_b2 = st.columns(2)
        btn_salvar = col_b1.form_submit_button("💾 Salvar Rascunho")
        btn_gerar = col_b2.form_submit_button("⚡ Finalizar Venda")

        if btn_salvar:
            if not nome:
                st.markdown('<div class="alert-err">Informe ao menos o nome.</div>', unsafe_allow_html=True)
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
                    "nome": nome, "cpf": cpf, "mae": mae, "email": email,
                    "whats1": whats1, "whats2": whats2, "cep": cep, "rua": rua,
                    "numero": numero, "bairro": bairro, "operadora": operadora, "plano": plano
                }
                
                texto_final = formatar_ficha(dados_ficha)
                
                # --- SISTEMA PARALELO DE ENVIO ---
                with st.spinner("Registrando venda nos sistemas..."):
                    # 1. Tenta Sheets
                    payload_sheets = {
                        "tipo": "venda", "acao": "inserir", "protocolo": f"PAP_{datetime.now().strftime('%H%M%S')}",
                        "nome": blindar_texto(nome), "cpf": cpf, "mae": blindar_texto(mae), "email": blindar_texto(email),
                        "whats1": blindar_texto(whats1), "whats2": blindar_texto(whats2), "cep": blindar_texto(cep),
                        "rua": blindar_texto(rua), "numero": blindar_texto(numero), "bairro": blindar_texto(bairro),
                        "operadora": operadora, "plano": plano, "status": "Pendente", "obs": "", "vendedor": "Portal Autônomo"
                    }
                    sheets_ok = api_google(payload_sheets)
                    
                    # 2. Tenta Notion
                    titulo_notion = f"{nome} - {operadora}"
                    notion_ok, msg_n = criar_tile_notion(titulo_notion, texto_final)

                # --- FEEDBACK RESILIENTE ---
                if sheets_ok and notion_ok:
                    st.markdown('<div class="alert-ok">✅ Venda salva no Google Sheets e no Notion!</div>', unsafe_allow_html=True)
                elif sheets_ok or notion_ok:
                    salvo_em = "Google Sheets" if sheets_ok else "Notion"
                    falha_em = "Notion" if sheets_ok else "Google Sheets"
                    st.markdown(f'<div class="alert-warn">⚠️ Salvo apenas no {salvo_em} (O {falha_em} apresentou instabilidade). Mas a venda está garantida!</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="alert-err">❌ Sistemas fora do ar. Use o botão do WhatsApp abaixo para enviar a ficha manualmente.</div>', unsafe_allow_html=True)

                # --- WHATSAPP SEMPRE DISPONÍVEL ---
                st.code(texto_final, language="text")
                link_wpp = f"https://api.whatsapp.com/send?text={urllib.parse.quote_plus(texto_final)}"
                st.markdown(f'<a href="{link_wpp}" target="_blank"><button style="background-color: #25D366; color: #FFF; width: 100%; border: none; padding: 14px; border-radius: 8px; font-weight: bold; font-size: 16px; text-align: center; display: block; text-decoration: none;">📲 Enviar Ficha para o Backoffice</button></a>', unsafe_allow_html=True)

# ================= ABA 2: CONTATO / ALERTA (NOTION TILE DIRETA) =================
elif st.session_state['aba_ativa'] == "📞 Contato Rápido":
    st.subheader("Criar Tile de Contato / Alerta no Notion")
    st.markdown("Escreva o que quiser abaixo. Ao enviar, vira um cartão (tile) limpo lá no seu Notion sem regras engessadas.")

    with st.form("form_tile_livre"):
        titulo_tile = st.text_input("Título do Cartão", placeholder="Ex: Retornar para João - Bairro Serra")
        conteudo_tile = st.text_area("Anotação / Alerta / Dados Livres", placeholder="Digite livremente o que precisar lembrar ou abordar...")
        
        btn_enviar_notion = st.form_submit_button("🚀 Enviar Tile para o Notion")
        
        if btn_enviar_notion:
            if not titulo_tile or not conteudo_tile:
                st.markdown('<div class="alert-err">Preencha o título e o conteúdo da tile.</div>', unsafe_allow_html=True)
            else:
                with st.spinner("Criando tile no Notion..."):
                    ok, msg = criar_tile_notion(titulo_tile, conteudo_tile)
                    if ok:
                        st.markdown('<div class="alert-ok">✅ Tile criada e salva com sucesso no Notion!</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="alert-err">⚠️ Erro ao criar tile: {msg}</div>', unsafe_allow_html=True)

# ================= ABA 3: RASCUNHOS =================
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
