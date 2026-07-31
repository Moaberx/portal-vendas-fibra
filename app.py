import streamlit as st
import requests
import json
import re
from streamlit_local_storage import LocalStorage

# ================= CONFIGURAÇÕES CRUCIAIS =================
# Esta é a sua ponte URL
URL_BACKEND_GOOGLE = "https://script.google.com/macros/s/AKfycbzi22IQcpef2kR8Sf__aFCE2VkSj_0uFi5MMne1yKQ6pwM4TGy3idDv0LqQwruu2AZS/exec"
# ==========================================================

# --- Configuração da Página para Mobile e Tema Chic Extremo ---
st.set_page_config(page_title="Portal de Vendas Premium", page_icon="📶", layout="centered")

# CSS para Ultra Otimização Mobile e Visual Chic
st.markdown("""
    <style>
    /* Fundo ainda mais profundo e limpo */
    .stApp {
        background-color: #050505;
        color: #E0E0E0;
    }
    
    /* Títulos limpos e brancos */
    h1, h2, h3, .stSubheader {
        color: #FFFFFF !important;
        font-family: 'Inter', 'Roboto', sans-serif;
        font-weight: 300;
        letter-spacing: -0.5px;
    }
    
    /* Entradas e Seleções: Mobile Otimizadas (Maiores) e Visuais Premium */
    .stTextInput>div>div>input, .stSelectbox>div>div>select, .stTextArea>div>div>textarea, .stNumberInput>div>div>input {
        background-color: #0A0A0A !important;
        color: #FFFFFF !important;
        border-radius: 8px !important;
        border: 1px solid #1A1A1A !important;
        padding: 12px !important;
        font-size: 16px !important; /* Tamanho perfeito para toque */
    }
    .stTextInput>div>div>input:focus {
        border-color: #374151 !important;
    }

    /* Botão Principal: Mobile Full Width e Visual Chic Grey */
    .stButton>button {
        background-color: #1F2937;
        color: #FFFFFF;
        border: 1px solid #374151;
        border-radius: 8px;
        transition: 0.3s;
        font-weight: 300;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-size: 14px;
        width: 100% !important; /* Full width no mobile */
        padding: 15px;
        margin-top: 10px;
    }
    .stButton>button:hover {
        background-color: #374151;
        border-color: #9CA3AF;
        color: #FFFFFF;
    }
    
    /* Botão Secundário (Buscar CEP): Menor e Limpo */
    div[data-testid="column"]>.stButton>button {
        width: auto !important;
        background-color: #0A0A0A;
        border: 1px solid #1A1A1A;
        padding: 8px 15px;
        text-transform: none;
        letter-spacing: normal;
    }

    /* Abas Premium e Mobile-first */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        width: 100%;
        border-bottom: 1px solid #1A1A1A;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #050505;
        color: #9CA3AF;
        border: none;
        font-weight: 300;
        flex: 1; /* Abas esticam igualmente */
        text-align: center;
        border-bottom: 2px solid transparent;
    }
    .stTabs [aria-selected="true"] {
        background-color: #050505 !important;
        color: #FFFFFF !important;
        font-weight: 500 !important;
        border-bottom: 2px solid #FFFFFF !important;
    }
    
    /* Removendo padding excessivo do Streamlit */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    
    /* Melhorando visual da ficha final */
    .stCode {
        background-color: #0A0A0A;
        border: 1px solid #1A1A1A;
        border-radius: 8px;
    }
    
    /* Escondendo cabeçalhos automáticos de coluna no mobile em certas seleções */
    @media (max-width: 640px) {
        [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            margin-bottom: 10px;
        }
    }
    </style>
""", unsafe_allow_html=True)

# --- SISTEMA DE RASCUNHO AUTOMÁTICO (Premium) ---
# Inicializa o armazenamento local
local_storage = LocalStorage()

def salvar_rascunho():
    """Salva os dados atuais da session_state no local_storage."""
    dados_rascunho = {k: v for k, v in st.session_state.items() if k.startswith('f_')}
    local_storage.set("rascunho_venda_fibra_tim", dados_rascunho)

def carregar_rascunho():
    """Carrega o rascunho salvo no local_storage para a session_state."""
    rascunho = local_storage.get("rascunho_venda_fibra_tim")
    if rascunho:
        for k, v in rascunho.items():
            st.session_state[k] = v
        st.success("✅ Rascunho carregado automaticamente do seu celular!")

def limpar_rascunho():
    """Limpa o rascunho no local_storage após sucesso."""
    local_storage.delete("rascunho_venda_fibra_tim")
    for k in [k for k in st.session_state.items() if k.startswith('f_')]:
        del st.session_state[k]

