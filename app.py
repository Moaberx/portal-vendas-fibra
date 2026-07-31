import streamlit as st
import requests
import json
import re
from streamlit_local_storage import LocalStorage

# ================= CONEXÃO DE DADOS =================
URL_BACKEND_GOOGLE = "https://script.google.com/macros/s/AKfycbyTF3qUfRvMKh5JcyxJ_rbo8fSc04n24s8y8X7wtS0nP1qVjv2nUbpQLZHmAWmpXhKJ/exec"
# ====================================================

# --- Configuração do Terminal (Layout Corporativo) ---
st.set_page_config(page_title="Sistema de Cadastros | Especialista Fibra", page_icon="📡", layout="centered")

# CSS: Tema Tech Sóbrio e Clean
st.markdown("""
    <style>
    /* Fundo Chumbo/Grafite: Elegante e poupa bateria no celular */
    .stApp { background-color: #121212; color: #E5E7EB; }
    
    /* Tipografia Limpa */
    h1, h2, h3, .stSubheader { color: #F9FAFB !important; font-family: 'Inter', 'Segoe UI', sans-serif; font-weight: 500; letter-spacing: -0.3px; }
    
    /* Campos de Entrada: Fundo levemente mais claro que a página, bordas sutis */
    .stTextInput>div>div>input, .stSelectbox>div>div>select, .stTextArea>div>div>textarea, .stNumberInput>div>div>input {
        background-color: #1F2937 !important; color: #F9FAFB !important; 
        border-radius: 6px !important; border: 1px solid #374151 !important; 
        padding: 10px 12px !important; font-size: 15px !important;
    }
    .stTextInput>div>div>input:focus { border-color: #3B82F6 !important; }

    /* Botão Principal: Azul Corporativo */
    .stButton>button { 
        background-color: #2563EB; color: #FFFFFF; border: none; border-radius: 6px; 
        width: 100% !important; padding: 14px; margin-top: 15px; 
        font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; 
    }
    .stButton>button:hover { background-color: #1D4ED8; color: #FFFFFF; }
    
    /* Botão Secundário (Buscar CEP) */
    div[data-testid="column"]>.stButton>button { 
        width: auto !important; background-color: #374151; padding: 6px 14px; 
        font-size: 13px; text-transform: none; margin-top: 28px;
    }

    /* Estilo das Abas de Navegação */
    .stTabs [data-baseweb="tab-list"] { border-bottom: 1px solid #374151; gap: 0; }
    .stTabs [data-baseweb="tab"] { 
        height: 45px; background-color: transparent; color: #9CA3AF; 
        border: none; flex: 1; text-align: center; font-size: 14px;
    }
    .stTabs [aria-selected="true"] { 
        color: #3B82F6 !important; border-bottom: 2px solid #3B82F6 !important; font-weight: 600 !important; 
    }
    
    /* Caixa de resultado (Ficha) */
    .stCode { background-color: #1F2937; border: 1px solid #374151; border-radius: 6px; }
    </style>
""", unsafe_allow_html=True)

# --- ENGINE DE PERSISTÊNCIA (Rascunho Automático) ---
local_storage = LocalStorage()

def salvar_rascunho():
    try:
        dados_rascunho = {k: v for k, v in st.session_state.items() if k.startswith('f_')}
        local_storage.setItem("memoria_cadastro_fibra", json.dumps(dados_rascunho))
    except:
        pass

def carregar_rascunho():
    try:
        rascunho_str = local_storage.getItem("memoria_cadastro_fibra")
        if rascunho_str:
            rascunho = json.loads(rascunho_str) if isinstance(rascunho_str, str) else rascunho_str
            for k, v in rascunho.items():
                st.session_state[k] = v
            st.success("✅ Dados temporários recuperados do terminal.")
    except:
        pass

def limpar_rascunho():
    try:
        local_storage.setItem("memoria_cadastro_fibra", "")
        for k in list(st.session_state.keys()):
            if k.startswith('f_'):
                del st.session_state[k]
    except:
        pass

# --- BANCO DE PLANOS COMERCIAIS ---
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

