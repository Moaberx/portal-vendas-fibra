import streamlit as st
import requests
import json
import re
import urllib.parse
from datetime import datetime
from streamlit_local_storage import LocalStorage

# ================= CONEXÃO DE DADOS =================
URL_BACKEND_GOOGLE = "https://script.google.com/macros/s/AKfycbyTF3qUfRvMKh5JcyxJ_rbo8fSc04n24s8y8X7wtS0nP1qVjv2nUbpQLZHmAWmpXhKJ/exec"

# SENHA DO PAINEL ADMINISTRATIVO
# IMPORTANTE: não deixe a senha real aqui no código se o repositório for público.
# No Streamlit Cloud: Settings > Secrets, adicione a linha:
#   senha_mestre_gestao = "sua_senha_aqui"
# O código abaixo tenta ler do secrets primeiro; se não encontrar, usa "102030" como fallback.
try:
    SENHA_MESTRE_GESTAO = st.secrets.get("senha_mestre_gestao", "102030")
except Exception:
    SENHA_MESTRE_GESTAO = "102030"
# ====================================================

st.set_page_config(page_title="PAP Fibra", page_icon="📶", layout="centered")

# --- MEMÓRIA LOCAL E CONFIGURAÇÕES GLOBAIS ---
local_storage = LocalStorage()

if 'historico_vendas' not in st.session_state: st.session_state['historico_vendas'] = []
if 'historico_leads' not in st.session_state: st.session_state['historico_leads'] = []
if 'modo_gestao_liberado' not in st.session_state: st.session_state['modo_gestao_liberado'] = False
if 'mostrar_login_secreto' not in st.session_state: st.session_state['mostrar_login_secreto'] = False

# Configurações visuais e de catálogo (editáveis na Gestão)
if 'config_sistema' not in st.session_state:
    st.session_state['config_sistema'] = {
        "titulo_app": "PAP Fibra",
        "logo_url": "",
        "tema_cor": "#3B82F6",  # Azul padrão
        "pedir_mae": True, "obrigatorio_mae": False,
        "pedir_email": True, "obrigatorio_email": True,
        "extra1_ativo": False, "nome_extra1": "Campo Extra 1", "ob_extra1": False,
        "extra2_ativo": False, "nome_extra2": "Campo Extra 2", "ob_extra2": False
    }

# Planos Dinâmicos Editáveis
if 'planos_dinamicos' not in st.session_state:
    st.session_state['planos_dinamicos'] = {
        "NIO Fibra": {
            "500 Mega (Residencial)": {"valor": 100.00, "detalhes": "Wi-Fi padrão"},
            "600 Mega (Residencial)": {"valor": 109.00, "detalhes": "Wi-Fi padrão"},
            "800 Mega (Residencial)": {"valor": 135.00, "detalhes": "Wi-Fi 6 + Globoplay"}
        },
        "TIM Ultrafibra": {
            "600 Mega (PF)": {"valor": 119.99, "detalhes": "Wi-Fi grátis + Globoplay"},
            "800 Mega (PF)": {"valor": 129.99, "detalhes": "Wi-Fi grátis + YouTube Premium"}
        },
        "Vivo": {"Plano Padrão": {"valor": 0.00, "detalhes": "Padrão"}},
        "Claro": {"Plano Padrão": {"valor": 0.00, "detalhes": "Padrão"}}
    }

def carregar_memorias():
    try:
        rasc = local_storage.getItem("pap_rascunho_v5")
        if rasc:
            for k, v in (json.loads(rasc) if isinstance(rasc, str) else rasc).items():
                st.session_state[k] = v
        hist_v = local_storage.getItem("pap_hist_vendas_v5")
        if hist_v: st.session_state['historico_vendas'] = json.loads(hist_v) if isinstance(hist_v, str) else hist_v
        hist_l = local_storage.getItem("pap_hist_leads_v5")
        if hist_l: st.session_state['historico_leads'] = json.loads(hist_l) if isinstance(hist_l, str) else hist_l

        cfg = local_storage.getItem("pap_config_sys_v5")
        if cfg: st.session_state['config_sistema'] = json.loads(cfg) if isinstance(cfg, str) else cfg

        pl = local_storage.getItem("pap_planos_v5")
        if pl: st.session_state['planos_dinamicos'] = json.loads(pl) if isinstance(pl, str) else pl
    except: pass