# --- DADOS DE PLANOS (Atualizados conforme solicitado) ---

PLANOS_NIO = {
    "Residencial": {
        "500 Mega (Essencial)": {"valor": 100.00, "detalhes": "Wi-Fi padrão incluso."},
        "600 Mega (Essencial)": {"valor": 109.00, "detalhes": "Wi-Fi padrão incluso."},
        "800 Mega (Super)": {"valor": 135.00, "detalhes": "Wi-Fi 6 + Globoplay 12m."},
        "1 Giga (Ultra)": {"valor": 160.00, "detalhes": "Wi-Fi 6 + 1 Ponto Mesh + Globoplay 12m."},
    },
    "Empresarial (B2B)": {
        "500 Mega (Empresarial Essencial)": {"valor": 100.00, "detalhes": "Wi-Fi 5 + Maquininha grátis."},
        "600 Mega (Empresarial Essencial)": {"valor": 109.00, "detalhes": "Wi-Fi 5 + Maquininha grátis."},
        "800 Mega (Empresarial Super)": {"valor": 135.00, "detalhes": "Wi-Fi 6 + Maquininha grátis + McAfee."},
        "1 Giga (Empresarial Ultra)": {"valor": 160.00, "detalhes": "Wi-Fi 6 + 1 Ponto Mesh."},
    }
}

PLANOS_TIM = {
    "Pessoa Física (PF)": {
        "600 Mega": {"valor": 119.99, "original": 159.99, "detalhes": "Wi-Fi grátis, Globoplay + Digital."},
        "800 Mega (Oferta Especial)": {"valor": 129.99, "original": 169.99, "detalhes": "Wi-Fi grátis, YouTube Premium + Digital."},
        "1 Giga": {"valor": 129.99, "original": 189.99, "detalhes": "Wi-Fi 6, Digital + Extra Paramount+."},
    },
    "Empresarial (CNPJ)": {
        "1 Giga (Custo-Benefício Premium)": {"valor": 99.90, "detalhes": "Oferta exclusiva CNPJ."},
    }
}

# --- Funções Inteligentes Otimizadas ---
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
    """Busca o endereço automaticamente pelo CEP (ViaCEP) - Rápida."""
    cep = re.sub(r'[^0-9]', '', str(cep))
    if len(cep) == 8:
        try:
            resp = requests.get(f"https://viacep.com.br/ws/{cep}/json/", timeout=3)
            if resp.status_code == 200:
                dados = resp.json()
                if "erro" not in dados:
                    return dados
        except:
            pass
    return None

def formatar_ficha_venda(dados_venda):
    """Gera o texto formatado para copiar e colar no WhatsApp."""
    return f"""🚀 NOVA VENDA (FIBRA/TIM)

👤 CLIENTE (Chic)
* Nome: {dados_venda['nome'].upper()}
* CPF: {dados_venda['cpf']}
* Nome Mãe: {dados_venda['mae'].upper()}
* Email (Obr.): {dados_venda['email']}

📞 CONTATOS
* Whats 1: {dados_venda['whats1']}
* Contato 2 (Opc.): {dados_venda['whats2'] or '---'}

📍 INSTALAÇÃO
* CEP: {dados_venda['cep']}
* Rua: {dados_venda['rua'].upper()}
* Nº: {dados_venda['numero']}
* Bairro: {dados_venda['bairro'].upper()}
* Ref.: {dados_venda['referencia'].upper()}

📶 O PEDIDO
* Operadora: {dados_venda['operadora'].upper()}
* Plano: {dados_venda['plano'].upper()}
* Valor: R$ {dados_venda['valor_plano']:.2f}

DETALHES PLANO:
* {dados_venda['detalhes_plano']}

OBS:
* {dados_venda['obs']}
* Vendedor: Moabe (P. Premium)"""

