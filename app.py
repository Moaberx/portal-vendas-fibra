import streamlit as st
import requests
import json
import re
import urllib.parse
from datetime import datetime
from streamlit_local_storage import LocalStorage

# ================= CONFIGURAÇÃO E CONEXÃO =================
URL_BACKEND_GOOGLE = "https://script.google.com/macros/s/AKfycbyTF3qUfRvMKh5JcyxJ_rbo8fSc04n24s8y8X7wtS0nP1qVjv2nUbpQLZHmAWmpXhKJ/exec"

try:
    SENHA_MESTRE_GESTAO = st.secrets.get("senha_mestre_gestao", "PAP_SECRETO_2026")
    NOTION_TOKEN = st.secrets.get("notion_token", "")
    NOTION_DATABASE_ID = st.secrets.get("notion_database_id", "")
except Exception:
    SENHA_MESTRE_GESTAO = "PAP_SECRETO_2026"
    NOTION_TOKEN = ""
    NOTION_DATABASE_ID = ""

st.set_page_config(page_title="PAP Fibra", page_icon="📶", layout="centered")
local_storage = LocalStorage()

# ================= ESTADO INICIAL =================
if 'init' not in st.session_state:
    st.session_state.update({
        'init': True,
        'aba_ativa': "Nova Venda",
        'vendedor_atual': "Moabe",
        'leads_locais': [],
        'rascunhos_locais': [],
        'crm_dados': [],
        'modo_gestao_liberado': False,
        'form_venda_cache': {},
        'config_sistema': {
            "titulo_app": "PAP Fibra",
            "tema_cor": "#3B82F6",
            "pedir_email": True,
            "obrigatorio_email": True,
            "campos_dinamicos": {
                "extra1": {"ativo": False, "nome": "Campo Extra 1", "obrig_operadoras": []},
                "extra2": {"ativo": False, "nome": "Campo Extra 2", "obrig_operadoras": []}
            }
        },
        'planos_dinamicos': {
            "NIO Fibra": {"500 Mega": 100.00, "800 Mega": 135.00},
            "TIM Ultrafibra": {"600 Mega": 119.99, "800 Mega": 129.99},
            "Vivo": {"Padrão": 0.00},
            "Claro": {"Padrão": 0.00}
        }
    })

# ================= FUNÇÕES AUXILIARES =================
def gerar_chave_id(prefixo):
    return f"{prefixo}_{datetime.now().strftime('%H%M%S%f')}"

def blindar_texto(texto):
    if not isinstance(texto, str): return texto
    t = texto.strip()
    if t[:1] in ("=", "+", "-", "@"): return "'" + t
    return t

def salvar_memoria_local():
    dados = {
        "leads": st.session_state['leads_locais'],
        "rascunhos": st.session_state['rascunhos_locais'],
        "config": st.session_state['config_sistema']
    }
    try:
        local_storage.setItem("pap_memoria_v5", json.dumps(dados), key="write_memoria_unica")
    except Exception:
        pass

# --- ESCUDO ANTI-LOOP DE CACHE ---
if not st.session_state.get('memoria_carregada'):
    memoria_bruta = local_storage.getItem("pap_memoria_v5")
    
    if memoria_bruta is not None:
        if memoria_bruta != "":
            try:
                dados_salvos = json.loads(memoria_bruta) if isinstance(memoria_bruta, str) else memoria_bruta
                if isinstance(dados_salvos, dict):
                    st.session_state['leads_locais'] = dados_salvos.get('leads', [])
                    st.session_state['rascunhos_locais'] = dados_salvos.get('rascunhos', [])
                    if 'config' in dados_salvos:
                        st.session_state['config_sistema'] = dados_salvos['config']
            except Exception:
                pass
                
        st.session_state['memoria_carregada'] = True
        st.rerun()
    else:
        st.markdown("<h3 style='text-align: center; margin-top: 40px; color: #E5E5E5;'>⏳ Sincronizando Cache...</h3>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #888;'>Se esta tela travar por mais de 3 segundos, seu navegador bloqueou a leitura automática.</p>", unsafe_allow_html=True)
        
        col_space1, col_btn, col_space2 = st.columns([1, 2, 1])
        with col_btn:
            if st.button("Forçar Entrada (Destravar)", use_container_width=True, type="primary"):
                st.session_state['memoria_carregada'] = True
                st.rerun()
        st.stop()

