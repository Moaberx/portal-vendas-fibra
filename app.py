import streamlit as st
import requests
import re
import urllib.parse
from datetime import datetime

# ================= CONFIGURAÇÕES E CONSTANTES =================
URL_BACKEND_GOOGLE = "https://script.google.com/macros/s/AKfycbyTF3qUfRvMKh5JcyxJ_rbo8fSc04n24s8y8X7wtS0nP1qVjv2nUbpQLZHmAWmpXhKJ/exec"

try:
    SENHA_MESTRE_GESTAO = st.secrets.get("senha_mestre_gestao", "PAP_SECRETO_2026")
    NOTION_TOKEN = st.secrets.get("notion_token")
    NOTION_DATABASE_ID = st.secrets.get("notion_database_id")
except Exception:
    SENHA_MESTRE_GESTAO = "PAP_SECRETO_2026"
    NOTION_TOKEN = None
    NOTION_DATABASE_ID = None

st.set_page_config(page_title="Cadastro de Serviço Seguro", page_icon="🔒", layout="centered")

# ================= ESTILIZAÇÃO (TEMA CLARO E CONFIÁVEL) =================
def aplicar_css_claro():
    st.markdown("""
        <style>
        /* Fundo e textos gerais */
        .stApp { background-color: #F8FAFC; color: #1E293B; font-family: 'Inter', 'Segoe UI', sans-serif; }
        h1, h2, h3, label, p, span { color: #0F172A !important; font-weight: 500; }
        hr { border-color: #E2E8F0; }
        
        /* Inputs limpos e modernos */
        .stTextInput>div>div>input, .stSelectbox>div>div>select, .stTextArea>div>div>textarea { 
            background-color: #FFFFFF !important; color: #1E293B !important; 
            border: 1px solid #CBD5E1 !important; border-radius: 8px !important; padding: 12px !important; 
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }
        .stTextInput>div>div>input:focus { border-color: #2563EB !important; box-shadow: 0 0 0 1px #2563EB !important; }
        
        /* Botões padronizados */
        .stButton>button { 
            background-color: #2563EB; color: #FFFFFF !important; border: none; 
            border-radius: 8px; width: 100%; padding: 12px; font-weight: 600; transition: 0.3s;
        }
        .stButton>button:hover { background-color: #1D4ED8; transform: translateY(-1px); }
        
        /* Botão específico do WhatsApp */
        .btn-wpp {
            display: block; background-color: #25D366; color: #FFFFFF !important; text-align: center;
            border-radius: 8px; width: 100%; padding: 14px; font-weight: bold; text-decoration: none; margin-top: 15px;
        }
        .btn-wpp:hover { background-color: #1ea952; }

        /* Selo de Segurança Fake */
        .security-badge {
            display: flex; align-items: center; justify-content: center; gap: 10px;
            background-color: #ECFDF5; border: 1px solid #10B981; color: #065F46;
            padding: 15px; border-radius: 8px; font-weight: 600; font-size: 15px; margin-bottom: 25px;
        }
        
        /* Tabela CRM Admin */
        .crm-row { background: #FFFFFF; border-left: 4px solid #CBD5E1; padding: 15px; margin-bottom: 10px; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .crm-row.atencao { border-left-color: #EF4444; }
        .crm-row.finalizada { border-left-color: #10B981; }
        </style>
    """, unsafe_allow_html=True)

# ================= FUNÇÕES AUXILIARES =================
def gerar_chave_id(prefixo):
    return f"{prefixo}_{datetime.now().strftime('%H%M%S%f')}"

def blindar_texto(texto):
    if not isinstance(texto, str): return texto
    texto_limpo = texto.strip()
    if texto_limpo.startswith(('=', '+', '-', '@')): return f"'{texto_limpo}"
    return texto_limpo

def limpar_formulario():
    for key in ['f_nome', 'f_cpf', 'f_nasc', 'f_mae', 'f_w1', 'f_w2', 'f_email', 'f_cep', 'f_rua', 'f_num', 'f_bairro', 'f_obs']:
        st.session_state[key] = ""

# ================= VALIDAÇÕES =================
def validar_cpf_cnpj(documento):
    doc = re.sub(r'[^0-9]', '', str(documento))
    if len(doc) == 11: 
        if doc == doc[0] * 11: return False
        for i in range(9, 11):
            val = sum((int(doc[num]) * ((i + 1) - num) for num in range(0, i)))
            if ((val * 10) % 11) % 10 != int(doc[i]): return False
        return True
    return False

