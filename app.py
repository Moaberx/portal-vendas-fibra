import streamlit as st
import requests
import json
import re
import urllib.parse
from datetime import datetime
import pandas as pd
from streamlit_local_storage import LocalStorage

# ================= CONEXÃO DE DADOS =================
URL_BACKEND_GOOGLE = "COLOQUE_AQUI_SUA_URL_DO_WEB_APP" # Substitua pela sua URL final do Google
SENHA_DA_API = "PAP_SECRETO_2026" # Senha para o App poder ler/editar a planilha
SENHA_MESTRE_GESTAO = "102030"    # Senha para você entrar no modo administrador
# ====================================================

st.set_page_config(page_title="PAP Fibra", page_icon="📶", layout="centered")

# --- MEMÓRIA LOCAL E CONFIGURAÇÕES GLOBAIS ---
local_storage = LocalStorage()

if 'vendedores_cadastrados' not in st.session_state: 
    st.session_state['vendedores_cadastrados'] = ["Moabe"]
if 'modo_gestao_liberado' not in st.session_state: 
    st.session_state['modo_gestao_liberado'] = False

# Catálogo de Planos Base
if 'planos_dinamicos' not in st.session_state:
    st.session_state['planos_dinamicos'] = {
        "NIO Fibra": {"500 Mega": 100.00, "600 Mega": 109.00, "800 Mega": 135.00, "1 Giga": 160.00},
        "TIM Ultrafibra": {"600 Mega": 119.99, "800 Mega": 129.99, "1 Giga": 129.99},
        "Vivo": {"Padrão": 0.00}, "Claro": {"Padrão": 0.00}
    }

def carregar_configs_locais():
    try:
        vends = local_storage.getItem("pap_vendedores_v1")
        if vends: st.session_state['vendedores_cadastrados'] = json.loads(vends) if isinstance(vends, str) else vends
    except: pass

def salvar_vendedores():
    local_storage.setItem("pap_vendedores_v1", json.dumps(st.session_state['vendedores_cadastrados']))

# --- COMUNICAÇÃO COM A API DO GOOGLE SHEETS ---
def chamar_api(dados_payload):
    try:
        resp = requests.post(URL_BACKEND_GOOGLE, data=json.dumps(dados_payload), headers={"Content-Type": "application/json"}, timeout=15)
        if resp.status_code == 200: return resp.json()
    except Exception as e:
        return {"status": "erro", "msg": str(e)}
    return {"status": "erro", "msg": "Servidor fora do ar."}

# --- HELPERS ---
def msg_erro(t): st.markdown(f'<div style="background:#2A0E0E; border:1px solid #B91C1C; color:#FECACA; padding:10px; border-radius:5px; margin-bottom:10px;">❌ {t}</div>', unsafe_allow_html=True)
def msg_sucesso(t): st.markdown(f'<div style="background:#0E2A17; border:1px solid #15803D; color:#BBF7D0; padding:10px; border-radius:5px; margin-bottom:10px;">✅ {t}</div>', unsafe_allow_html=True)

def validar_cpf_cnpj(doc):
    doc = re.sub(r'[^0-9]', '', str(doc))
    return len(doc) == 11 or len(doc) == 14

def validar_telefone(tel):
    nums = re.sub(r'[^0-9]', '', str(tel))
    return 10 <= len(nums) <= 11

