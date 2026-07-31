import streamlit as st
import requests
import json
import re
from streamlit_local_storage import LocalStorage

# ================= CONEXÃO DE DADOS =================
URL_BACKEND_GOOGLE = "https://script.google.com/macros/s/AKfycbyTF3qUfRvMKh5JcyxJ_rbo8fSc04n24s8y8X7wtS0nP1qVjv2nUbpQLZHmAWmpXhKJ/exec"
# ====================================================

# --- Configuração do App ---
st.set_page_config(page_title="PAP Fibra", page_icon="📶", layout="centered")

# CSS: Dark Mode robusto + correções de UX
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    h1, h2, h3, .stSubheader, label, p, span { color: #FFFFFF !important; font-family: sans-serif; font-weight: 500; }

    /* Legenda de campo obrigatório */
    .legenda-obrigatorio { color: #9CA3AF !important; font-size: 13px; margin-bottom: 10px; }

    /* Inputs */
    .stTextInput>div>div>input, .stSelectbox>div>div>select, .stTextArea>div>div>textarea, .stNumberInput>div>div>input {
        background-color: #121212 !important; color: #FFFFFF !important;
        border-radius: 6px !important; border: 1px solid #333333 !important;
        padding: 10px 12px !important; font-size: 16px !important;
    }
    textarea { color: #FFFFFF !important; }

    /* Placeholders */
    input::placeholder, textarea::placeholder { color: #6B7280 !important; }

    /* Dropdown ABERTO do selectbox (evita "flash branco") */
    ul[data-baseweb="menu"] { background-color: #121212 !important; border: 1px solid #333333 !important; }
    ul[data-baseweb="menu"] li { background-color: #121212 !important; color: #FFFFFF !important; }
    ul[data-baseweb="menu"] li:hover { background-color: #1F2937 !important; }
    div[data-baseweb="popover"] { background-color: #121212 !important; }

    /* Caixa base do selectbox (fechado) */
    div[data-baseweb="select"] > div { background-color: #121212 !important; border-color: #333333 !important; color: #FFFFFF !important; }

    /* Alertas nativos do Streamlit (fallback, caso apareçam em outros pontos) */
    div[data-testid="stAlert"] { background-color: #121212 !important; border: 1px solid #333333 !important; color: #FFFFFF !important; }

    /* Caixas de mensagem customizadas (usadas no lugar de st.error/st.success) */
    .msg-caixa { border-radius: 6px; padding: 12px 16px; margin: 10px 0; font-weight: 500; font-size: 15px; }
    .msg-erro { background-color: #2A0E0E; border: 1px solid #B91C1C; color: #FECACA !important; }
    .msg-erro * { color: #FECACA !important; }
    .msg-sucesso { background-color: #0E2A17; border: 1px solid #15803D; color: #BBF7D0 !important; }
    .msg-sucesso * { color: #BBF7D0 !important; }
    .msg-info { background-color: #0A1929; border: 1px solid #1E3A8A; color: #BFDBFE !important; }
    .msg-info * { color: #BFDBFE !important; }

    /* Botão Principal */
    .stButton>button {
        background-color: #1F2937; color: #FFFFFF; border: 1px solid #374151; border-radius: 6px;
        width: 100% !important; padding: 14px; margin-top: 15px; font-weight: bold;
    }
    .stButton>button:hover { background-color: #374151; border-color: #9CA3AF; }
    .stButton>button:disabled { background-color: #111827 !important; color: #6B7280 !important; border-color: #1F2937 !important; }

    /* Botão Buscar CEP - alinhado por flexbox, igual em qualquer tela */
    div[data-testid="column"] { display: flex; align-items: flex-end; }
    div[data-testid="column"]>.stButton { width: 100%; }
    div[data-testid="column"]>.stButton>button {
        background-color: #121212; border: 1px solid #333333; padding: 10px 14px; margin-top: 0;
    }

    /* Abas com Ícones */
    .stTabs [data-baseweb="tab-list"] { border-bottom: 1px solid #222222; gap: 0; background-color: #000000; }
    .stTabs [data-baseweb="tab"] { height: 45px; background-color: #000000; color: #888888; border: none; flex: 1; }
    .stTabs [aria-selected="true"] { color: #FFFFFF !important; border-bottom: 2px solid #FFFFFF !important; font-weight: bold !important; }

    /* Ficha Final (Destaque Azul Escuro) */
    .stCode { background-color: #0A1929 !important; border: 1px solid #1E3A8A !important; border-radius: 6px; color: #FFFFFF !important; }

    /* Indicador de envio em andamento */
    .enviando-caixa {
        background-color: #1F2937; border: 1px solid #374151; border-radius: 6px;
        padding: 12px 16px; margin-top: 10px; text-align: center; font-weight: bold;
        animation: pulse 1.2s infinite;
    }
    @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
    </style>
""", unsafe_allow_html=True)

# --- Helpers de mensagem (substituem st.error/st.success para garantir cor certa) ---
def msg_erro(texto):
    st.markdown(f'<div class="msg-caixa msg-erro">❌ {texto}</div>', unsafe_allow_html=True)

def msg_sucesso(texto):
    st.markdown(f'<div class="msg-caixa msg-sucesso">✅ {texto}</div>', unsafe_allow_html=True)

def msg_info(texto):
    st.markdown(f'<div class="msg-caixa msg-info">ℹ️ {texto}</div>', unsafe_allow_html=True)

# --- SISTEMA DE RASCUNHO ---
local_storage = LocalStorage()

def salvar_rascunho():
    try:
        dados_rascunho = {k: v for k, v in st.session_state.items() if k.startswith('f_')}
        local_storage.setItem("pap_fibra_rascunho", json.dumps(dados_rascunho))
    except: pass

def carregar_rascunho():
    try:
        rascunho_str = local_storage.getItem("pap_fibra_rascunho")
        if rascunho_str:
            rascunho = json.loads(rascunho_str) if isinstance(rascunho_str, str) else rascunho_str
            for k, v in rascunho.items():
                st.session_state[k] = v
    except: pass

def limpar_rascunho():
    try:
        local_storage.setItem("pap_fibra_rascunho", "")
        for k in list(st.session_state.keys()):
            if k.startswith('f_'): del st.session_state[k]
    except: pass

# --- DADOS DE PLANOS (UNIFICADOS - MENOS CLIQUES) ---
PLANOS_NIO = {
    "500 Mega (Residencial)": {"valor": 100.00, "detalhes": "Wi-Fi padrão"},
    "600 Mega (Residencial)": {"valor": 109.00, "detalhes": "Wi-Fi padrão"},
    "800 Mega (Residencial)": {"valor": 135.00, "detalhes": "Wi-Fi 6 + Globoplay"},
    "1 Giga (Residencial)": {"valor": 160.00, "detalhes": "Wi-Fi 6 + Mesh + Globoplay"},
    "500 Mega (Empresarial)": {"valor": 100.00, "detalhes": "Wi-Fi 5 + Maquininha"},
    "600 Mega (Empresarial)": {"valor": 109.00, "detalhes": "Wi-Fi 5 + Maquininha"},
    "800 Mega (Empresarial)": {"valor": 135.00, "detalhes": "Wi-Fi 6 + Maquininha + McAfee"},
    "1 Giga (Empresarial)": {"valor": 160.00, "detalhes": "Wi-Fi 6 + Mesh"}
}

PLANOS_TIM = {
    "600 Mega (PF)": {"valor": 119.99, "detalhes": "Wi-Fi grátis + Globoplay"},
    "800 Mega (PF)": {"valor": 129.99, "detalhes": "Wi-Fi grátis + YouTube Premium"},
    "1 Giga (PF)": {"valor": 129.99, "detalhes": "Wi-Fi 6 + Paramount+"},
    "1 Giga (CNPJ)": {"valor": 99.90, "detalhes": "Oferta CNPJ"}
}

# --- FUNÇÕES ---
def validar_cpf(cpf):
    cpf = re.sub(r'[^0-9]', '', str(cpf))
    if len(cpf) != 11 or cpf == cpf[0] * 11: return False
    for i in range(9, 11):
        val = sum((int(cpf[num]) * ((i + 1) - num) for num in range(0, i)))
        digito = ((val * 10) % 11) % 10
        if digito != int(cpf[i]): return False
    return True

def buscar_cep(cep):
    cep = re.sub(r'[^0-9]', '', str(cep))
    if len(cep) == 8:
        try:
            resp = requests.get(f"https://viacep.com.br/ws/{cep}/json/", timeout=3)
            if resp.status_code == 200 and "erro" not in resp.json(): return resp.json()
        except: pass
    return None

def formatar_ficha_venda(d):
    return f"""NOVA VENDA

CLIENTE
* Nome: {d['nome'].upper()}
* CPF/CNPJ: {d['cpf']}
* Nome da Mãe: {d['mae'].upper()}
* Email: {d['email']}

CONTATOS
* WhatsApp: {d['whats1']}
* Contato 2: {d['whats2'] or '---'}

ENDEREÇO
* CEP: {d['cep']}
* Rua: {d['rua'].upper()}, Nº {d['numero']}
* Bairro: {d['bairro'].upper()}
* Referência: {d['referencia'].upper()}

PEDIDO
* Operadora: {d['operadora'].upper()}
* Plano: {d['plano'].upper()}
* Valor: R$ {d['valor_plano']:.2f}
* Detalhes: {d['detalhes_plano']}

OBS: {d['obs']}"""

def enviar_para_planilha(dados):
    try:
        resp = requests.post(URL_BACKEND_GOOGLE, data=json.dumps(dados), headers={"Content-Type": "application/json"}, timeout=10)
        if resp.status_code == 200 and resp.json().get('status') == 'sucesso': return True
    except: pass
    return False

# --- INTERFACE ---
st.title("📶 PAP Fibra")

if 'rascunho_carregado' not in st.session_state:
    st.session_state['rascunho_carregado'] = False
if not st.session_state['rascunho_carregado']:
    if st.button("Recuperar dados digitados"):
        carregar_rascunho()
        st.session_state['rascunho_carregado'] = True
        st.rerun()

aba_vendas, aba_leads = st.tabs(["📝 Nova Venda", "📞 Leads"])

with aba_vendas:
    st.markdown('<p class="legenda-obrigatorio">🔴 = campo obrigatório</p>', unsafe_allow_html=True)

    with st.form("form_venda", clear_on_submit=False):

        st.markdown("#### Cliente")
        nome = st.text_input("Nome Completo", key='f_nome')
        cpf = st.text_input("CPF / CNPJ", key='f_cpf')
        email = st.text_input("Email 🔴", key='f_email')
        mae = st.text_input("Nome da Mãe", key='f_mae')

        col_tel1, col_tel2 = st.columns(2)
        with col_tel1: whatsapp = st.text_input("WhatsApp 🔴", key='f_whats1')
        with col_tel2: contato2 = st.text_input("Contato 2", key='f_whats2')

        st.markdown("#### Endereço")
        col_cep, col_btn = st.columns([2, 1])
        with col_cep: cep_input = st.text_input("CEP", key='f_cep')
        with col_btn:
            if st.form_submit_button("Buscar CEP"):
                salvar_rascunho()
                dados_cep = buscar_cep(cep_input)
                if dados_cep:
                    st.session_state['f_rua'] = dados_cep.get("logradouro", "")
                    st.session_state['f_bairro'] = dados_cep.get("bairro", "")
                    st.rerun()
                else:
                    msg_erro("CEP não encontrado.")

        rua = st.text_input("Rua", key='f_rua')
        col_num, col_bairro = st.columns([1, 2])
        with col_num: numero = st.text_input("Número", key='f_numero')
        with col_bairro: bairro = st.text_input("Bairro", key='f_bairro')
        referencia = st.text_input("Ponto de Referência", key='f_referencia')

        st.markdown("#### O Pedido")
        operadora = st.selectbox("Operadora 🔴", ["Selecione", "NIO Fibra", "TIM Ultrafibra", "Vivo", "Claro"], key='f_operadora')

        plano_final, valor_plano, detalhes_plano = "Selecione", 0.00, "---"

        if operadora == "NIO Fibra":
            plano_selecionado = st.selectbox("Plano", ["Selecione"] + list(PLANOS_NIO.keys()), key='f_nio_plano')
            if plano_selecionado != "Selecione":
                p = PLANOS_NIO[plano_selecionado]
                plano_final = f"NIO - {plano_selecionado}"
                valor_plano, detalhes_plano = p['valor'], p['detalhes']
                msg_info(f"R$ {valor_plano:.2f}/mês")

        elif operadora == "TIM Ultrafibra":
            plano_selecionado = st.selectbox("Plano", ["Selecione"] + list(PLANOS_TIM.keys()), key='f_tim_plano')
            if plano_selecionado != "Selecione":
                p = PLANOS_TIM[plano_selecionado]
                plano_final = f"TIM - {plano_selecionado}"
                valor_plano, detalhes_plano = p['valor'], p['detalhes']
                msg_info(f"R$ {valor_plano:.2f}/mês")

        elif operadora in ["Vivo", "Claro"]:
            st.selectbox("Plano", ["Selecione", "Plano Padrão"], key='f_default_plano')
            if st.session_state['f_default_plano'] == "Plano Padrão":
                plano_final, valor_plano, detalhes_plano = "Plano Padrão (Vivo/Claro)", 0.00, "Padrão"
                msg_info("Valor sob consulta.")

        observacoes = st.text_area("Observações", key='f_obs')

        salvar_rascunho()
        btn_salvar = st.form_submit_button("Salvar Venda e Gerar Ficha")

        if btn_salvar:
            if not nome or not cpf or not email or not whatsapp:
                msg_erro("Preencha todos os campos obrigatórios (marcados com 🔴).")
            elif operadora == "Selecione" or plano_final == "Selecione":
                msg_erro("Selecione Operadora e Plano.")
            elif not validar_cpf(cpf):
                msg_erro("CPF ou CNPJ inválido.")
            else:
                dados_venda = {
                    "tipo": "venda", "nome": nome, "cpf": cpf, "mae": mae, "email": email, "whats1": whatsapp,
                    "whats2": contato2, "cep": cep_input, "rua": rua, "numero": numero, "bairro": bairro,
                    "referencia": referencia, "operadora": operadora, "plano": plano_final, "valor_plano": valor_plano,
                    "detalhes_plano": detalhes_plano, "status": "Nova", "obs": observacoes
                }
                placeholder_envio = st.empty()
                placeholder_envio.markdown('<div class="enviando-caixa">⏳ Enviando dados...</div>', unsafe_allow_html=True)
                sucesso = enviar_para_planilha(dados_venda)
                placeholder_envio.empty()

                if sucesso:
                    msg_sucesso("Venda salva na planilha!")
                    limpar_rascunho()
                    st.code(formatar_ficha_venda(dados_venda), language="text")
                else:
                    msg_erro("Erro de conexão.")

with aba_leads:
    with st.form("form_lead", clear_on_submit=True):
        nome_lead = st.text_input("Nome")
        whatsapp_lead = st.text_input("WhatsApp")
        status_lead = st.selectbox("Status", ["Quente", "Frio", "Retorno", "Sem Viabilidade", "Outros"])
        obs_lead = st.text_area("Observações")
        if st.form_submit_button("Salvar Lead"):
            if not nome_lead or not whatsapp_lead:
                msg_erro("Preencha Nome e WhatsApp.")
            else:
                placeholder_envio_lead = st.empty()
                placeholder_envio_lead.markdown('<div class="enviando-caixa">⏳ Enviando dados...</div>', unsafe_allow_html=True)
                sucesso_lead = enviar_para_planilha({"tipo": "lead", "nome": nome_lead, "whatsapp": whatsapp_lead, "status": status_lead, "obs": obs_lead})
                placeholder_envio_lead.empty()

                if sucesso_lead:
                    msg_sucesso("Lead salvo!")
                else:
                    msg_erro("Erro ao enviar.")
