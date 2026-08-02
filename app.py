import streamlit as st
import requests
import json
import re
import urllib.parse
from datetime import datetime
from streamlit_local_storage import LocalStorage

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

st.set_page_config(page_title="PAP Fibra", page_icon="📶", layout="centered")
local_storage = LocalStorage()

# ================= ESTILIZAÇÃO (CSS) =================
def aplicar_css(cor_tema):
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
        .stButton>button {{ 
            background-color: #171717; color: #FFF; border: 1px solid #333; 
            border-radius: 8px; width: 100%; padding: 12px; font-weight: bold; transition: 0.3s;
        }}
        .stButton>button:hover {{ border-color: {cor_tema}; color: {cor_tema}; background-color: #1A1A1A; }}
        .tile-card {{ background-color: #171717; border-radius: 10px; padding: 16px; margin-bottom: 15px; border-left: 5px solid {cor_tema}; }}
        .tile-card h4 {{ margin: 0 0 5px 0; color: #FFF !important; font-size: 18px; }}
        .tile-card p {{ margin: 0; font-size: 14px; color: #AAA !important; }}
        .crm-row {{ background: #171717; border-left: 4px solid #333; padding: 15px; margin-bottom: 10px; border-radius: 6px; }}
        .crm-row.atencao {{ border-left-color: #EF4444; }}
        .crm-row.finalizada {{ border-left-color: #10B981; }}
        </style>
    """, unsafe_allow_html=True)

# ================= FUNÇÕES AUXILIARES =================
def gerar_chave_id(prefixo):
    return f"{prefixo}_{datetime.now().strftime('%H%M%S%f')}"

def blindar_texto(texto):
    if not isinstance(texto, str): 
        return texto
    texto_limpo = texto.strip()
    if texto_limpo.startswith(('=', '+', '-', '@')): 
        return f"'{texto_limpo}"
    return texto_limpo

def salvar_memoria_local():
    dados = {
        "leads": st.session_state['leads_locais'],
        "rascunhos": st.session_state['rascunhos_locais'],
        "config": st.session_state['config_sistema']
    }
    try:
        local_storage.setItem("pap_memoria_v3", json.dumps(dados), key="write_memoria_unica")
    except Exception as e:
        st.toast(f"Erro ao salvar localmente: {e}")

def carregar_memoria_silenciosa():
    if not st.session_state.get('memoria_carregada'):
        memoria_bruta = local_storage.getItem("pap_memoria_v3")
        if memoria_bruta:
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

# ================= VALIDAÇÕES =================
def validar_cpf_cnpj(documento):
    doc = re.sub(r'[^0-9]', '', str(documento))
    if len(doc) == 11: 
        if doc == doc[0] * 11: return False
        for i in range(9, 11):
            val = sum((int(doc[num]) * ((i + 1) - num) for num in range(0, i)))
            if ((val * 10) % 11) % 10 != int(doc[i]): return False
        return True
    elif len(doc) == 14: 
        if doc == doc[0] * 14: return False
        pesos = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        for i in range(12, 14):
            soma = sum(int(doc[num]) * pesos[num + 14 - i] for num in range(i))
            digito = 11 - (soma % 11)
            if digito >= 10: digito = 0
            if digito != int(doc[i]): return False
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
def criar_ficha_notion(nome, telefone, texto_ficha="", status_notion="Não iniciada"):
    if not NOTION_TOKEN or not NOTION_DATABASE_ID: 
        return False, "Notion não configurado."
    
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}", 
        "Content-Type": "application/json", 
        "Notion-Version": "2022-06-28"
    }
    telefone_limpo = re.sub(r'[^0-9+]', '', str(telefone))[:20] if telefone else ""
    
    data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Nome": {"title": [{"text": {"content": str(nome)[:100]}}]},
            "Status": {"status": {"name": status_notion}},
            "Telefone": {"phone_number": telefone_limpo},
            "Data": {"date": {"start": datetime.now().strftime("%Y-%m-%d")}}
        }
    }
    
    if texto_ficha:
        data["children"] = [{
            "object": "block", "type": "paragraph", 
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": texto_ficha}}]}
        }]
        
    try:
        r = requests.post(url, headers=headers, json=data, timeout=8)
        return (True, "Sucesso") if r.status_code == 200 else (False, f"Erro: {r.text}")
    except Exception as e:
        return False, str(e)

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
        return True
    return False

def formatar_ficha_texto(d):
    f = f"📄 *NOVA VENDA*\n\n👤 *CLIENTE*\nNome: {d['nome']}\nDoc: {d['cpf']}\n"
    if d.get('email'): 
        f += f"Email: {d['email']}\n"
    f += f"\n📞 *CONTATO*\nWhatsApp: {d['whats1']}\n\n📍 *ENDEREÇO*\nCEP: {d['cep']}\n{d['rua']}, Nº {d.get('numero','')} - {d['bairro']}\n\n📶 *SERVIÇO*\nOperadora: {d['operadora']}\nPlano: {d['plano']}"
    if d.get('obs'): 
        f += f"\n\n📝 *OBSERVAÇÕES*\n{d['obs']}"
    return f

# ================= INICIALIZAÇÃO DE ESTADO =================
def inicializar_estado():
    defaults = {
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
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# ================= COMPONENTES VISUAIS =================
def renderizar_badges():
    qtd_rascunhos = len(st.session_state['rascunhos_locais'])
    qtd_leads = len(st.session_state['leads_locais'])
    qtd_pendentes = qtd_atencao = qtd_finalizadas = 0
    linhas_vendedor = []

    if st.session_state['crm_dados'] and len(st.session_state['crm_dados']) > 1:
        linhas_reais = st.session_state['crm_dados'][1:]
        for l in linhas_reais:
            while len(l) < 23: l.append("")
            if str(l[21]) == st.session_state['vendedor_atual'] and str(l[1]).startswith("PAP"):
                linhas_vendedor.append(l)
                stt = str(l[19]).strip().lower()
                if stt in ["pendente", "nova"]: qtd_pendentes += 1
                elif stt == "atenção": qtd_atencao += 1
                elif stt == "instalada": qtd_finalizadas += 1

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Leads", qtd_leads)
    col2.metric("Rascunhos", qtd_rascunhos)
    col3.metric("Pendentes", qtd_pendentes)
    col4.metric("Atenção", qtd_atencao)
    col5.metric("Finalizadas", qtd_finalizadas)
    
    return linhas_vendedor

def renderizar_navegacao():
    col_nav1, col_nav2, col_nav3, col_nav4 = st.columns(4)
    if col_nav1.button("📝 Venda"): 
        st.session_state['aba_ativa'] = "Nova Venda"
        st.rerun()
    if col_nav2.button("📞 Leads"): 
        st.session_state['aba_ativa'] = "Leads"
        st.rerun()
    if col_nav3.button("🗂️ CRM"): 
        st.session_state['aba_ativa'] = "CRM"
        st.rerun()
    if col_nav4.button("⚙️ Admin"): 
        st.session_state['aba_ativa'] = "Admin"
        st.rerun()
    st.markdown("---")

# ================= MÓDULOS DA APLICAÇÃO =================
def modulo_leads():
    st.subheader("Gestão de Leads Rápida")
    with st.form("form_novo_lead", clear_on_submit=True):
        c1, c2 = st.columns([3, 2])
        nome_l = c1.text_input("Nome do Contato")
        tel_l = c2.text_input("WhatsApp")
        cor_l = st.color_picker("Cor de Destaque", "#FCD34D")

        if st.form_submit_button("Salvar Lead"):
            if nome_l:
                novo_lead = {
                    "id": gerar_chave_id('ld'), "nome": nome_l, 
                    "telefone": tel_l, "cor": cor_l, 
                    "data": datetime.now().strftime("%d/%m %H:%M")
                }
                st.session_state['leads_locais'].insert(0, novo_lead)
                salvar_memoria_local()
                criar_ficha_notion(nome_l, tel_l, status_notion="Não iniciada")
                st.rerun()
            else:
                st.error("Informe o nome do contato.")

    for lead in st.session_state['leads_locais']:
        st.markdown(f"""
            <div class="tile-card" style="border-left-color: {lead['cor']};">
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

def modulo_venda():
    if st.session_state['rascunhos_locais']:
        with st.expander(f"📦 Seus Rascunhos ({len(st.session_state['rascunhos_locais'])})", expanded=False):
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
    op_idx = ops.index(cache['f_operadora']) if cache.get('f_operadora') in ops else 0
    operadora = st.selectbox("Operadora", ops, index=op_idx, key='sel_op_livre')
    planos_da_op = st.session_state['planos_dinamicos'].get(operadora, {}) if operadora != "Selecione" else {}

    with st.form("form_motor_vendas", clear_on_submit=False):
        st.subheader("Dados do Cliente")
        nome = st.text_input("Nome Completo", value=cache.get('f_nome', ''))
        cpf = st.text_input("CPF / CNPJ", value=cache.get('f_cpf', ''))
        whats = st.text_input("WhatsApp", value=cache.get('f_whats', ''))
        email = st.text_input("Email", value=cache.get('f_email', '')) if cfg.get('pedir_email', True) else ""

        st.subheader("Endereço & Serviço")
        col_cep, col_btn = st.columns([2, 1])
        with col_cep: 
            cep = st.text_input("CEP", value=cache.get('f_cep', ''))
        with col_btn:
            # Fake label para alinhar o botão com o input
            st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
            if st.form_submit_button("Buscar CEP"):
                dc = buscar_cep(cep)
                if dc == "erro_conexao": 
                    st.error("Falha de rede ao buscar CEP.")
                elif dc:
                    st.session_state['form_venda_cache'] = {
                        **cache, 'f_nome': nome, 'f_cpf': cpf, 'f_whats': whats, 'f_email': email, 
                        'f_cep': cep, 'f_rua': dc.get("logradouro", ""), 'f_bairro': dc.get("bairro", ""), 'f_operadora': operadora
                    }
                    st.rerun()
                else: 
                    st.error("CEP não localizado.")

        rua = st.text_input("Rua", value=cache.get('f_rua', ''))
        numero_end = st.text_input("Número", value=cache.get('f_numero', ''))
        bairro = st.text_input("Bairro", value=cache.get('f_bairro', ''))

        lista_planos = ["Selecione"] + list(planos_da_op.keys())
        pl_idx = lista_planos.index(cache['f_plano']) if cache.get('f_plano') in lista_planos else 0
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
            dados_r = {
                "id": gerar_chave_id('rsc'), "f_nome": nome, "f_cpf": cpf, "f_whats": whats, 
                "f_email": email, "f_cep": cep, "f_rua": rua, "f_numero": numero_end, 
                "f_bairro": bairro, "f_operadora": operadora, "f_plano": plano, "f_obs": obs
            }
            for k, v in extras.items(): 
                dados_r[f"f_{k}"] = v
                
            st.session_state['rascunhos_locais'].insert(0, dados_r)
            salvar_memoria_local()
            st.session_state['form_venda_cache'] = {}
            st.rerun()

        if btn_enviar_oficial:
            if not nome or not cpf or operadora == "Selecione" or plano == "Selecione":
                st.error("Verifique os campos obrigatórios (Nome, CPF, Operadora e Plano).")
            elif not validar_cpf_cnpj(cpf): 
                st.error("Documento inválido.")
            elif cfg.get('pedir_email', True) and cfg.get('obrigatorio_email', True) and not email: 
                st.error("Email obrigatório.")
            else:
                falhou_obrig = False
                for chave, config_c in cfg_campos.items():
                    if config_c['ativo'] and operadora in config_c['obrig_operadoras'] and not extras.get(chave):
                        st.error(f"Preencha o campo obrigatório: {config_c['nome']}")
                        falhou_obrig = True
                
                if not falhou_obrig:
                    protocolo = gerar_chave_id("PAP")
                    dados_venda_form = {
                        "nome": nome, "cpf": cpf, "whats1": whats, "email": email, "cep": cep, 
                        "rua": rua, "numero": numero_end, "bairro": bairro, "operadora": operadora, 
                        "plano": plano, "obs": obs
                    }
                    
                    linha_dados = {
                        "tipo": "venda", "acao": "inserir", "protocolo": protocolo,
                        "nome": blindar_texto(nome), "cpf": cpf, "mae": "", "email": blindar_texto(email), 
                        "whats1": blindar_texto(whats), "whats2": "", "cep": blindar_texto(cep), 
                        "rua": blindar_texto(rua), "numero": blindar_texto(numero_end), 
                        "bairro": blindar_texto(bairro), "referencia": "",
                        "operadora": operadora, "plano": plano, "valor_plano": planos_da_op.get(plano, 0.00), 
                        "detalhes_plano": "", "extra1": blindar_texto(extras.get('extra1', '')), 
                        "extra2": blindar_texto(extras.get('extra2', '')),
                        "status": "Pendente", "obs": blindar_texto(obs), "vendedor": st.session_state['vendedor_atual']
                    }

                    with st.spinner("Enviando dados..."):
                        resposta = api_google(linha_dados)
                        if resposta and resposta.get('status') == 'sucesso':
                            st.session_state['form_venda_cache'] = {}
                            ficha_texto = formatar_ficha_texto(dados_venda_form)
                            criar_ficha_notion(nome, whats, ficha_texto, "Em progresso")
                            
                            st.success("Venda enviada com sucesso!")
                            st.code(ficha_texto, language="text")
                            link_wpp = f"https://api.whatsapp.com/send?text={urllib.parse.quote_plus(ficha_texto)}"
                            st.markdown(f'<a href="{link_wpp}" target="_blank"><button style="background-color: #25D366; color: #000; width: 100%; border: none; padding: 14px; border-radius: 8px; font-weight: bold;">📲 Enviar Ficha WhatsApp</button></a>', unsafe_allow_html=True)
                        else: 
                            st.error("Falha ao salvar no Google Sheets.")

def modulo_crm(linhas_vendedor):
    st.subheader("Esteira de Vendas")
    if st.button("Sincronizar Base"):
        with st.spinner("Atualizando base de dados..."): 
            fetch_crm()

    if not linhas_vendedor:
        st.info("Nenhuma venda sincronizada para o seu usuário.")
        return

    filtro_status = st.selectbox("Filtrar por Status", ["Pendentes", "Atenção", "Finalizadas", "Canceladas"])
    
    for linha in linhas_vendedor:
        prot, op_c, plano_c, status_raw, val_recebido = linha[1], linha[13], linha[14], str(linha[19]).strip(), linha[22]
        status_clean = status_raw.lower()

        cor_linha, mostrar = "", False
        if filtro_status == "Pendentes" and status_clean in ["pendente", "nova"]: mostrar = True
        elif filtro_status == "Atenção" and status_clean == "atenção": mostrar, cor_linha = True, "atencao"
        elif filtro_status == "Finalizadas" and status_clean == "instalada": mostrar, cor_linha = True, "finalizada"
        elif filtro_status == "Canceladas" and status_clean in ["cancelada", "reprovada"]: mostrar = True

        if mostrar:
            st.markdown(f'<div class="crm-row {cor_linha}">', unsafe_allow_html=True)
            c_info, c_act = st.columns([3, 2])
            with c_info:
                st.markdown(f"**{linha[2]}** ({op_c})")
                st.caption(f"{linha[0][:10]} | 📱 {linha[6]} | 📦 {plano_c}")
                if status_clean == "instalada": 
                    st.markdown(f"Faturamento: **R$ {val_recebido}**")

            with c_act:
                opts_status = ["Pendente", "Atenção", "Instalada", "Reprovada", "Cancelada"]
                idx_st = opts_status.index(status_raw.capitalize()) if status_raw.capitalize() in opts_status else 0
                novo_st = st.selectbox("Status", opts_status, index=idx_st, key=f"st_{prot}")

                novo_val = val_recebido
                if novo_st == "Instalada":
                    novo_val = st.text_input("Valor Líquido (R$)", value=val_recebido, key=f"val_{prot}")

                col_b1, col_b2 = st.columns(2)
                if col_b1.button("Salvar", key=f"sv_{prot}"):
                    linha[19] = novo_st
                    if novo_st == "Instalada": 
                        linha[22] = blindar_texto(novo_val)
                        
                    payload = {"acao": "editar", "senha_api": SENHA_MESTRE_GESTAO, "id_busca": prot, "coluna_busca": 1, "novos_dados": linha}
                    with st.spinner("Processando..."):
                        if api_google(payload):
                            st.toast("Status atualizado com sucesso!")
                            fetch_crm()
                            st.rerun()
                        else: 
                            st.error("Falha de gravação.")

                link_agenda = f"https://calendar.google.com/calendar/render?action=TEMPLATE&text=Retorno+{urllib.parse.quote(str(linha[2]))}&details=Whats:+{linha[6]}"
                col_b2.markdown(f'<a href="{link_agenda}" target="_blank"><button style="width:100%; padding:8px; border-radius:6px; background:#2563EB; border:none; color:#FFF;">Agendar</button></a>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

def modulo_admin(linhas_vendedor):
    if not st.session_state['modo_gestao_liberado']:
        senha = st.text_input("Senha de Acesso", type="password")
        if st.button("Acessar"):
            if senha == SENHA_MESTRE_GESTAO:
                st.session_state['modo_gestao_liberado'] = True
                st.rerun()
            else: 
                st.error("Credenciais inválidas.")
        return

    st.subheader("Painel de Administração")
    if st.button("Sair do Painel"):
        st.session_state['modo_gestao_liberado'] = False
        st.rerun()

    tb1, tb2 = st.tabs(["Campos Customizados", "Relatórios"])
    with tb1:
        cfg = st.session_state['config_sistema']
        ops_disponiveis = list(st.session_state['planos_dinamicos'].keys())
        with st.form("form_admin_campos"):
            for chave_campo in ["extra1", "extra2"]:
                cc = cfg['campos_dinamicos'][chave_campo]
                st.markdown(f"**Variável: {chave_campo.upper()}**")
                st.checkbox("Habilitar", value=cc['ativo'], key=f"atv_{chave_campo}")
                st.text_input("Rótulo", value=cc['nome'], key=f"nm_{chave_campo}")
                st.multiselect("Obrigatório em:", ops_disponiveis, default=cc['obrig_operadoras'], key=f"ob_{chave_campo}")
                st.markdown("---")
            
            if st.form_submit_button("Salvar Configurações"):
                cfg['campos_dinamicos']['extra1'] = {'ativo': st.session_state['atv_extra1'], 'nome': st.session_state['nm_extra1'], 'obrig_operadoras': st.session_state['ob_extra1']}
                cfg['campos_dinamicos']['extra2'] = {'ativo': st.session_state['atv_extra2'], 'nome': st.session_state['nm_extra2'], 'obrig_operadoras': st.session_state['ob_extra2']}
                salvar_memoria_local()
                st.success("Configurações registradas com sucesso.")

    with tb2:
        if not linhas_vendedor:
            st.info("Sincronize o CRM para visualizar relatórios.")
        else:
            lucro_total, instaladas, perdidas = 0.0, 0, 0
            for l in linhas_vendedor:
                stt = str(l[19]).strip().lower()
                if stt == "instalada":
                    instaladas += 1
                    if len(l) > 22 and l[22]:
                        try: lucro_total += float(str(l[22]).replace(',', '.'))
                        except ValueError: pass
                elif stt in ["reprovada", "cancelada"]: 
                    perdidas += 1

            st.metric("Total Liquidado", f"R$ {lucro_total:.2f}")
            c_met1, c_met2 = st.columns(2)
            c_met1.metric("Contratos Instalados", instaladas)
            c_met2.metric("Cancelamentos", perdidas)

# ================= EXECUÇÃO PRINCIPAL =================
def main():
    inicializar_estado()
    carregar_memoria_silenciosa()
    aplicar_css(st.session_state['config_sistema'].get('tema_cor', '#3B82F6'))

    # Topbar / Header
    linhas_vendedor = renderizar_badges()
    renderizar_navegacao()

    # Roteamento
    aba = st.session_state['aba_ativa']
    if aba == "Leads":
        modulo_leads()
    elif aba == "Nova Venda":
        modulo_venda()
    elif aba == "CRM":
        modulo_crm(linhas_vendedor)
    elif aba == "Admin":
        modulo_admin(linhas_vendedor)

if __name__ == "__main__":
    main()