# --- INTEGRAÇÃO NOTION (BLOCO DE NOTAS / LEADS) ---
def enviar_nota_notion(titulo, texto):
    if not NOTION_TOKEN or not NOTION_DATABASE_ID:
        return False, "Chaves do Notion não configuradas nos Secrets."
    
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    titulo_resumo = titulo[:50] if titulo else "Anotação PAP Fibra"
    
    data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Name": {
                "title": [{"text": {"content": titulo_resumo}}]
            }
        },
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": texto}}]
                }
            }
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            return True, "Nota salva na nuvem!"
        else:
            return False, f"Erro Notion: {response.status_code}"
    except Exception as e:
        return False, f"Falha de conexão com Notion."

# --- VALIDAÇÃO DE CPF E CNPJ ---
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
    if len(cep_limpo) != 8: return None
    try:
        r = requests.get(f"https://viacep.com.br/ws/{cep_limpo}/json/", timeout=5)
        if r.status_code == 200 and "erro" not in r.json():
            return r.json()
        return None
    except requests.exceptions.RequestException:
        return "erro_conexao"

# --- API GOOGLE ---
def api_google(payload):
    try:
        r = requests.post(URL_BACKEND_GOOGLE, data=json.dumps(payload), headers={"Content-Type": "application/json"}, timeout=15)
        if r.status_code == 200: return r.json()
        return {"status": "erro", "msg": f"O servidor respondeu com código {r.status_code}."}
    except requests.exceptions.Timeout:
        return {"status": "erro", "msg": "Tempo de conexão esgotado."}
    except requests.exceptions.RequestException:
        return {"status": "erro", "msg": "Falha na conexão com o servidor."}
    except ValueError:
        return {"status": "erro", "msg": "Resposta inválida do servidor."}

def fetch_crm():
    res = api_google({"acao": "ler", "senha_api": SENHA_MESTRE_GESTAO, "aba_alvo": "VENDAS"})
    if res and res.get("status") == "sucesso":
        st.session_state['crm_dados'] = res.get("dados", [])
        return True, None
    msg = res.get("msg", "Erro desconhecido ao sincronizar.") if res else "Sem resposta do servidor."
    return False, msg

# ================= UI E ESTILO =================
cor_tema = st.session_state['config_sistema'].get('tema_cor', '#3B82F6')

st.markdown(f"""
    <style>
    .stApp {{ background-color: #0A0A0A; color: #E5E5E5; font-family: 'Segoe UI', Tahoma, sans-serif; }}
    h1, h2, h3, h4, h5, label, p, span {{ color: #FFFFFF !important; font-weight: 600; }}
    hr {{ border-color: #262626; }}
    .stTextInput>div>div>input, .stSelectbox>div>div>select, .stTextArea>div>div>textarea {{
        background-color: #171717 !important; color: #FFFFFF !important;
        border: 1px solid #333 !important; border-radius: 8px !important; padding: 12px !important;
    }}
    .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {{ border-color: {cor_tema} !important; }}
    ul[data-baseweb="menu"] {{ background-color: #171717 !important; border: 1px solid #333 !important; }}
    ul[data-baseweb="menu"] li {{ background-color: #171717 !important; color: #FFFFFF !important; }}
    div[data-baseweb="select"] > div {{ background-color: #171717 !important; border-color: #333 !important; color: #FFFFFF !important; }}
    .stButton>button {{ background-color: #171717; color: #FFF; border: 1px solid #333; border-radius: 8px; width: 100%; padding: 12px; font-weight: bold; transition: 0.2s; }}
    .stButton>button:hover {{ border-color: {cor_tema}; color: {cor_tema}; background-color: #1A1A1A; }}
    .tile-card {{ border-radius: 10px; padding: 16px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }}
    .tile-card h4 {{ margin: 0 0 5px 0; color: #000 !important; font-size: 18px; font-weight: 800; }}
    .tile-card p {{ margin: 0; font-size: 14px; font-weight: 600; opacity: 0.8; color: #000 !important; }}
    .badge-container {{ display: flex; justify-content: space-between; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; }}
    .badge-box {{ flex: 1; background: #171717; border: 1px solid #333; border-radius: 8px; padding: 10px; text-align: center; min-width: 70px; }}
    .badge-num {{ display: block; font-size: 22px; font-weight: bold; color: {cor_tema}; }}
    .badge-label {{ font-size: 11px; color: #888 !important; text-transform: uppercase; }}
    .crm-row {{ background: #171717; border-left: 4px solid #333; padding: 15px; margin-bottom: 10px; border-radius: 6px; }}
    .crm-row.lead {{ border-left-color: #FCD34D; }}
    .crm-row.atencao {{ border-left-color: #EF4444; }}
    .crm-row.finalizada {{ border-left-color: #10B981; }}
    .crm-row.perdida {{ border-left-color: #6B7280; opacity: 0.6; }}
    .msg-box {{ padding: 12px; border-radius: 6px; margin: 10px 0; font-weight: 500; font-size: 14px; }}
    .msg-erro {{ background: #450a0a; border: 1px solid #7f1d1d; color: #fca5a5 !important; }}
    .msg-ok {{ background: #064e3b; border: 1px solid #065f46; color: #6ee7b7 !important; }}
    .msg-info {{ background: #0A1929; border: 1px solid #1E3A8A; color: #BFDBFE !important; }}
    </style>
""", unsafe_allow_html=True)