def salvar_tudo():
    try:
        local_storage.setItem("pap_config_sys_v5", json.dumps(st.session_state['config_sistema']))
        local_storage.setItem("pap_planos_v5", json.dumps(st.session_state['planos_dinamicos']))
    except: pass

def salvar_rascunho():
    try:
        local_storage.setItem("pap_rascunho_v5", json.dumps({k: v for k, v in st.session_state.items() if k.startswith('f_')}))
    except: pass

def limpar_rascunho():
    try:
        local_storage.setItem("pap_rascunho_v5", "")
        for k in list(st.session_state.keys()):
            if k.startswith('f_'): del st.session_state[k]
    except: pass

def add_hist_venda(d):
    reg = {"protocolo": d['protocolo'], "nome": d['nome'].split()[0], "bairro": d['bairro'], "operadora": d['operadora'], "valor": d['valor_plano'], "data": datetime.now().strftime("%Y-%m-%d")}
    st.session_state['historico_vendas'].insert(0, reg)
    local_storage.setItem("pap_hist_vendas_v5", json.dumps(st.session_state['historico_vendas']))

def add_hist_lead(nome, status):
    st.session_state['historico_leads'].insert(0, {"nome": nome, "status": status, "data": datetime.now().strftime("%Y-%m-%d")})
    local_storage.setItem("pap_hist_leads_v5", json.dumps(st.session_state['historico_leads']))

# --- Helpers de mensagem (SEMPRE usar estes, nunca st.error/st.success/st.info nativos) ---
def msg_erro(t): st.markdown(f'<div class="msg-caixa msg-erro">❌ {t}</div>', unsafe_allow_html=True)
def msg_sucesso(t): st.markdown(f'<div class="msg-caixa msg-sucesso">✅ {t}</div>', unsafe_allow_html=True)
def msg_info(t): st.markdown(f'<div class="msg-caixa msg-info">ℹ️ {t}</div>', unsafe_allow_html=True)
def msg_venda_item(t): st.markdown(f'<div class="msg-caixa msg-info">🟢 {t}</div>', unsafe_allow_html=True)

def buscar_cep(cep):
    cep = re.sub(r'[^0-9]', '', str(cep))
    if len(cep) == 8:
        try:
            r = requests.get(f"https://viacep.com.br/ws/{cep}/json/", timeout=3)
            if r.status_code == 200 and "erro" not in r.json(): return r.json()
        except: pass
    return None

def formatar_ficha(d, cfg):
    f = f"""NOVA VENDA\n\nCLIENTE\n* Nome: {d['nome'].upper()}\n* CPF/CNPJ: {d['cpf']}"""
    if cfg.get('pedir_email') and d.get('email'): f += f"\n* Email: {d['email']}"
    if cfg.get('pedir_mae') and d.get('mae'): f += f"\n* Mãe: {d['mae'].upper()}"
    f += f"""\n\nCONTATOS\n* WhatsApp: {d['whats1']} (Ref: {d['ultimos_digitos']})\n* Contato 2: {d['whats2'] or '---'}"""
    f += f"""\n\nENDEREÇO\n* CEP: {d['cep']}\n* Rua: {d['rua'].upper()}, Nº {d['numero']} - {d['bairro'].upper()}\n* Ref: {d['referencia'].upper()}"""
    f += f"""\n\nPEDIDO\n* Operadora: {d['operadora'].upper()}\n* Plano: {d['plano'].upper()}\n* Valor: R$ {d['valor_plano']:.2f}\n* Detalhes: {d['detalhes_plano']}"""
    if cfg.get('extra1_ativo') and d.get('extra1'): f += f"\n* {cfg.get('nome_extra1')}: {d['extra1']}"
    if cfg.get('extra2_ativo') and d.get('extra2'): f += f"\n* {cfg.get('nome_extra2')}: {d['extra2']}"
    f += f"\n\nOBS: {d['obs']}"
    return f

