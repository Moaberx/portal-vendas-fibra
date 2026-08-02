import streamlit as st
import requests
import re
import urllib.parse
from datetime import datetime

# ================= CONFIGURAÇÕES =================
URL_BACKEND_GOOGLE = "https://script.google.com/macros/s/AKfycbyTF3qUfRvMKh5JcyxJ_rbo8fSc04n24s8y8X7wtS0nP1qVjv2nUbpQLZHmAWmpXhKJ/exec"

try:
    SENHA_MESTRE = st.secrets.get("senha_mestre_gestao", "PAP_SECRETO_2026")
    NOTION_TOKEN = st.secrets.get("notion_token")
    NOTION_DATABASE_ID = st.secrets.get("notion_database_id")
except Exception:
    SENHA_MESTRE = "PAP_SECRETO_2026"
    NOTION_TOKEN = None
    NOTION_DATABASE_ID = None

st.set_page_config(
    page_title="Cadastro Seguro - Fibra",
    page_icon="🔒",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ================= CSS TEMA CLARO E CONFIÁVEL =================
def aplicar_css():
    st.markdown("""
    <style>
    .stApp { background-color: #F8FAFC; color: #1E293B; font-family: 'Inter', system-ui, sans-serif; }
    h1, h2, h3, label { color: #0F172A !important; font-weight: 600; }
    hr { border-color: #E2E8F0; }
    .stTextInput>div>div>input, .stSelectbox>div>div>select, .stTextArea>div>div>textarea {
        background: #FFFFFF !important; color: #1E293B !important;
        border: 1px solid #CBD5E1 !important; border-radius: 10px !important; padding: 12px !important;
    }
    .stTextInput>div>div>input:focus { border-color: #2563EB !important; box-shadow: 0 0 0 2px rgba(37,99,235,0.2) !important; }
    .stButton>button {
        background: #2563EB; color: white !important; border: none; border-radius: 10px;
        width: 100%; padding: 14px; font-weight: 600; transition: all 0.2s;
    }
    .stButton>button:hover { background: #1D4ED8; transform: translateY(-1px); }
    .security-badge {
        background: #ECFDF5; border: 1px solid #10B981; color: #065F46;
        padding: 14px 18px; border-radius: 10px; font-weight: 600; text-align: center;
        margin-bottom: 24px; font-size: 15px;
    }
    .btn-wpp {
        display: block; background: #25D366; color: white !important; text-align: center;
        border-radius: 10px; padding: 16px; font-weight: 700; text-decoration: none; margin-top: 16px;
    }
    .btn-wpp:hover { background: #1ea952; }
    .alert-ok { background: #ECFDF5; border: 1px solid #A7F3D0; color: #065F46; padding: 14px; border-radius: 10px; font-weight: 600; margin: 12px 0; }
    .alert-warn { background: #FFFBEB; border: 1px solid #FDE68A; color: #92400E; padding: 14px; border-radius: 10px; font-weight: 600; margin: 12px 0; }
    .alert-err { background: #FEF2F2; border: 1px solid #FECACA; color: #991B1B; padding: 14px; border-radius: 10px; font-weight: 600; margin: 12px 0; }
    </style>
    """, unsafe_allow_html=True)

# ================= FUNÇÕES AUXILIARES =================
def gerar_protocolo():
    return f"PAP_{datetime.now().strftime('%Y%m%d_%H%M%S%f')[:20]}"

def blindar(texto):
    if not isinstance(texto, str):
        return texto
    t = texto.strip()
    return f"'{t}" if t.startswith(('=', '+', '-', '@')) else t

def limpar_formulario():
    keys = ['f_nome', 'f_cpf', 'f_nasc', 'f_mae', 'f_email', 'f_w1', 'f_w2',
            'f_cep', 'f_rua', 'f_num', 'f_bairro']
    for k in keys:
        st.session_state[k] = ""

def validar_cpf(doc):
    d = re.sub(r'[^0-9]', '', str(doc))
    if len(d) != 11 or d == d[0] * 11:
        return False
    for i in range(9, 11):
        s = sum(int(d[n]) * ((i + 1) - n) for n in range(i))
        if ((s * 10) % 11) % 10 != int(d[i]):
            return False
    return True

def buscar_cep(cep):
    cep = re.sub(r'[^0-9]', '', str(cep))
    if len(cep) != 8:
        return None
    try:
        r = requests.get(f"https://viacep.com.br/ws/{cep}/json/", timeout=5)
        data = r.json()
        return data if r.status_code == 200 and "erro" not in data else None
    except:
        return "erro_conexao"

def formatar_ficha(d):
    return f"""📄 *NOVA VENDA* 📄

👤 *CLIENTE*
Nome: {d['nome']}
CPF: {d['cpf']}
Nascimento: {d['nasc']}
Mãe: {d['mae']}
Email: {d.get('email') or 'Não informado'}

📞 *CONTATOS*
WhatsApp: {d['w1']}
2º Contato: {d.get('w2') or 'Não informado'}

📍 *ENDEREÇO*
CEP: {d['cep']}
{d['rua']}, Nº {d['num']} - {d['bairro']}

📶 *SERVIÇO*
Operadora: {d['operadora']}
Plano: {d['plano']}
Protocolo: {d.get('protocolo', '')}"""

# ================= NOTION (INFALÍVEL COM DUPLA TENTATIVA) =================
def criar_notion(dados, texto):
    if not NOTION_TOKEN or not NOTION_DATABASE_ID:
        return False, "Notion não configurado nas secrets."

    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    tel = re.sub(r'[^0-9+]', '', str(dados.get('w1', '')))[:20]
    nome = str(dados.get('nome', 'Sem nome'))[:100]

    # Tentativa 1: versão completa (O ideal com colunas mapeadas)
    payload_completo = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Nome": {"title": [{"text": {"content": nome}}]},
            "Status": {"status": {"name": "Nova"}},
            "Telefone": {"phone_number": tel},
            "Data": {"date": {"start": datetime.now().strftime("%Y-%m-%d")}}
        },
        "children": [{
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": texto[:1900]}}]
            }
        }]
    }

    try:
        r = requests.post(url, headers=headers, json=payload_completo, timeout=12)
        if r.status_code == 200:
            return True, "OK (completo)"
        
        # Tentativa 2: Se falhou por causa das colunas, manda o modo mínimo de emergência
        payload_minimo = {
            "parent": {"database_id": NOTION_DATABASE_ID},
            "properties": {
                "Nome": {"title": [{"text": {"content": nome}}]}
            },
            "children": [{
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": texto[:1900]}}]
                }
            }]
        }
        
        r2 = requests.post(url, headers=headers, json=payload_minimo, timeout=12)
        if r2.status_code == 200:
            return True, "OK (modo mínimo de emergência)"
        
        return False, f"Erro Notion: {r2.text[:400]}"
        
    except Exception as e:
        return False, f"Exceção: {str(e)}"