def m_erro(t): st.markdown(f'<div class="msg-box msg-erro">❌ {t}</div>', unsafe_allow_html=True)
def m_ok(t): st.markdown(f'<div class="msg-box msg-ok">✅ {t}</div>', unsafe_allow_html=True)
def m_info(t): st.markdown(f'<div class="msg-box msg-info">ℹ️ {t}</div>', unsafe_allow_html=True)

# ================= CÁLCULO DOS INDICADORES =================
qtd_rascunhos = len(st.session_state['rascunhos_locais'])
qtd_leads_locais = len(st.session_state['leads_locais'])
qtd_pendentes = qtd_atencao = qtd_finalizadas = qtd_leads_crm = 0
aviso_colunas = None

if st.session_state['crm_dados']:
    cabecalho = st.session_state['crm_dados'][0]
    linhas = st.session_state['crm_dados'][1:]

    if "Vendedor" not in cabecalho or "Status" not in cabecalho:
        aviso_colunas = "As colunas 'Vendedor' ou 'Status' não foram encontradas na planilha."
    else:
        idx_vendedor = cabecalho.index("Vendedor")
        idx_status = cabecalho.index("Status")
        linhas_vendedor = [l for l in linhas if len(l) > idx_vendedor and l[idx_vendedor] == st.session_state['vendedor_atual']]
        for l in linhas_vendedor:
            if len(l) > idx_status:
                stt = str(l[idx_status]).strip().lower()
                if stt == "lead": qtd_leads_crm += 1
                elif stt in ["pendente", "nova"]: qtd_pendentes += 1
                elif stt == "atenção": qtd_atencao += 1
                elif stt == "instalada": qtd_finalizadas += 1

st.markdown(f"""
    <div class="badge-container">
        <div class="badge-box"><span class="badge-num">{qtd_leads_locais}</span><span class="badge-label">Notas/Leads</span></div>
        <div class="badge-box"><span class="badge-num">{qtd_rascunhos}</span><span class="badge-label">Rascunhos</span></div>
        <div class="badge-box"><span class="badge-num">{qtd_pendentes}</span><span class="badge-label">Pendentes</span></div>
        <div class="badge-box" style="border-color:#EF4444;"><span class="badge-num" style="color:#EF4444;">{qtd_atencao}</span><span class="badge-label">Atenção</span></div>
        <div class="badge-box" style="border-color:#10B981;"><span class="badge-num" style="color:#10B981;">{qtd_finalizadas}</span><span class="badge-label">Fim</span></div>
    </div>
""", unsafe_allow_html=True)
if aviso_colunas: m_erro(aviso_colunas)

# ================= NAVEGAÇÃO =================
st.title(f"📶 {st.session_state['config_sistema'].get('titulo_app', 'PAP Fibra')}")

col_nav1, col_nav2, col_nav3, col_nav4 = st.columns(4)
if col_nav1.button("📝 Venda"): st.session_state['aba_ativa'] = "Nova Venda"; st.rerun()
if col_nav2.button("📞 Leads/Notas"): st.session_state['aba_ativa'] = "Leads"; st.rerun()
if col_nav3.button("🗂️ CRM"): st.session_state['aba_ativa'] = "CRM"; st.rerun()
if col_nav4.button("⚙️ Admin"): st.session_state['aba_ativa'] = "Admin"; st.rerun()

