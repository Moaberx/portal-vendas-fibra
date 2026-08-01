import streamlit as st
import requests
import json
import re
import urllib.parse
from datetime import datetime
from streamlit_local_storage import LocalStorage

# ================= CONFIGURAÇÕES E API =================
URL_BACKEND_GOOGLE = "https://script.google.com/macros/s/AKfycbyTF3qUfRvMKh5JcyxJ_rbo8fSc04n24s8y8X7wtS0nP1qVjv2nUbpQLZHmAWmpXhKJ/exec"

try:
    SENHA_MESTRE_GESTAO = st.secrets.get("senha_mestre_gestao", "PAP_SECRETO_2026")
except Exception:
    SENHA_MESTRE_GESTAO = "PAP_SECRETO_2026"

st.set_page_config(page_title="PAP Fibra", page_icon="📶", layout="centered")
local_storage = LocalStorage()

# ================= GERENCIAMENTO DE ESTADO =================
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
            "pedir_email": True, "obrigatorio_email": True,
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

# ================= FUNÇÕES DE SISTEMA =================
def gerar_chave_id(prefixo):
    return f"{prefixo}_{datetime.now().strftime('%H%M%S%f')}"

def salvar_memoria_local():
    # Salva todos os dados locais em um único pacote para evitar perda de dados
    dados = {
        "leads": st.session_state['leads_locais'],
        "rascunhos": st.session_state['rascunhos_locais'],
        "config": st.session_state['config_sistema']
    }
    try:
        local_storage.setItem("pap_memoria_v3", json.dumps(dados), key="write_memoria_unica")
    except: pass

# Trava de carregamento (Impede que F5 apague os dados)
if not st.session_state.get('memoria_carregada'):
    memoria_bruta = local_storage.getItem("pap_memoria_v3", key="read_memoria_unica")
    
    if memoria_bruta is None:
        st.caption("Sincronizando dados locais...")
        st.stop() # Força o Python a esperar a resposta do navegador
    else:
        if memoria_bruta:
            try:
                dados_salvos = json.loads(memoria_bruta)
                st.session_state['leads_locais'] = dados_salvos.get('leads', [])
                st.session_state['rascunhos_locais'] = dados_salvos.get('rascunhos', [])
                st.session_state['config_sistema'] = dados_salvos.get('config', st.session_state['config_sistema'])
            except: pass
        st.session_state['memoria_carregada'] = True
        st.rerun()

# --- VALIDAÇÃO DE CPF & CEP ---
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
            r = requests.get(f"https://viacep.com.br/ws/{cep}/json/", timeout=3)
            if r.status_code == 200 and "erro" not in r.json(): return r.json()
        except: pass
    return None

# --- API GOOGLE CRUD ---
def api_google(payload):
    try:
        r = requests.post(URL_BACKEND_GOOGLE, data=json.dumps(payload), headers={"Content-Type": "application/json"}, timeout=12)
        return r.json() if r.status_code == 200 else None
    except: return None

def fetch_crm():
    res = api_google({"acao": "ler", "senha_api": SENHA_MESTRE_GESTAO, "aba_alvo": "VENDAS"})
    if res and res.get("status") == "sucesso":
        st.session_state['crm_dados'] = res.get("dados", [])
        return True
    return False