def buscar_cep(cep):
    cep_limpo = re.sub(r'[^0-9]', '', str(cep))
    if len(cep_limpo) == 8:
        try:
            r = requests.get(f"https://viacep.com.br/ws/{cep_limpo}/json/", timeout=5)
            if r.status_code == 200 and "erro" not in r.json():
                return r.json()
        except requests.exceptions.RequestException:
            return "erro_conexao"
    return None

# ================= INTEGRAÇÕES (APIs) =================

# ---> O CAMISA 10 (NOTION)
def criar_ficha_notion(dados, texto_ficha):
    if not NOTION_TOKEN or not NOTION_DATABASE_ID: 
        return False, "Notion não configurado nas Secrets."
    
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}", 
        "Content-Type": "application/json", 
        "Notion-Version": "2022-06-28"
    }
    
    # Limpa o telefone para o padrão do Notion
    telefone_limpo = re.sub(r'[^0-9+]', '', str(dados.get('w1', '')))[:20]
    
    data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Nome": {"title": [{"text": {"content": str(dados.get('nome', ''))[:100]}}]},
            "Status": {"status": {"name": "Nova"}},  # Ajuste o nome do status conforme seu Notion
            "Telefone": {"phone_number": telefone_limpo},
            "Data": {"date": {"start": datetime.now().strftime("%Y-%m-%d")}}
        },
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": texto_ficha}}]
                }
            }
        ]
    }
        
    try:
        r = requests.post(url, headers=headers, json=data, timeout=10)
        return (True, "Sucesso") if r.status_code == 200 else (False, f"Erro: {r.text}")
    except Exception as e:
        return False, str(e)

# ---> O GOLEIRO (GOOGLE SHEETS)
def api_google(payload):
    try:
        r = requests.post(URL_BACKEND_GOOGLE, json=payload, timeout=15)
        return r.json() if r.status_code in [200, 201] else None
    except requests.exceptions.Timeout:
        return {"status": "erro", "msg": "Tempo esgotado."}
    except Exception as e:
        return {"status": "erro", "msg": str(e)}

def fetch_crm():
    res = api_google({"acao": "ler", "senha_api": SENHA_MESTRE_GESTAO, "aba_alvo": "VENDAS"})
    if res and res.get("status") == "sucesso":
        st.session_state['crm_dados'] = res.get("dados", [])

def formatar_ficha_texto(d):
    return (f"📄 *NOVO CADASTRO*\n\n"
            f"👤 *CLIENTE*\nNome: {d['nome']}\nCPF: {d['cpf']}\nNascimento: {d['nasc']}\nMãe: {d['mae']}\nEmail: {d['email']}\n\n"
            f"📞 *CONTATO*\nWhatsApp 1: {d['w1']}\nWhatsApp 2: {d.get('w2', 'Não informado')}\n\n"
            f"📍 *ENDEREÇO*\nCEP: {d['cep']}\n{d['rua']}, Nº {d['num']} - {d['bairro']}\n\n"
            f"📶 *SERVIÇO*\nOperadora: {d['operadora']}\nPlano: {d['plano']}")

# ================= INICIALIZAÇÃO DE ESTADO =================
def inicializar_estado():
    if 'init' not in st.session_state:
        st.session_state['init'] = True
        st.session_state['modo_admin_ativo'] = False
        st.session_state['crm_dados'] = []
        
        # Variáveis do formulário reativas
        limpar_formulario()
        
        st.session_state['planos_dinamicos'] = {
            "NIO Fibra": ["500 Mega - R$ 100,00", "800 Mega - R$ 135,00"],
            "TIM Ultrafibra": ["600 Mega - R$ 119,99", "800 Mega - R$ 129,99"],
            "Vivo": ["Padrão"],
            "Claro": ["Padrão"]
        }