st.markdown("---")

# ================= MÓDULO 1: LEADS & NOTAS (INTEGRADO) =================
if st.session_state['aba_ativa'] == "Leads":
    st.markdown("<h3 style='text-align: center;'>☁️ Bloco de Notas & Leads</h3>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #888; font-size: 14px; margin-bottom: 30px;'>Crie post-its coloridos de contatos. Tudo é salvo no seu celular, enviado para o seu CRM e tem backup no Notion.</p>", unsafe_allow_html=True)

    if not NOTION_TOKEN or not NOTION_DATABASE_ID:
        m_info("⚠️ O Notion não está configurado nos Secrets. Os leads serão salvos apenas no celular e no Google Sheets.")

    with st.form("form_novo_lead", clear_on_submit=True):
        c1, c2 = st.columns([3, 2])
        nome_l = c1.text_input("Nome do Contato ou Título da Nota")
        whats_l = c2.text_input("WhatsApp (Opcional)")
        anotacao_l = st.text_area("Anotações, Script ou Detalhes Rápidos", height=100)
        cor_l = st.color_picker("Cor de Destaque do Post-it", "#FCD34D")

        st.markdown("<br>", unsafe_allow_html=True)
        btn_salvar_lead = st.form_submit_button("🚀 Salvar Post-it e Enviar para Nuvem")

        if btn_salvar_lead:
            if nome_l:
                novo_id = gerar_chave_id('ld')
                
                # 1. Salva na Memória Local (Post-it)
                st.session_state['leads_locais'].insert(0, {
                    "id": novo_id,
                    "nome": nome_l,
                    "telefone": whats_l,
                    "anotacao": anotacao_l,
                    "cor": cor_l,
                    "data": datetime.now().strftime("%d/%m %H:%M")
                })
                salvar_memoria_local()
                
                # 2. Envia para o Google Sheets (CRM)
                texto_obs = f"{anotacao_l} [Criado via Bloco de Notas]" if anotacao_l else "Lead criado no aplicativo local."
                payload_lead = {
                    "tipo": "venda", "acao": "inserir", "protocolo": novo_id,
                    "nome": blindar_texto(nome_l), "cpf": "", "mae": "", "email": "",
                    "whats1": blindar_texto(whats_l), "whats2": "",
                    "cep": "", "rua": "", "numero": "", "bairro": "", "referencia": "",
                    "operadora": "N/A", "plano": "N/A", "valor_plano": 0, "detalhes_plano": "",
                    "extra1": "", "extra2": "",
                    "status": "Lead", "obs": blindar_texto(texto_obs), "vendedor": st.session_state['vendedor_atual']
                }
                api_google(payload_lead) # Fundo invisível
                
                # 3. Envia para o Notion (Backup Extra)
                if NOTION_TOKEN and NOTION_DATABASE_ID:
                    conteudo_notion = f"WhatsApp: {whats_l}\n\n{anotacao_l}"
                    sucesso_notion, msg_notion = enviar_nota_notion(nome_l, conteudo_notion)
                    if not sucesso_notion:
                        st.toast(msg_notion)
                
                st.rerun()
            else:
                m_erro("Informe ao menos o nome do contato ou título da nota.")

    if not st.session_state['leads_locais']:
        st.caption("Nenhum post-it registrado no seu aparelho.")

    for lead in st.session_state['leads_locais']:
        st.markdown(f"""
            <div class="tile-card" style="background-color: {lead['cor']};">
                <h4 style="color: #000 !important; margin: 0 0 5px 0;">{lead['nome']}</h4>
                <p style="color: #000 !important; margin: 0 0 5px 0;">📞 {lead.get('telefone', 'S/ Tel')} | 🕒 {lead['data']}</p>
                <p style="color: #333 !important; font-size: 13px; margin: 0; white-space: pre-wrap;">{lead.get('anotacao', '')}</p>
            </div>
        """, unsafe_allow_html=True)

        c_btn1, c_btn2 = st.columns(2)
        if c_btn1.button("Transformar em Venda", key=f"cvt_{lead['id']}"):
            st.session_state['form_venda_cache'] = {
                "f_protocolo": lead['id'], 
                "f_nome": lead['nome'], 
                "f_whats": lead.get('telefone', ''),
                "f_obs": lead.get('anotacao', '')
            }
            st.session_state['leads_locais'] = [l for l in st.session_state['leads_locais'] if l['id'] != lead['id']]
            salvar_memoria_local()
            st.session_state['aba_ativa'] = "Nova Venda"
            st.rerun()

        if c_btn2.button("Descartar Local", key=f"del_{lead['id']}"):
            st.session_state['leads_locais'] = [l for l in st.session_state['leads_locais'] if l['id'] != lead['id']]
            salvar_memoria_local()
            st.rerun()