def enviar_planilha(dados):
    try:
        r = requests.post(URL_BACKEND_GOOGLE, data=json.dumps(dados), headers={"Content-Type": "application/json"}, timeout=10)
        return r.status_code == 200 and r.json().get('status') == 'sucesso'
    except: return False

# --- CARREGA MEMÓRIAS ANTES DE QUALQUER RENDERIZAÇÃO ---
# (Corrigido: isso precisa acontecer ANTES de montar o CSS, senão a cor do tema
# e o título só aparecem corretos depois de uma interação extra do usuário.)
if not st.session_state.get('memorias_carregadas'):
    carregar_memorias()
    st.session_state['memorias_carregadas'] = True

# --- CSS DINÂMICO (agora já usa a config carregada corretamente) ---
cfg = st.session_state['config_sistema']
cor_tema = cfg.get('tema_cor', '#3B82F6')

st.markdown(f"""
    <style>
    .stApp {{ background-color: #000000; color: #FFFFFF; }}
    h1, h2, h3, .stSubheader, label, p, span {{ color: #FFFFFF !important; font-family: sans-serif; font-weight: 500; }}
    .legenda-obrigatorio {{ color: #9CA3AF !important; font-size: 13px; margin-bottom: 10px; }}

    .stTextInput>div>div>input, .stSelectbox>div>div>select, .stTextArea>div>div>textarea {{
        background-color: #121212 !important; color: #FFFFFF !important;
        border-radius: 6px !important; border: 1px solid #333333 !important; padding: 10px 12px !important;
    }}
    textarea {{ color: #FFFFFF !important; }}
    ul[data-baseweb="menu"] {{ background-color: #121212 !important; border: 1px solid #333333 !important; }}
    ul[data-baseweb="menu"] li {{ background-color: #121212 !important; color: #FFFFFF !important; }}
    div[data-baseweb="select"] > div {{ background-color: #121212 !important; border-color: #333333 !important; color: #FFFFFF !important; }}

    /* Alertas nativos (fallback de segurança, caso algum st.error/success escape) */
    div[data-testid="stAlert"] {{ background-color: #121212 !important; border: 1px solid #333333 !important; color: #FFFFFF !important; }}
    div[data-testid="stAlert"] * {{ color: #FFFFFF !important; }}

    .msg-caixa {{ border-radius: 6px; padding: 12px 16px; margin: 10px 0; font-weight: 500; }}
    .msg-erro {{ background-color: #2A0E0E; border: 1px solid #B91C1C; color: #FECACA !important; }}
    .msg-erro * {{ color: #FECACA !important; }}
    .msg-sucesso {{ background-color: #0E2A17; border: 1px solid #15803D; color: #BBF7D0 !important; }}
    .msg-sucesso * {{ color: #BBF7D0 !important; }}
    .msg-info {{ background-color: #0A1929; border: 1px solid #1E3A8A; color: #BFDBFE !important; }}
    .msg-info * {{ color: #BFDBFE !important; }}

    .stButton>button {{
        background-color: #1F2937; color: #FFFFFF; border: 1px solid #374151; border-radius: 6px;
        width: 100% !important; padding: 14px; margin-top: 15px; font-weight: bold;
    }}
    .stButton>button:hover {{ background-color: #374151; border-color: {cor_tema}; }}

    .btn-whatsapp {{
        display: block; width: 100%; background-color: #25D366; color: #000000 !important;
        text-align: center; font-weight: bold; padding: 14px; border-radius: 6px; text-decoration: none; margin-top: 10px;
    }}
    .card-metrica {{ background-color: #121212; border: 1px solid #333333; border-radius: 8px; padding: 15px; text-align: center; }}
    .card-metrica h2 {{ margin: 0; font-size: 28px; color: {cor_tema} !important; }}
    .card-metrica p {{ margin: 4px 0 0 0; color: #9CA3AF !important; }}
    .enviando-caixa {{ background-color: #1F2937; border: 1px solid #374151; border-radius: 6px; padding: 12px; text-align: center; font-weight: bold; animation: pulse 1.2s infinite; }}
    @keyframes pulse {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0.5; }} 100% {{ opacity: 1; }} }}

    .aviso-local {{ color: #6B7280 !important; font-size: 12px; margin-top: -5px; margin-bottom: 15px; }}

    /* Botão discreto de admin */
    .botao-admin-discreto button {{
        background-color: transparent !important; border: none !important; color: #374151 !important;
        width: auto !important; padding: 4px !important; font-size: 12px !important; margin-top: 30px !important;
    }}
    </style>
""", unsafe_allow_html=True)