# ================= MÓDULO: CLIENTE (FORMULÁRIO LIMPO) =================
def modulo_cliente():
    st.markdown('<div class="security-badge">🔒 AMBIENTE SEGURO | Seus dados são criptografados de ponta a ponta e protegidos pela LGPD.</div>', unsafe_allow_html=True)
    st.title("Cadastro de Serviços")
    st.markdown("Preencha os dados abaixo para darmos continuidade ao seu pedido.")
    st.markdown("---")

    # --- DADOS PESSOAIS ---
    st.subheader("1. Dados Pessoais")
    st.text_input("Nome Completo", key="f_nome")
    
    col_cpf, col_nasc = st.columns(2)
    with col_cpf:
        st.text_input("CPF", key="f_cpf", placeholder="Apenas números")
    with col_nasc:
        st.text_input("Data de Nascimento", key="f_nasc", placeholder="DD/MM/AAAA")
        
    st.text_input("Nome completo da Mãe", key="f_mae")
    st.text_input("Email", key="f_email", placeholder="seuemail@exemplo.com")

    col_w1, col_w2 = st.columns(2)
    with col_w1:
        st.text_input("WhatsApp Principal", key="f_w1", placeholder="(XX) 9XXXX-XXXX")
    with col_w2:
        st.text_input("WhatsApp 2 (Opcional)", key="f_w2")

    st.markdown("---")

    # --- ENDEREÇO ---
    st.subheader("2. Endereço de Instalação")
    col_cep, col_btn_cep = st.columns([2, 1], vertical_alignment="bottom")
    
    with col_cep:
        st.text_input("CEP", key="f_cep", placeholder="Apenas números")
    with col_btn_cep:
        if st.button("🔍 Buscar CEP"):
            if st.session_state.f_cep:
                res_cep = buscar_cep(st.session_state.f_cep)
                if res_cep == "erro_conexao":
                    st.error("Falha de rede ao buscar CEP.")
                elif res_cep:
                    st.session_state.f_rua = res_cep.get("logradouro", "")
                    st.session_state.f_bairro = res_cep.get("bairro", "")
                    st.rerun()
                else:
                    st.error("CEP não localizado.")

    st.text_input("Rua / Logradouro", key="f_rua")
    col_num, col_bairro = st.columns([1, 2])
    with col_num:
        st.text_input("Número", key="f_num")
    with col_bairro:
        st.text_input("Bairro", key="f_bairro")

    st.markdown("---")

    # --- SERVIÇO ---
    st.subheader("3. Serviço Escolhido")
    ops = ["Selecione"] + list(st.session_state['planos_dinamicos'].keys())
    operadora = st.selectbox("Operadora", ops)
    
    planos_da_op = st.session_state['planos_dinamicos'].get(operadora, []) if operadora != "Selecione" else ["Selecione a operadora primeiro"]
    plano = st.selectbox("Plano Solicitado", planos_da_op)
    
    st.markdown("<br>", unsafe_allow_html=True)

    # --- ENVIO ---
    if st.button("✅ ENVIAR SOLICITAÇÃO"):
        s = st.session_state
        if not s.f_nome or not s.f_cpf or not s.f_nasc or not s.f_mae or not s.f_w1 or not s.f_cep or operadora == "Selecione":
            st.error("⚠️ Por favor, preencha todos os campos obrigatórios.")
        elif not validar_cpf_cnpj(s.f_cpf): 
            st.error("⚠️ O CPF informado é inválido.")
        else:
            protocolo = gerar_chave_id("PAP")
            dados_resumo = {
                "nome": s.f_nome, "cpf": s.f_cpf, "nasc": s.f_nasc, "mae": s.f_mae,
                "w1": s.f_w1, "w2": s.f_w2, "email": s.f_email, "cep": s.f_cep,
                "rua": s.f_rua, "num": s.f_num, "bairro": s.f_bairro, "operadora": operadora, "plano": plano
            }
            
            # Payload para o Sheets
            linha_dados = {
                "tipo": "venda", "acao": "inserir", "protocolo": protocolo,
                "nome": blindar_texto(s.f_nome), "cpf": s.f_cpf, "mae": blindar_texto(s.f_mae), "nascimento": blindar_texto(s.f_nasc),
                "email": blindar_texto(s.f_email), "whats1": blindar_texto(s.f_w1), "whats2": blindar_texto(s.f_w2),
                "cep": blindar_texto(s.f_cep), "rua": blindar_texto(s.f_rua), "numero": blindar_texto(s.f_num), 
                "bairro": blindar_texto(s.f_bairro), "operadora": operadora, "plano": plano, 
                "status": "Nova", "obs": "", "vendedor": "Cliente Autônomo"
            }

            with st.spinner("Processando dados de forma segura..."):
                # Goleiro pega a bola
                resposta_sheets = api_google(linha_dados)
                
                # Camisa 10 cria a jogada (Envia pra API do Notion)
                ficha = formatar_ficha_texto(dados_resumo)
                notion_ok, notion_msg = criar_ficha_notion(dados_resumo, ficha)
                
                if resposta_sheets and resposta_sheets.get('status') == 'sucesso':
                    limpar_formulario()
                    st.success("🎉 Solicitação enviada com sucesso! Nossos consultores entrarão em contato em breve.")
                    
                    if not notion_ok:
                        st.toast(f"Aviso Admin: Falha ao enviar para o Notion ({notion_msg})", icon="⚠️")
                    
                    # Se você quiser permitir que o cliente mande a ficha no WhatsApp
                    link_wpp = f"https://api.whatsapp.com/send?text={urllib.parse.quote_plus(ficha)}"
                    st.markdown(f'<a href="{link_wpp}" target="_blank" class="btn-wpp">💬 Falar com Especialista Agora</a>', unsafe_allow_html=True)
                else: 
                    st.error("Ocorreu um erro no servidor. Tente novamente mais tarde.")

