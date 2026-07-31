import streamlit as st
import requests
import json
import re

# ================= CONFIGURAÇÕES CRUCIAIS =================
# Esta é a URL que você gerou, já inserida aqui!
URL_BACKEND_GOOGLE = "https://script.google.com/macros/s/AKfycbzi22IQcpef2kR8Sf__aFCE2VkSj_0uFi5MMne1yKQ6pwM4TGy3idDv0LqQwruu2AZS/exec"
# ==========================================================

# --- Configuração da Página e Tema Escuro Premium (CSS Customizado) ---
st.set_page_config(page_title="Portal de Vendas Premium", page_icon="🏎️", layout="wide")

st.markdown("""
    <style>
    .stApp {
        background-color: #0A0A0A;
        color: #E0E0E0;
    }
    h1, h2, h3, .stSubheader {
        color: #FFFFFF !important;
        font-family: 'Inter', sans-serif;
    }
    .stButton>button {
        background-color: #1F2937;
        color: #FFFFFF;
        border: 1px solid #374151;
        border-radius: 8px;
        transition: 0.3s;
        font-weight: bold;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #374151;
        border-color: #9CA3AF;
        color: #FFFFFF;
    }
    .stTextInput>div>div>input, .stSelectbox>div>div>select, .stTextArea>div>div>textarea {
        background-color: #111827;
        color: #FFFFFF;
        border-radius: 5px;
        border: 1px solid #374151;
    }
    /* Estilo para as abas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #111827;
        border-radius: 5px 5px 0px 0px;
        color: #E0E0E0;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1F2937;
        color: #FFFFFF !important;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# --- Funções Inteligentes ---
def validar_cpf(cpf):
    """Valida o CPF usando algoritmo oficial."""
    cpf = re.sub(r'[^0-9]', '', str(cpf))
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for i in range(9, 11):
        val = sum((int(cpf[num]) * ((i + 1) - num) for num in range(0, i)))
        digito = ((val * 10) % 11) % 10
        if digito != int(cpf[i]):
            return False
    return True

def buscar_cep(cep):
    """Busca o endereço automaticamente pelo CEP (ViaCEP)."""
    cep = re.sub(r'[^0-9]', '', str(cep))
    if len(cep) == 8:
        try:
            resp = requests.get(f"https://viacep.com.br/ws/{cep}/json/", timeout=5)
            if resp.status_code == 200:
                dados = resp.json()
                if "erro" not in dados:
                    return dados
        except:
            pass
    return None

def formatar_ficha_venda(dados_venda):
    """Gera o texto formatado para copiar e colar no WhatsApp."""
    return f"""🚀 NOVA VENDA

👤 DADOS DO CLIENTE
* Nome: {dados_venda['nome'].upper()}
* CPF: {dados_venda['cpf']}
* Nome da Mãe: {dados_venda['mae'].upper()}

📞 CONTATO
* WhatsApp: {dados_venda['whatsapp']}

📍 ENDEREÇO DE INSTALAÇÃO
* CEP: {dados_venda['cep']}
* Rua: {dados_venda['rua'].upper()}
* Nº: {dados_venda['numero']}
* Bairro: {dados_venda['bairro'].upper()}
* Referência: {dados_venda['referencia'].upper()}

📶 DETALHES DO PLANO
* Operadora: {dados_venda['operadora'].upper()}
* Plano: {dados_venda['plano'].upper()}

OBSERVAÇÕES:
* {dados_venda['obs']}
* Vendedor: Moabe"""

def enviar_para_planilha(dados):
    """Envia os dados via POST para o Google Apps Script."""
    try:
        # Adiciona o campo 'data' no formato ISO
        response = requests.post(
            URL_BACKEND_GOOGLE, 
            data=json.dumps(dados), 
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'sucesso':
                return True
    except Exception as e:
        print(f"Erro ao enviar para planilha: {e}")
    return False

# --- Título Principal ---
st.title("🏎️ Portal de Vendas Premium")
st.markdown("---")

# --- Interface Principal com Abas ---
aba_vendas, aba_leads = st.tabs(["🚀 Nova Venda", "📝 Controle de Leads"])

# =========================================================================
# ABA 1: NOVA VENDA
# =========================================================================
with aba_vendas:
    st.subheader("📋 Preencha a Ficha")
    
    with st.form("form_venda", clear_on_submit=True):
        col_nome, col_cpf = st.columns(2)
        with col_nome:
            nome = st.text_input("Nome Completo do Cliente")
        with col_cpf:
            cpf = st.text_input("CPF (Apenas números)")
            
        col_mae, col_whats = st.columns(2)
        with col_mae:
            mae = st.text_input("Nome da Mãe do Cliente")
        with col_whats:
            whatsapp = st.text_input("WhatsApp (com DDD)")

        st.markdown("##### 📍 Endereço")
        col_cep, col_btn_cep = st.columns([3, 1])
        with col_cep:
            cep = st.text_input("CEP")
        with col_btn_cep:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("🔍 Buscar CEP"):
                dados_cep = buscar_cep(cep)
                if dados_cep:
                    # Usamos state para preencher os outros campos
                    st.session_state['rua_venda'] = dados_cep.get("logradouro", "")
                    st.session_state['bairro_venda'] = dados_cep.get("bairro", "")
                else:
                    st.error("CEP não encontrado")

        rua = st.text_input("Rua", value=st.session_state.get('rua_venda', ""))
        col_num, col_bairro = st.columns([1, 3])
        with col_num:
            numero = st.text_input("Número")
        with col_bairro:
            bairro = st.text_input("Bairro", value=st.session_state.get('bairro_venda', ""))
        referencia = st.text_input("Ponto de Referência")

        st.markdown("##### 📶 O Pedido")
        # --- Configurações de Operadora e Plano ---
        # Exemplo: Você pode mudar 'NIO' e os planos para os que você vende
        lista_operadoras = ["Selecione", "NIO", "Claro", "Vivo", "Oi Fibra"]
        operadora = st.selectbox("Operadora", lista_operadoras)
        
        # Lógica simples para os planos (exemplo)
        if operadora == "NIO":
            lista_planos = ["Selecione", "400 MEGA", "600 MEGA", "800 MEGA NIO"]
        elif operadora == "Claro":
            lista_planos = ["Selecione", "500 MEGA", "750 MEGA", "1 GIGA Claro"]
        else:
            lista_planos = ["Selecione"]
            
        plano = st.selectbox("Plano", lista_planos)
        observacoes = st.text_area("Observações Adicionais (opcional)")

        # Campo oculto para status
        status_venda = "Nova"

        # Botão de ação principal
        st.markdown("<br>", unsafe_allow_html=True)
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            btn_salvar = st.form_submit_button("💾 Salvar na Planilha e Gerar Ficha")

        if btn_salvar:
            if not nome or not cpf or operadora == "Selecione" or plano == "Selecione":
                st.error("⚠️ Preencha Nome, CPF, Operadora e Plano.")
            elif not validar_cpf(cpf):
                st.error("❌ CPF Inválido! Verifique.")
            else:
                # Prepara os dados para envio
                dados_venda = {
                    "tipo": "venda",
                    "nome": nome,
                    "cpf": cpf,
                    "mae": mae,
                    "whatsapp": whatsapp,
                    "cep": cep,
                    "rua": rua,
                    "numero": numero,
                    "bairro": bairro,
                    "referencia": referencia,
                    "operadora": operadora,
                    "plano": plano,
                    "status": status_venda,
                    "obs": observacoes
                }
                
                # Envia para a planilha
                with st.spinner("Enviando para a planilha..."):
                    if enviar_para_planilha(dados_venda):
                        st.success("✅ Venda salva com sucesso na sua Planilha Google!")
                        # Mostra a ficha formatada para cópia
                        ficha_whatsapp = formatar_ficha_venda(dados_venda)
                        st.markdown("### 📋 Copie a Ficha (WhatsApp)")
                        st.code(ficha_whatsapp, language="text")
                    else:
                        st.error("❌ Erro ao enviar para a planilha. Verifique o backend ou tente mais tarde.")

# =========================================================================
# ABA 2: CONTROLE DE LEADS
# =========================================================================
with aba_leads:
    st.subheader("📝 Novo Lead")
    with st.form("form_lead", clear_on_submit=True):
        nome_lead = st.text_input("Nome/Apelido")
        whatsapp_lead = st.text_input("WhatsApp/Contato")
        
        lista_status_lead = ["Quente", "Frio", "Agendar Retorno", "Sem Viabilidade", "Outro"]
        status_lead = st.selectbox("Status", lista_status_lead)
        obs_lead = st.text_area("Anotações Livres")
        
        st.markdown("<br>", unsafe_allow_html=True)
        btn_salvar_lead = st.form_submit_button("💾 Salvar Lead")
        
        if btn_salvar_lead:
            if not nome_lead or not whatsapp_lead:
                st.error("⚠️ Nome e WhatsApp são obrigatórios.")
            else:
                # Prepara dados do lead
                dados_lead = {
                    "tipo": "lead",
                    "nome": nome_lead,
                    "whatsapp": whatsapp_lead,
                    "status": status_lead,
                    "obs": obs_lead
                }
                
                # Envia para a planilha
                with st.spinner("Enviando lead para a planilha..."):
                    if enviar_para_planilha(dados_lead):
                        st.success(f"✅ Lead '{nome_lead}' salvo com sucesso na aba LEADS da planilha!")
                    else:
                        st.error("❌ Erro ao enviar lead. Tente mais tarde.")