# ================= MÓDULO 2: NOVA VENDA =================
elif st.session_state['aba_ativa'] == "Nova Venda":
    if st.session_state['rascunhos_locais']:
        with st.expander(f"📦 Rascunhos Salvos ({qtd_rascunhos})", expanded=False):
            for r in st.session_state['rascunhos_locais']:
                rc1, rc2 = st.columns([3, 1])
                rc1.markdown(f"**{r.get('f_nome', 'Sem Nome')}** - {r.get('f_operadora', 'Sem operadora')}")
                if rc2.button("Carregar Ficha", key=f"load_{r['id']}"):
                    st.session_state['form_venda_cache'] = r
                    st.session_state['rascunhos_locais'] = [x for x in st.session_state['rascunhos_locais'] if x['id'] != r['id']]
                    salvar_memoria_local()
                    st.rerun()

    cfg = st.session_state['config_sistema']
    cfg_campos = cfg['campos_dinamicos']
    cache = st.session_state.get('form_venda_cache', {})

    ops = ["Selecione"] + list(st.session_state['planos_dinamicos'].keys())
    op_idx = ops.index(cache['f_operadora']) if 'f_operadora' in cache and cache['f_operadora'] in ops else 0
    operadora = st.selectbox("Operadora", ops, index=op_idx, key='sel_operadora_livre')
    planos_da_op = st.session_state['planos_dinamicos'].get(operadora, {}) if operadora != "Selecione" else {}

    with st.form("form_motor_vendas", clear_on_submit=False):
        st.subheader("Dados do Cliente")
        nome = st.text_input("Nome Completo", value=cache.get('f_nome', ''))
        cpf = st.text_input("CPF / CNPJ", value=cache.get('f_cpf', ''))
        whats = st.text_input("WhatsApp", value=cache.get('f_whats', ''))
        email = ""
        if cfg.get('pedir_email', True):
            rotulo_email = "Email" if cfg.get('obrigatorio_email', True) else "Email (Opcional)"
            email = st.text_input(rotulo_email, value=cache.get('f_email', ''))

        st.subheader("Endereço e Serviço")
        col_cep, col_btn = st.columns([2, 1])
        with col_cep:
            cep = st.text_input("CEP", value=cache.get('f_cep', ''))
        with col_btn:
            if st.form_submit_button("Buscar CEP"):
                resultado_cep = buscar_cep(cep)
                if resultado_cep == "erro_conexao":
                    m_erro("Falha de conexão ao buscar o CEP.")
                elif resultado_cep:
                    st.session_state['form_venda_cache'] = {
                        **cache, 'f_nome': nome, 'f_cpf': cpf, 'f_whats': whats, 'f_email': email,
                        'f_cep': cep, 'f_rua': resultado_cep.get("logradouro", ""),
                        'f_bairro': resultado_cep.get("bairro", ""), 'f_operadora': operadora
                    }
                    st.rerun()
                else:
                    m_erro("CEP não localizado.")

        rua = st.text_input("Rua", value=cache.get('f_rua', ''))
        bairro = st.text_input("Bairro", value=cache.get('f_bairro', ''))

        lista_planos = ["Selecione"] + list(planos_da_op.keys())
        pl_idx = lista_planos.index(cache['f_plano']) if 'f_plano' in cache and cache['f_plano'] in lista_planos else 0
        plano = st.selectbox("Plano Solicitado", lista_planos, index=pl_idx)

        extras = {}
        for chave, config_c in cfg_campos.items():
            if config_c['ativo']:
                obrigatorio = operadora in config_c['obrig_operadoras']
                rotulo = config_c['nome'] + (" (obrigatório)" if obrigatorio else "")
                extras[chave] = st.text_input(rotulo, value=cache.get(f'f_{chave}', ''))

        obs = st.text_area("Observações Internas", value=cache.get('f_obs', ''))

        c_sub1, c_sub2 = st.columns(2)
        btn_salvar_rascunho = c_sub1.form_submit_button("Salvar Rascunho")
        btn_enviar_oficial = c_sub2.form_submit_button("Finalizar e Enviar")

        if btn_salvar_rascunho:
            dados_r = {
                "id": gerar_chave_id('rsc'), "f_protocolo": cache.get('f_protocolo'),
                "f_nome": nome, "f_cpf": cpf, "f_whats": whats,
                "f_email": email, "f_cep": cep, "f_rua": rua, "f_bairro": bairro,
                "f_operadora": operadora, "f_plano": plano, "f_obs": obs
            }
            for k, v in extras.items():
                dados_r[f"f_{k}"] = v
            st.session_state['rascunhos_locais'].insert(0, dados_r)
            salvar_memoria_local()
            st.session_state['form_venda_cache'] = {}
            st.rerun()

        if btn_enviar_oficial:
            if not nome or not cpf or operadora == "Selecione" or plano == "Selecione":
                m_erro("Verifique os campos obrigatórios: Nome, CPF/CNPJ, Operadora e Plano.")
            elif not validar_cpf_cnpj(cpf):
                m_erro("Documento (CPF ou CNPJ) inválido.")
            elif cfg.get('pedir_email', True) and cfg.get('obrigatorio_email', True) and not email:
                m_erro("O preenchimento do e-mail é obrigatório.")
            else:
                falhou_obrig = False
                for chave, config_c in cfg_campos.items():
                    if config_c['ativo'] and operadora in config_c['obrig_operadoras'] and not extras.get(chave):
                        m_erro(f"Preencha o campo: {config_c['nome']}")
                        falhou_obrig = True

                if not falhou_obrig:
                    valor_final_plano = planos_da_op.get(plano, 0.00)
                    
                    protocolo = cache.get('f_protocolo', gerar_chave_id("PAP"))
                    acao_backend = "editar" if 'f_protocolo' in cache else "inserir"

                    linha_dados = {
                        "tipo": "venda", "acao": acao_backend, "protocolo": protocolo,
                        "nome": blindar_texto(nome), "cpf": cpf, "mae": "",
                        "email": blindar_texto(email), "whats1": blindar_texto(whats), "whats2": "",
                        "cep": blindar_texto(cep), "rua": blindar_texto(rua), "numero": "",
                        "bairro": blindar_texto(bairro), "referencia": "",
                        "operadora": operadora, "plano": plano, "valor_plano": valor_final_plano,
                        "detalhes_plano": "",
                        "extra1": blindar_texto(extras.get('extra1', '')),
                        "extra2": blindar_texto(extras.get('extra2', '')),
                        "status": "Pendente", "obs": blindar_texto(obs),
                        "vendedor": st.session_state['vendedor_atual']
                    }
                    
                    if acao_backend == "editar":
                        linha_dados["id_busca"] = protocolo
                        linha_dados["coluna_busca"] = 1
                        linha_dados["novos_dados"] = list(linha_dados.values())[3:-3]

                    with st.spinner("Enviando dados para o Google Sheets..."):
                        resposta = api_google(linha_dados)

                    if resposta and resposta.get('status') == 'sucesso':
                        st.session_state['form_venda_cache'] = {}
                        fetch_crm()
                        st.session_state['aba_ativa'] = "CRM"
                        st.rerun()
                    else:
                        erro_msg = resposta.get('msg', 'Falha na gravação.') if resposta else "Sem resposta do servidor."
                        m_erro(f"Erro: {erro_msg}. Salve nos rascunhos para não perder a ficha.")