# ================= GOOGLE SHEETS (GOLEIRO) =================
def api_sheets(payload):
    try:
        r = requests.post(URL_BACKEND_GOOGLE, json=payload, timeout=12)
        return r.status_code in [200, 201] and (r.json().get("status") == "sucesso" if r.text else True)
    except:
        return False

# ================= INICIALIZAÇÃO =================
def init_state():
    if "init" not in st.session_state:
        st.session_state.init = True
        st.session_state.modo_admin = False
        st.session_state.pedido_enviado = False
        st.session_state.ficha_recente = ""
        st.session_state.msg_status = ""
        limpar_formulario()
        
        st.session_state.planos = {
            "NIO Fibra": ["500 Mega - R$ 100,00", "800 Mega - R$ 135,00"],
            "TIM Ultrafibra": ["600 Mega - R$ 119,99", "800 Mega - R$ 129,99"],
            "Vivo": ["Padrão"],
            "Claro": ["Padrão"]
        }

# ================= TELA DO CLIENTE =================
def tela_cliente():
    # Feedback pós-envio (antes de desenhar os inputs)
    if st.session_state.pedido_enviado:
        limpar_formulario()
        st.markdown(f'<div class="{st.session_state.msg_status.split("|")[0]}">{st.session_state.msg_status.split("|")[1]}</div>', unsafe_allow_html=True)
        
        link = f"https://api.whatsapp.com/send?text={urllib.parse.quote_plus(st.session_state.ficha_recente)}"
        st.markdown(f'<a href="{link}" target="_blank" class="btn-wpp">📲 Enviar Ficha pelo WhatsApp agora</a>', unsafe_allow_html=True)
        st.markdown("---")
        
        st.session_state.pedido_enviado = False
        st.session_state.msg_status = ""

    st.markdown('<div class="security-badge">🔒 AMBIENTE SEGURO | Seus dados são protegidos e tratados conforme a LGPD</div>', unsafe_allow_html=True)
    
    st.title("Cadastro de Serviço")
    st.caption("Preencha os dados abaixo. É rápido e seguro.")
    st.markdown("---")

    # 1. Dados Pessoais
    st.subheader("1. Dados Pessoais")
    st.text_input("Nome Completo *", key="f_nome")
    
    c1, c2 = st.columns(2)
    c1.text_input("CPF *", key="f_cpf", placeholder="Somente números")
    c2.text_input("Data de Nascimento *", key="f_nasc", placeholder="DD/MM/AAAA")
    
    st.text_input("Nome completo da Mãe *", key="f_mae")
    st.text_input("E-mail", key="f_email", placeholder="opcional")

    c3, c4 = st.columns(2)
    c3.text_input("WhatsApp Principal *", key="f_w1", placeholder="(XX) 9XXXX-XXXX")
    c4.text_input("2º Contato (opcional)", key="f_w2")

    st.markdown("---")

    # 2. Endereço
    st.subheader("2. Endereço de Instalação")
    c5, c6 = st.columns([3, 1])
    with c5:
        st.text_input("CEP *", key="f_cep", placeholder="Somente números")
    with c6:
        st.write("")  # espaçamento
        if st.button("🔍 Buscar"):
            res = buscar_cep(st.session_state.f_cep)
            if res == "erro_conexao":
                st.error("Falha de conexão ao buscar CEP")
            elif res:
                st.session_state.f_rua = res.get("logradouro", "")
                st.session_state.f_bairro = res.get("bairro", "")
                st.rerun()
            else:
                st.error("CEP não encontrado")

    st.text_input("Rua / Logradouro *", key="f_rua")
    c7, c8 = st.columns([1, 2])
    c7.text_input("Número *", key="f_num")
    c8.text_input("Bairro *", key="f_bairro")

    st.markdown("---")

    # 3. Serviço
    st.subheader("3. Serviço")
    ops = ["Selecione"] + list(st.session_state.planos.keys())
    operadora = st.selectbox("Operadora *", ops)
    
    planos = st.session_state.planos.get(operadora, ["Selecione a operadora"]) if operadora != "Selecione" else ["Selecione a operadora"]
    plano = st.selectbox("Plano *", planos)
    
    st.write("")
    
    # BOTÃO FINAL
    if st.button("✅ ENVIAR SOLICITAÇÃO", type="primary"):
        s = st.session_state
        
        # Validações
        if not all([s.f_nome, s.f_cpf, s.f_nasc, s.f_mae, s.f_w1, s.f_cep, s.f_rua, s.f_num, s.f_bairro]) or operadora == "Selecione" or "Selecione" in plano:
            st.error("Preencha todos os campos obrigatórios (*)")
        elif not validar_cpf(s.f_cpf):
            st.error("CPF inválido")
        else:
            protocolo = gerar_protocolo()
            
            dados = {
                "nome": s.f_nome.strip(),
                "cpf": s.f_cpf.strip(),
                "nasc": s.f_nasc.strip(),
                "mae": s.f_mae.strip(),
                "email": s.f_email.strip(),
                "w1": s.f_w1.strip(),
                "w2": s.f_w2.strip(),
                "cep": s.f_cep.strip(),
                "rua": s.f_rua.strip(),
                "num": s.f_num.strip(),
                "bairro": s.f_bairro.strip(),
                "operadora": operadora,
                "plano": plano,
                "protocolo": protocolo
            }
            
            ficha = formatar_ficha(dados)
            
            # Payload Sheets
            payload = {
                "tipo": "venda",
                "acao": "inserir",
                "protocolo": protocolo,
                "nome": blindar(dados["nome"]),
                "cpf": dados["cpf"],
                "mae": blindar(dados["mae"]),
                "nascimento": blindar(dados["nasc"]),
                "email": blindar(dados["email"]),
                "whats1": blindar(dados["w1"]),
                "whats2": blindar(dados["w2"]),
                "cep": blindar(dados["cep"]),
                "rua": blindar(dados["rua"]),
                "numero": blindar(dados["num"]),
                "bairro": blindar(dados["bairro"]),
                "operadora": operadora,
                "plano": plano,
                "status": "Nova",
                "obs": "",
                "vendedor": "Cliente Autônomo"
            }

            with st.spinner("Registrando de forma segura nos sistemas..."):
                sheets_ok = api_sheets(payload)
                # Chamando a função infalível do Notion
                notion_ok, notion_msg = criar_notion(dados, ficha)

            # Feedback resiliente
            if sheets_ok and notion_ok:
                status = "alert-ok|✅ Solicitação enviada com sucesso para Notion e Google Sheets!"
            elif sheets_ok:
                status = "alert-warn|⚠️ Salvo no Google Sheets. Notion apresentou instabilidade (mas a venda está segura)."
            elif notion_ok:
                status = "alert-warn|⚠️ Salvo no Notion. Google Sheets apresentou instabilidade (mas a venda está segura)."
            else:
                status = "alert-err|❌ Ambos os sistemas instáveis no momento. Use o botão do WhatsApp abaixo para garantir o envio."

            st.session_state.pedido_enviado = True
            st.session_state.ficha_recente = ficha
            st.session_state.msg_status = status
            st.rerun()

# ================= ADMIN SIMPLES =================
def tela_admin():
    st.subheader("Painel Interno")
    if st.button("Sair do Admin"):
        st.session_state.modo_admin = False
        st.rerun()
    
    st.info("Aqui você pode adicionar mais tarde a leitura do CRM do Sheets se quiser.")
    st.write("Por enquanto o foco é o fluxo de venda nunca parar.")

# ================= MAIN =================
def main():
    init_state()
    aplicar_css()

    with st.sidebar:
        st.markdown("### 🔒 Área Restrita")
        if not st.session_state.modo_admin:
            with st.expander("Login Consultor"):
                senha = st.text_input("Senha", type="password", key="senha_admin")
                if st.button("Entrar"):
                    if senha == SENHA_MESTRE:
                        st.session_state.modo_admin = True
                        st.rerun()
                    else:
                        st.error("Senha incorreta")
        else:
            st.success("Logado como Admin")

    if st.session_state.modo_admin:
        tela_admin()
    else:
        tela_cliente()

if __name__ == "__main__":
    main()
