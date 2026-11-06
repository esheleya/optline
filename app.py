"""OptiLine — Balanceador de linha de costura com RPW e restrições de recursos."""
import io
import math
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import networkx as nx

st.set_page_config(page_title="OptiLine — Célula de Costura", page_icon="🧵", layout="wide")
MACHINE_TYPES = ["Overloque", "Reta", "Franzidor", "Galoneira"]
DEFAULT_MACHINE_LIMITS = {"Overloque": 4, "Reta": 3, "Franzidor": 2, "Galoneira": 1}
DEFAULT_SKILLS = pd.DataFrame([
    ["A",1,0,0,1],["B",1,0,1,1],["C",1,0,0,0],["D",1,0,0,0],
    ["E",1,0,0,0],["F",1,1,1,0],["G",1,1,0,0],["H",0,1,0,0]],
    columns=["Costureira", *MACHINE_TYPES])
EXAMPLE = pd.DataFrame([
    ["O01","Chulear babado alça",0.371,"Overloque","-"],
    ["O02","Franzir babado nas alças",0.979,"Franzidor","O01"],
    ["O03","Unir frente e cavas com forro",0.332,"Overloque","-"],
    ["O04","Unir costas e cavas com forro",0.558,"Overloque","-"],
    ["O05","Pespontar frente e cavas",0.487,"Reta","O03"],
    ["O06","Pespontar costas e cavas",0.957,"Reta","O04"],
    ["O07","Pespontar alças",2.468,"Reta","O02"],
    ["O08","Fechar laterais",0.420,"Overloque","O05,O06"],
    ["O09","Unir saia menor",0.735,"Overloque","-"],
    ["O10","Chulear acabamento da saia menor",0.228,"Overloque","O09"],
    ["O11","Unir saia maior",0.698,"Overloque","-"],
    ["O12","Chulear acabamento da saia maior",0.228,"Overloque","O11"],
    ["O13","Unir saias na parte superior",1.287,"Overloque","O10,O12"],
    ["O14","Fechar costa da saia",0.707,"Overloque","O13"],
    ["O15","Chulear barra menor e maior",0.387,"Overloque","O14"],
    ["O16","Apanhar saias",2.165,"Reta","O13"]],
    columns=["ID","Operação","Tempo","Equipamento","Predecessores"])


def normalize_operations(df):
    df = df.copy()
    aliases = {"Tarefa":"ID", "Descrição":"Operação", "Tempo padrão":"Tempo", "Máquina":"Equipamento"}
    df = df.rename(columns={a:b for a,b in aliases.items() if a in df.columns})
    for c in ["ID","Operação","Tempo","Equipamento","Predecessores"]:
        if c not in df.columns: df[c] = 0.0 if c == "Tempo" else ""
    df["ID"] = df["ID"].fillna("").astype(str).str.strip().str.upper()
    df["Operação"] = df["Operação"].fillna("").astype(str).str.strip()
    df["Tempo"] = pd.to_numeric(df["Tempo"], errors="coerce").fillna(0.0)
    df["Equipamento"] = df["Equipamento"].fillna("").astype(str).str.strip()
    df["Predecessores"] = df["Predecessores"].fillna("-").astype(str).str.strip().replace("", "-")
    return df[["ID","Operação","Tempo","Equipamento","Predecessores"]]


def parse_preds(v):
    if pd.isna(v) or str(v).strip() in ("", "-"): return []
    return [x.strip().upper() for x in str(v).split(",") if x.strip()]


def build_model(df):
    df = normalize_operations(df); df = df[df["ID"] != ""].copy()
    ids = df["ID"].tolist(); times = dict(zip(ids, df["Tempo"].astype(float)))
    names = dict(zip(ids, df["Operação"])); machines = dict(zip(ids, df["Equipamento"]))
    predecessors = {x:[] for x in ids}; successors = {x:[] for x in ids}
    for _, row in df.iterrows():
        op = row["ID"]; predecessors[op] = parse_preds(row["Predecessores"])
        for p in predecessors[op]:
            if p in successors:
                successors[p].append(op)
    return ids,times,names,machines,predecessors,successors,df