# ================= MÓDULO 3: GESTÃO CRM =================
elif st.session_state['aba_ativa'] == "CRM":
    st.subheader("Esteira de Vendas")

    if st.button("Sincronizar Base de Dados"):
        with st.spinner("Atualizando registros..."):
            sucesso, erro = fetch_crm()
        if not sucesso:
            m_erro(f"Falha ao sincronizar: {erro}")

    if not st.session_state['crm_dados']:
        m_info("Base de dados vazia. Realize a sincronização.")
    else:
        cabecalho = st.session_state['crm_dados'][0]
        linhas_raw = st.session_state['crm_dados'][1:]

        if "Protocolo" not in cabecalho or "Status" not in cabecalho:
            m_erro("A planilha retornada não tem as colunas 'Protocolo' ou 'Status'.")
        else:
            c_map = {nome: idx for idx, nome in enumerate(cabecalho)}

            if "Vendedor" in c_map:
                linhas = [l for l in linhas_raw if len(l) > c_map['Vendedor'] and str(l[c_map['Vendedor']]) == st.session_state['vendedor_atual']]
            else:
                linhas = linhas_raw

            filtro_status = st.selectbox("Filtro de Status", ["Pendentes", "Leads na Nuvem", "Atenção", "Finalizadas", "Canceladas / Reprovadas"])
            idx_valor_recebido = c_map.get('ValorRecebido', len(cabecalho))

            for linha in linhas:
                while len(linha) <= idx_valor_recebido:
                    linha.append("")

                prot = linha[c_map['Protocolo']]
                nome_c = linha[c_map.get('Nome', 2)] if len(linha) > c_map.get('Nome', 2) else ""
                whats_c = linha[c_map.get('Whats1', 6)] if len(linha) > c_map.get('Whats1', 6) else ""
                op_c = linha[c_map.get('Operadora', 13)] if len(linha) > c_map.get('Operadora', 13) else ""
                plano_c = linha[c_map.get('Plano', 14)] if len(linha) > c_map.get('Plano', 14) else ""

                status_raw = str(linha[c_map['Status']]).strip()
                status_clean = status_raw.lower()
                data_c = str(linha[c_map.get('Data', 0)])[:10] if len(linha) > c_map.get('Data', 0) else ""
                val_recebido = linha[idx_valor_recebido]

                cor_linha, mostrar = "", False
                if filtro_status == "Pendentes" and status_clean in ["pendente", "nova"]:
                    mostrar = True
                elif filtro_status == "Leads na Nuvem" and status_clean == "lead":
                    mostrar, cor_linha = True, "lead"
                elif filtro_status == "Atenção" and status_clean == "atenção":
                    mostrar, cor_linha = True, "atencao"
                elif filtro_status == "Finalizadas" and status_clean == "instalada":
                    mostrar, cor_linha = True, "finalizada"
                elif filtro_status == "Canceladas / Reprovadas" and status_clean in ["cancelada", "reprovada"]:
                    mostrar, cor_linha = True, "perdida"

                if mostrar:
                    st.markdown(f'<div class="crm-row {cor_linha}">', unsafe_allow_html=True)
                    c_info, c_act = st.columns([3, 2])

                    with c_info:
                        st.markdown(f"**{nome_c}** ({op_c})")
                        st.caption(f"{data_c} | {whats_c} | {plano_c}")
                        if status_clean == "instalada":
                            st.markdown(f"Faturamento: **R$ {val_recebido}**")

                    with c_act:
                        opts_status = ["Lead", "Pendente", "Atenção", "Instalada", "Reprovada", "Cancelada"]
                        idx_st = opts_status.index(status_raw.capitalize()) if status_raw.capitalize() in opts_status else 1
                        novo_st = st.selectbox("Status", opts_status, index=idx_st, key=f"st_{prot}")

                        novo_val = val_recebido
                        if novo_st == "Instalada":
                            novo_val = st.text_input("Valor Líquido (R$)", value=val_recebido, key=f"val_{prot}")

                        col_b1, col_b2 = st.columns(2)
                        if col_b1.button("Salvar", key=f"sv_{prot}"):
                            linha[c_map['Status']] = novo_st
                            if novo_st == "Instalada":
                                linha[idx_valor_recebido] = blindar_texto(str(novo_val))

                            payload = {
                                "acao": "editar", "senha_api": SENHA_MESTRE_GESTAO,
                                "id_busca": prot, "coluna_busca": c_map['Protocolo'],
                                "novos_dados": linha
                            }

                            with st.spinner("Processando..."):
                                resposta = api_google(payload)

                            if resposta and resposta.get('status') == 'sucesso':
                                st.toast("Atualização concluída.")
                                fetch_crm()
                                st.rerun()
                            else:
                                erro_msg = resposta.get('msg', 'Falha na gravação.') if resposta else "Sem resposta do servidor."
                                m_erro(erro_msg)

                        link_agenda = f"https://calendar.google.com/calendar/render?action=TEMPLATE&text=Retorno+{urllib.parse.quote(str(nome_c))}&details=WhatsApp:+{whats_c}"
                        col_b2.markdown(
                            f'<a href="{link_agenda}" target="_blank"><button style="width:100%; padding:8px; border-radius:6px; background:#2563EB; border:none; color:#FFF;">Agendar</button></a>',
                            unsafe_allow_html=True
                        )
                    st.markdown('</div>', unsafe_allow_html=True)