# ================= MÓDULO: ADMIN (CRM) =================
def modulo_admin():
    st.subheader("Painel de Gestão Interna")
    if st.button("Sair do Painel Admin"):
        st.session_state['modo_admin_ativo'] = False
        st.rerun()

    if st.button("🔄 Sincronizar CRM (Sheets)"):
        with st.spinner("Atualizando base de dados..."): 
            fetch_crm()

    linhas = st.session_state['crm_dados'][1:] if len(st.session_state['crm_dados']) > 1 else []
    if not linhas:
        st.info("Nenhuma venda encontrada no CRM.")
        return

    for linha in reversed(linhas):
        while len(linha) < 23: linha.append("")
        prot, status_raw = linha[1], str(linha[19]).strip()
        cor_linha = "atencao" if status_raw.lower() == "atenção" else "finalizada" if status_raw.lower() == "instalada" else ""

        st.markdown(f'<div class="crm-row {cor_linha}">', unsafe_allow_html=True)
        c_info, c_act = st.columns([3, 2])
        with c_info:
            st.markdown(f"**{linha[2]}** ({linha[13]})") 
            st.caption(f"📱 {linha[6]} | 📦 {linha[14]}")
            st.caption(f"Mãe: {linha[4]} | Nasc: {linha[5]}")

        with c_act:
            opts_st = ["Nova", "Pendente", "Atenção", "Instalada", "Cancelada"]
            idx_st = opts_st.index(status_raw.capitalize()) if status_raw.capitalize() in opts_st else 0
            novo_st = st.selectbox("Status", opts_st, index=idx_st, key=f"st_{prot}")

            if st.button("Salvar Alteração", key=f"sv_{prot}"):
                linha[19] = novo_st
                payload = {"acao": "editar", "senha_api": SENHA_MESTRE_GESTAO, "id_busca": prot, "coluna_busca": 1, "novos_dados": linha}
                with st.spinner("Gravando..."):
                    if api_google(payload):
                        st.toast("Atualizado!")
                        fetch_crm()
                        st.rerun()
                    else:
                        st.error("Erro.")
        st.markdown('</div>', unsafe_allow_html=True)

# ================= EXECUÇÃO PRINCIPAL =================
def main():
    inicializar_estado()
    aplicar_css_claro()

    # --- MENU LATERAL (APENAS PARA LOGIN DO CONSULTOR) ---
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3592/3592869.png", width=60)
        st.markdown("### Área Restrita")
        
        if not st.session_state['modo_admin_ativo']:
            with st.expander("🔐 Login do Consultor"):
                senha = st.text_input("Senha de Acesso", type="password")
                if st.button("Entrar"):
                    if senha == SENHA_MESTRE_GESTAO:
                        st.session_state['modo_admin_ativo'] = True
                        fetch_crm()
                        st.rerun()
                    else: 
                        st.error("Credenciais inválidas.")
        else:
            st.success("Você está logado como Admin.")

    # --- CONTROLE DE ROTEAMENTO (TELA PRINCIPAL) ---
    if st.session_state['modo_admin_ativo']:
        modulo_admin()
    else:
        modulo_cliente()

if __name__ == "__main__":
    main()