def validate(ids,times,machines,predecessors,takt,limits,skills):
    if not ids: return False,"Inclua pelo menos uma operação."
    if len(ids) != len(set(ids)): return False,"Há IDs de operação duplicados."
    if takt <= 0: return False,"O tempo de ciclo deve ser maior que zero."
    if any(times[x] <= 0 for x in ids): return False,"Todos os tempos devem ser maiores que zero."
    missing = sorted({p for ps in predecessors.values() for p in ps if p not in ids})
    if missing: return False,f"Predecessor(es) inexistente(s): {', '.join(missing)}."
    if any(machines[x] not in MACHINE_TYPES for x in ids): return False,"Escolha um equipamento válido para todas as operações."
    long = [x for x in ids if times[x] > takt]
    if long: return False,f"Operação acima do tempo de ciclo: {', '.join(long)}."
    g=nx.DiGraph(); g.add_nodes_from(ids)
    for op,ps in predecessors.items(): g.add_edges_from((p,op) for p in ps)
    if list(nx.simple_cycles(g)): return False,"Existem ciclos nas precedências."
    if not skills: return False,"Cadastre pelo menos uma costureira."
    for m in set(machines.values()):
        if not any(m in s and int(s.get(m,0)) == 1 for s in skills): return False,f"Nenhuma costureira habilitada para {m}."
    return True,""


def positional_weights(ids,times,successors):
    memo={}
    def w(op):
        if op not in memo: memo[op]=times[op]+sum(w(s) for s in successors[op])
        return memo[op]
    return {op:w(op) for op in ids}


def allocate_rpw(ids,times,machines,predecessors,successors,takt,limits,skills):
    weights=positional_weights(ids,times,successors)
    order=sorted(ids,key=lambda x:(-weights[x],x)); pending=list(order); assigned=set(); stations=[]
    skill_map={str(s["Costureira"]):{m for m in MACHINE_TYPES if int(s.get(m,0))==1} for s in skills}
    while pending:
        available=[op for op in pending if all(p in assigned for p in predecessors[op])]
        if not available: return None,weights,"Não foi possível resolver a ordem de precedência."
        placed=False
        for op in available:
            machine=machines[op]
            candidates=[s for s in stations if s["Equipamento"]==machine and s["Tempo"]+times[op] <= takt+1e-9 and machine in skill_map.get(s["Costureira"],set())]
            if candidates:
                target=min(candidates,key=lambda s:s["Tempo"]); target["Operações"].append(op); target["Tempo"]+=times[op]
                assigned.add(op); pending.remove(op); placed=True; continue
            if sum(s["Equipamento"]==machine for s in stations) >= int(limits.get(machine,0)): continue
            used={s["Costureira"] for s in stations}
            eligible=[w for w,ms in skill_map.items() if machine in ms and w not in used]
            if eligible:
                worker=min(eligible,key=lambda w:sum(s["Tempo"] for s in stations if s["Costureira"]==w))
                stations.append({"Costureira":worker,"Equipamento":machine,"Operações":[op],"Tempo":times[op]})
                assigned.add(op); pending.remove(op); placed=True
        if not placed:
            op=available[0]
            return None,weights,f"Não foi possível alocar {op} ({machines[op]}). Verifique tempo de ciclo, máquinas e habilidades."
    return stations,weights,""


def calc_metrics(stations,times,takt):
    loads=[s["Tempo"] for s in stations]; total=sum(times.values()); n=len(stations); mx=max(loads,default=0)
    return {"n":n,"total":total,"loads":loads,"tc":mx,"eff":total/(n*takt)*100 if n else 0,"idle":n*takt-total if n else 0,"smooth":math.sqrt(sum((mx-x)**2 for x in loads)) if loads else 0,"theoretical":math.ceil(total/takt) if takt else 0}


def precedence_graph(ids,times,names,predecessors,station_of=None):
    g=nx.DiGraph(); g.add_nodes_from(ids)
    for op,ps in predecessors.items(): g.add_edges_from((p,op) for p in ps)
    depth={x:0 for x in ids}
    try:
        for x in nx.topological_sort(g): depth[x]=max([depth[p]+1 for p in g.predecessors(x)] or [0])
    except nx.NetworkXUnfeasible: pass
    groups={}
    for x,d in depth.items(): groups.setdefault(d,[]).append(x)
    pos={}
    for d,group in groups.items():
        for i,x in enumerate(sorted(group)): pos[x]=(d*2.4,-(i-(len(group)-1)/2)*1.4)
    ex=[]; ey=[]
    for a,b in g.edges(): ex += [pos[a][0],pos[b][0],None]; ey += [pos[a][1],pos[b][1],None]
    palette=["#2E86AB","#A23B72","#F18F01","#3CB371","#C73E1D","#6A4C93","#1982C4","#FFCA3A"]
    colors=[station_of.get(x,0) if station_of else 0 for x in ids]
    fig=go.Figure(); fig.add_trace(go.Scatter(x=ex,y=ey,mode="lines",line=dict(color="#999",width=1.5),hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=[pos[x][0] for x in ids],y=[pos[x][1] for x in ids],mode="markers+text",text=ids,textposition="middle center",marker=dict(size=52,color=[palette[c%len(palette)] for c in colors],line=dict(width=2,color="white")),hovertext=[f"{x} — {names[x]}<br>Tempo: {times[x]:.3f}" for x in ids],hoverinfo="text",textfont=dict(color="white",size=11)))
    fig.update_layout(height=480,showlegend=False,plot_bgcolor="white",xaxis=dict(visible=False),yaxis=dict(visible=False,scaleanchor="x",scaleratio=1),margin=dict(t=20,b=20,l=10,r=10))
    return fig