# ================= MÓDULO 4: ADMIN =================
elif st.session_state['aba_ativa'] == "Admin":
    if not st.session_state['modo_gestao_liberado']:
        senha = st.text_input("Senha Administrativa", type="password")
        if st.button("Acessar"):
            if senha == SENHA_MESTRE_GESTAO:
                st.session_state['modo_gestao_liberado'] = True
                st.rerun()
            else:
                m_erro("Credenciais inválidas.")
    else:
        st.subheader("Painel de Administração")
        if st.button("Encerrar Sessão"):
            st.session_state['modo_gestao_liberado'] = False
            st.rerun()

        tb1, tb2 = st.tabs(["Campos Customizados", "Relatórios"])

        with tb1:
            st.write("### Estrutura do Formulário")
            cfg = st.session_state['config_sistema']
            ops_disponiveis = list(st.session_state['planos_dinamicos'].keys())

            with st.form("form_admin_campos"):
                for chave_campo in ["extra1", "extra2"]:
                    cc = cfg['campos_dinamicos'][chave_campo]
                    st.markdown(f"**Campo: {chave_campo.upper()}**")
                    st.checkbox("Habilitar no formulário", value=cc['ativo'], key=f"atv_{chave_campo}")
                    st.text_input("Identificação (Rótulo)", value=cc['nome'], key=f"nm_{chave_campo}")
                    st.multiselect("Obrigatório para as operadoras:", ops_disponiveis, default=cc['obrig_operadoras'], key=f"ob_{chave_campo}")
                    st.markdown("---")

                if st.form_submit_button("Salvar Configurações"):
                    cfg['campos_dinamicos']['extra1'] = {
                        'ativo': st.session_state['atv_extra1'],
                        'nome': st.session_state['nm_extra1'],
                        'obrig_operadoras': st.session_state['ob_extra1']
                    }
                    cfg['campos_dinamicos']['extra2'] = {
                        'ativo': st.session_state['atv_extra2'],
                        'nome': st.session_state['nm_extra2'],
                        'obrig_operadoras': st.session_state['ob_extra2']
                    }
                    salvar_memoria_local()
                    m_ok("Configurações registradas.")

        with tb2:
            st.write("### Fechamento de Vendas")
            if st.session_state['crm_dados'] and "Status" in st.session_state['crm_dados'][0]:
                cabecalho = st.session_state['crm_dados'][0]
                linhas = st.session_state['crm_dados'][1:]
                c_map = {nome: idx for idx, nome in enumerate(cabecalho)}
                idx_valor_recebido = c_map.get('ValorRecebido', len(cabecalho))

                if "Vendedor" in c_map:
                    linhas = [l for l in linhas if len(l) > c_map['Vendedor'] and str(l[c_map['Vendedor']]) == st.session_state['vendedor_atual']]

                lucro_total = 0.0
                instaladas, perdidas = 0, 0

                for l in linhas:
                    if len(l) > c_map['Status']:
                        stt = str(l[c_map['Status']]).strip().lower()
                        if stt == "instalada":
                            instaladas += 1
                            if len(l) > idx_valor_recebido and l[idx_valor_recebido]:
                                try:
                                    lucro_total += float(str(l[idx_valor_recebido]).replace(',', '.'))
                                except ValueError:
                                    pass
                        elif stt in ["reprovada", "cancelada"]:
                            perdidas += 1

                st.metric("Total Liquidado", f"R$ {lucro_total:.2f}")
                c_met1, c_met2 = st.columns(2)
                c_met1.metric("Contratos Instalados", instaladas)
                c_met2.metric("Perdas / Cancelamentos", perdidas)
            else:
                m_info("Dados insuficientes. Realize a sincronização do CRM.")