# ================= UI & ESTILIZAÇÃO =================
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
    .stTextInput>div>div>input:focus {{ border-color: {cor_tema} !important; }}
    ul[data-baseweb="menu"] {{ background-color: #171717 !important; border: 1px solid #333 !important; }}
    ul[data-baseweb="menu"] li {{ background-color: #171717 !important; color: #FFFFFF !important; }}
    div[data-baseweb="select"] > div {{ background-color: #171717 !important; border-color: #333 !important; color: #FFFFFF !important; }}
    .stButton>button {{ background-color: #171717; color: #FFF; border: 1px solid #333; border-radius: 8px; width: 100%; padding: 12px; font-weight: bold; }}
    .stButton>button:hover {{ border-color: {cor_tema}; color: {cor_tema}; background-color: #1A1A1A; }}
    .tile-card {{ border-radius: 10px; padding: 16px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }}
    .tile-card h4 {{ margin: 0 0 5px 0; color: #000 !important; font-size: 18px; font-weight: 800; }}
    .tile-card p {{ margin: 0; font-size: 14px; font-weight: 600; opacity: 0.8; color: #000 !important; }}
    .badge-container {{ display: flex; justify-content: space-between; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; }}
    .badge-box {{ flex: 1; background: #171717; border: 1px solid #333; border-radius: 8px; padding: 10px; text-align: center; min-width: 70px; }}
    .badge-num {{ display: block; font-size: 22px; font-weight: bold; color: {cor_tema}; }}
    .badge-label {{ font-size: 11px; color: #888 !important; text-transform: uppercase; }}
    .crm-row {{ background: #171717; border-left: 4px solid #333; padding: 15px; margin-bottom: 10px; border-radius: 6px; }}
    .crm-row.atencao {{ border-left-color: #EF4444; }}
    .crm-row.finalizada {{ border-left-color: #10B981; }}
    .crm-row.perdida {{ border-left-color: #6B7280; opacity: 0.6; }}
    .msg-box {{ padding: 12px; border-radius: 6px; margin: 10px 0; font-weight: 500; font-size: 14px; }}
    .msg-erro {{ background: #450a0a; border: 1px solid #7f1d1d; color: #fca5a5 !important; }}
    .msg-ok {{ background: #064e3b; border: 1px solid #065f46; color: #6ee7b7 !important; }}
    </style>
""", unsafe_allow_html=True)

def m_erro(t): st.markdown(f'<div class="msg-box msg-erro">❌ {t}</div>', unsafe_allow_html=True)
def m_ok(t): st.markdown(f'<div class="msg-box msg-ok">✅ {t}</div>', unsafe_allow_html=True)
def m_info(t): st.markdown(f'<div class="msg-box" style="background:#0A1929;border:1px solid #1E3A8A;color:#BFDBFE;">ℹ️ {t}</div>', unsafe_allow_html=True)

# ================= CÁLCULO DE BADGES =================
qtd_rascunhos = len(st.session_state['rascunhos_locais'])
qtd_leads = len(st.session_state['leads_locais'])
qtd_pendentes = qtd_atencao = qtd_finalizadas = 0
aviso_colunas = None

if st.session_state['crm_dados']:
    cabecalho = st.session_state['crm_dados'][0]
    linhas = st.session_state['crm_dados'][1:]

    if "Vendedor" not in cabecalho or "Status" not in cabecalho:
        aviso_colunas = "⚠️ Colunas 'Vendedor' ou 'Status' ausentes na planilha."
    else:
        idx_vendedor = cabecalho.index("Vendedor")
        idx_status = cabecalho.index("Status")
        linhas_vendedor = [l for l in linhas if len(l) > idx_vendedor and l[idx_vendedor] == st.session_state['vendedor_atual']]
        for l in linhas_vendedor:
            if len(l) > idx_status:
                stt = str(l[idx_status]).strip().lower()
                if stt in ["pendente", "nova"]: qtd_pendentes += 1
                elif stt == "atenção": qtd_atencao += 1
                elif stt == "instalada": qtd_finalizadas += 1

st.markdown(f"""
    <div class="badge-container">
        <div class="badge-box"><span class="badge-num">{qtd_leads}</span><span class="badge-label">Leads</span></div>
        <div class="badge-box"><span class="badge-num">{qtd_rascunhos}</span><span class="badge-label">Rascunhos</span></div>
        <div class="badge-box"><span class="badge-num">{qtd_pendentes}</span><span class="badge-label">Pendentes</span></div>
        <div class="badge-box" style="border-color:#EF4444;"><span class="badge-num" style="color:#EF4444;">{qtd_atencao}</span><span class="badge-label">Atenção</span></div>
        <div class="badge-box" style="border-color:#10B981;"><span class="badge-num" style="color:#10B981;">{qtd_finalizadas}</span><span class="badge-label">Finalizadas</span></div>
    </div>
""", unsafe_allow_html=True)
if aviso_colunas: m_erro(aviso_colunas)

# ================= ROTEADOR PRINCIPAL =================
col_nav1, col_nav2, col_nav3, col_nav4 = st.columns(4)
if col_nav1.button("📝 Venda"): st.session_state['aba_ativa'] = "Nova Venda"; st.rerun()
if col_nav2.button("📞 Leads"): st.session_state['aba_ativa'] = "Leads"; st.rerun()
if col_nav3.button("🗂️ CRM"): st.session_state['aba_ativa'] = "CRM"; st.rerun()
if col_nav4.button("⚙️ Admin"): st.session_state['aba_ativa'] = "Admin"; st.rerun()

st.markdown("---")

# ================= MÓDULO 1: LEADS =================
if st.session_state['aba_ativa'] == "Leads":
    st.subheader("Gestão de Leads")

    with st.form("form_novo_lead", clear_on_submit=True):
        c1, c2 = st.columns([3, 2])
        nome_l = c1.text_input("Nome do Contato")
        tel_l = c2.text_input("WhatsApp")
        cor_l = st.color_picker("Cor de Destaque", "#FCD34D")

        if st.form_submit_button("Salvar Lead"):
            if nome_l:
                st.session_state['leads_locais'].insert(0, {"id": gerar_chave_id('ld'), "nome": nome_l, "telefone": tel_l, "cor": cor_l, "data": datetime.now().strftime("%d/%m %H:%M")})
                salvar_memoria_local()
                st.rerun()
            else:
                m_erro("Informe o nome do contato.")

    if not st.session_state['leads_locais']: st.caption("Nenhum lead registrado.")

    for lead in st.session_state['leads_locais']:
        st.markdown(f"""
            <div class="tile-card" style="background-color: {lead['cor']};">
                <h4>{lead['nome']}</h4>
                <p>📞 {lead['telefone']} | 🕒 {lead['data']}</p>
            </div>
        """, unsafe_allow_html=True)

        c_btn1, c_btn2 = st.columns(2)
        if c_btn1.button("Iniciar Venda", key=f"cvt_{lead['id']}"):
            st.session_state['form_venda_cache'] = {"f_nome": lead['nome'], "f_whats": lead['telefone']}
            st.session_state['leads_locais'] = [l for l in st.session_state['leads_locais'] if l['id'] != lead['id']]
            salvar_memoria_local()
            st.session_state['aba_ativa'] = "Nova Venda"
            st.rerun()

        if c_btn2.button("Excluir", key=f"del_{lead['id']}"):
            st.session_state['leads_locais'] = [l for l in st.session_state['leads_locais'] if l['id'] != lead['id']]
            salvar_memoria_local()
            st.rerun()

# ================= MÓDULO 2: NOVA VENDA =================
elif st.session_state['aba_ativa'] == "Nova Venda":
    if st.session_state['rascunhos_locais']:
        with st.expander(f"📦 Rascunhos ({qtd_rascunhos})", expanded=False):
            for r in st.session_state['rascunhos_locais']:
                rc1, rc2 = st.columns([3, 1])
                rc1.markdown(f"**{r.get('f_nome', 'Sem Nome')}** - {r.get('f_operadora', 'S/ Op')}")
                if rc2.button("Carregar", key=f"load_{r['id']}"):
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
            email = st.text_input("Email" if cfg.get('obrigatorio_email', True) else "Email (Opcional)", value=cache.get('f_email', ''))

        st.subheader("Endereço & Serviço")
        col_cep, col_btn = st.columns([2, 1])
        with col_cep: cep = st.text_input("CEP", value=cache.get('f_cep', ''))
        with col_btn:
            if st.form_submit_button("Buscar CEP"):
                dc = buscar_cep(cep)
                if dc:
                    st.session_state['form_venda_cache'] = {**cache, 'f_nome': nome, 'f_cpf': cpf, 'f_whats': whats, 'f_email': email,
                                                              'f_cep': cep, 'f_rua': dc.get("logradouro", ""), 'f_bairro': dc.get("bairro", ""),
                                                              'f_operadora': operadora}
                    st.rerun()
                else: m_erro("CEP não localizado.")

        rua = st.text_input("Rua", value=cache.get('f_rua', ''))
        bairro = st.text_input("Bairro", value=cache.get('f_bairro', ''))

        lista_planos = ["Selecione"] + list(planos_da_op.keys())
        pl_idx = lista_planos.index(cache['f_plano']) if 'f_plano' in cache and cache['f_plano'] in lista_planos else 0
        plano = st.selectbox("Plano Solicitado", lista_planos, index=pl_idx)

        extras = {}
        for chave, config_c in cfg_campos.items():
            if config_c['ativo']:
                extras[chave] = st.text_input(f"{config_c['nome']}", value=cache.get(f'f_{chave}', ''))

        obs = st.text_area("Observações Internas", value=cache.get('f_obs', ''))

        c_sub1, c_sub2 = st.columns(2)
        btn_salvar_rascunho = c_sub1.form_submit_button("Salvar Rascunho")
        btn_enviar_oficial = c_sub2.form_submit_button("Finalizar e Enviar")

        if btn_salvar_rascunho:
            dados_r = {"id": gerar_chave_id('rsc'), "f_nome": nome, "f_cpf": cpf, "f_whats": whats, "f_email": email,
                       "f_cep": cep, "f_rua": rua, "f_bairro": bairro, "f_operadora": operadora, "f_plano": plano, "f_obs": obs}
            for k, v in extras.items(): dados_r[f"f_{k}"] = v
            st.session_state['rascunhos_locais'].insert(0, dados_r)
            salvar_memoria_local()
            st.session_state['form_venda_cache'] = {}
            st.rerun()

        if btn_enviar_oficial:
            if not nome or not cpf or operadora == "Selecione" or plano == "Selecione":
                m_erro("Verifique os campos obrigatórios (Nome, CPF, Operadora, Plano).")
            elif not validar_cpf(cpf):
                m_erro("Documento inválido.")
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
                    protocolo = gerar_chave_id("PAP")
                    
                    linha_dados = {
                        "tipo": "venda", "acao": "inserir", "protocolo": protocolo,
                        "nome": nome, "cpf": cpf, "mae": "", "email": email, "whats1": whats, "whats2": "",
                        "cep": cep, "rua": rua, "numero": "", "bairro": bairro, "referencia": "",
                        "operadora": operadora, "plano": plano, "valor_plano": valor_final_plano, "detalhes_plano": "",
                        "extra1": extras.get('extra1', ''), "extra2": extras.get('extra2', ''),
                        "status": "Pendente", "obs": obs, "vendedor": st.session_state['vendedor_atual']
                    }

                    with st.spinner("Enviando dados..."):
                        if api_google(linha_dados):
                            st.session_state['form_venda_cache'] = {}
                            fetch_crm()
                            st.session_state['aba_ativa'] = "CRM"
                            st.rerun()
                        else: m_erro("Erro de conexão. Salve o rascunho temporariamente.")

# ================= MÓDULO 3: GESTÃO CRM =================
elif st.session_state['aba_ativa'] == "CRM":
    st.subheader("Esteira de Vendas")

    if st.button("Sincronizar Base de Dados"):
        with st.spinner("Atualizando registros..."): fetch_crm()

    if not st.session_state['crm_dados']:
        m_info("Base de dados vazia. Realize a sincronização.")
    else:
        cabecalho = st.session_state['crm_dados'][0]
        linhas_raw = st.session_state['crm_dados'][1:]

        if "Protocolo" not in cabecalho or "Status" not in cabecalho:
            m_erro("Planilha inválida. Faltam colunas de registro.")
        else:
            c_map = {nome: idx for idx, nome in enumerate(cabecalho)}
            
            if "Vendedor" not in c_map: linhas = linhas_raw
            else: linhas = [l for l in linhas_raw if len(l) > c_map['Vendedor'] and str(l[c_map['Vendedor']]) == st.session_state['vendedor_atual']]

            filtro_status = st.selectbox("Filtro de Status", ["⏳ Pendentes", "⚠️ Atenção", "✅ Finalizadas", "❌ Canceladas / Reprovadas"])
            
            idx_valor_recebido = c_map.get('ValorRecebido', len(cabecalho))

            for i_linha, linha in enumerate(linhas):
                while len(linha) <= idx_valor_recebido: linha.append("")

                prot = linha[c_map['Protocolo']]
                nome_c = linha[c_map.get('Nome', 2)] 
                whats_c = linha[c_map.get('Whats1', 6)]
                op_c = linha[c_map.get('Operadora', 13)] 
                plano_c = linha[c_map.get('Plano', 14)] 

                status_raw = str(linha[c_map['Status']]).strip()
                status_clean = status_raw.lower()
                data_c = str(linha[c_map.get('Data', 0)])[:10]
                val_recebido = linha[idx_valor_recebido]

                cor_linha, mostrar = "", False
                if filtro_status == "⏳ Pendentes" and status_clean in ["pendente", "nova"]: mostrar = True
                elif filtro_status == "⚠️ Atenção" and status_clean == "atenção": mostrar, cor_linha = True, "atencao"
                elif filtro_status == "✅ Finalizadas" and status_clean == "instalada": mostrar, cor_linha = True, "finalizada"
                elif filtro_status == "❌ Canceladas / Reprovadas" and status_clean in ["cancelada", "reprova
