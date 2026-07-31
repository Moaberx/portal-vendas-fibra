import streamlit as st
import requests
import json
import re
import urllib.parse
from datetime import datetime
import pandas as pd
from streamlit_local_storage import LocalStorage

# ================= CONEXÃO DE DADOS =================
URL_BACKEND_GOOGLE = "https://script.google.com/macros/s/AKfycbxpacnXvvIMh7tfqcH6iUmmRLF_9l4XhBBGdr0Iyl4RfqVnhtg4bv3daMN80yXgvyFS/exec"
SENHA_DA_API = "PAP_SECRETO_2026" 
SENHA_MESTRE_GESTAO = "102030"    
LINK_DFV_TIM = "https://app.powerbi.com/view?r=eyJrIjoiODgyZDdiMTItOTM1MS00ZGFkLTkyZTktOTg5ZmJjNjc0OTViIiwidCI6ImI1MmJhNGIzLWM0MTEtNGQxNi04Yzc2LTAwNDg5YzBhMjA1YSJ9"
# ====================================================

st.set_page_config(page_title="📶 PAP Fibra Pro", page_icon="📶", layout="centered")
local_storage = LocalStorage()

if 'vendedores_cadastrados' not in st.session_state: st.session_state['vendedores_cadastrados'] = ["Moabe"]
if 'modo_gestao_liberado' not in st.session_state: st.session_state['modo_gestao_liberado'] = False
if 'tema' not in st.session_state: st.session_state['tema'] = "Claro Premium"
if 'aba_ativa' not in st.session_state: st.session_state['aba_ativa'] = "Home"

if 'planos_dinamicos' not in st.session_state:
    st.session_state['planos_dinamicos'] = {
        "TIM Ultrafibra": {"600 Mega (PF)": 119.99, "800 Mega (PF)": 129.99, "1 Giga (PF)": 129.99, "1 Giga (CNPJ)": 99.90},
        "NIO Fibra": {"500 Mega": 100.00, "600 Mega": 109.00, "800 Mega": 135.00, "1 Giga": 160.00},
        "Vivo": {"Padrão": 0.00}, "Claro": {"Padrão": 0.00}
    }

def chamar_api(dados_payload):
    try:
        resp = requests.post(URL_BACKEND_GOOGLE, data=json.dumps(dados_payload), headers={"Content-Type": "application/json"}, timeout=15)
        if resp.status_code == 200: return resp.json()
    except Exception as e:
        return {"status": "erro", "msg": str(e)}
    return {"status": "erro", "msg": "Servidor fora do ar."}

def buscar_cep(cep):
    cep = re.sub(r'[^0-9]', '', str(cep))
    if len(cep) == 8:
        try:
            r = requests.get(f"https://viacep.com.br/ws/{cep}/json/", timeout=3)
            if r.status_code == 200 and "erro" not in r.json(): return r.json()
        except: pass
    return None

def msg_erro(t): st.markdown(f'<div class="alerta-erro">❌ {t}</div>', unsafe_allow_html=True)
def msg_sucesso(t): st.markdown(f'<div class="alerta-sucesso">✅ {t}</div>', unsafe_allow_html=True)

def validar_cpf_cnpj(doc):
    doc = re.sub(r'[^0-9]', '', str(doc))
    return len(doc) == 11 or len(doc) == 14

def validar_telefone(tel):
    nums = re.sub(r'[^0-9]', '', str(tel))
    return 10 <= len(nums) <= 11

# --- CSS PREMIUM INTEGRADO (INSPIRADO NAS IMAGENS) ---
header_color = "#7E22CE" if st.session_state['tema'] == "Claro Premium" else "#9333EA"
detail_color = "#C026D3" if st.session_state['tema'] == "Claro Premium" else "#EC4899"
background_color = "#FFFFFF" if st.session_state['tema'] == "Claro Premium" else "#0F172A"
text_color = "#000000" if st.session_state['tema'] == "Claro Premium" else "#FFFFFF"
label_color = "#7E22CE" if st.session_state['tema'] == "Claro Premium" else "#C026D3"
card_background = "#F9FAFB" if st.session_state['tema'] == "Claro Premium" else "#1A1C23"

