import streamlit as st
import requests
import json
import re
import urllib.parse
from datetime import datetime
from streamlit_local_storage import LocalStorage

# ================= SEGURANÇA E CONEXÕES =================
URL_BACKEND_GOOGLE = "https://script.google.com/macros/s/AKfycbyTF3qUfRvMKh5JcyxJ_rbo8fSc04n24s8y8X7wtS0nP1qVjv2nUbpQLZHmAWmpXhKJ/exec"

# As chaves NUNCA ficam no código. Se não houver secrets configurados, o acesso é bloqueado.
SENHA_MESTRE_GESTAO = st.secrets.get("senha_mestre_gestao")
NOTION_TOKEN = st.secrets.get("notion_token")
NOTION_DATABASE_ID = st.secrets.get("notion_database_id")

st.set_page_config(page_title="Portal de Vendas", page_icon="📶", layout="centered")
local_storage = LocalStorage()

# ================= ESTADO INICIAL =================
if 'init' not in st.session_state:
    st.session_state.update({
        'init': True,
        'aba_ativa': "📝 Nova Venda",
        'vendedor_atual': "Moabe",
        'rascunhos_locais': [],
        'crm_dados': [],
        'notion_leads': [],
        'modo_gestao_liberado': False,
        'form_venda_cache': {},
        'config_sistema': {
            "titulo_app": "Portal de Atendimento",
            "tema_cor": "#2563EB", # Azul confiável e limpo
            "campos_dinamicos": {
                "extra1": {"ativo": False, "nome": "Referência / Complemento", "obrig_operadoras": []},
                "extra2": {"ativo": False, "nome": "Campo Extra", "obrig_operadoras": []}
            }
        },
        'planos_dinamicos': {
            "NIO Fibra": {"500 Mega": 100.00, "800 Mega": 135.00},
            "TIM Ultrafibra": {"600 Mega": 119.99, "800 Mega": 129.99},
            "Vivo": {"Padrão": 0.00},
            "Claro": {"Padrão": 0.00}
        }
    })

# ================= FUNÇÕES ESSENCIAIS =================
def gerar_protocolo_seguro():
    # Prefixo de texto evita que o Google Sheets converta silenciosamente para objeto Data
    return f"ID-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

def gerar_chave_dinamica():
    return f"key_{datetime.now().timestamp()}"

def salvar_rascunhos_local():
    try:
        dados = {"rascunhos": st.session_state['rascunhos_locais']}
        local_storage.setItem("pap_rascunhos_v4", json.dumps(dados), key=gerar_chave_dinamica())
    except: pass

def carregar_memorias():
    try:
        rs = local_storage.getItem("pap_rascunhos_v4")
        if rs:
            dados = json.loads(rs) if isinstance(rs, str) else rs
            st.session_state['rascunhos_locais'] = dados.get('rascunhos', [])
    except: pass

if not st.session_state.get('memoria_carregada'):
    carregar_memorias()
    st.session_state['memoria_carregada'] = True

def validar_cpf_cnpj(documento):
    doc = re.sub(r'[^0-9]', '', str(documento))
    if len(doc) == 11:
        if doc == doc[0] * 11: return False
        for i in range(9, 11):
            val = sum(int(doc[num]) * ((i + 1) - num) for num in range(i))
            digito = ((val * 10) % 11) % 10
            if digito != int(doc[i]): return False
        return True
    if len(doc) == 14:
        if doc == doc[0] * 14: return False
        pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        soma1 = sum(int(doc[i]) * pesos1[i] for i in range(12))
        d1 = 11 - (soma1 % 11)
        d1 = 0 if d1 >= 10 else d1
        if d1 != int(doc[12]): return False
        soma2 = sum(int(doc[i]) * pesos2[i] for i in range(13))
        d2 = 11 - (soma2 % 11)
        d2 = 0 if d2 >= 10 else d2
        if d2 != int(doc[13]): return False
        return True
    return False

def buscar_cep(cep):
    cep_limpo = re.sub(r'[^0-9]', '', str(cep))
    if len(cep_limpo) == 8:
        try:
            r = requests.get(f"https://viacep.com.br/ws/{cep_limpo}/json/", timeout=4)
            if r.status_code == 200 and "erro" not in r.json():
                return r.json()
        except: pass
    return None