def build_xlsx(result,weight_df,met,takt,limits,skills):
    buf=io.BytesIO()
    with pd.ExcelWriter(buf,engine="xlsxwriter") as writer:
        result.to_excel(writer,sheet_name="Distribuição",index=False); weight_df.to_excel(writer,sheet_name="Pesos RPW",index=False)
        pd.DataFrame([{"Indicador":"Tempo de ciclo","Valor":takt},{"Indicador":"Postos","Valor":met["n"]},{"Indicador":"Eficiência (%)","Valor":met["eff"]},{"Indicador":"Ociosidade total","Valor":met["idle"]},{"Indicador":"Índice de suavidade","Valor":met["smooth"]}]).to_excel(writer,sheet_name="Indicadores",index=False)
        pd.DataFrame([{"Equipamento":m,"Disponível":v,"Utilizado":int((result["Equipamento"]==m).sum())} for m,v in limits.items()]).to_excel(writer,sheet_name="Máquinas",index=False)
        skills.to_excel(writer,sheet_name="Habilidades",index=False)
    return buf.getvalue()


st.sidebar.header("⚙️ Parâmetros da célula")
mode=st.sidebar.radio("Definição do tempo de ciclo",["Tempo disponível e demanda","Valor direto"])
if mode=="Tempo disponível e demanda":
    available=st.sidebar.number_input("Tempo disponível por turno (min)",min_value=1.0,value=480.0,step=10.0)
    demand=st.sidebar.number_input("Demanda por turno (peças)",min_value=1,value=216,step=1); takt=available/demand
else: takt=st.sidebar.number_input("Tempo de ciclo (min/peça)",min_value=0.001,value=2.5,step=0.1)
st.sidebar.metric("Tempo de ciclo",f"{takt:.3f} min")
st.sidebar.subheader("Máquinas disponíveis")
limits={m:st.sidebar.number_input(m,min_value=0,max_value=20,value=DEFAULT_MACHINE_LIMITS[m],step=1) for m in MACHINE_TYPES}
st.sidebar.subheader("Habilidades das costureiras")
if "skills" not in st.session_state: st.session_state["skills"]=DEFAULT_SKILLS.copy()
skills_edited=st.sidebar.data_editor(st.session_state["skills"],num_rows="dynamic",hide_index=True,use_container_width=True,key="skills_editor"); skills=skills_edited.to_dict("records")

st.title("🧵 OptiLine — Balanceador da Célula de Costura")
st.caption("Alocação por RPW respeitando precedência, tempo de ciclo, máquinas disponíveis e habilidades das costureiras.")
if "operations" not in st.session_state: st.session_state["operations"]=EXAMPLE.copy()
c1,c2,c3=st.columns([1,1,2])
if c1.button("Carregar exemplo da proposta",use_container_width=True): st.session_state["operations"]=EXAMPLE.copy(); st.rerun()
if c2.button("Limpar",use_container_width=True): st.session_state["operations"]=pd.DataFrame(columns=EXAMPLE.columns); st.rerun()
up=c3.file_uploader("Importar CSV/XLSX",type=["csv","xlsx"])
if up:
    try: st.session_state["operations"]=normalize_operations(pd.read_excel(up) if up.name.endswith("xlsx") else pd.read_csv(up)); st.success("Arquivo carregado.")
    except Exception as exc: st.error(f"Falha ao importar: {exc}")
