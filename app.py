import streamlit as st
import requests
import json
import re
import urllib.parse
from datetime import datetime
import pandas as pd
from streamlit_local_storage import LocalStorage

# ================= CONEXÃO DE DADOS =================
# PREFERÊNCIA 41 & 42: URL ÚNICA DO GAS E DADOS REAIS
URL_BACKEND_GOOGLE = "COLOQUE_AQUI_SUA_URL_DO_WEB_APP"
SENHA_DA_API = "PAP_SECRETO_2026" # PREFERÊNCIA 47: SEGURANÇA POR TOKEN
SENHA_MESTRE_GESTAO = "102030"    # PREFERÊNCIA 49: SENHA MESTRE
# ====================================================

# PREFERÊNCIA 3, 19 & 20: TÍTULO, TEMA PADRÃO E OPÇÃO DE ALTERNAR
st.set_page_config(page_title="PAP FIBRA", page_icon="📶", layout="centered", initial_sidebar_state="collapsed")

local_storage = LocalStorage()

if 'vendedores_dinamicos' not in st.session_state: st.session_state['vendedores_dinamicos'] = []
if 'planos_dinamicos' not in st.session_state: st.session_state['planos_dinamicos'] = {}
if 'operadoras_dinamicas' not in st.session_state: st.session_state['operadoras_dinamicas'] = []
if 'modo_gestao_liberado' not in st.session_state: st.session_state['modo_gestao_liberado'] = False

# --- AJUSTES LOCAIS INICIAIS ---
if not st.session_state.get('configs_carregadas'):
    # PREFERÊNCIA 34: RASCUNHO LOCAL E DADOS LOCAIS
    try:
        vends = local_storage.getItem("pap_vendedores_v2")
        if vends: st.session_state['vendedores_dinamicos'] = json.loads(vends) if isinstance(vends, str) else vends
    except: pass
    
    # Carrega dados essenciais da planilha uma única vez ao iniciar
    # (Prepara o app para Preferências 25, 27 & 28)
    # payload_inicial = {"acao": "carregar_inicial", "senha_api": SENHA_DA_API}
    # resposta_inicial = chamar_api(payload_inicial)
    # (Descomentar acima e tratar resposta quando tiver o GAS definitivo)
    # Por enquanto, simula o carregamento inicial:
    st.session_state['vendedores_dinamicos'] = ["Moabe", "Renan"]
    st.session_state['operadoras_dinamicas'] = ["TIM Ultrafibra", "NIO Fibra", "Claro", "Giga+ Fibra"]
    st.session_state['planos_dinamicos'] = {
        "TIM Ultrafibra": ["600 Mega", "800 Mega"],
        "NIO Fibra": ["500 Mega", "600 Mega", "800 Mega"],
        "Claro": ["Padrão Claro"],
        "Giga+ Fibra": ["Padrão Giga+"]
    }
    st.session_state['configs_carregadas'] = True

# --- FUNÇÕES DE COMUNICAÇÃO ---
# PREFERÊNCIA 46: "MODO DEUS" CRUD DEFINITIVO NO GAS
def chamar_api(dados_payload):
    try:
        resp = requests.post(URL_BACKEND_GOOGLE, data=json.dumps(dados_payload), headers={"Content-Type": "application/json"}, timeout=15)
        if resp.status_code == 200: return resp.json()
    except Exception as e:
        return {"status": "erro", "msg": str(e)}
    return {"status": "erro", "msg": "Servidor fora do ar."}

# PREFERÊNCIA 22: BUSCA CEP MÁGICA
def buscar_cep(cep):
    cep = re.sub(r'[^0-9]', '', str(cep))
    if len(cep) == 8:
        try:
            r = requests.get(f"https://viacep.com.br/ws/{cep}/json/", timeout=3)
            if r.status_code == 200 and "erro" not in r.json(): return r.json()
        except: pass
    return None