if cfg.get('logo_url'):
    try: st.image(cfg.get('logo_url'), width=120)
    except: pass

st.title(f"📶 {cfg.get('titulo_app', 'PAP Fibra')}")

aba_vendas, aba_leads, aba_metricas = st.tabs(["📝 Nova Venda", "📞 Leads", "📊 Métricas"])

# ==================== ABA 1: VENDAS ====================
with aba_vendas:
    st.markdown('<p class="legenda-obrigatorio">🔴 = campos obrigatórios</p>', unsafe_allow_html=True)

    with st.form("form_venda", clear_on_submit=False):
        st.markdown("#### Cliente")
        nome = st.text_input("Nome Completo 🔴", key='f_nome')
        cpf = st.text_input("CPF / CNPJ 🔴", key='f_cpf')

        email, mae = "", ""
        if cfg.get('pedir_email'):
            email = st.text_input("Email 🔴" if cfg.get('obrigatorio_email') else "Email", key='f_email')
        if cfg.get('pedir_mae'):
            mae = st.text_input("Nome da Mãe 🔴" if cfg.get('obrigatorio_mae') else "Nome da Mãe", key='f_mae')

        col_tel1, col_tel2 = st.columns(2)
        with col_tel1: whatsapp = st.text_input("WhatsApp 🔴", key='f_whats1')
        with col_tel2: contato2 = st.text_input("Contato 2", key='f_whats2')

        st.markdown("#### Endereço")
        col_cep, col_btn = st.columns([2, 1])
        with col_cep: cep_input = st.text_input("CEP", key='f_cep')
        with col_btn:
            if st.form_submit_button("Buscar CEP"):
                salvar_rascunho()
                dc = buscar_cep(cep_input)
                if dc:
                    st.session_state['f_rua'] = dc.get("logradouro", "")
                    st.session_state['f_bairro'] = dc.get("bairro", "")
                    st.rerun()
                else: msg_erro("CEP não localizado.")

        rua = st.text_input("Rua", key='f_rua')
        col_num, col_bairro = st.columns([1, 2])
        with col_num: numero = st.text_input("Número", key='f_numero')
        with col_bairro: bairro = st.text_input("Bairro", key='f_bairro')
        referencia = st.text_input("Ponto de Referência", key='f_referencia')

        st.markdown("#### O Pedido")
        lista_ops = ["Selecione"] + list(st.session_state['planos_dinamicos'].keys())
        operadora = st.selectbox("Operadora 🔴", lista_ops, key='f_operadora')

        plano_final, valor_plano, detalhes_plano = "Selecione", 0.00, "---"

        if operadora != "Selecione":
            planos_op = st.session_state['planos_dinamicos'][operadora]
            plano_sel = st.selectbox("Plano", ["Selecione"] + list(planos_op.keys()), key='f_plano_op')
            if plano_sel != "Selecione":
                p_info = planos_op[plano_sel]
                plano_final = f"{operadora} - {plano_sel}"
                valor_plano = p_info['valor']
                detalhes_plano = p_info['detalhes']
                msg_info(f"R$ {valor_plano:.2f}/mês")

        extra1, extra2 = "", ""
        if cfg.get('extra1_ativo'):
            extra1 = st.text_input(f"{cfg.get('nome_extra1')} 🔴" if cfg.get('ob_extra1') else cfg.get('nome_extra1'), key='f_extra1')
        if cfg.get('extra2_ativo'):
            extra2 = st.text_input(f"{cfg.get('nome_extra2')} 🔴" if cfg.get('ob_extra2') else cfg.get('nome_extra2'), key='f_extra2')

        observacoes = st.text_area("Observações", key='f_obs')
        salvar_rascunho()
        btn_salvar = st.form_submit_button("📤 Validar, Salvar e Gerar Ficha")

        if btn_salvar:
            if not nome or not cpf or not whatsapp or operadora == "Selecione" or plano_final == "Selecione":
                msg_erro("Preencha os campos obrigatórios e selecione o plano.")
            else:
                nums_w = re.sub(r'[^0-9]', '', whatsapp)
                ult_dig = nums_w[-4:] if len(nums_w) >= 4 else nums_w
                protocolo = f"PAP{datetime.now().strftime('%Y%m%d%H%M%S')}"

                dados = {
                    "tipo": "venda", "protocolo": protocolo, "ultimos_digitos": ult_dig, "nome": nome, "cpf": cpf,
                    "mae": mae, "email": email, "whats1": whatsapp, "whats2": contato2, "cep": cep_input,
                    "rua": rua, "numero": numero, "bairro": bairro, "referencia": referencia, "operadora": operadora,
                    "plano": plano_final, "valor_plano": valor_plano, "detalhes_plano": detalhes_plano,
                    "extra1": extra1, "extra2": extra2, "status": "Nova", "obs": observacoes
                }

                pe = st.empty()
                pe.markdown('<div class="enviando-caixa">⏳ Registrando venda...</div>', unsafe_allow_html=True)
                sucesso = enviar_planilha(dados)
                pe.empty()

                if sucesso:
                    # Nota: essa mensagem NÃO afirma envio de e-mail, pois este código
                    # só confirma o registro na planilha. Se seu Apps Script também
                    # dispara e-mail, ajuste o texto abaixo para refletir isso.
                    msg_sucesso("Venda registrada com sucesso!")
                    add_hist_venda(dados)
                    limpar_rascunho()
                    txt_f = formatar_ficha(dados, cfg)
                    st.code(txt_f, language="text")
                    st.markdown(f'<a href="https://api.whatsapp.com/send?text={urllib.parse.quote(txt_f)}" target="_blank" class="btn-whatsapp">📲 Enviar Ficha Direto no WhatsApp</a>', unsafe_allow_html=True)
                else:
                    msg_erro("Erro de conexão. Rascunho salvo.")