# --- CSS E LAYOUT ---
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    .stTextInput>div>div>input, .stSelectbox>div>div>select, .stTextArea>div>div>textarea {
        background-color: #121212 !important; color: #FFFFFF !important; border-radius: 6px !important; border: 1px solid #333333 !important;
    }
    .stButton>button { background-color: #1F2937; color: #FFFFFF; border: 1px solid #374151; border-radius: 6px; width: 100%; font-weight: bold; }
    .stButton>button:hover { border-color: #3B82F6; }
    .btn-whatsapp { display: block; width: 100%; background-color: #25D366; color: #000000 !important; text-align: center; font-weight: bold; padding: 12px; border-radius: 6px; text-decoration: none; margin-top: 10px; }
    </style>
""", unsafe_allow_html=True)

if not st.session_state.get('configs_carregadas'):
    carregar_configs_locais()
    st.session_state['configs_carregadas'] = True

st.title("📶 PAP Fibra")

aba_vendas, aba_leads, aba_gestao = st.tabs(["📝 Nova Venda", "📞 Leads", "🔒 Gestão Master"])

# ==================== ABA 1: VENDAS (MODO RUA) ====================
with aba_vendas:
    with st.form("form_venda", clear_on_submit=False):
        vendedor_atual = st.selectbox("Vendedor (Você)", st.session_state['vendedores_cadastrados'])
        
        st.markdown("#### Cliente")
        nome = st.text_input("Nome Completo 🔴")
        cpf = st.text_input("CPF / CNPJ 🔴")
        email = st.text_input("Email")
        mae = st.text_input("Nome da Mãe")
        col1, col2 = st.columns(2)
        with col1: whatsapp = st.text_input("WhatsApp (DDD) 🔴")
        with col2: contato2 = st.text_input("Contato 2")

        st.markdown("#### Endereço")
        cep = st.text_input("CEP")
        rua = st.text_input("Rua")
        col3, col4 = st.columns([1, 2])
        with col3: numero = st.text_input("Número")
        with col4: bairro = st.text_input("Bairro")
        ref = st.text_input("Referência")

        st.markdown("#### Pedido")
        operadora = st.selectbox("Operadora 🔴", ["Selecione"] + list(st.session_state['planos_dinamicos'].keys()))
        
        plano_sel, valor_plano = "Selecione", 0.00
        if operadora != "Selecione":
            plano_sel = st.selectbox("Plano", ["Selecione"] + list(st.session_state['planos_dinamicos'][operadora].keys()))
            if plano_sel != "Selecione":
                valor_plano = st.session_state['planos_dinamicos'][operadora][plano_sel]
                st.info(f"Valor estimado: R$ {valor_plano:.2f}")

        obs = st.text_area("Observações")

        btn_salvar = st.form_submit_button("📤 Validar e Registrar Venda")

        if btn_salvar:
            if not nome or not cpf or not whatsapp or operadora == "Selecione" or plano_sel == "Selecione":
                msg_erro("Preencha todos os campos obrigatórios (marcados com 🔴).")
            elif not validar_cpf_cnpj(cpf) or not validar_telefone(whatsapp):
                msg_erro("CPF/CNPJ ou WhatsApp em formato inválido.")
            else:
                nums_w = re.sub(r'[^0-9]', '', whatsapp)
                protocolo = f"PAP{datetime.now().strftime('%Y%m%d%H%M%S')}"
                plano_final = f"{operadora} - {plano_sel}"
                
                payload = {
                    "acao": "inserir", "tipo": "venda", "protocolo": protocolo, "nome": nome, "cpf": cpf,
                    "mae": mae, "email": email, "whats1": whatsapp, "whats2": contato2, "cep": cep,
                    "rua": rua, "numero": numero, "bairro": bairro, "referencia": ref, "operadora": operadora,
                    "plano": plano_final, "valor_plano": valor_plano, "detalhes_plano": "", "status": "Nova", 
                    "obs": obs, "vendedor": vendedor_atual
                }
                
                with st.spinner("⏳ Enviando para a base de dados..."):
                    resposta = chamar_api(payload)
                
                if resposta.get('status') == 'sucesso':
                    msg_sucesso(f"Venda Registrada! (Prot: {protocolo})")
                    
                    ficha = f"NOVA VENDA\n\nVendedor: {vendedor_atual}\n\nCLIENTE: {nome.upper()}\nCPF: {cpf}\nWhatsApp: {whatsapp}\n\nENDEREÇO: {rua}, {numero} - {bairro}\nCEP: {cep}\n\nPEDIDO: {plano_final}\nVALOR: R$ {valor_plano:.2f}\nOBS: {obs}"
                    st.code(ficha, language="text")
                    st.markdown(f'<a href="https://api.whatsapp.com/send?text={urllib.parse.quote(ficha)}" target="_blank" class="btn-whatsapp">📲 Abrir WhatsApp</a>', unsafe_allow_html=True)
                else:
                    msg_erro(f"Erro ao salvar: {resposta.get('msg', 'Falha desconhecida')}")

# ==================== ABA 2: LEADS ====================
with aba_leads:
    with st.form("form_lead", clear_on_submit=True):
        vend_lead = st.selectbox("Vendedor", st.session_state['vendedores_cadastrados'])
        n_lead = st.text_input("Nome do Lead")
        w_lead = st.text_input("WhatsApp")
        status_l = st.selectbox("Status", ["Quente", "Frio", "Agendado", "Sem Viabilidade"])
        o_lead = st.text_area("Notas")
        
        if st.form_submit_button("Salvar Lead"):
            if n_lead and w_lead:
                with st.spinner("Salvando..."):
                    resp = chamar_api({"acao": "inserir", "tipo": "lead", "nome": n_lead, "whatsapp": w_lead, "status": status_l, "obs": o_lead, "vendedor": vend_lead})
                if resp.get('status') == 'sucesso': msg_sucesso("Lead Salvo com Sucesso!")
                else: msg_erro("Erro ao salvar o Lead.")
            else:
                msg_erro("Preencha Nome e WhatsApp.")

# ==================== ABA 3: GESTÃO MASTER ====================
with aba_gestao:
    if not st.session_state['modo_gestao_liberado']:
        senha = st.text_input("🔑 Digite a Senha Mestre de Gestão", type="password")
        if st.button("🔓 Acessar Central"):
            if senha == SENHA_MESTRE_GESTAO:
                st.session_state['modo_gestao_liberado'] = True
                st.rerun()
            else: msg_erro("Senha Incorreta!")
    else:
        st.success("🔓 MODO DEUS ATIVADO. Você tem controle total sobre a base de dados.")
        if st.button("🔒 Sair do Modo Gestão"):
            st.session_state['modo_gestao_liberado'] = False
            st.rerun()
        
        st.markdown("---")
        
        sub_aba1, sub_aba2, sub_aba3 = st.tabs(["👥 Vendedores", "🔍 Buscar & Editar Vendas", "📊 Visão Geral"])
        
        # --- SUB ABA: VENDEDORES ---
        with sub_aba1:
            st.markdown("##### Gerenciar Equipe")
            novo_vendedor = st.text_input("Nome do Novo Vendedor")
            if st.button("➕ Adicionar Vendedor"):
                if novo_vendedor and novo_vendedor not in st.session_state['vendedores_cadastrados']:
                    st.session_state['vendedores_cadastrados'].append(novo_vendedor)
                    salvar_vendedores()
                    msg_sucesso(f"{novo_vendedor} adicionado com sucesso! Já está disponível no app de todos.")
                    st.rerun()
            
            st.write("Vendedores Atuais:")
            for v in st.session_state['vendedores_cadastrados']:
                st.info(f"👤 {v}")

        # --- SUB ABA: BUSCAR, EDITAR E EXCLUIR ---
        with sub_aba2:
            st.markdown("##### Gestão de Vendas")
            st.info("Puxe os dados do Google Sheets para editar ou gerenciar status.")
            
            if st.button("📥 Baixar Vendas da Planilha Oficial"):
                with st.spinner("Conectando ao cofre do Google..."):
                    payload_leitura = {"acao": "ler", "senha_api": SENHA_DA_API, "aba_alvo": "VENDAS"}
                    res = chamar_api(payload_leitura)
                    
                    if res.get('status') == 'sucesso':
                        dados_puros = res.get('dados', [])
                        if len(dados_puros) > 1:
                            # Converte para tabela bonita (Tira a primeira linha que é o cabeçalho)
                            df = pd.DataFrame(dados_puros[1:], columns=dados_puros[0])
                            st.session_state['df_vendas'] = df
                            msg_sucesso(f"Base carregada! ({len(df)} vendas encontradas)")
                        else:
                            msg_erro("A planilha de Vendas está vazia.")
                    else:
                        msg_erro(res.get('msg', 'Erro ao acessar.'))
            
            if 'df_vendas' in st.session_state:
                df = st.session_state['df_vendas']
                
                termo = st.text_input("🔍 Buscar por Nome, CPF, Bairro ou Protocolo:")
                if termo:
                    # Filtra a tabela
                    mascara = df.apply(lambda row: row.astype(str).str.contains(termo, case=False).any(), axis=1)
                    df_filtrado = df[mascara]
                    
                    for index, row in df_filtrado.iterrows():
                        with st.expander(f"🟢 {row.get('Nome', 'Cliente')} - {row.get('Operadora', '')} ({row.get('Status', '')})"):
                            st.write(f"**Protocolo:** {row.get('Protocolo')}")
                            st.write(f"**Vendedor:** {row.get('Vendedor', 'Moabe')}")
                            st.write(f"**Endereço:** {row.get('Rua')}, {row.get('Bairro')}")
                            
                            # EDIÇÃO RÁPIDA DE STATUS
                            novo_status = st.selectbox("Atualizar Status", ["Nova", "Em Andamento", "Instalado", "Cancelado", "Atenção"], index=0, key=f"status_{index}")
                            
                            col_ed, col_del = st.columns(2)
                            with col_ed:
                                if st.button("💾 Salvar Novo Status", key=f"btn_salvar_{index}"):
                                    # Monta a linha inteira nova (atualizando o status que é a coluna T - índice 19)
                                    linha_nova = list(row.values)
                                    linha_nova[19] = novo_status 
                                    
                                    payload_edita = {
                                        "acao": "editar", "senha_api": SENHA_DA_API, "aba_alvo": "VENDAS",
                                        "id_busca": row.get('Protocolo'), "coluna_busca": 1, 
                                        "novos_dados": linha_nova
                                    }
                                    if chamar_api(payload_edita).get('status') == 'sucesso':
                                        msg_sucesso("Status alterado na planilha com sucesso!")
                                    else: msg_erro("Erro ao alterar.")
                            
                            with col_del:
                                if st.button("🗑️ Excluir Venda", type="secondary", key=f"btn_excluir_{index}"):
                                    payload_del = {
                                        "acao": "excluir", "senha_api": SENHA_DA_API, "aba_alvo": "VENDAS",
                                        "id_busca": row.get('Protocolo'), "coluna_busca": 1
                                    }
                                    if chamar_api(payload_del).get('status') == 'sucesso':
                                        msg_sucesso("Venda apagada da planilha permanentemente.")
                                    else: msg_erro("Erro ao excluir.")

        # --- SUB ABA: VISÃO GERAL (MÉTRICAS REAIS) ---
        with sub_aba3:
            st.markdown("##### Resumo Operacional")
            if 'df_vendas' in st.session_state:
                df = st.session_state['df_vendas']
                
                total_vendas = len(df)
                instalados = len(df[df['Status'].astype(str).str.contains('Instalado', case=False, na=False)])
                cancelados = len(df[df['Status'].astype(str).str.contains('Cancelado', case=False, na=False)])
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Cadastros", total_vendas)
                c2.metric("🟢 Instalados", instalados)
                c3.metric("🔴 Cancelados", cancelados)
                
                st.write("Vendas por Operadora:")
                st.bar_chart(df['Operadora'].value_counts())
            else:
                st.info("Baixe a base de dados na aba ao lado para visualizar os gráficos de gestão.")