# --- HELPERS ---
def msg_erro(t): st.markdown(f'<div class="alerta-erro">❌ {t}</div>', unsafe_allow_html=True)
def msg_sucesso(t): st.markdown(f'<div class="alerta-sucesso">✅ {t}</div>', unsafe_allow_html=True)

# PREFERÊNCIA 31: VALIDAÇÃO CPF/CNPJ
def validar_cpf_cnpj(doc):
    doc = re.sub(r'[^0-9]', '', str(doc))
    return len(doc) == 11 or len(doc) == 14

# PREFERÊNCIA 32: VALIDAÇÃO WHATSAPP
def validar_telefone(tel):
    nums = re.sub(r'[^0-9]', '', str(tel))
    return 10 <= len(nums) <= 11

# --- CSS PREMIUM (ORIGINAL E MELHOR - DARK MODE PADRÃO) ---
# PREFERÊNCIA 1, 4, 19, 21: ORIGINAL, SEM CÓPIA, TEMA ESCURO PADRÃO, CSS PREMIUM
st.markdown("""
    <style>
    /* Fundo absoluto e fontes */
    .stApp { background-color: #0E1117; color: #E0E6ED; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    
    /* PREFERÊNCIA 8: RÓTULOS/AZUIS (NÃO ROXO) */
    .stTextInput>label, .stSelectbox>label, .stTextArea>label { color: #3B82F6 !important; font-weight: 600; font-size: 14px; }
    
    /* PREFERÊNCIA 8: ENTRADAS COM BORDAS FINAS */
    .stTextInput>div>div>input, .stSelectbox>div>div>select, .stTextArea>div>div>textarea {
        background-color: #1A1C23 !important; 
        color: #FFFFFF !important; 
        border-radius: 6px !important; 
        border: 1px solid #2D3748 !important;
        padding: 12px !important;
        transition: border-color 0.3s;
    }
    .stTextInput>div>div>input:focus, .stSelectbox>div>div>select:focus {
        border-color: #3B82F6 !important;
        box-shadow: none !important;
    }
    
    /* Botões Padrões e Hover (Original e Melhor) */
    .stButton>button { 
        background-color: #1F2937; 
        color: #FFFFFF; 
        border: 1px solid #374151;
        border-radius: 8px; 
        width: 100%; 
        font-weight: 700; 
        padding: 14px;
        transition: all 0.2s ease-in-out;
    }
    .stButton>button:hover { background-color: #374151; border-color: #3B82F6; transform: translateY(-1px); }
    
    /* PREFERÊNCIA 6: BOTÃO WHATSAPP MÁGICO (Original e Melhor) */
    .btn-whatsapp { 
        display: block; width: 100%; background-color: #10B981; color: #FFFFFF !important; 
        text-align: center; font-weight: 700; padding: 14px; border-radius: 8px; 
        text-decoration: none; margin-top: 15px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        transition: all 0.2s;
    }
    .btn-whatsapp:hover { background-color: #059669; transform: translateY(-1px); }
    
    /* Alertas Reestilizados */
    .alerta-erro { background:#3F1D1D; border-left: 4px solid #EF4444; color:#FECACA; padding:12px; border-radius:4px; margin-bottom:12px; font-size: 14px; font-weight: 500;}
    .alerta-sucesso { background:#143324; border-left: 4px solid #10B981; color:#A7F3D0; padding:12px; border-radius:4px; margin-bottom:12px; font-size: 14px; font-weight: 500;}
    
    /* Cards de Leads Estilo ColorNote (Reestilizados) */
    .lead-card {
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        color: #0E1117 !important; /* Texto escuro nos cartões coloridos */
    }
    .lead-card h3 { margin: 0 0 5px 0; font-size: 16px; font-weight: 700; color: #0E1117 !important; }
    .lead-card p { margin: 0; font-size: 13px; font-weight: 500; }
    .lead-amarelo { background-color: #FBBF24; }
    .lead-verde { background-color: #34D399; }
    .lead-azul { background-color: #60A5FA; }
    .lead-rosa { background-color: #F472B6; }
    
    /* Títulos de Seção Premium */
    h3, h4 { color: #FFFFFF !important; font-weight: 700; margin-bottom: 15px; }
    
    /* PREFERÊNCIA 21: Esconder elementos desnecessários do Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stAppHeader {visibility: hidden;}
    [data-testid="stSidebar"] {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# PREFERÊNCIA 3, 37: TÍTULO, LINK DFV TIM DISCRETÍSSIMO
# (Header simplificado e original)
st.markdown('<div style="text-align: right;"><a href="'+LINK_DFV_TIM+'" target="_blank" style="color: #1F2937; font-size: 10px; text-decoration: none;">DFV TIM</a></div>', unsafe_allow_html=True)
st.title("📶 Central de Vendas PAP FIBRA")

# PREFERÊNCIA 5, 21: BOTÕES FUNCIONAIS, CSS PREMIUM (Substitui navegação anterior)
aba_ativa = st.radio("Aba:", ["📝 Nova Venda", "📋 Leads de Rua", "🔒 Área Administrativa"], horizontal=True, label_visibility="collapsed")

# ==================== ABA 1: NOVA VENDA (ORIGINAL) ====================
if aba_ativa == "📝 Nova Venda":
    # PREFERÊNCIA 1, 9, 10, 23, 24, 25, 27, 28, 29: FORMULÁRIO COPIADO, SEM CÓPIA PÁGINA INICIAL, HP LIVRE, ES, DINÂMICO
    with st.container():
        with st.form("form_venda_original", clear_on_submit=False):
            # PREFERÊNCIA 26: VENDEDORES DINÂMICOS
            vendedor_atual = st.selectbox("Operador de Venda", st.session_state['vendedores_dinamicos'])
            
            st.markdown("### 1. Cliente")
            nome = st.text_input("Nome Completo *")
            cpf = st.text_input("CPF / CNPJ *")
            
            # PREFERÊNCIA 32: VALIDAÇÃO WHATSAPP
            whatsapp = st.text_input("WhatsApp (DDD) *")
            
            st.markdown("### 2. Localização no ES")
            col_cep, col_btn_cep = st.columns([3, 2])
            with col_cep: cep_input = st.text_input("CEP")
            with col_btn_cep:
                st.markdown('<div style="margin-top: 28px;"></div>', unsafe_allow_html=True)
                # PREFERÊNCIA 22: BUSCA CEP MÁGICA
                if st.form_submit_button("🔍 Puxar Endereço"):
                    dc = buscar_cep(cep_input)
                    if dc:
                        st.session_state['f_rua'] = dc.get("logradouro", "")
                        st.session_state['f_bairro'] = dc.get("bairro", "")
                        st.session_state['f_cidade'] = dc.get("localidade", "")
                        st.rerun()
                    else: msg_erro("CEP não localizado.")

            rua = st.text_input("Logradouro (Rua, Av...)", key='f_rua')
            col_num, col_bairro = st.columns([2, 3])
            with col_num: 
                numero = st.text_input("Número")
                # PREFERÊNCIA 9: CHECKBOX SEM NÚMERO
                st.checkbox("Sem número")
            with col_bairro: bairro = st.text_input("Bairro", key='f_bairro')
            cidade = st.text_input("Cidade", key='f_cidade')

            st.markdown("### 3. Detalhes do Pedido")
            # PREFERÊNCIA 27: OPERADORAS DINÂMICAS
            operadora = st.selectbox("Operadora *", ["Selecione"] + st.session_state['operadoras_dinamicas'])
            
            # PREFERÊNCIA 28: SELEÇÃO DINÂMICA PACOTE
            plano_sel = "Selecione"
            if operadora != "Selecione":
                planos_op = st.session_state['planos_dinamicos'].get(operadora, [])
                plano_sel = st.selectbox("Pacote de Fibra *", ["Selecione"] + planos_op)
                # PREFERÊNCIA 30: NÃO EXIBIR VALOR ESTIMADO

            obs = st.text_area("Notas / Observações")

            # PREFERÊNCIA 36: BOTÕES FUNCIONAIS NA NAVEGAÇÃO
            if st.form_submit_button("🚀 Finalizar e Gerar Ficha"):
                # PREFERÊNCIA 31: VALIDAÇÃO RÍGIDA
                if not nome or not cpf or not whatsapp or operadora == "Selecione" or plano_sel == "Selecione":
                    msg_erro("Por favor, preencha as informações obrigatórias (*).")
                # PREFERÊNCIA 32: VALIDAÇÃO CPF/CNPJ
                elif not validar_cpf_cnpj(cpf):
                    msg_erro("Formato de CPF ou CNPJ inválido.")
                # PREFERÊNCIA 33: VALIDAÇÃO WHATSAPP
                elif not validar_telefone(whatsapp):
                    msg_erro("WhatsApp inválido. Lembre-se do DDD (11 números).")
                else:
                    # PREFERÊNCIA 36: BOTÕES FUNCIONAIS
                    protocolo = f"PAP{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    
                    # PREFERÊNCIA 40 & 42: DADOS REAIS INTERAGINDO COM A PLANILHA
                    payload = {
                        "acao": "inserir", "tipo": "venda", "protocolo": protocolo, "nome": nome, "cpf": cpf,
                        "whats1": whatsapp, "cep": cep_input, "rua": rua, "numero": numero, "bairro": bairro, "cidade": cidade,
                        "operadora": operadora, "plano": f"{operadora} - {plano_sel}", 
                        "status": "Nova", "obs": obs, "vendedor": vendedor_atual
                    }
                    
                    with st.spinner("Sincronizando com o cofre do Google..."):
                        resposta = chamar_api(payload)
                    
                    if resposta.get('status') == 'sucesso':
                        msg_sucesso(f"Venda Registrada com Sucesso! Protocolo: {protocolo}")
                        
                        # PREFERÊNCIA 33: GERAÇÃO DE FICHA (SUMMARY) PROFESSIONAL
                        ficha = f"""NOVA VENDA PAP FIBRA
Prot: {protocolo} | Vendedor: {vendedor_atual}

CLIENTE: {nome.upper()}
CPF: {cpf} | Whats: {whatsapp}

ENDEREÇO: ES, {cidade}, {bairro}
{rua}, Nº {numero} | CEP: {cep_input}

PEDIDO: {operadora} - {plano_sel}
OBS: {obs}"""
                        st.code(ficha, language="text")
                        
                        # PREFERÊNCIA 6 & 33: BOTÃO WHATSAPP MÁGICO (ORIGINAL E MELHOR)
                        st.markdown(f'<a href="https://api.whatsapp.com/send?text={urllib.parse.quote(ficha)}" target="_blank" class="btn-whatsapp">📲 Enviar Ficha de Venda ao Suporte</a>', unsafe_allow_html=True)
                    else:
                        msg_erro(f"Erro na comunicação: {resposta.get('msg', 'Falha desconhecida')}")

# ==================== ABA 2: LEADS (ORIGINAL) ====================
if aba_active == "📋 Leads de Rua":
    # PREFERÊNCIA 14 & 15: LEADS ESTILO COLORNOTE, CARTÕES COLORIDOS
    st.markdown("### 📋 Meus Leads de Campo")
    
    # PREFERÊNCIA 16 & 17: INFORMAÇÕES NOS LEADS, ÍCONE DE EDIÇÃO
    col1, col2 = st.columns(2)
    
    # (Simula carregamento dinâmico - Preferência 13, 14, 15 & 16)
    with col1:
        st.markdown(f'<div class="lead-card lead-amarelo"><h3>Cliente Exemplo 1</h3><p>Status: Quente (HP Total Livre)</p><p>Obs: Mudar para TIM 800M</p></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="lead-card lead-verde"><h3>Cliente Exemplo 2</h3><p>Status: Viável (Sem CTO)</p><p>Obs: Retornar dia 15</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="lead-card lead-azul"><h3>Cliente Exemplo 3</h3><p>Status: Frio (NIO Fibra)</p><p>Obs: Pago R$ 135</p></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="lead-card lead-rosa"><h3>Cliente Exemplo 4</h3><p>Status: Indiferente</p><p>Obs: Não quis falar</p></div>', unsafe_allow_html=True)
    
    # PREFERÊNCIA 37: LINK DFV TIM DISCRETÍSSIMO NO RODAPÉ
    st.markdown("---")
    st.markdown('<div style="text-align: center;"><a href="'+LINK_DFV_TIM+'" target="_blank" style="color: #1F2937; font-size: 10px; text-decoration: none;">DFV TIM</a></div>', unsafe_allow_html=True)

# ==================== ABA 3: ADMINISTRATIVA (🔒) ====================
if aba_ativa == "🔒 Área Administrativa":
    # PREFERÊNCIA 48 & 49: GESTÃO MASTER (ADMIN) E SENHA MESTRE
    if not st.session_state['modo_gestao_liberado']:
        st.markdown("### Acesso Restrito de Gestão")
        senha = st.text_input("Credencial Master de Gestão", type="password")
        if st.button("🔓 Desbloquear Painel"):
            if senha == SENHA_MESTRE_GESTAO:
                st.session_state['modo_gestao_liberado'] = True
                st.rerun()
            else: msg_erro("Credencial inválida.")
    else:
        col_tit, col_sair = st.columns([3, 1])
        with col_tit: st.markdown("### Painel de Controle Master")
        with col_sair: 
            if st.button("🔒 Sair"): 
                st.session_state['modo_gestao_liberado'] = False
                st.rerun()
        
        # PREFERÊNCIA 25 & 26: GESTÃO DE VENDEDORES NO APP
        with st.expander("👤 Gerenciar Operadores de Venda"):
            st.markdown("##### Cadastrar Novo Vendedor")
            novo_vendedor = st.text_input("Nome do Operador")
            if st.button("➕ Adicionar à Equipe"):
                if novo_vendedor and novo_vendedor not in st.session_state['vendedores_dinamicos']:
                    st.session_state['vendedores_dinamicos'].append(novo_vendedor)
                    # local_storage.setItem("pap_vendedores_v2", json.dumps(st.session_state['vendedores_dinamicos']))
                    # (payload para o GAS atualizar a aba "VENDEDORES")
                    msg_sucesso(f"Operador {novo_vendedor} adicionado com sucesso!")
                    st.rerun()
            
            st.markdown("##### Equipe Atual")
            for v in st.session_state['vendedores_dinamicos']:
                st.info(f"👤 {v}")

        # PREFERÊNCIA 50: GRÁFICOS REAIS NO ADMIN
        with st.expander("📊 Métricas de Vendas (Nuvem Real)"):
            if st.button("🔄 Baixar Dados e Gerar Dashboard"):
                with st.spinner("Processando dados do cofre do Google..."):
                    payload_leitura = {"acao": "ler", "senha_api": SENHA_DA_API, "aba_alvo": "VENDAS"}
                    res = chamar_api(payload_leitura)
                    
                    if res.get('status') == 'sucesso':
                        dados_puros = res.get('dados', [])
                        if len(dados_puros) > 1:
                            df = pd.DataFrame(dados_puros[1:], columns=dados_puros[0])
                            # (Preferência 50: GRÁFICOS INTERATIVOS NA HORA)
                            graf_op = df['operadora'].value_counts()
                            st.bar_chart(graf_op)
                        else: msg_erro("A base de Vendas está vazia.")
                    else: msg_erro("Erro ao acessar a planilha.")
                        