# --- FUNÇÕES UTILITÁRIAS ---
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
    return f"""📡 ORDEM DE SERVIÇO - ESPECIALISTA FIBRA

📄 DADOS DO TITULAR
* Titular: {d['nome'].upper()}
* CPF/CNPJ: {d['cpf']}
* Nome da Mãe: {d['mae'].upper()}
* Email: {d['email']}

📞 CONTATOS REGISTRADOS
* Linha 1 (Principal): {d['whats1']}
* Linha 2 (Alternativa): {d['whats2'] or 'Não informado'}

📍 ENDEREÇO DE INSTALAÇÃO
* CEP: {d['cep']}
* Logradouro: {d['rua'].upper()}, Nº {d['numero']}
* Bairro: {d['bairro'].upper()}
* Referência: {d['referencia'].upper()}

⚙️ ESPECIFICAÇÕES DO SERVIÇO
* Provedor: {d['operadora'].upper()}
* Pacote Contratado: {d['plano'].upper()}
* Faturamento: R$ {d['valor_plano']:.2f}/mês

DETALHES TÉCNICOS/COMERCIAIS:
* {d['detalhes_plano']}

OBSERVAÇÕES DO OPERADOR:
* {d['obs']}

---
Operador: Moabe Xavier | Especialista Fibra"""

def enviar_para_planilha(dados):
    try:
        resp = requests.post(URL_BACKEND_GOOGLE, data=json.dumps(dados), headers={"Content-Type": "application/json"}, timeout=10)
        if resp.status_code == 200 and resp.json().get('status') == 'sucesso': return True
    except: pass
    return False

# --- ESTRUTURA DA INTERFACE ---
st.title("📡 Terminal de Cadastros")
st.markdown("Sistema integrado de gestão de vendas e instalações.")
st.markdown("---")

if 'rascunho_carregado' not in st.session_state:
    st.session_state['rascunho_carregado'] = False

if not st.session_state['rascunho_carregado']:
    if st.button("🔄 Sincronizar Memória do Cache (Clique em caso de perda)"):
        carregar_rascunho()
        st.session_state['rascunho_carregado'] = True
        st.rerun()

aba_vendas, aba_leads = st.tabs(["📝 Solicitar Instalação", "📊 Fila de Retorno"])