# ================= INTEGRAÇÕES (SHEETS E NOTION) =================
def api_google(payload):
    try:
        r = requests.post(URL_BACKEND_GOOGLE, data=json.dumps(payload), headers={"Content-Type": "application/json"}, timeout=12)
        return r.json() if r.status_code == 200 else None
    except: return None

def fetch_crm_sheets():
    if not SENHA_MESTRE_GESTAO: return False
    res = api_google({"acao": "ler", "senha_api": SENHA_MESTRE_GESTAO, "aba_alvo": "VENDAS"})
    if res and res.get("status") == "sucesso":
        st.session_state['crm_dados'] = res.get("dados", [])
        return True
    return False

def enviar_lead_notion(nome, telefone, observacoes):
    if not NOTION_TOKEN or not NOTION_DATABASE_ID: return False
    url = "https://api.notion.com/v1/pages"
    headers = {"Authorization": f"Bearer {NOTION_TOKEN}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}
    
    data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": nome}}]},
            "Telefone": {"rich_text": [{"text": {"content": telefone}}]},
            "Status": {"select": {"name": "Novo Lead"}}
        },
        "children": [{"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": observacoes}}]}}]
    }
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=8)
        return resp.status_code == 200
    except: return False

def consultar_leads_notion():
    if not NOTION_TOKEN or not NOTION_DATABASE_ID: return []
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    headers = {"Authorization": f"Bearer {NOTION_TOKEN}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}
    try:
        resp = requests.post(url, headers=headers, json={}, timeout=10)
        if resp.status_code == 200:
            resultados = []
            for page in resp.json().get('results', []):
                props = page['properties']
                id_page = page['id']
                nome = props.get('Name', {}).get('title', [{}])[0].get('plain_text', 'Sem Nome') if props.get('Name', {}).get('title') else 'Sem Nome'
                tel = props.get('Telefone', {}).get('rich_text', [{}])[0].get('plain_text', '') if props.get('Telefone', {}).get('rich_text') else ''
                status = props.get('Status', {}).get('select', {}).get('name', 'Indefinido') if props.get('Status', {}).get('select') else 'Indefinido'
                resultados.append({"id": id_page, "nome": nome, "telefone": tel, "status": status})
            return resultados
    except: pass
    return []

def atualizar_status_notion(page_id, novo_status):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    headers = {"Authorization": f"Bearer {NOTION_TOKEN}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}
    data = {"properties": {"Status": {"select": {"name": novo_status}}}}
    try:
        requests.patch(url, headers=headers, json=data, timeout=8)
    except: pass

# ================= UI E TEMA CLARO (LIGHT THEME) =================
cor_tema = st.session_state['config_sistema']['tema_cor']

st.markdown(f"""
    <style>
    /* Fundo Branco, Texto Escuro (Alta Legibilidade) */
    .stApp {{ background-color: #F9FAFB; color: #111827; font-family: 'Segoe UI', system-ui, sans-serif; }}
    h1, h2, h3, h4, h5, p, span, label {{ color: #111827 !important; }}
    hr {{ border-color: #E5E7EB; }}
    
    /* Campos de Digitação Seguros e Claros */
    .stTextInput>div>div>input, .stSelectbox>div>div>select, .stTextArea>div>div>textarea {{
        background-color: #FFFFFF !important; 
        color: #111827 !important;
        border: 1px solid #D1D5DB !important; 
        border-radius: 8px !important; 
        padding: 14px !important;
        font-size: 16px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }}
    .stTextInput>div>div>input::placeholder, .stTextArea>div>div>textarea::placeholder {{ color: #9CA3AF !important; }}
    .stTextInput>div>div>input:focus, .stSelectbox>div>div>select:focus {{ border-color: {cor_tema} !important; outline: none; box-shadow: 0 0 0 2px rgba(37,99,235,0.2) !important; }}
    
    /* Popover Selectbox */
    div[data-baseweb="select"] > div {{ background-color: #FFFFFF !important; border-color: #D1D5DB !important; color: #111827 !important; }}
    ul[data-baseweb="menu"] {{ background-color: #FFFFFF !important; border: 1px solid #D1D5DB !important; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
    ul[data-baseweb="menu"] li {{ color: #111827 !important; }}
    ul[data-baseweb="menu"] li:hover {{ background-color: #F3F4F6 !important; }}
    
    /* Botões Modernos */
    .stButton>button {{
        background-color: {cor_tema}; color: #FFFFFF !important; border: none; border-radius: 8px; 
        width: 100%; padding: 14px; font-weight: 600; font-size: 15px; box-shadow: 0 4px 6px rgba(37,99,235,0.2); transition: 0.2s;
    }}
    .stButton>button:hover {{ background-color: #1D4ED8; box-shadow: 0 6px 8px rgba(37,99,235,0.3); transform: translateY(-1px); }}
    
    /* Alertas Amigáveis ao Cliente */
    .client-alert-success {{ background-color: #ECFDF5; border: 1px solid #A7F3D0; color: #065F46; padding: 16px; border-radius: 8px; font-weight: 500; text-align: center; margin-bottom: 16px; }}
    .client-alert-error {{ background-color: #FEF2F2; border: 1px solid #FECACA; color: #991B1B; padding: 16px; border-radius: 8px; font-weight: 500; text-align: center; margin-bottom: 16px; }}
    
    /* Cartões e Badges (Área Gestão) */
    .badge-container {{ display: flex; justify-content: space-between; gap: 10px; margin-bottom: 24px; flex-wrap: wrap; }}
    .badge-box {{ flex: 1; background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 10px; padding: 16px 10px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.05); min-width: 80px; }}
    .badge-num {{ display: block; font-size: 26px; font-weight: 800; color: {cor_tema}; line-height: 1.2; }}
    .badge-label {{ font-size: 12px; color: #6B7280 !important; text-transform: uppercase; font-weight: 600; }}
    
    .crm-row {{ background: #FFFFFF; border: 1px solid #E5E7EB; border-left: 5px solid #D1D5DB; padding: 20px; margin-bottom: 12px; border-radius: 8px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }}
    .crm-row.atencao {{ border-left-color: #EF4444; }}
    .crm-row.finalizada {{ border-left-color: #10B981; }}
    .crm-row.perdida {{ border-left-color: #6B7280; opacity: 0.7; }}
    
    .tile-card {{ background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 12px; padding: 18px; margin-bottom: 16px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
    .tile-card h4 {{ margin: 0 0 8px 0; color: #111827 !important; font-size: 18px; font-weight: 700; }}
    .tile-card p {{ margin: 0 0 4px 0; font-size: 14px; color: #4B5563 !important; font-weight: 500; }}
    </style>
""", unsafe_allow_html=True)

def m_erro(t): st.markdown(f'<div class="client-alert-error">{t}</div>', unsafe_allow_html=True)
def m_ok(t): st.markdown(f'<div class="client-alert-success">{t}</div>', unsafe_allow_html=True)

# ================= ROTEADOR =================
st.title(f"{st.session_state['config_sistema']['titulo_app']}")

col_n1, col_n2, col_n3 = st.columns(3)
if col_n1.button("📝 Fazer Pedido"): st.session_state['aba_ativa'] = "📝 Nova Venda"; st.rerun()
if col_n2.button("📞 Contato Rápido"): st.session_state['aba_ativa'] = "📞 Contato Rápido"; st.rerun()
if col_n3.button("🔒 Acesso Restrito"): st.session_state['aba_ativa'] = "🔒 Painel Interno"; st.rerun()

st.markdown("<hr style='margin-top: 5px; margin-bottom: 25px;'>", unsafe_allow_html=True)

# ================= ÁREA PÚBLICA 1: NOVA VENDA (CLIENTE SAFE) =================
if st.session_state['aba_ativa'] == "📝 Nova Venda":
    
    if st.session_state['rascunhos_locais']:
        with st.expander("📂 Continuar preenchimento anterior", expanded=False):
            for r in st.session_state['rascunhos_locais']:
                rc1, rc2 = st.columns([3, 1])
                rc1.markdown(f"**{r.get('f_nome', 'Sem Nome')}** - {r.get('f_operadora', 'S/ Op')}")
                if rc2.button("Abrir", key=f"load_{r['id']}"):
                    st.session_state['form_venda_cache'] = r
                    st.session_state['rascunhos_locais'] = [x for x in st.session_state['rascunhos_locais'] if x['id'] != r['id']]
                    salvar_rascunhos_local()
                    st.rerun()

    cfg = st.session_state['config_sistema']
    cache = st.session_state.get('form_venda_cache', {})

    # Operadora independente para forçar a renderização dinâmica dos Planos
    ops = ["Selecione o Serviço"] + list(st.session_state['planos_dinamicos'].keys())
    op_idx = ops.index(cache['f_operadora']) if 'f_operadora' in cache and cache['f_operadora'] in ops else 0
    operadora = st.selectbox("Qual serviço deseja contratar?", ops, index=op_idx, key='sel_operadora')
    planos_da_op = st.session_state['planos_dinamicos'].get(operadora, {}) if operadora != "Selecione o Serviço" else {}

    with st.form("form_captacao", clear_on_submit=False):
        st.markdown("<h4 style='color: #374151;'>Seus Dados</h4>", unsafe_allow_html=True)
        nome = st.text_input("Nome Completo", value=cache.get('f_nome', ''), placeholder="Ex: João da Silva")
        cpf = st.text_input("CPF ou CNPJ", value=cache.get('f_cpf', ''), placeholder="Apenas números")
        whats = st.text_input("WhatsApp com DDD", value=cache.get('f_whats', ''), placeholder="Ex: 27999999999")
        
        st.markdown("<h4 style='color: #374151; margin-top: 20px;'>Endereço de Instalação</h4>", unsafe_allow_html=True)
        col_cep, col_btn = st.columns([2, 1])
        with col_cep: 
            cep = st.text_input("CEP", value=cache.get('f_cep', ''), placeholder="Ex: 29169-100")
        with col_btn:
            if st.form_submit_button("Buscar Endereço"):
                dc = buscar_cep(cep)
                if dc:
                    st.session_state['form_venda_cache'] = {**cache, 'f_nome': nome, 'f_cpf': cpf, 'f_whats': whats, 'f_cep': cep, 'f_rua': dc.get("logradouro", ""), 'f_bairro': dc.get("bairro", ""), 'f_operadora': operadora}
                    st.rerun()
                else: 
                    m_erro("CEP não encontrado. Por favor, digite o endereço manualmente.")

        rua = st.text_input("Rua/Avenida", value=cache.get('f_rua', ''))
        col_num, col_bairro = st.columns([1, 2])
        with col_num: numero = st.text_input("Número", value=cache.get('f_numero', ''))
        with col_bairro: bairro = st.text_input("Bairro", value=cache.get('f_bairro', ''))

        lista_planos = ["Selecione uma opção"] + list(planos_da_op.keys())
        pl_idx = lista_planos.index(cache['f_plano']) if 'f_plano' in cache and cache['f_plano'] in lista_planos else 0
        plano = st.selectbox("Qual plano escolhido?", lista_planos, index=pl_idx)

        extras = {}
        for chave, config_c in cfg['campos_dinamicos'].items():
            if config_c['ativo']:
                extras[chave] = st.text_input(config_c['nome'], value=cache.get(f'f_{chave}', ''))

        st.markdown("<br>", unsafe_allow_html=True)
        c_sub1, c_sub2 = st.columns(2)
        btn_salvar = c_sub1.form_submit_button("💾 Guardar para depois")
        btn_enviar = c_sub2.form_submit_button("✅ Enviar Pedido")

        if btn_salvar:
            dados_r = {"id": gerar_chave_dinamica(), "f_nome": nome, "f_cpf": cpf, "f_whats": whats, "f_cep": cep, "f_rua": rua, "f_numero": numero, "f_bairro": bairro, "f_operadora": operadora, "f_plano": plano}
            for k, v in extras.items(): dados_r[f"f_{k}"] = v
            st.session_state['rascunhos_locais'].insert(0, dados_r)
            salvar_rascunhos_local()
            st.session_state['form_venda_cache'] = {}
            st.rerun()

        if btn_enviar:
            if not nome or not cpf or operadora == "Selecione o Serviço" or plano == "Selecione uma opção":
                m_erro("Por favor, preencha os dados essenciais (Nome, CPF, Serviço e Plano) para enviarmos o pedido.")
            elif not validar_cpf_cnpj(cpf):
                m_erro("O documento informado parece estar incorreto. Verifique os números.")
            else:
                linha_dados = {
                    "tipo": "venda", "acao": "inserir", "protocolo": gerar_protocolo_seguro(),
                    "nome": nome, "cpf": cpf, "mae": "", "email": "", "whats1": whats, "whats2": "",
                    "cep": cep, "rua": rua, "numero": numero, "bairro": bairro, "referencia": "",
                    "operadora": operadora, "plano": plano, "valor_plano": 0, "detalhes_plano": "",
                    "extra1": extras.get('extra1', ''), "extra2": extras.get('extra2', ''),
                    "status": "Pendente", "obs": "", "vendedor": st.session_state['vendedor_atual']
                }
                with st.spinner("Processando pedido de forma segura..."):
                    if api_google(linha_dados):
                        st.session_state['form_venda_cache'] = {}
                        m_ok("Tudo certo! Seu pedido foi enviado com sucesso e está em processamento.")
                    else:
                        m_erro("Tivemos um problema com a conexão. Por favor, guarde para depois e tente em instantes.")

# ================= ÁREA PÚBLICA 2: NOVO LEAD (NOTION) =================
elif st.session_state['aba_ativa'] == "📞 Contato Rápido":
    st.markdown("<h3 style='color: #111827;'>Deixe seu contato</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color: #4B5563; margin-bottom: 20px;'>Preencha os dados abaixo e retornaremos em breve para tirar suas dúvidas.</p>", unsafe_allow_html=True)

    with st.form("form_lead", clear_on_submit=True):
        nome_lead = st.text_input("Seu Nome")
        tel_lead = st.text_input("Seu Telefone / WhatsApp")
        obs_lead = st.text_area("Como podemos ajudar? (Opcional)")
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.form_submit_button("✅ Enviar Contato"):
            if not nome_lead or not tel_lead:
                m_erro("Por favor, informe um nome e telefone válidos.")
            else:
                with st.spinner("Enviando..."):
                    enviar_lead_notion(nome_lead, tel_lead, obs_lead)
                    m_ok("Agradecemos o contato! Faremos um retorno em breve.")

# ================= ÁREA RESTRITA: GESTÃO & CRM =================
elif st.session_state['aba_ativa'] == "🔒 Painel Interno":
    if not SENHA_MESTRE_GESTAO:
        st.error("Aviso do Sistema: O Cofre não possui chave configurada nos Secrets. Acesso negado.")
        st.stop()

    if not st.session_state['modo_gestao_liberado']:
        st.markdown("<h3 style='text-align:center;'>Acesso Restrito</h3>", unsafe_allow_html=True)
        senha = st.text_input("Insira sua credencial", type="password", placeholder="Digite a chave de segurança")
        if st.button("Destrancar Cofre"):
            if senha == SENHA_MESTRE_GESTAO:
                st.session_state['modo_gestao_liberado'] = True
                st.rerun()
            else:
                m_erro("Credencial inválida.")
    else:
        st.markdown("<div style='display:flex; justify-content:space-between; align-items:center;'><h3>Painel do Gestor</h3></div>", unsafe_allow_html=True)
        if st.button("🔒 Encerrar Sessão", key="btn_logout"):
            st.session_state['modo_gestao_liberado'] = False
            st.rerun()
        
        tab_crm, tab_leads, tab_config = st.tabs(["🗂️ Esteira Operacional", "📞 Funil Notion", "⚙️ Ajustes"])

        # --- ABA 1: CRM OFICIAL (SHEETS) ---
        with tab_crm:
            col_sync, col_hora = st.columns([1, 2])
            with col_sync:
                if st.button("🔄 Puxar Dados (Sincronizar)"):
                    with st.spinner("Consultando base criptografada..."):
                        if fetch_crm_sheets(): st.session_state['hora_sync'] = datetime.now().strftime("%H:%M")
                        else: st.error("Erro na comunicação com o banco de dados principal.")
            with col_hora:
                hora = st.session_state.get('hora_sync', '--:--')
                st.markdown(f"<p style='color: #6B7280; font-size: 13px; margin-top: 15px;'>Última sincronização: <b>{hora}</b></p>", unsafe_allow_html=True)

            if not st.session_state['crm_dados']:
                st.info("O painel está vazio. Clique no botão de sincronizar para carregar os clientes.")
            else:
                cabecalho = st.session_state['crm_dados'][0]
                linhas = st.session_state['crm_dados'][1:]
                
                # Mapeamento estrito por nome da coluna
                c_map = {nome: idx for idx, nome in enumerate(cabecalho)}
                
                if "Protocolo" not in c_map or "Status" not in c_map:
                    st.error("Falha estrutural: As colunas 'Protocolo' ou 'Status' não foram encontradas na planilha mestre.")
                else:
                    # Isolamento visual (Pode ser removido depois se o Gestor for ver tudo)
                    linhas = [l for l in linhas if len(l) > c_map.get('Vendedor', 99) and str(l[c_map.get('Vendedor', 99)]) == st.session_state['vendedor_atual']]

                    qtd_pendentes = qtd_atencao = qtd_finalizadas = 0
                    for linha in linhas:
                        while len(linha) <= c_map['Status']: linha.append("") 
                        stt = str(linha[c_map['Status']]).strip().lower()
                        
                        is_atrasado = False
                        if stt in ["pendente", "nova"]:
                            try:
                                data_venda = datetime.strptime(str(linha[c_map['Protocolo']]).replace('ID-', ''), "%Y%m%d-%H%M%S")
                                if (datetime.now() - data_venda).days >= 3: is_atrasado = True
                            except: pass
                            
                            if is_atrasado: qtd_atencao += 1
                            else: qtd_pendentes += 1
                        elif stt == "atenção": qtd_atencao += 1
                        elif stt == "instalada": qtd_finalizadas += 1

                    st.markdown(f"""
                        <div class="badge-container">
                            <div class="badge-box"><span class="badge-num">{qtd_pendentes}</span><span class="badge-label">Em Rota</span></div>
                            <div class="badge-box" style="border-color:#EF4444;"><span class="badge-num" style="color:#EF4444;">{qtd_atencao}</span><span class="badge-label">SLA Estourado</span></div>
                            <div class="badge-box" style="border-color:#10B981;"><span class="badge-num" style="color:#10B981;">{qtd_finalizadas}</span><span class="badge-label">Concluídas</span></div>
                        </div>
                    """, unsafe_allow_html=True)

                    filtro = st.selectbox("Selecione a Gaveta:", ["Em Rota (Pendentes)", "Tratamento (Atenção)", "Sucesso (Instaladas)", "Cemitério (Perdidas)"])

                    for linha in linhas:
                        while len(linha) < len(cabecalho): linha.append("")
                        
                        prot = linha[c_map['Protocolo']]
                        nome_c = linha[c_map.get('Nome', 2)] if 'Nome' in c_map else "S/N"
                        whats_c = linha[c_map.get('Whats1', 6)] if 'Whats1' in c_map else ""
                        op_c = linha[c_map.get('Operadora', 13)] if 'Operadora' in c_map else ""
                        
                        stt_raw = str(linha[c_map['Status']]).strip()
                        stt_clean = stt_raw.lower()
                        
                        is_atrasado = False
                        if stt_clean in ["pendente", "nova"]:
                            try:
                                data_venda = datetime.strptime(str(prot).replace('ID-', ''), "%Y%m%d-%H%M%S")
                                if (datetime.now() - data_venda).days >= 3: is_atrasado = True
                            except: pass

                        mostrar, cl = False, ""
                        if filtro == "Em Rota (Pendentes)" and stt_clean in ["pendente", "nova"] and not is_atrasado: mostrar = True
                        elif filtro == "Tratamento (Atenção)" and (stt_clean == "atenção" or is_atrasado): mostrar, cl = True, "atencao"
                        elif filtro == "Sucesso (Instaladas)" and stt_clean == "instalada": mostrar, cl = True, "finalizada"
                        elif filtro == "Cemitério (Perdidas)" and stt_clean in ["reprovada", "cancelada"]: mostrar, cl = True, "perdida"

                        if mostrar:
                            st.markdown(f'<div class="crm-row {cl}">', unsafe_allow_html=True)
                            ca1, ca2 = st.columns([3, 2])
                            with ca1:
                                marca_atraso = " ⏱️ **(Atrasado)**" if is_atrasado else ""
                                st.markdown(f"<p style='font-size: 18px; font-weight: 700; margin: 0;'>{nome_c}{marca_atraso}</p>", unsafe_allow_html=True)
                                st.markdown(f"<p style='color: #6B7280; font-size: 14px; margin: 0;'>Ref: {prot} | {op_c} | 📱 {whats_c}</p>", unsafe_allow_html=True)
                            with ca2:
                                opts = ["Pendente", "Atenção", "Instalada", "Reprovada", "Cancelada"]
                                id_idx = opts.index(stt_raw.capitalize()) if stt_raw.capitalize() in opts else 0
                                n_stt = st.selectbox("Atualizar Fase", opts, index=id_idx, key=f"sel_{prot}")
                                
                                cb1, cb2 = st.columns(2)
                                if cb1.button("Salvar", key=f"sv_{prot}"):
                                    linha[c_map['Status']] = n_stt
                                    with st.spinner("Atualizando base oficial..."):
                                        if api_google({"acao": "editar", "senha_api": SENHA_MESTRE_GESTAO, "id_busca": prot, "coluna_busca": c_map['Protocolo'], "novos_dados": linha}):
                                            st.toast("Sucesso!")
                                            fetch_crm_sheets()
                                            st.rerun()
                                        else: st.error("Erro na atualização.")
                                
                                if whats_c:
                                    w_code = urllib.parse.quote_plus(f"Olá {nome_c}, atendimento sobre seu pedido da {op_c}.")
                                    cb2.markdown(f'<a href="https://wa.me/55{re.sub(r"[^0-9]", "", whats_c)}?text={w_code}" target="_blank"><button style="width:100%; padding:8px; border-radius:6px; background:#10B981; border:none; color:#FFF; font-weight:600;">WhatsApp</button></a>', unsafe_allow_html=True)
                            st.markdown("</div>", unsafe_allow_html=True)

        # --- ABA 2: FUNIL NOTION (LEADS) ---
        with tab_leads:
            if st.button("🔄 Puxar Funil do Notion"):
                with st.spinner("Consultando Workspace..."):
                    st.session_state['notion_leads'] = consultar_leads_notion()
            
            if not st.session_state['notion_leads']:
                st.info("Nenhum lead encontrado no Notion ou base não conectada.")
            else:
                for l in st.session_state['notion_leads']:
                    st.markdown('<div class="tile-card">', unsafe_allow_html=True)
                    ln1, ln2 = st.columns([3, 2])
                    with ln1:
                        st.markdown(f"<h4>{l['nome']}</h4><p>📱 {l['telefone']}</p>", unsafe_allow_html=True)
                    with ln2:
                        opt_notion = ["Novo Lead", "Em Contato", "Convertido", "Perdido"]
                        curr_opt = l['status'] if l['status'] in opt_notion else "Novo Lead"
                        new_notion_st = st.selectbox("Progresso do Lead", opt_notion, index=opt_notion.index(curr_opt), key=f"notion_st_{l['id']}")
                        if st.button("Atualizar Funil", key=f"notion_btn_{l['id']}"):
                            atualizar_status_notion(l['id'], new_notion_st)
                            st.toast("Status atualizado no Notion!")
                    st.markdown("</div>", unsafe_allow_html=True)

        # --- ABA 3: AJUSTES DO SISTEMA ---
        with tab_config:
            st.markdown("#### Configuração Dinâmica da Rua")
            cfg = st.session_state['config_sistema']
            ops_disp = list(st.session_state['planos_dinamicos'].keys())
            
            with st.form("form_config_campos"):
                for k in ["extra1", "extra2"]:
                    cc = cfg['campos_dinamicos'][k]
                    st.markdown(f"**Personalização: {k.upper()}**")
                    c_ativo = st.checkbox("Exibir campo no formulário da rua?", value=cc['ativo'], key=f"atv_{k}")
                    c_nome = st.text_input("Pergunta/Rótulo que o cliente verá", value=cc['nome'], key=f"nm_{k}")
                    c_obr = st.multiselect("Travar preenchimento para quais operadoras?", ops_disp, default=cc['obrig_operadoras'], key=f"ob_{k}")
                    st.markdown("<hr>", unsafe_allow_html=True)
                    
                if st.form_submit_button("Salvar Layout Oficial"):
                    cfg['campos_dinamicos']['extra1'] = {'ativo': st.session_state['atv_extra1'], 'nome': st.session_state['nm_extra1'], 'obrig_operadoras': st.session_state['ob_extra1']}
                    cfg['campos_dinamicos']['extra2'] = {'ativo': st.session_state['atv_extra2'], 'nome': st.session_state['nm_extra2'], 'obrig_operadoras': st.session_state['ob_extra2']}
                    salvar_rascunhos_local() # Aproveita a função pra forçar o save no cache config tbm
                    st.success("A interface dos clientes foi atualizada com sucesso.")
