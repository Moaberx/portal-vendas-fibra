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
# CORREÇÃO DO NameError: O SEU LINK REAL ESTÁ AQUI
URL_BACKEND_GOOGLE = "https://script.google.com/macros/s/AKfycbxpacnXvvIMh7tfqcH6iUmmRLF_9l4XhBBGdr0Iyl4RfqVnhtg4bv3daMN80yXgvyFS/exec"
SENHA_DA_API = "PAP_SECRETO_2026" # PREFERÊNCIA 47: SEGURANÇA POR TOKEN
SENHA_MESTRE_GESTAO = "102030"    # PREFERÊNCIA 49: SENHA MESTRE

# CORREÇÃO DO NameError: Definição da variável do link DVF TIM
LINK_DFV_TIM = "https://app.powerbi.com/view?r=eyJrIjoiODgyZDdiMTItOTM1MS00ZGFkLTkyZTktOTg5ZmJjNjc0OTViIiwidCI6ImI1MmJhNGIzLWM0MTEtNGQxNi04Yzc2LTAwNDg5YzBhMjA1YSJ9"
# ====================================================

# PREFERÊNCIA 3, 19: TÍTULO, TEMA PADRÃO E OPÇÃO DE ALTERNAR
st.set_page_config(page_title="PAP FIBRA", page_icon="📶", layout="centered", initial_sidebar_state="collapsed")

local_storage = LocalStorage()

if 'vendedores_dinamicos' not in st.session_state: st.session_state['vendedores_dinamicos'] = []
if 'planos_dinamicos' not in st.session_state: st.session_state['planos_dinamicos'] = {}
if 'operadoras_dinamicas' not in st.session_state: st.session_state['operadoras_dinamicas'] = []
if 'modo_gestao_liberado' not in st.session_state: st.session_state['modo_gestao_liberado'] = False

# --- FUNÇÕES DE COMUNICAÇÃO ---
# PREFERÊNCIA 46: "MODO DEUS" CRUD DEFINITIVO NO GAS
def chamar_api(dados_payload):
    try:
        resp = requests.post(URL_BACKEND_GOOGLE, data=json.dumps(dados_payload), headers={"Content-Type": "application/json"}, timeout=15)
        if resp.status_code == 200: return resp.json()
    except Exception as e:
        return {"status": "erro", "msg": str(e)}
    return {"status": "erro", "msg": "Servidor fora do ar."}

# --- CARREGAMENTO INICIAL DE DADOS REAIS ---
if not st.session_state.get('configs_carregadas'):
    with st.spinner("Sincronizando com o cofre do Google..."):
        # Payload para carregar os dados dinâmicos da planilha de uma vez
        # (Isso requer que seu Apps Script tenha uma 'acao': 'carregar_inicial')
        payload_inicial = {"acao": "carregar_inicial", "senha_api": SENHA_DA_API}
        resposta_inicial = chamar_api(payload_inicial)
        
        if resposta_inicial and resposta_inicial.get('status') == 'sucesso':
            # PREFERÊNCIA 25: VENDEDORES DINÂMICOS DA PLANILHA
            st.session_state['vendedores_dinamicos'] = resposta_inicial.get('vendedores', ["Moabe"])
            
            # PREFERÊNCIA 27: OPERADORAS E PACOTES DINÂMICOS
            st.session_state['operadoras_dinamicas'] = resposta_inicial.get('operadoras', ["TIM Ultrafibra", "NIO Fibra", "Claro", "Giga+ Fibra"])
            
            # PREFERÊNCIA 28: DETALHES DOS PLANOS DINÂMICOS
            st.session_state['planos_dinamicos'] = resposta_inicial.get('planos', {})
            st.session_state['configs_carregadas'] = True
        else:
            # Fallback seguro para o app não quebrar enquanto o GAS não é configurado
            st.session_state['vendedores_dinamicos'] = ["Moabe"]
            st.session_state['operadoras_dinamicas'] = ["TIM Ultrafibra", "NIO Fibra", "Claro", "Giga+ Fibra"]
            st.warning("⚠️ Não foi possível carregar os dados da planilha oficial. Usando dados locais de fallback.")

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

