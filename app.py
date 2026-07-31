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

st.set_page_config(page_title="PAP Fibra", page_icon="📶", layout="centered")
local_storage = LocalStorage()

if 'vendedores_cadastrados' not in st.session_state: st.session_state['vendedores_cadastrados'] = ["Moabe"]
if 'modo_gestao_liberado' not in st.session_state: st.session_state['modo_gestao_liberado'] = False

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

# --- CSS PREMIUM (DARK MODE PURO) ---
st.markdown("""
    <style>
    /* Fundo absoluto e fontes */
    .stApp { background-color: #0E1117; color: #E0E6ED; font-family: 'Inter', sans-serif; }
    
    /* Inputs estilizados */
    .stTextInput>div>div>input, .stSelectbox>div>div>select, .stTextArea>div>div>textarea {
        background-color: #1A1C23 !important; 
        color: #FFFFFF !important; 
        border-radius: 8px !important; 
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
        background-color: #2563EB; 
        color: #FFFFFF; 
        border: none; 
        border-radius: 8px; 
        width: 100%; 
        font-weight: 600; 
        padding: 12px;
        transition: all 0.2s ease-in-out;
    }
    .stButton>button:hover { background-color: #1D4ED8; transform: translateY(-1px); }
    
    /* Botão WhatsApp Específico */
    .btn-whatsapp { 
        display: block; width: 100%; background-color: #10B981; color: #FFFFFF !important; 
        text-align: center; font-weight: 600; padding: 14px; border-radius: 8px; 
        text-decoration: none; margin-top: 15px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        transition: background-color 0.2s;
    }
    .btn-whatsapp:hover { background-color: #059669; }
    
    /* Cards e Alertas */
    .alerta-erro { background:#3F1D1D; border-left: 4px solid #EF4444; color:#FECACA; padding:12px; border-radius:4px; margin-bottom:12px; font-size: 14px;}
    .alerta-sucesso { background:#143324; border-left: 4px solid #10B981; color:#A7F3D0; padding:12px; border-radius:4px; margin-bottom:12px; font-size: 14px;}
    
    /* Cards de Métricas */
    div[data-testid="metric-container"] {
        background-color: #1A1C23;
        border: 1px solid #2D3748;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    div[data-testid="metric-container"] > label { color: #9CA3AF !important; font-weight: 500; }
    div[data-testid="metric-container"] > div { color: #FFFFFF !important; }
    
    /* Esconder elementos desnecessários do Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- CABEÇALHO COM LINK DISCRETO ---
col_logo, col_link = st.columns([4, 1])
with col_link:
    st.markdown(f'<div style="text-align: right; padding-top: 10px;"><a href="{LINK_DFV_TIM}" target="_blank" style="color: #374151; font-size: 10px; text-decoration: none;">DFV TIM</a></div>', unsafe_allow_html=True)

st.title("📶 Central de Vendas")

aba_vendas, aba_gestao = st.tabs(["📝 Formulário de Venda", "📊 Gestão & Gráficos"])

# ==================== ABA 1: VENDAS ====================
with aba_vendas:
    with st.container():
        with st.form("form_venda", clear_on_submit=False):
            vendedor_atual = st.selectbox("Operador", st.session_state['vendedores_cadastrados'])
            
            st.markdown("### Dados do Cliente")
            nome = st.text_input("Nome Completo", placeholder="Ex: João da Silva")
            cpf = st.text_input("CPF / CNPJ")
            col1, col2 = st.columns(2)
            with col1: whatsapp = st.text_input("WhatsApp (DDD)")
            with col2: cep_input = st.text_input("CEP (Opcional)")
            
            if st.form_submit_button("🔍 Buscar Endereço pelo CEP"):
                dc = buscar_cep(cep_input)
                if dc:
                    st.session_state['f_rua'] = dc.get("logradouro", "")
                    st.session_state['f_bairro'] = dc.get("bairro", "")
                    st.rerun()
                else: msg_erro("CEP não encontrado.")

            rua = st.text_input("Rua", key='f_rua')
            col3, col4 = st.columns([1, 2])
            with col3: numero = st.text_input("Número")
            with col4: bairro = st.text_input("Bairro", key='f_bairro')

            st.markdown("### Configuração do Plano")
            operadora = st.selectbox("Operadora", ["Selecione"] + list(st.session_state['planos_dinamicos'].keys()))
            
            plano_sel, valor_plano = "Selecione", 0.00
            if operadora != "Selecione":
                plano_sel = st.selectbox("Pacote", ["Selecione"] + list(st.session_state['planos_dinamicos'][operadora].keys()))
                if plano_sel != "Selecione":
                    valor_plano = st.session_state['planos_dinamicos'][operadora][plano_sel]
                    st.markdown(f"**Mensalidade Estimada:** R$ {valor_plano:.2f}")

            obs = st.text_area("Notas / Observações")

            if st.form_submit_button("🚀 Finalizar Venda"):
                if not nome or not cpf or not whatsapp or operadora == "Selecione" or plano_sel == "Selecione":
                    msg_erro("Preencha as informações obrigatórias (Nome, CPF, WhatsApp, Operadora e Plano).")
                else:
                    protocolo = f"PAP{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    plano_final = f"{operadora} - {plano_sel}"
                    
                    payload = {
                        "acao": "inserir", "tipo": "venda", "protocolo": protocolo, "nome": nome, "cpf": cpf,
                        "whats1": whatsapp, "cep": cep_input, "rua": rua, "numero": numero, "bairro": bairro,
                        "operadora": operadora, "plano": plano_final, "valor_plano": valor_plano, 
                        "status": "Nova", "obs": obs, "vendedor": vendedor_atual
                    }
                    
                    with st.spinner("Sincronizando com a base de dados..."):
                        resposta = chamar_api(payload)
                    
                    if resposta.get('status') == 'sucesso':
                        msg_sucesso(f"Sucesso! Protocolo gerado: {protocolo}")
                        ficha = f"NOVA VENDA\n\nVendedor: {vendedor_atual}\n\nCLIENTE: {nome.upper()}\nCPF: {cpf}\nWhatsApp: {whatsapp}\n\nENDEREÇO: {rua}, {numero} - {bairro}\nCEP: {cep_input}\n\nPEDIDO: {plano_final}\nVALOR: R$ {valor_plano:.2f}\nOBS: {obs}"
                        st.markdown(f'<a href="https://api.whatsapp.com/send?text={urllib.parse.quote(ficha)}" target="_blank" class="btn-whatsapp">📲 Enviar Ficha no WhatsApp</a>', unsafe_allow_html=True)
                    else:
                        msg_erro("Falha na comunicação com o servidor.")

# ==================== ABA 2: GESTÃO E GRÁFICOS (DASHBOARD REAL) ====================
with aba_gestao:
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
        with col_tit: st.markdown("### Dashboard de Operações")
        with col_sair: 
            if st.button("Sair"): 
                st.session_state['modo_gestao_liberado'] = False
                st.rerun()
        
        st.markdown("---")
        
        if st.button("🔄 Atualizar Dados da Nuvem"):
            with st.spinner("Processando dados do Data Lake..."):
                res = chamar_api({"acao": "ler", "senha_api": SENHA_DA_API, "aba_alvo": "VENDAS"})
                if res.get('status') == 'sucesso':
                    dados_puros = res.get('dados', [])
                    if len(dados_puros) > 1:
                        df = pd.DataFrame(dados_puros[1:], columns=dados_puros[0])
                        st.session_state['df_vendas'] = df
                    else: msg_erro("Nenhuma venda registrada na base.")
                else: msg_erro("Erro de conexão.")

        if 'df_vendas' in st.session_state:
            df = st.session_state['df_vendas']
            
            # --- CARDS DE MÉTRICAS ---
            total = len(df)
            instalados = len(df[df['Status'].astype(str).str.contains('Instalado', case=False, na=False)])
            receita = df['valor_plano'].apply(pd.to_numeric, errors='coerce').sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric(label="Volume Total", value=f"{total} Vendas")
            c2.metric(label="Instalados (Sucesso)", value=f"{instalados}")
            c3.metric(label="Receita Bruta", value=f"R$ {receita:,.2f}")
            
            st.markdown("---")
            
            # --- GRÁFICOS REAIS RENDERIZADOS NA TELA ---
            st.markdown("#### Performance Visual")
            col_graf1, col_graf2 = st.columns(2)
            
            with col_graf1:
                st.markdown("**Vendas por Operadora**")
                # Conta quantas vendas tem por operadora e plota um gráfico de barras nativo
                graf_op = df['Operadora'].value_counts()
                st.bar_chart(graf_op, color="#3B82F6")
                
            with col_graf2:
                st.markdown("**Status do Funil**")
                # Conta quantas vendas tem por status e plota
                graf_status = df['Status'].value_counts()
                st.bar_chart(graf_status, color="#10B981")
                
            st.markdown("---")
            
            # --- LUPA E EDIÇÃO ---
            st.markdown("#### Buscar e Editar Registros")
            termo = st.text_input("Digite o nome, bairro ou CPF do cliente:")
            if termo:
                mascara = df.apply(lambda row: row.astype(str).str.contains(termo, case=False).any(), axis=1)
                for index, row in df[mascara].iterrows():
                    with st.expander(f"📌 {row.get('Nome')} | {row.get('Operadora')} ({row.get('Status')})"):
                        st.write(f"**Protocolo:** {row.get('Protocolo')} | **Endereço:** {row.get('Rua')}")
                        
                        novo_status = st.selectbox("Mudar Status", ["Nova", "Em Andamento", "Instalado", "Cancelado"], index=0, key=f"st_{index}")
                        if st.button("💾 Atualizar Linha", key=f"bs_{index}"):
                            ln = list(row.values)
                            ln[19] = novo_status # Coluna T na planilha
                            res_ed = chamar_api({"acao": "editar", "senha_api": SENHA_DA_API, "aba_alvo": "VENDAS", "id_busca": row.get('Protocolo'), "coluna_busca": 1, "novos_dados": ln})
                            if res_ed.get('status') == 'sucesso': msg_sucesso("Atualizado na base!")
                            else: msg_erro("Erro ao atualizar.")
            