# ================= ABA 1: SOLICITAÇÃO DE INSTALAÇÃO =================
with aba_vendas:
    
    with st.form("form_venda", clear_on_submit=False):
        st.markdown("#### 📄 Dados do Titular")
        nome = st.text_input("Nome Completo / Razão Social", key='f_nome')
        cpf = st.text_input("CPF ou CNPJ (Apenas números)", key='f_cpf')
        email = st.text_input("Correio Eletrônico (Email)*", key='f_email')
        mae = st.text_input("Nome da Mãe (Validação de Segurança)", key='f_mae')
        
        col_tel1, col_tel2 = st.columns(2)
        with col_tel1:
            whatsapp = st.text_input("Telefone Principal (WhatsApp)*", key='f_whats1')
        with col_tel2:
            contato2 = st.text_input("Telefone Alternativo", key='f_whats2')

        st.markdown("<br>#### 📍 Endereço de Instalação", unsafe_allow_html=True)
        
        col_cep, col_btn = st.columns([2, 1])
        with col_cep:
            cep_input = st.text_input("Código Postal (CEP)", key='f_cep')
        with col_btn:
            if st.form_submit_button("🔍 Consultar base"):
                salvar_rascunho()
                dados_cep = buscar_cep(cep_input)
                if dados_cep:
                    st.session_state['f_rua'] = dados_cep.get("logradouro", "")
                    st.session_state['f_bairro'] = dados_cep.get("bairro", "")
                    st.rerun()
                else:
                    st.error("Erro: CEP não localizado na base dos Correios.")

        rua = st.text_input("Logradouro (Rua/Av)", key='f_rua')
        col_num, col_bairro = st.columns([1, 2])
        with col_num: 
            numero = st.text_input("Número", key='f_numero')
        with col_bairro: 
            bairro = st.text_input("Bairro", key='f_bairro')
        referencia = st.text_input("Ponto de Referência para Equipe Técnica", key='f_referencia')

        st.markdown("<br>#### ⚙️ Especificações do Serviço", unsafe_allow_html=True)
        operadora = st.selectbox("Provedor de Infraestrutura*", ["Selecione", "NIO Fibra", "TIM Ultrafibra", "Vivo", "Claro"], key='f_operadora')
        
        plano_final, valor_plano, detalhes_plano = "Selecione", 0.00, "---"

        if operadora == "NIO Fibra":
            categoria_nio = st.selectbox("Segmento", ["Selecione", "Residencial", "Empresarial (B2B)"], key='f_nio_cat')
            if categoria_nio != "Selecione":
                plano_selecionado = st.selectbox("Pacote Comercial", ["Selecione"] + list(PLANOS_NIO[categoria_nio].keys()), key='f_nio_plano')
                if plano_selecionado != "Selecione":
                    p = PLANOS_NIO[categoria_nio][plano_selecionado]
                    plano_final = f"NIO - {categoria_nio} - {plano_selecionado}"
                    valor_plano, detalhes_plano = p['valor'], p['detalhes']
                    st.info(f"Faturamento: R$ {valor_plano:.2f}/mês. Equipamento: {detalhes_plano}")

        elif operadora == "TIM Ultrafibra":
            categoria_tim = st.selectbox("Segmento", ["Selecione", "Pessoa Física (PF)", "Empresarial (CNPJ)"], key='f_tim_cat')
            if categoria_tim != "Selecione":
                plano_selecionado = st.selectbox("Pacote Comercial", ["Selecione"] + list(PLANOS_TIM[categoria_tim].keys()), key='f_tim_plano')
                if plano_selecionado != "Selecione":
                    p = PLANOS_TIM[categoria_tim][plano_selecionado]
                    plano_final = f"TIM - {categoria_tim} - {plano_selecionado}"
                    valor_plano, detalhes_plano = p['valor'], p['detalhes']
                    if 'original' in p: 
                        st.info(f"Faturamento Promocional (Débito): R$ {valor_plano:.2f}/mês. Valor de Tabela/Boleto: R$ {p['original']:.2f}/mês.")
                    else: 
                        st.info(f"Faturamento: R$ {valor_plano:.2f}/mês. Detalhes: {detalhes_plano}")

        elif operadora in ["Vivo", "Claro"]:
            st.selectbox("Pacote Comercial", ["Selecione", "Configuração Padrão"], key='f_default_plano')
            if st.session_state['f_default_plano'] == "Configuração Padrão":
                plano_final, valor_plano, detalhes_plano = "Plano Padrão (Vivo/Claro)", 0.00, "Configuração comercial padrão."
                st.info("Valores sob consulta. (Via Provedor Selecionado).")

        observacoes = st.text_area("Anotações para Backoffice (Opcional)", key='f_obs')
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Botão de Envio
        btn_salvar = st.form_submit_button("📤 Transmitir Pedido e Gerar O.S.")

        # Persistência acionada a cada interação no formulário
        salvar_rascunho()

        if btn_salvar:
            if not nome or not cpf or not email or not whatsapp: 
                st.error("⚠️ Alerta do Sistema: Campos obrigatórios (Nome, CPF/CNPJ, Email e Telefone Principal) não preenchidos.")
            elif operadora == "Selecione" or plano_final == "Selecione": 
                st.error("⚠️ Alerta do Sistema: Provedor e Pacote Comercial devem ser especificados.")
            elif not validar_cpf(cpf): 
                st.error("❌ Falha de Validação: O documento informado (CPF/CNPJ) é inválido.")
            else:
                dados_venda = {
                    "tipo": "venda", "nome": nome, "cpf": cpf, "mae": mae, "email": email, "whats1": whatsapp,
                    "whats2": contato2, "cep": cep_input, "rua": rua, "numero": numero, "bairro": bairro,
                    "referencia": referencia, "operadora": operadora, "plano": plano_final, "valor_plano": valor_plano,
                    "detalhes_plano": detalhes_plano, "status": "Nova", "obs": observacoes
                }
                with st.spinner("Autenticando e transmitindo dados para a base..."):
                    if enviar_para_planilha(dados_venda):
                        st.success("✅ Transmissão Concluída! O.S. registrada no banco de dados.")
                        limpar_rascunho()
                        st.markdown("### 📋 Resumo da O.S. (Pronto para Cópia)")
                        st.code(formatar_ficha_venda(dados_venda), language="text")
                    else: 
                        st.error("❌ Falha de Conexão: Servidor remoto indisponível. O rascunho foi salvo localmente.")

# ================= ABA 2: FILA DE RETORNO =================
with aba_leads:
    with st.form("form_lead", clear_on_submit=True):
        st.markdown("#### 👤 Dados do Contato")
        nome_lead = st.text_input("Identificação (Nome/Empresa)")
        whatsapp_lead = st.text_input("Terminal de Contato (WhatsApp)")
        status_lead = st.selectbox("Qualificação do Contato", ["Alta Prioridade (Quente)", "Baixa Prioridade (Frio)", "Agendado para Retorno", "Inviabilidade Técnica", "Outros"])
        obs_lead = st.text_area("Registro de Interações")
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.form_submit_button("💾 Arquivar Contato no Banco de Dados"):
            if not nome_lead or not whatsapp_lead: 
                st.error("⚠️ Identificação e Terminal de Contato são obrigatórios para o arquivamento.")
            else:
                with st.spinner("Transmitindo registro..."):
                    if enviar_para_planilha({"tipo": "lead", "nome": nome_lead, "whatsapp": whatsapp_lead, "status": status_lead, "obs": obs_lead}):
                        st.success(f"✅ Contato '{nome_lead}' devidamente arquivado na base.")
                    else: 
                        st.error("❌ Erro de Transmissão.")