# --- CSS PREMIUM (DARK MODE PADRÃO - AZUL/NÃO ROXO) ---
# PREFERÊNCIA 4, 19, 21: TEMA ESCURO PADRÃO, CSS PREMIUM, HIDE STREAMLIT
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
    
    /* Botões Padrões e Hover */
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
    
    /* Botão WhatsApp Mágico */
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
    
    /* Cards de Leads Estilo ColorNote */
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
    
    /* Esconder elementos desnecessários do Streamlit */
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

# PREFERÊNCIA 21: CSS PREMIUM (Substitui rádio ou botões de navegação, foca no formulário)
st.markdown("---")

# PREFERÊNCIA 1, 9, 23, 24, 25, 27, 28, 29: FORMULÁRIO COPIADO, SEM PÁGINA INICIAL, HP LIVRE, ES, DINÂMICO
with st.container():
    with st.form("form_venda_original", clear_on_submit=False):
        # PREFERÊNCIA 26: VENDEDORES DINÂMICOS
        vendedor_atual = st.selectbox("Operador de Venda", st.session_state['vendedores_dinamicos'])
        
        st.markdown("### 1. Cliente")
        nome = st.text_input("Nome Completo *", placeholder="Nome sem abreviações")
        cpf = st.text_input("CPF / CNPJ *")
        
        # PREFERÊNCIA 32: VALIDAÇÃO WHATSAPP
        whatsapp = st.text_input("WhatsApp (DDD) *", placeholder="(27) 99999-9999")
        
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

        st.markdown("---")
        # PREFERÊNCIA 1, 36: SEM BOTÕES QUE NÃO FUNCIONAM
        btn_finalizar = st.form_submit_button("🚀 Finalizar e Gerar Ficha")

        if btn_finalizar:
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
                protocolo = f"PAP{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                # Payload para o Apps Script registrar a venda (Aba VENDAS)
                # PREFERÊNCIA 40 & 42: DADOS REAIS INTERAGINDO COM A PLANILHA
                payload = {
                    "acao": "inserir", "tipo": "venda", "protocolo": protocolo, "nome": nome, "cpf": cpf,
                    "whats1": whatsapp, "cep": cep_input, "rua": rua, "numero": numero, "bairro": bairro, "cidade": cidade,
                    "operadora": operadora, "plano": plano_sel, 
                    "status": "Nova", "obs": obs, "vendedor": vendedor_atual
                }
                
                with st.spinner("Sincronizando com o cofre do Google..."):
                    resposta = chamar_api(payload)
                
                if resposta and resposta.get('status') == 'sucesso':
                    msg_sucesso(f"Pedido Registrado com Sucesso! Protocolo: {protocolo}")
                    
                    # PREFERÊNCIA 33: GERAÇÃO DE FICHA (SUMMARY) PROFESSIONAL
                    ficha = f"""NOVO PEDIDO PAP FIBRA
Prot: {protocolo} | Operador: {vendedor_atual}

CLIENTE: {nome.upper()}
CPF: {cpf} | Whats: {whatsapp}

ENDEREÇO: ES, {cidade}, {bairro}
{rua}, Nº {numero} | CEP: {cep_input}

PEDIDO: {operadora} - {plano_sel}
OBS: {obs}"""
                    st.code(ficha, language="text")
                    
                    # PREFERÊNCIA 6 & 33: BOTÃO WHATSAPP MÁGICO
                    st.markdown(f'<a href="https://api.whatsapp.com/send?text={urllib.parse.quote(ficha)}" target="_blank" class="btn-whatsapp">📲 Enviar Ficha de Venda ao Suporte</a>', unsafe_allow_html=True)
                else:
                    msg_erro(f"Erro na comunicação com o servidor: {resposta.get('msg', 'Falha desconhecida')}")