st.markdown(f"""
    <style>
    /* Fundo absoluto e fontes */
    .stApp {{ background-color: {background_color}; color: {text_color}; font-family: 'Inter', sans-serif; }}
    
    /* Header Premium Inspirado */
    .header-premium {{
        background-color: {header_color};
        color: #FFFFFF;
        padding: 15px;
        position: fixed;
        top: 0; left: 0; width: 100%;
        display: flex; justify-content: space-between; align-items: center;
        z-index: 1000;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }}
    .header-title {{ font-size: 20px; font-weight: 700; display: flex; align-items: center; }}
    .header-icons {{ display: flex; align-items: center; }}
    .header-icons span {{ margin-left: 15px; cursor: pointer; }}
    .message-badge {{
        background-color: #EF4444; color: #FFFFFF;
        border-radius: 50%; padding: 2px 6px;
        font-size: 10px; position: relative; top: -8px; left: -8px;
    }}
    
    /* Toggle de Tema no Header */
    .theme-toggle {{ font-size: 16px; cursor: pointer; }}
    
    /* Bottom Navigation Inspirado */
    .bottom-nav {{
        background-color: {background_color};
        position: fixed; bottom: 0; left: 0; width: 100%;
        display: flex; justify-content: space-around; align-items: center;
        padding: 10px 0;
        z-index: 1000;
        border-top: 1px solid {"#E0E6ED" if st.session_state['tema'] == "Claro Premium" else "#333333"};
        box-shadow: 0 -4px 6px -1px rgba(0, 0, 0, 0.05);
    }}
    .nav-item {{
        display: flex; flex-direction: column; align-items: center;
        cursor: pointer; color: #6B7280; font-size: 12px; font-weight: 500;
    }}
    .nav-item.active {{ color: {detail_color}; font-weight: 600; }}
    .nav-item i {{ font-size: 20px; margin-bottom: 2px; }}
    
    /* Botão Central Flutuante (+) */
    .central-button {{
        background-color: {detail_color}; color: #FFFFFF !important;
        border-radius: 50%; padding: 12px; margin-top: -15px;
        font-size: 24px; box-shadow: 0 6px 8px -1px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s;
    }}
    .central-button:hover {{ transform: scale(1.05); }}

    /* Estilização de Inputs Reestilizada */
    .stTextInput>div>div>input, .stSelectbox>div>div>select, .stTextArea>div>div>textarea {{
        background-color: {background_color} !important; 
        color: {text_color} !important; 
        border-radius: 6px !important; 
        border: 1px solid {"#E0E6ED" if st.session_state['tema'] == "Claro Premium" else "#333333"} !important;
        padding: 12px !important;
        transition: border-color 0.3s;
    }}
    .stTextInput>div>div>input:focus, .stSelectbox>div>div>select:focus {{
        border-color: {detail_color} !important;
        box-shadow: none !important;
    }}
    .stTextInput>label {{ color: {label_color} !important; font-weight: 600; }}
    .stSelectbox>label {{ color: {label_color} !important; font-weight: 600; }}
    
    /* Checkbox Estilizado (Sem número) */
    .stCheckbox>label>span {{ color: #6B7280; font-size: 14px; }}
    
    /* Botões Padrões e Hover Reestilizados */
    .stButton>button {{ 
        background-color: {detail_color}; 
        color: #FFFFFF; 
        border: none; 
        border-radius: 8px; 
        width: 100%; 
        font-weight: 600; 
        padding: 12px;
        transition: all 0.2s ease-in-out;
    }}
    .stButton>button:hover {{ background-color: {"#A21CAE" if st.session_state['tema'] == "Claro Premium" else "#DB2777"}; transform: translateY(-1px); }}
    
    /* Botão WhatsApp Específico Reestilizado */
    .btn-whatsapp {{ 
        display: block; width: 100%; background-color: #10B981; color: #FFFFFF !important; 
        text-align: center; font-weight: 600; padding: 14px; border-radius: 8px; 
        text-decoration: none; margin-top: 15px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        transition: background-color 0.2s;
    }}
    .btn-whatsapp:hover {{ background-color: #059669; }}
    
    /* Alertas Reestilizados */
    .alerta-erro {{ background:{"#FEE2E2" if st.session_state['tema'] == "Claro Premium" else "#3F1D1D"}; border-left: 4px solid #EF4444; color:{"#991B1B" if st.session_state['tema'] == "Claro Premium" else "#FECACA"}; padding:12px; border-radius:4px; margin-bottom:12px; font-size: 14px;}}
    .alerta-sucesso {{ background:{"#A7F3D0" if st.session_state['tema'] == "Claro Premium" else "#143324"}; border-left: 4px solid #10B981; color:{"#065F46" if st.session_state['tema'] == "Claro Premium" else "#A7F3D0"}; padding:12px; border-radius:4px; margin-bottom:12px; font-size: 14px;}}
    
    /* Cards de Dashboard Reestilizados (Inspirados na imagem 1) */
    .dashboard-card {{
        background-color: #F9FAFB;
        border: 1px solid #E0E6ED;
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        display: flex; flex-direction: column; align-items: center; justify-content: space-between;
        margin-bottom: 15px;
    }}
    .dashboard-card h3 {{ margin: 0; color: #000000; font-size: 14px; font-weight: 600; }}
    .dashboard-card .metric {{ font-size: 28px; font-weight: 700; }}
    .dashboard-card .icon {{ font-size: 24px; }}
    .card-aprovadas {{ border-color: #10B981; color: #10B981; }}
    .card-reprovadas {{ border-color: #EF4444; color: #EF4444; }}
    .card-pendente {{ border-color: #F97316; color: #F97316; }}
    .card-finalizadas {{ border-color: #6B7280; color: #6B7280; }}
    .card-aguardando {{ border-color: #8B5CF6; color: #8B5CF6; }}
    .card-andamento {{ border-color: #3B82F6; color: #3B82F6; }}
    
    /* Cards de Leads Estilo ColorNote (Cópia Reestilizada) */
    .lead-card {{
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        display: flex; flex-direction: column; justify-content: space-between;
        color: #000000; /* Texto preto nos cartões coloridos */
    }}
    .lead-card h3 {{ margin: 0 0 5px 0; font-size: 16px; font-weight: 700; color: #000000; }}
    .lead-card p {{ margin: 0; font-size: 12px; color: #374151; }}
    .lead-card .edit-icon {{ align-self: flex-end; font-size: 16px; cursor: pointer; color: #000000; }}
    .lead-amarelo {{ background-color: #FEF3C7; }}
    .lead-azul {{ background-color: #BFDBFE; }}
    .lead-verde {{ background-color: #A7F3D0; }}
    .lead-rosa {{ background-color: #FBCFE8; }}
    
    /* Títulos de Seção Premium */
    h3, h4 {{ color: {label_color} !important; font-weight: 700; margin-bottom: 10px; }}
    
    /* Esconder elementos desnecessários do Streamlit */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    .stAppHeader {{visibility: hidden;}}
    [data-testid="stSidebar"] {{visibility: hidden;}}
    
    /* Correção de Margem Superior devido ao Header fixo */
    .stApp {{ margin-top: 80px; padding-bottom: 100px; }}
    </style>
""", unsafe_allow_html=True)