# ==================== ABA 2: LEADS ====================
with aba_leads:
    with st.form("form_lead", clear_on_submit=True):
        nome_l = st.text_input("Nome do Contato")
        whats_l = st.text_input("WhatsApp")
        status_l = st.selectbox("Qualificação", ["Quente", "Frio", "Retorno", "Sem Viabilidade", "Outros"])
        obs_l = st.text_area("Anotações")
        if st.form_submit_button("Salvar Lead"):
            if not nome_l or not whats_l: msg_erro("Preencha Nome e WhatsApp.")
            else:
                sucesso_l = enviar_planilha({"tipo": "lead", "nome": nome_l, "whatsapp": whats_l, "status": status_l, "obs": obs_l})
                if sucesso_l:
                    msg_sucesso("Lead salvo!")
                    add_hist_lead(nome_l, status_l)
                else: msg_erro("Erro de conexão.")

# ==================== ABA 3: MÉTRICAS ====================
with aba_metricas:
    st.markdown("#### 📊 Desempenho Pessoal")
    st.markdown('<p class="aviso-local">⚠️ Esses números ficam salvos só neste navegador/aparelho — se trocar de celular ou limpar o cache, o histórico local some (as vendas continuam seguras na planilha).</p>', unsafe_allow_html=True)

    hj, mes = datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%Y-%m")
    v_hj = [v for v in st.session_state['historico_vendas'] if v.get('data') == hj]
    v_mes = [v for v in st.session_state['historico_vendas'] if v.get('data', '').startswith(mes)]
    val_mes = sum([v.get('valor', 0) for v in v_mes])

    c1, c2 = st.columns(2)
    with c1: st.markdown(f'<div class="card-metrica"><h2>{len(v_hj)}</h2><p>Vendas Hoje</p></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="card-metrica"><h2>{len(v_mes)}</h2><p>Mês (R$ {val_mes:.2f})</p></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("##### 📜 Últimas Vendas Locais")
    if not st.session_state['historico_vendas']:
        msg_info("Nenhuma venda registrada neste aparelho ainda.")
    for v in st.session_state['historico_vendas'][:10]:
        msg_venda_item(f"{v['nome']} ({v.get('bairro','')}) - {v['operadora']} (R$ {v.get('valor',0):.2f})")

# ==================== ENTRADA SECRETA PARA GESTÃO ====================
st.markdown("---")
if not st.session_state['mostrar_login_secreto']:
    st.markdown('<div class="botao-admin-discreto">', unsafe_allow_html=True)
    if st.button("⚙️", help="Acesso Administrativo"):
        st.session_state['mostrar_login_secreto'] = True
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
else:
    st.markdown("#### 🔒 Acesso Restrito de Gestão")
    if not st.session_state['modo_gestao_liberado']:
        senha = st.text_input("Senha Mestre", type="password")
        if st.button("Destravar"):
            if senha == SENHA_MESTRE_GESTAO:
                st.session_state['modo_gestao_liberado'] = True
                st.rerun()
            else: msg_erro("Senha incorreta.")
    else:
        msg_sucesso("🔓 Painel Administrativo Ativo!")
        if st.button("Sair da Gestão"):
            st.session_state['modo_gestao_liberado'] = False
            st.session_state['mostrar_login_secreto'] = False
            st.rerun()

        st.markdown("---")
        st.markdown("##### 🛠️ Editor Universal de Planos e Layout")

        with st.form("form_gestao_supremo"):
            st.markdown("**Personalização Visual**")
            n_tit = st.text_input("Nome do Sistema", value=cfg.get('titulo_app'))
            n_logo = st.text_input("URL da Logo (Opcional)", value=cfg.get('logo_url'))
            n_cor = st.color_picker("Cor de Destaque", value=cfg.get('tema_cor'))

            st.markdown("---")
            st.markdown("**Gestão de Planos (Valores Atuais)**")
            msg_info("Aqui você edita os preços atuais para refletirem na rua imediatamente.")

            # Exemplo de edição rápida de valores NIO
            novo_p_nio_800 = st.number_input("Preço 800 Mega NIO (Residencial)", value=float(st.session_state['planos_dinamicos']['NIO Fibra']['800 Mega (Residencial)']['valor']))

            if st.form_submit_button("💾 Salvar Alterações Definitivas"):
                cfg['titulo_app'] = n_tit
                cfg['logo_url'] = n_logo
                cfg['tema_cor'] = n_cor
                st.session_state['planos_dinamicos']['NIO Fibra']['800 Mega (Residencial)']['valor'] = novo_p_nio_800
                salvar_tudo()
                msg_sucesso("Sistema atualizado com sucesso!")
                st.rerun()