def enviar_para_planilha(dados):
    """Envia os dados via POST para o Google Script."""
    try:
        response = requests.post(
            URL_BACKEND_GOOGLE, 
            data=json.dumps(dados), 
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'sucesso':
                return True
    except:
        pass
    return False

# --- Título Chic e Minimalista ---
st.title("📶 Portal de Vendas Premium")
st.markdown("---")

# --- SISTEMA DE RASCUNHO: Tentativa de Carregamento Automático ---
# No Streamlit, precisamos fazer isso antes dos widgets serem desenhados
# mas após o local_storage ser inicializado. Usamos uma variável de controle.
if 'rascunho_carregado' not in st.session_state:
    st.session_state['rascunho_carregado'] = False

if not st.session_state['rascunho_carregado']:
    # O Streamlit às vezes precisa de um pequeno delay para carregar o localStorage
    if st.button("⚠️ Carregar Rascunho do Celular (Aperte se CPF não apareceu)"):
        carregar_rascunho()
        st.session_state['rascunho_carregado'] = True
        st.rerun() # Recarrega para preencher os widgets

# --- Interface Principal com Abas Premium ---
aba_vendas, aba_leads = st.tabs(["🚀 Nova Venda", "📝 Leads (Opc.)"])

# =========================================================================
# ABA 1: NOVA VENDA (Mobile Total Otimizado)
# =========================================================================
with aba_vendas:
    st.subheader("📋 Preencha a Ficha")
    
    # Usamos st.form para agrupar e enviar no mobile com um toque
    with st.form("form_venda", clear_on_submit=False): # False para não limpar o CPF/Whats se houver erro
        
        st.markdown("##### 👤 Cliente")
        
        # Widgets com session_state para rascunho automático
        nome = st.text_input("Nome Completo", key='f_nome')
        cpf = st.text_input("CPF (Apenas números)", key='f_cpf')
        
        # Email (OBRIGATÓRIO)
        email = st.text_input("Email do Cliente (Obrigatório)*", key='f_email')
        
        mae = st.text_input("Nome da Mãe do Cliente", key='f_mae')
        
        # WhatsApp Principal
        whatsapp = st.text_input("WhatsApp (com DDD)*", key='f_whats1')
        
        # 2º Contato (OPCIONAL)
        contato2 = st.text_input("2º Telefone/Contato (Opcional)", key='f_whats2')

        st.markdown("##### 📍 Endereço")
        
        # CEP e Botão otimizados para Mobile
        cep_input = st.text_input("CEP", key='f_cep')
        # Botão de CEP secundário, mas otimizado
        
        if st.form_submit_button("🔍 Buscar CEP"):
            # Salva rascunho antes de qualquer ação que recarregue a página
            salvar_rascunho()
            dados_cep = buscar_cep(cep_input)
            if dados_cep:
                st.session_state['f_rua'] = dados_cep.get("logradouro", "")
                st.session_state['f_bairro'] = dados_cep.get("bairro", "")
                st.rerun() # Atualiza os campos na tela
            else:
                st.error("CEP não encontrado.")

        rua = st.text_input("Rua", key='f_rua')
        col_num, col_bairro = st.columns([1, 2])
        with col_num:
            numero = st.text_input("Nº", key='f_numero')
        with col_bairro:
            bairro = st.text_input("Bairro", key='f_bairro')
        referencia = st.text_input("Ponto de Referência", key='f_referencia')

        st.markdown("##### 📶 O Pedido")
        
        # --- Lógica Premium de Operadora e Planos ---
        lista_operadoras = ["Selecione", "NIO Fibra", "TIM Ultrafibra", "Vivo", "Claro"]
        operadora = st.selectbox("Operadora*", lista_operadoras, key='f_operadora')
        
        plano_final = "Selecione"
        valor_plano = 0.00
        detalhes_plano = "---"

        # Lógica dinâmica para NIO Fibra
        if operadora == "NIO Fibra":
            # Primeiro nível: Residencial ou Empresarial
            categoria_nio = st.selectbox("Categoria", ["Selecione", "Residencial", "Empresarial (B2B)"], key='f_nio_cat')
            if categoria_nio != "Selecione":
                # Segundo nível: Lista de planos
                lista_planos_nio = ["Selecione"] + list(PLANOS_NIO[categoria_nio].keys())
                plano_selecionado = st.selectbox("Escolha o Plano", lista_planos_nio, key='f_nio_plano')
                if plano_selecionado != "Selecione":
                    p = PLANOS_NIO[categoria_nio][plano_selecionado]
                    plano_final = f"NIO - {categoria_nio} - {plano_selecionado}"
                    valor_plano = p['valor']
                    detalhes_plano = p['detalhes']
                    st.info(f"R$ {valor_plano:.2f}/mês. {detalhes_plano}")

        # Lógica dinâmica para TIM Ultrafibra
        elif operadora == "TIM Ultrafibra":
            # Primeiro nível: PF ou Empresarial
            categoria_tim = st.selectbox("Categoria", ["Selecione", "Pessoa Física (PF)", "Empresarial (CNPJ)"], key='f_tim_cat')
            if categoria_tim != "Selecione":
                # Segundo nível: Lista de planos
                lista_planos_tim = ["Selecione"] + list(PLANOS_TIM[categoria_tim].keys())
                plano_selecionado = st.selectbox("Escolha o Plano", lista_planos_tim, key='f_tim_plano')
                if plano_selecionado != "Selecione":
                    p = PLANOS_TIM[categoria_tim][plano_selecionado]
                    plano_final = f"TIM - {categoria_tim} - {plano_selecionado}"
                    valor_plano = p['valor']
                    detalhes_plano = p['detalhes']
                    # Mostra valor promocional e original se houver
                    if 'original' in p:
                        st.info(f"Promocional R$ {valor_plano:.2f}/mês (Débito)*. Original/Boleto: R$ {p['original']:.2f}/mês.")
                    else:
                        st.info(f"Valor R$ {valor_plano:.2f}/mês. {detalhes_plano}")
                    st.warning("⚠️ Planos PF: Valor promocional exclusivo para pagamento no Débito Automático.")

        # Lógica PADRÃO (Oi Fiber removida, Vivo/Claro)
        elif operadora in ["Vivo", "Claro"]:
            st.selectbox("Plano", ["Selecione", "Plano Padrão"], key='f_default_plano')
            # Lógica para prosseguir como padrão com valor 0
            if st.session_state['f_default_plano'] == "Plano Padrão":
                plano_final = "Plano Padrão (Vivo/Claro)"
                valor_plano = 0.00
                detalhes_plano = "Plano padrão pré-configurado."
                st.info(f"Valor: ---. (Vivo/Claro selecionado).")

        observacoes = st.text_area("Observações Adicionais (opcional)", key='f_obs')

        st.markdown("<br>", unsafe_allow_html=True)
        # Botão de ação principal, MOBILE OTIMIZADO (full width)
        # Se você clicar nele, o Streamlit vai recarregar a página para enviar, 
        # mas nosso sistema de rascunho automático garante que o CPF não suma se falhar.
        btn_salvar = st.form_submit_button("💾 Salvar na Planilha e Gerar Ficha")

        # Antes de processar, salva rascunho "quietamente" no local storage
        salvar_rascunho()

        if btn_salvar:
            # Validações Otimizadas
            if not nome or not cpf or not email or not whatsapp:
                st.error("⚠️ Nome, CPF, Email (Obr.) e Whats 1 são obrigatórios.")
            elif operadora == "Selecione" or plano_final == "Selecione":
                st.error("⚠️ Escolha a Operadora e o Plano.")
            elif not validar_cpf(cpf):
                st.error("❌ CPF Inválido! Verifique e tente novamente.")
            else:
                # Prepara os dados para envio
                dados_venda = {
                    "tipo": "venda",
                    "nome": nome,
                    "cpf": cpf,
                    "mae": mae,
                    "email": email,      # Novo (OBRIGATÓRIO)
                    "whats1": whatsapp,
                    "whats2": contato2,   # Novo (OPCIONAL)
                    "cep": cep_input,
                    "rua": rua,
                    "numero": numero,
                    "bairro": bairro,
                    "referencia": referencia,
                    "operadora": operadora,
                    "plano": plano_final, # Nome completo
                    "valor_plano": valor_plano, # Valor numérico
                    "detalhes_plano": detalhes_plano, # Detalhes string
                    "status": "Nova",
                    "obs": observacoes
                }
                
                # Envia para a planilha com spinner móvel
                with st.spinner("Enviando venda premium..."):
                    if enviar_para_planilha(dados_venda):
                        st.success("✅ Venda salva com sucesso na sua Planilha Google!")
                        
                        # Limpa rascunho após sucesso
                        limpar_rascunho()
                        
                        # Mostra a ficha formatada para cópia
                        ficha_whatsapp = formatar_ficha_venda(dados_venda)
                        st.markdown("### 📋 Ficha (Copie pro Whats)")
                        st.code(ficha_whatsapp, language="text")
                    else:
                        st.error("❌ Erro ao enviar. Tente novamente mais tarde ou contate suporte.")

# =========================================================================
# ABA 2: LEADS (Mobile Otimizada) - Mantido limpo
# =========================================================================
with aba_leads:
    st.subheader("📝 Controle de Leads (Prospecção)")
    with st.form("form_lead", clear_on_submit=True):
        nome_lead = st.text_input("Nome/Contato")
        whatsapp_lead = st.text_input("WhatsApp (com DDD)")
        
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
                with st.spinner("Enviando lead..."):
                    if enviar_para_planilha(dados_lead):
                        st.success(f"✅ Lead '{nome_lead}' salvo com sucesso!")
                    else:
                        st.error("❌ Erro ao enviar lead. Tente novamente.")