# --- CABEÇALHO PREMIUM INTEGRADO (INSPIRADO) ---
theme_icon = "☀️" if st.session_state['tema'] == "Claro Premium" else "🌙"
st.markdown(f"""
    <div class="header-premium">
        <div class="header-title">📶 PAP Fibra Pro</div>
        <div class="header-icons">
            <span class="theme-toggle" id="theme-toggle">{theme_icon}</span>
            <span>💬 <span class="message-badge">188</span></span>
            <span>🔔</span>
            <span>👤</span>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- SISTEMA DE NAVEGAÇÃO INTEGRADO (BOTTOM NAV) ---
def navegar(aba):
    st.session_state['aba_ativa'] = aba
    st.rerun()

st.markdown(f"""
    <div class="bottom-nav">
        <div class="nav-item {'active' if st.session_state['aba_ativa'] == 'Home' else ''}" id="home-nav">
            <i>🏠</i> Início
        </div>
        <div class="nav-item {'active' if st.session_state['aba_ativa'] == 'Vendas' else ''}" id="vendas-nav">
            <i>📝</i> Pedidos
        </div>
        <div class="central-button" id="cadastrar-nav">
            <i>➕</i>
        </div>
        <div class="nav-item {'active' if st.session_state['aba_ativa'] == 'Leads' else ''}" id="leads-nav">
            <i>📋</i> Leads
        </div>
        <div class="nav-item {'active' if st.session_state['aba_ativa'] == 'Métricas' else ''}" id="metricas-nav">
            <i>📊</i> Métricas
        </div>
    </div>
""", unsafe_allow_html=True)

# --- LÓGICA DE NAVEGAÇÃO ---
# (Em Streamlit web, imitar o clique do bottom nav é complexo. Usaremos botões transparentes por cima ou rádio.)
# A opção mais prática é usar rádio e CSS para reposicionar. Mas para imitar perfeitamente o visual,
# vou manter os botões Streamlit em uma seção separada e usar CSS para reposicionar.

# --- CONTEÚDO PRINCIPAL (BASEADO NA ABA ATIVA) ---

# ABA: HOME (DASHBOARD INSPIRADO)
if st.session_state['aba_ativa'] == 'Home':
    st.markdown("### Status de Vendas")
    # Puxar dados reais da planilha (simulação aqui)
    instalados, cancelados, pendente, finalizadas, aguardando, andamento = 15, 15, 0, 30, 0, 0
    
    col1, col2, col3 = st.columns(3)
    with col1: st.markdown(f'<div class="dashboard-card card-aprovadas"><h3>Aprovadas</h3><span class="metric">{instalados}</span><span class="icon">✅</span></div>', unsafe_allow_html=True)
    with col2: st.markdown(f'<div class="dashboard-card card-reprovadas"><h3>Reprovadas</h3><span class="metric">{cancelados}</span><span class="icon">❌</span></div>', unsafe_allow_html=True)
    with col3: st.markdown(f'<div class="dashboard-card card-pendente"><h3>Pendente</h3><span class="metric">{pendente}</span><span class="icon">✏️</span></div>', unsafe_allow_html=True)
    
    col4, col5, col6 = st.columns(3)
    with col4: st.markdown(f'<div class="dashboard-card card-finalizadas"><h3>Finalizadas</h3><span class="metric">{finalizadas}</span><span class="icon">❌</span></div>', unsafe_allow_html=True)
    with col5: st.markdown(f'<div class="dashboard-card card-aguardando"><h3>Aguardando</h3><span class="metric">{aguardando}</span><span class="icon">🕒</span></div>', unsafe_allow_html=True)
    with col6: st.markdown(f'<div class="dashboard-card card-andamento"><h3>Andamento</h3><span class="metric">{andamento}</span><span class="icon">➡️</span></div>', unsafe_allow_html=True)

# ABA: VENDAS (VISUALIZAÇÃO DE PEDIDOS)
elif st.session_state['aba_ativa'] == 'Vendas':
    st.markdown("### Histórico de Pedidos")
    if st.button("🔄 Puxar Dados da Planilha"):
        with st.spinner("Sincronizando..."):
            res = chamar_api({"acao": "ler", "senha_api": SENHA_DA_API, "aba_alvo": "VENDAS"})
            if res.get('status') == 'sucesso':
                dados_puros = res.get('dados', [])
                if len(dados_puros) > 1:
                    df = pd.DataFrame(dados_puros[1:], columns=dados_puros[0])
                    st.session_state['df_pedidos'] = df
                    msg_sucesso(f"Base carregada! ({len(df)} pedidos)")
                else: msg_erro("Nenhum pedido registrado.")
            else: msg_erro("Erro de conexão.")
    
    if 'df_pedidos' in st.session_state:
        st.dataframe(st.session_state['df_pedidos'], use_container_width=True)

# ABA: CADASTRAR (FORMULÁRIO INSPIRADO E REESTILIZADO)
elif st.session_state['aba_ativa'] == 'Cadastrar':
    st.markdown("### Cadastrar Novo Pedido")
    with st.form("form_venda_premium", clear_on_submit=False):
        vendedor_atual = st.selectbox("Operador", st.session_state['vendedores_cadastrados'])
        
        st.markdown("#### Endereço")
        cep_input = st.text_input("CEP *")
        col_end, col_num = st.columns([2, 1])
        with col_end: rua = st.text_input("Endereço * - (rua, av...)")
        with col_num: 
            numero = st.text_input("Número")
            st.checkbox("Sem número")
        
        col_bairro, col_estado = st.columns(2)
        with col_bairro: bairro = st.text_input("Bairro *")
        with col_estado: estado = st.text_input("Estado(UF)")
        
        st.text_input("Cidades")

        st.markdown("#### Cliente")
        nome = st.text_input("Nome Completo *", placeholder="Ex: João da Silva")
        cpf = st.text_input("CPF / CNPJ *")
        whatsapp = st.text_input("WhatsApp (DDD) *")
        
        st.markdown("#### Pedido")
        operadora = st.selectbox("Operadora *", ["Selecione"] + list(st.session_state['planos_dinamicos'].keys()))
        
        plano_sel, valor_plano = "Selecione", 0.00
        if operadora != "Selecione":
            plano_sel = st.selectbox("Pacote *", ["Selecione"] + list(st.session_state['planos_dinamicos'][operadora].keys()))
            if plano_sel != "Selecione":
                valor_plano = st.session_state['planos_dinamicos'][operadora][plano_sel]
                st.markdown(f"**Mensalidade Estimada:** R$ {valor_plano:.2f}")

        obs = st.text_area("Notas / Observações")

        if st.form_submit_button("🚀 Finalizar Venda"):
            if not nome or not cpf or not whatsapp or operadora == "Selecione" or plano_sel == "Selecione":
                msg_erro("Preencha as informações obrigatórias (marcadas com *).")
            else:
                protocolo = f"PAP{datetime.now().strftime('%Y%m%d%H%M%S')}"
                plano_final = f"{operadora} - {plano_sel}"
                
                payload = {
                    "acao": "inserir", "tipo": "venda", "protocolo": protocolo, "nome": nome, "cpf": cpf,
                    "whats1": whatsapp, "cep": cep_input, "rua": rua, "numero": numero, "bairro": bairro,
                    "operadora": operadora, "plano": plano_final, "valor_plano": valor_plano, 
                    "status": "Nova", "obs": obs, "vendedor": vendedor_atual
                }
                
                with st.spinner("Sincronizando..."):
                    resposta = chamar_api(payload)
                
                if resposta.get('status') == 'sucesso':
                    msg_sucesso(f"Pedido Finalizado! Protocolo: {protocolo}")
                    ficha = f"NOVO PEDIDO\n\nOperador: {vendedor_atual}\n\nCLIENTE: {nome.upper()}\nCPF: {cpf}\nWhatsApp: {whatsapp}\n\nENDEREÇO: {rua}, {numero} - {bairro}\nCEP: {cep_input}\n\nPEDIDO: {plano_final}\nVALOR: R$ {valor_plano:.2f}\nOBS: {obs}"
                    st.markdown(f'<a href="https://api.whatsapp.com/send?text={urllib.parse.quote(ficha)}" target="_blank" class="btn-whatsapp">📲 Enviar Ficha no WhatsApp</a>', unsafe_allow_html=True)
                else:
                    msg_erro("Falha na comunicação com o servidor.")

# ABA: LEADS (ESTILO COLORNOTE INTEGRADO E REESTILIZADO)
elif st.session_state['aba_ativa'] == 'Leads':
    st.markdown("### Meus Leads")
    st.text_input("🔍 Buscar lead...")
    
    # Simulação de leads estilo ColorNote (cartões coloridos)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'<div class="lead-card lead-amarelo"><h3>João da Silva</h3><p>Quente</p><p>Obs: Apro da tagor nomera</p><span class="edit-icon">✏️</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="lead-card lead-verde"><h3>João da Silva</h3><p>Quente</p><p>Obs: Companta esta hoizona entudo</p><span class="edit-icon">✏️</span></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="lead-card lead-azul"><h3>João da Silva</h3><p>Frio</p><p>Obs: Apro da un moriina namera</p><span class="edit-icon">✏️</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="lead-card lead-rosa"><h3>João da Silva</h3><p>Frio</p><p>Obs: João da Silva</p><span class="edit-icon">✏️</span></div>', unsafe_allow_html=True)
    
    st.markdown(f'<a href="{LINK_DFV_TIM}" target="_blank" style="color: #6B7280; font-size: 10px; text-decoration: none; display: block; text-align: center; margin-top: 10px;">DFV TIM</a>', unsafe_allow_html=True)

# ABA: MÉTRICAS (GESTÃO DETALHADA COM SENHA)
elif st.session_state['aba_ativa'] == 'Métricas':
    if not st.session_state['modo_gestao_liberado']:
        st.markdown("### Acesso Restrito")
        senha = st.text_input("Credencial Administrativa", type="password")
        if st.button("Autenticar"):
            if senha == SENHA_MESTRE_GESTAO:
                st.session_state['modo_gestao_liberado'] = True
                st.rerun()
            else: msg_erro("Credencial inválida.")
    else:
        col_tit, col_sair = st.columns([3, 1])
        with col_tit: st.markdown("### Gestão Detalhada")
        with col_sair: 
            if st.button("🔒 Sair"): 
                st.session_state['modo_gestao_liberado'] = False
                st.rerun()
        
        # Puxar dados reais e mostrar gráficos anteriores (reestilizados)
        if st.button("🔄 Puxar Dados e Gerar Gráficos"):
            with st.spinner("Processando..."):
                res = chamar_api({"acao": "ler", "senha_api": SENHA_DA_API, "aba_alvo": "VENDAS"})
                if res.get('status') == 'sucesso':
                    dados_puros = res.get('dados', [])
                    if len(dados_puros) > 1:
                        df = pd.DataFrame(dados_puros[1:], columns=dados_puros[0])
                        st.session_state['df_gestao'] = df
                    else: msg_erro("Base vazia.")
                else: msg_erro("Erro de conexão.")
        
        if 'df_gestao' in st.session_state:
            df = st.session_state['df_gestao']
            
            # --- CARDS DE MÉTRICAS GESTÃO ---
            total = len(df)
            instalados = len(df[df['Status'].astype(str).str.contains('Instalado', case=False, na=False)])
            receita = df['valor_plano'].apply(pd.to_numeric, errors='coerce').sum()
            
            col_g1, col_g2, col_g3 = st.columns(3)
            col_g1.metric(label="Vendas Total", value=f"{total}")
            col_g2.metric(label="🟢 Instalados", value=f"{instalados}")
            col_g3.metric(label="Receita Bruta", value=f"R$ {receita:,.2f}")
            
            # --- GRÁFICOS REAIS REESTILIZADOS ---
            st.markdown("---")
            col_graf1, col_graf2 = st.columns(2)
            
            with col_graf1:
                st.markdown("**Vendas por Operadora**")
                graf_op = df['Operadora'].value_counts()
                st.bar_chart(graf_op, color=detail_color)
                
            with col_graf2:
                st.markdown("**Status do Funil**")
                graf_status = df['Status'].value_counts()
                st.bar_chart(graf_status, color="#10B981")

# --- LÓGICA DE CONTROLE DA BOTTOM NAV ---
# Como Streamlit web não detecta cliques no HTML personalizado nativamente, 
# usaremos botões transparentes por cima (não ideal) ou rádio estilizado.
# Mas para imitar perfeitamente o visual, vou usar botões Streamlit em uma seção separada e usar CSS para reposicionar.

# --- SEÇÃO DE CONTROLE DA BOTTOM NAV (INVISÍVEL MAS FUNCIONAL) ---
# Usamos rádio Streamlit para controlar a aba ativa e reestilizamos para esconder.
# Mas, para manter a fidelidade visual, vou usar botões Streamlit em uma seção oculta.
# A melhor alternativa em Streamlit para esse caso é usar rádio e reestilizá-lo com CSS.

st.markdown("---")
# Controle de Tema (no Header)
if st.button("Alternar Tema"):
    st.session_state['tema'] = "Escuro Premium" if st.session_state['tema'] == "Claro Premium" else "Claro Premium"
    st.rerun()

# Controle da Bottom Nav
st.write("### Navegação de Desenvolvimento")
c1, c2, c3, c4, c5 = st.columns(5)
if c1.button("Início"): navegar("Home")
if c2.button("Pedidos"): navegar("Vendas")
if c3.button("Cadastrar (+)", key="cad"): navegar("Cadastrar")
if c4.button("Leads"): navegar("Leads")
if c5.button("Métricas"): navegar("Métricas")