st.subheader("1. Operações do processo")
st.caption("Informe ID, operação, tempo padrão, equipamento e predecessoras separadas por vírgula.")
edited=st.data_editor(normalize_operations(st.session_state["operations"]),num_rows="dynamic",use_container_width=True,height=410,column_config={"ID":st.column_config.TextColumn(required=True),"Operação":st.column_config.TextColumn(required=True),"Tempo":st.column_config.NumberColumn(min_value=0.001,format="%.3f",required=True),"Equipamento":st.column_config.SelectboxColumn(options=MACHINE_TYPES,required=True),"Predecessores":st.column_config.TextColumn(help="Use - ou IDs separados por vírgula")},key="operations_editor")
if not edited.empty:
    ids,times,names,machines,predecessors,successors,_=build_model(edited)
    st.info(f"{len(ids)} operações | Tempo total: {sum(times.values()):.3f} min | Mínimo teórico de postos: {math.ceil(sum(times.values())/takt) if takt else 0}")
    st.subheader("2. Diagrama de precedência"); st.plotly_chart(precedence_graph(ids,times,names,predecessors),use_container_width=True)

st.divider(); run=st.button("🚀 Gerar balanceamento RPW",type="primary",use_container_width=True)
if run:
    ids,times,names,machines,predecessors,successors,df=build_model(edited); ok,msg=validate(ids,times,machines,predecessors,takt,limits,skills)
    if not ok: st.error(msg); st.stop()
    stations,weights,error=allocate_rpw(ids,times,machines,predecessors,successors,takt,limits,skills)
    if error: st.error(error); st.stop()
    met=calc_metrics(stations,times,takt); station_of={op:i for i,s in enumerate(stations) for op in s["Operações"]}
    st.success("Balanceamento gerado respeitando as restrições informadas.")
    a,b,c,d=st.columns(4); a.metric("Postos",met["n"]); b.metric("Eficiência",f"{met['eff']:.2f}%"); c.metric("Ociosidade total",f"{met['idle']:.3f} min"); d.metric("Índice de suavidade",f"{met['smooth']:.4f}")
    l,r=st.columns([1.2,1])
    with l: st.plotly_chart(precedence_graph(ids,times,names,predecessors,station_of),use_container_width=True)
    with r:
        fig=go.Figure()
        for i,s in enumerate(stations): fig.add_trace(go.Bar(x=[f"P{i+1}"],y=[s["Tempo"]],name=f"P{i+1}",text=[f"{s['Tempo']:.3f}"],textposition="inside"))
        fig.add_hline(y=takt,line_dash="dash",line_color="red",annotation_text=f"TC {takt:.3f}"); fig.update_layout(barmode="stack",height=430,yaxis_title="Minutos",xaxis_title="Posto",showlegend=False); st.plotly_chart(fig,use_container_width=True)
    rows=[]
    for i,s in enumerate(stations,1): rows.append({"Posto":f"P{i}","Costureira":s["Costureira"],"Equipamento":s["Equipamento"],"Operações":" → ".join(f"{x} — {names[x]}" for x in s["Operações"]),"Carga (min)":round(s["Tempo"],4),"Ociosidade (min)":round(takt-s["Tempo"],4),"Utilização (%)":round(s["Tempo"]/takt*100,2),"Precedências":"Sim"})
    result=pd.DataFrame(rows); st.subheader("3. Distribuição proposta"); st.dataframe(result,use_container_width=True,hide_index=True)
    st.subheader("4. Compatibilidade e recursos"); skill_map={str(s["Costureira"]):s for s in skills}; compat=[]
    for i,s in enumerate(stations,1):
        eligible=[w for w,row in skill_map.items() if int(row.get(s["Equipamento"],0))==1]
        compat.append({"Posto":f"P{i}","Equipamento":s["Equipamento"],"Costureira alocada":s["Costureira"],"Costureiras habilitadas":", ".join(eligible)})
    st.dataframe(pd.DataFrame(compat),use_container_width=True,hide_index=True)
    st.subheader("5. Pesos posicionais RPW")
    weight_df=pd.DataFrame([{"ID":x,"Operação":names[x],"Equipamento":machines[x],"Tempo":times[x],"Peso posicional":round(weights[x],4),"Posto":f"P{station_of[x]+1}"} for x in sorted(ids,key=lambda x:(-weights[x],x))]); st.dataframe(weight_df,use_container_width=True,hide_index=True)
    st.subheader("6. Exportação")
    st.download_button("Baixar distribuição CSV",result.to_csv(index=False).encode("utf-8"),"balanceamento_costura.csv","text/csv",use_container_width=True)
    st.download_button("Baixar relatório completo XLSX",build_xlsx(result,weight_df,met,takt,limits,pd.DataFrame(skills)),"relatorio_balanceamento_costura.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True)
