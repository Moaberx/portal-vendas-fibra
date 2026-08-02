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
    page_title="Portal Fibra Seguro",
    page_icon="🔒",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ================= CSS =================
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
    .stButton>button {
        background: #2563EB; color: white !important; border: none; border-radius: 10px;
        width: 100%; padding: 14px; font-weight: 600;
    }
    .stButton>button:hover { background: #1D4ED8; }
    .security-badge {
        background: #ECFDF5; border: 1px solid #10B981; color: #065F46;
        padding: 14px; border-radius: 10px; font-weight: 600; text-align: center; margin-bottom: 20px;
    }
    .btn-wpp {
        display: block; background: #25D366; color: white !important; text-align: center;
        border-radius: 10px; padding: 16px; font-weight: 700; text-decoration: none; margin-top: 12px;
    }
    .alert-ok { background: #ECFDF5; border: 1px solid #A7F3D0; color: #065F46; padding: 14px; border-radius: 10px; font-weight: 600; margin: 10px 0; }
    .alert-warn { background: #FFFBEB; border: 1px solid #FDE68A; color: #92400E; padding: 14px; border-radius: 10px; font-weight: 600; margin: 10px 0; }
    .alert-err { background: #FEF2F2; border: 1px solid #FECACA; color: #991B1B; padding: 14px; border-radius: 10px; font-weight: 600; margin: 10px 0; }
    .cred-box {
        background: #F1F5F9; border: 1px solid #CBD5E1; border-radius: 10px;
        padding: 16px; margin-bottom: 12px; font-size: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

# ================= FUNÇÕES BASE =================
def gerar_protocolo():
    return f"PAP_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def blindar(texto):
    if not isinstance(texto, str): return texto
    t = texto.strip()
    return f"'{t}" if t.startswith(('=', '+', '-', '@')) else t

def limpar_formulario():
    keys = ['f_nome', 'f_cpf', 'f_nasc', 'f_mae', 'f_email', 'f_w1', 'f_w2',
            'f_cep', 'f_rua', 'f_num', 'f_bairro', 'f_extra1', 'f_extra2', 'f_extra3']
    for k in keys:
        if k in st.session_state:
            st.session_state[k] = ""

def validar_cpf(doc):
    d = re.sub(r'[^0-9]', '', str(doc))
    if len(d) != 11 or d == d[0] * 11: return False
    for i in range(9, 11):
        s = sum(int(d[n]) * ((i + 1) - n) for n in range(i))
        if ((s * 10) % 11) % 10 != int(d[i]): return False
    return True

def buscar_cep(cep):
    cep = re.sub(r'[^0-9]', '', str(cep))
    if len(cep) != 8: return None
    try:
        r = requests.get(f"https://viacep.com.br/ws/{cep}/json/", timeout=5)
        data = r.json()
        return data if r.status_code == 200 and "erro" not in data else None
    except:
        return "erro_conexao"

def formatar_ficha(d):
    extras = ""
    for i in range(1, 4):
        if d.get(f'extra{i}'):
            extras += f"\nExtra {i}: {d[f'extra{i}']}"
    
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
Plano: {d['plano']}{extras}

Protocolo: {d.get('protocolo', '')}"""

# ================= NOTION =================
def criar_notion(titulo, texto, is_anotacao=False):
    if not NOTION_TOKEN or not NOTION_DATABASE_ID:
        return False, "Notion não configurado"

    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    # Prefixo claro para anotações
    if is_anotacao:
        titulo_final = f"📝 ANOTAÇÃO - {titulo}"
    else:
        titulo_final = titulo

    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Nome": {"title": [{"text": {"content": titulo_final[:100]}}]}
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
        r = requests.post(url, headers=headers, json=payload, timeout=12)
        if r.status_code == 200:
            return True, "OK"
        return False, r.text[:300]
    except Exception as e:
        return False, str(e)

def api_sheets(payload):
    try:
        r = requests.post(URL_BACKEND_GOOGLE, json=payload, timeout=12)
        return r.status_code in [200, 201]
    except:
        return False

# ================= ESTADO =================
def init_state():
    if "init" not in st.session_state:
        st.session_state.init = True
        st.session_state.modo_admin = False
        st.session_state.pedido_enviado = False
        st.session_state.ficha_recente = ""
        st.session_state.msg_status = ""
        
        # 3 campos extras configuráveis
        st.session_state.campos_extras = {
            "extra1": {"ativo": False, "nome": "Campo Extra 1", "obrigatorio": False},
            "extra2": {"ativo": False, "nome": "Campo Extra 2", "obrigatorio": False},
            "extra3": {"ativo": False, "nome": "Campo Extra 3", "obrigatorio": False},
        }
        
        # Links úteis (já com os que você passou)
        st.session_state.links_uteis = [
            {
                "nome": "DFV | Nio (Power BI)",
                "url": "https://app.powerbi.com/view?r=eyJrIjoiOGE5ZGI4ZjktN2NmMS00ZGI1LTkwZDItNTI1OWFkMTQ5ZWJhIiwidCI6Ijg1YjI4NDIxLWQ0NWEtNGIwNy04ODlkLTI0YjUyOGM3ZjI1MCJ9",
                "login": "PARCEIRO",
                "senha1": "6566",
                "senha2": "7791"
            },
            {
                "nome": "DFV Tim (sem senha)",
                "url": "https://app.powerbi.com/view?r=eyJrIjoiODgyZDdiMTItOTM1MS00ZGFkLTkyZTktOTg5ZmJjNjc0OTViIiwidCI6ImI1MmJhNGIzLWM0MTEtNGQxNi04Yzc2LTAwNDg5YzBhMjA1YSJ9",
                "login": "",
                "senha1": "",
                "senha2": ""
            }
        ]
        
        st.session_state.planos = {
            "NIO Fibra": ["500 Mega - R$ 100,00", "800 Mega - R$ 135,00"],
            "TIM Ultrafibra": ["600 Mega - R$ 119,99", "800 Mega - R$ 129,99"],
            "Vivo": ["Padrão"],
            "Claro": ["Padrão"]
        }
        
        limpar_formulario()

# ================= TELA CLIENTE =================
def tela_cliente():
    if st.session_state.pedido_enviado:
        limpar_formulario()
        tipo, msg = st.session_state.msg_status.split("|", 1)
        st.markdown(f'<div class="{tipo}">{msg}</div>', unsafe_allow_html=True)
        
        link = f"https://api.whatsapp.com/send?text={urllib.parse.quote_plus(st.session_state.ficha_recente)}"
        st.markdown(f'<a href="{link}" target="_blank" class="btn-wpp">📲 Enviar Ficha pelo WhatsApp</a>', unsafe_allow_html=True)
        st.markdown("---")
        st.session_state.pedido_enviado = False

    st.markdown('<div class="security-badge">🔒 AMBIENTE SEGURO | Dados protegidos conforme LGPD</div>', unsafe_allow_html=True)
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
    st.text_input("E-mail", key="f_email")

    c3, c4 = st.columns(2)
    c3.text_input("WhatsApp Principal *", key="f_w1")
    c4.text_input("2º Contato (opcional)", key="f_w2")

    st.markdown("---")

    # 2. Endereço
    st.subheader("2. Endereço de Instalação")
    c5, c6 = st.columns([3, 1])
    c5.text_input("CEP *", key="f_cep", placeholder="Somente números")
    with c6:
        st.write("")
        if st.button("🔍 Buscar"):
            res = buscar_cep(st.session_state.f_cep)
            if res == "erro_conexao":
                st.error("Falha de conexão")
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

    # 3. Serviço + Extras
    st.subheader("3. Serviço")
    ops = ["Selecione"] + list(st.session_state.planos.keys())
    operadora = st.selectbox("Operadora *", ops)
    
    planos = st.session_state.planos.get(operadora, ["Selecione a operadora"]) if operadora != "Selecione" else ["Selecione a operadora"]
    plano = st.selectbox("Plano *", planos)

    # Campos extras dinâmicos
    for i in range(1, 4):
        cfg = st.session_state.campos_extras[f"extra{i}"]
        if cfg["ativo"]:
            obrig = " *" if cfg["obrigatorio"] else ""
            st.text_input(f"{cfg['nome']}{obrig}", key=f"f_extra{i}")

    st.write("")
    
    if st.button("✅ ENVIAR SOLICITAÇÃO", type="primary"):
        s = st.session_state
        
        # Validação básica
        obrigatorios_ok = all([s.f_nome, s.f_cpf, s.f_nasc, s.f_mae, s.f_w1, s.f_cep, s.f_rua, s.f_num, s.f_bairro])
        if not obrigatorios_ok or operadora == "Selecione" or "Selecione" in str(plano):
            st.error("Preencha todos os campos obrigatórios (*)")
        elif not validar_cpf(s.f_cpf):
            st.error("CPF inválido")
        else:
            # Valida extras obrigatórios
            falhou_extra = False
            for i in range(1, 4):
                cfg = st.session_state.campos_extras[f"extra{i}"]
                if cfg["ativo"] and cfg["obrigatorio"] and not s.get(f"f_extra{i}"):
                    st.error(f"Preencha o campo: {cfg['nome']}")
                    falhou_extra = True
            
            if not falhou_extra:
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
                    "protocolo": protocolo,
                    "extra1": s.get("f_extra1", ""),
                    "extra2": s.get("f_extra2", ""),
                    "extra3": s.get("f_extra3", ""),
                }
                
                ficha = formatar_ficha(dados)
                
                payload = {
                    "tipo": "venda", "acao": "inserir", "protocolo": protocolo,
                    "nome": blindar(dados["nome"]), "cpf": dados["cpf"],
                    "mae": blindar(dados["mae"]), "nascimento": blindar(dados["nasc"]),
                    "email": blindar(dados["email"]), "whats1": blindar(dados["w1"]),
                    "whats2": blindar(dados["w2"]), "cep": blindar(dados["cep"]),
                    "rua": blindar(dados["rua"]), "numero": blindar(dados["num"]),
                    "bairro": blindar(dados["bairro"]), "operadora": operadora,
                    "plano": plano, "status": "Nova", "obs": "",
                    "vendedor": "Cliente Autônomo",
                    "extra1": blindar(dados["extra1"]),
                    "extra2": blindar(dados["extra2"]),
                    "extra3": blindar(dados["extra3"]),
                }

                with st.spinner("Registrando nos sistemas..."):
                    sheets_ok = api_sheets(payload)
                    notion_ok, _ = criar_notion(f"{dados['nome']} - {operadora}", ficha, is_anotacao=False)

                if sheets_ok and notion_ok:
                    status = "alert-ok|✅ Solicitação enviada com sucesso!"
                elif sheets_ok or notion_ok:
                    status = "alert-warn|⚠️ Salvo em um dos sistemas. A venda está garantida."
                else:
                    status = "alert-err|❌ Sistemas instáveis. Use o WhatsApp abaixo."

                st.session_state.pedido_enviado = True
                st.session_state.ficha_recente = ficha
                st.session_state.msg_status = status
                st.rerun()

# ================= TELA ADMIN =================
def tela_admin():
    st.title("Painel Administrativo")
    
    if st.button("🚪 Sair do Admin"):
        st.session_state.modo_admin = False
        st.rerun()

    tab1, tab2, tab3, tab4 = st.tabs(["📝 Anotações Livres", "⚙️ Campos Extras", "🔗 Links Úteis", "🔑 Credenciais DFV"])

    # --- TAB 1: ANOTAÇÕES LIVRES ---
    with tab1:
        st.subheader("Anotações / Leads Livres no Notion")
        st.caption("Crie blocos de notas livres. Eles aparecem no Notion com o prefixo 📝 ANOTAÇÃO para não misturar com vendas.")
        
        titulo = st.text_input("Título da anotação (opcional)", placeholder="Ex: Retornar João - Bairro X")
        conteudo = st.text_area("Anotação livre (pode escrever qualquer coisa)", height=150)
        
        if st.button("💾 Salvar Anotação no Notion"):
            if not conteudo.strip():
                st.error("Escreva alguma coisa na anotação.")
            else:
                with st.spinner("Salvando..."):
                    ok, msg = criar_notion(titulo or "Anotação livre", conteudo, is_anotacao=True)
                    if ok:
                        st.success("✅ Anotação salva no Notion com sucesso!")
                    else:
                        st.error(f"Erro: {msg}")

    # --- TAB 2: CAMPOS EXTRAS ---
    with tab2:
        st.subheader("Configurar 3 Campos Extras do Formulário")
        st.caption("Ative e renomeie os campos. Eles aparecem automaticamente no formulário de venda.")
        
        for i in range(1, 4):
            key = f"extra{i}"
            cfg = st.session_state.campos_extras[key]
            
            st.markdown(f"**Campo Extra {i}**")
            c1, c2, c3 = st.columns([1, 2, 1])
            ativo = c1.checkbox("Ativo", value=cfg["ativo"], key=f"atv_{i}")
            nome = c2.text_input("Nome do campo", value=cfg["nome"], key=f"nm_{i}")
            obrig = c3.checkbox("Obrigatório", value=cfg["obrigatorio"], key=f"ob_{i}")
            
            st.session_state.campos_extras[key] = {
                "ativo": ativo,
                "nome": nome,
                "obrigatorio": obrig
            }
            st.markdown("---")
        
        st.success("Alterações salvas automaticamente nesta sessão.")

    # --- TAB 3: LINKS ÚTEIS ---
    with tab3:
        st.subheader("Links Úteis")
        
        for idx, link in enumerate(st.session_state.links_uteis):
            with st.expander(f"🔗 {link['nome']}", expanded=False):
                st.markdown(f"**Link:** [{link['url']}]({link['url']})")
                if link.get("login"):
                    st.markdown(f"**Login:** `{link['login']}`")
                    st.markdown(f"**Senha 1:** `{link['senha1']}`")
                    st.markdown(f"**Senha 2:** `{link['senha2']}`")
                
                if st.button("🗑️ Remover", key=f"rm_link_{idx}"):
                    st.session_state.links_uteis.pop(idx)
                    st.rerun()
        
        st.markdown("---")
        st.subheader("Adicionar novo link")
        novo_nome = st.text_input("Nome do link")
        novo_url = st.text_input("URL")
        novo_login = st.text_input("Login (opcional)")
        c1, c2 = st.columns(2)
        nova_s1 = c1.text_input("Senha 1 (opcional)")
        nova_s2 = c2.text_input("Senha 2 (opcional)")
        
        if st.button("➕ Adicionar Link"):
            if novo_nome and novo_url:
                st.session_state.links_uteis.append({
                    "nome": novo_nome,
                    "url": novo_url,
                    "login": novo_login,
                    "senha1": nova_s1,
                    "senha2": nova_s2
                })
                st.success("Link adicionado!")
                st.rerun()
            else:
                st.error("Nome e URL são obrigatórios.")

    # --- TAB 4: CREDENCIAIS DFV ---
    with tab4:
        st.subheader("Credenciais DFV | Nio")
        
        st.markdown("""
        <div class="cred-box">
            <b>DFV | Nio (Power BI)</b><br><br>
            <b>Login:</b> PARCEIRO<br>
            <b>Senha 1:</b> 6566<br>
            <b>Senha 2:</b> 7791<br><br>
            <a href="https://app.powerbi.com/view?r=eyJrIjoiOGE5ZGI4ZjktN2NmMS00ZGI1LTkwZDItNTI1OWFkMTQ5ZWJhIiwidCI6Ijg1YjI4NDIxLWQ0NWEtNGIwNy04ODlkLTI0YjUyOGM3ZjI1MCJ9" target="_blank">Abrir Power BI Nio</a>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="cred-box">
            <b>DFV Tim (sem senha)</b><br><br>
            <a href="https://app.powerbi.com/view?r=eyJrIjoiODgyZDdiMTItOTM1MS00ZGFkLTkyZTktOTg5ZmJjNjc0OTViIiwidCI6ImI1MmJhNGIzLWM0MTEtNGQxNi04Yzc2LTAwNDg5YzBhMjA1YSJ9" target="_blank">Abrir Power BI Tim</a>
        </div>
        """, unsafe_allow_html=True)

# ================= MAIN =================
def main():
    init_state()
    aplicar_css()

    with st.sidebar:
        st.markdown("### 🔒 Área Restrita")
        if not st.session_state.modo_admin:
            with st.expander("Login do Consultor"):
                senha = st.text_input("Senha", type="password")
                if st.button("Entrar"):
                    if senha == SENHA_MESTRE:
                        st.session_state.modo_admin = True
                        st.rerun()
                    else:
                        st.error("Senha incorreta")
        else:
            st.success("Você está no modo Admin")

    if st.session_state.modo_admin:
        tela_admin()
    else:
        tela_cliente()

if __name__ == "__main__":
    main()
