import React,{useEffect,useMemo,useState} from "react";
import {createRoot} from "react-dom/client";
import "./styles.css";

const roles={
  REQUESTER:{id:"usr_requester",label:"طالب التنفيذ"},
  EXECUTOR:{id:"usr_executor",label:"منفذ المهمة"},
  TRAINER:{id:"usr_trainer",label:"مراجع التدريب"}
};
const base=import.meta.env.VITE_API_BASE_URL||"";
const demo=import.meta.env.VITE_DEMO_MODE!=="false";
const useDemo=demo&&!base;

const id=p=>p+"_"+Math.random().toString(36).slice(2,9);
const now=()=>new Date().toISOString();

function demoStore(){
  const s={tasks:[],assignments:[],executions:[],results:[],evidence:[],effort:[],rt:[],settlements:[],training:[],trace:[]};
  const t=(event,entity_type,entity_id,actor,payload={})=>s.trace.push({trace_event_id:id("trace"),event_type:event,entity_type,entity_id,timestamp:now(),actor_id:actor,payload});
  return {async call(path,method,actor,body={}){
    await new Promise(r=>setTimeout(r,80)); const p=path.split("/").filter(Boolean);
    if(method==="POST"&&path==="/tasks"){const x={task_id:id("task"),requester_id:actor,description:body.description,created_at:now(),status:"CREATED"};s.tasks.push(x);t("TASK_CREATED","TASK",x.task_id,actor);return x}
    if(method==="POST"&&p[0]==="tasks"&&p[2]==="validate"){const x=s.tasks.find(v=>v.task_id===p[1]);if(!x)throw Error("Unknown task");if(!x.description.trim())throw Error("Task description required");x.status="VALIDATED";t("TASK_VALIDATED","TASK",x.task_id,actor);return x}
    if(method==="POST"&&p[0]==="tasks"&&p[2]==="assign"){const x=s.tasks.find(v=>v.task_id===p[1]);if(!x||x.status!=="VALIDATED")throw Error("Task must be VALIDATED");const a={assignment_id:id("assign"),task_id:x.task_id,executor_id:body.executor_id,assigned_at:now(),status:"ASSIGNED"};s.assignments.push(a);x.status="ASSIGNED";t("TASK_ASSIGNED","TASK",x.task_id,actor);return a}
    if(method==="POST"&&path==="/executions/start"){const x=s.tasks.find(v=>v.task_id===body.task_id),a=s.assignments.find(v=>v.task_id===body.task_id);if(!a||a.executor_id!==actor)throw Error("No valid assignment");const e={execution_id:id("exec"),task_id:x.task_id,executor_id:actor,started_at:now(),finished_at:null,status:"IN_EXECUTION"};s.executions.push(e);x.status="IN_EXECUTION";t("EXECUTION_STARTED","EXECUTION",e.execution_id,actor,{execution_id:e.execution_id});return e}
    if(method==="POST"&&p[0]==="executions"&&p[2]==="result"){const e=s.executions.find(v=>v.execution_id===p[1]);if(!e||e.executor_id!==actor||e.status!=="IN_EXECUTION")throw Error("Execution not active");const r={result_id:id("result"),execution_id:e.execution_id,result_status:body.result_status,result_data:body.result_data,created_at:now()};s.results.push(r);t("RESULT_SUBMITTED","RESULT",r.result_id,actor,{execution_id:e.execution_id});return r}
    if(method==="POST"&&p[0]==="executions"&&p[2]==="evidence"){const r=s.results.find(v=>v.execution_id===p[1]);if(!r)throw Error("Evidence requires Result");const e={evidence_id:id("evid"),execution_id:p[1],result_id:r.result_id,evidence_type:body.evidence_type||"TEXT",evidence_text:body.evidence_text,evidence_reference:"demo://evidence/"+p[1],created_at:now(),status:"SUBMITTED"};s.evidence.push(e);t("EVIDENCE_SUBMITTED","EVIDENCE",e.evidence_id,actor,{execution_id:p[1]});return e}
    if(method==="POST"&&p[0]==="evidence"&&p[2]==="validate"){const e=s.evidence.find(v=>v.evidence_id===p[1]);if(!e)throw Error("Evidence not found");e.status="VALIDATED";t("EVIDENCE_VALIDATED","EVIDENCE",e.evidence_id,actor);return e}
    if(method==="POST"&&p[0]==="executions"&&p[2]==="complete"){const e=s.executions.find(v=>v.execution_id===p[1]),r=s.results.find(v=>v.execution_id===p[1]);if(!e||e.status!=="IN_EXECUTION"||!r)throw Error("Completion requires active execution and result");e.status="COMPLETED";e.finished_at=now();s.tasks.find(v=>v.task_id===e.task_id).status="COMPLETED";t("EXECUTION_FINISHED","EXECUTION",e.execution_id,actor,{execution_id:e.execution_id});return e}
    if(method==="POST"&&p[0]==="executions"&&p[2]==="effort"){const n=Number(body.t_accounted_ns);if(!Number.isInteger(n)||n<=0)throw Error("T_accounted_ns must be positive integer");const e=s.executions.find(v=>v.execution_id===p[1]);if(!e||e.status!=="COMPLETED")throw Error("Effort requires COMPLETED execution");const x={effort_id:id("effort"),execution_id:p[1],t_accounted_ns:n,calculation_rule:"RT = T_accounted_ns / 30ns",created_at:now(),status:"ACCOUNTED"};s.effort.push(x);t("EFFORT_RECORDED","EFFORT",x.effort_id,actor,{execution_id:p[1]});return x}
    if(method==="POST"&&p[0]==="executions"&&p[2]==="rt"){const e=s.effort.find(v=>v.execution_id===p[1]);if(!e)throw Error("T_accounted missing");const x={rt_record_id:id("rt"),execution_id:p[1],effort_id:e.effort_id,t_accounted_ns:e.t_accounted_ns,rt_value:e.t_accounted_ns/30,calculation_rule:"1 RT = 30 ns",created_at:now()};s.rt.push(x);t("RT_CALCULATED","RT",x.rt_record_id,actor,{execution_id:p[1],rt_value:x.rt_value});return x}
    if(method==="POST"&&p[0]==="executions"&&p[2]==="settlement"){const e=s.executions.find(v=>v.execution_id===p[1]),r=s.results.find(v=>v.execution_id===p[1]),ev=s.evidence.find(v=>v.execution_id===p[1]&&v.status==="VALIDATED"),rt=s.rt.find(v=>v.execution_id===p[1]);if(!e||e.status!=="COMPLETED"||!r||!ev||!rt)throw Error("Settlement requires completed execution, result, validated evidence and valid RT");const x={settlement_id:id("settle"),task_id:e.task_id,execution_id:p[1],rt_record_id:rt.rt_record_id,rt_value:rt.rt_value,settlement_status:"RECORDED",created_at:now()};s.settlements.push(x);t("SETTLEMENT_RECORDED","SETTLEMENT",x.settlement_id,actor,{execution_id:p[1]});return x}
    if(method==="POST"&&p[0]==="executions"&&p[2]==="training"){const r=s.results.find(v=>v.execution_id===p[1]),e=s.executions.find(v=>v.execution_id===p[1]),ev=s.evidence.find(v=>v.execution_id===p[1]&&v.status==="VALIDATED"),rt=s.rt.find(v=>v.execution_id===p[1]);if(!r||!e||e.status!=="COMPLETED"||!ev||!rt)throw Error("Training requires completed execution, result, validated evidence and RT");if(s.training.some(v=>v.execution_id===p[1]))throw Error("Training already recorded");const x={training_record_id:id("train"),execution_id:p[1],result_reference:r.result_id,input_data_reference:JSON.stringify({execution_id:p[1],scope:"MVP_EXECUTION_DATA"}),created_at:now(),status:"RECORDED"};s.training.push(x);t("TRAINING_RECORDED","TRAINING",x.training_record_id,actor,{execution_id:p[1]});return x}
    if(method==="GET"&&p[0]==="executions"&&p[2]==="trace"){const e=s.executions.find(v=>v.execution_id===p[1]);return {task:s.tasks.find(v=>v.task_id===e?.task_id),assignment:s.assignments.find(v=>v.task_id===e?.task_id),execution:e,result:s.results.find(v=>v.execution_id===p[1])||null,evidence:s.evidence.filter(v=>v.execution_id===p[1]),effort:s.effort.find(v=>v.execution_id===p[1])||null,rt:s.rt.find(v=>v.execution_id===p[1])||null,settlement:s.settlements.find(v=>v.execution_id===p[1])||null,training:s.training.find(v=>v.execution_id===p[1])||null,trace:s.trace.filter(v=>v.entity_id===p[1]||v.payload?.execution_id===p[1])}}
    if(method==="GET"&&path==="/training")return s.training;
    throw Error("Demo endpoint not implemented")
  }};
}
const ds=demoStore();
async function call(path,method,actor,body={}){
  if(useDemo)return ds.call(path,method,actor,body);
  const r=await fetch(base+path,{method,headers:{"Content-Type":"application/json","X-User-ID":actor},body:method==="GET"?undefined:JSON.stringify(body)});
  const data=await r.json(); if(!r.ok)throw Error(data.message||data.error||"Request failed"); return data;
}

function App(){
  const [role,setRole]=useState("REQUESTER");
  const actor=roles[role].id;
  const [task,setTask]=useState(null),[execution,setExecution]=useState(null),[trace,setTrace]=useState(null),[training,setTraining]=useState([]);
  const [desc,setDesc]=useState("اختبار دورة تنفيذ مركزية"),[result,setResult]=useState("SUCCESS"),[resultData,setResultData]=useState("نتيجة التنفيذ مرصودة"),[evidence,setEvidence]=useState("دليل التنفيذ المرصود"),[effort,setEffort]=useState("30"),[notice,setNotice]=useState("");
  const [tab,setTab]=useState("dashboard");

  async function act(fn,msg){try{setNotice("جارٍ التنفيذ...");const x=await fn();setNotice(msg);return x}catch(e){setNotice("خطأ: "+e.message)}}
  const refresh=async idv=>act(async()=>{const x=await call("/executions/"+idv+"/trace","GET",actor);setTrace(x);return x},"تم تحديث الأثر");
  async function create(){const x=await act(()=>call("/tasks","POST",actor,{description:desc}),"تم إنشاء المهمة");if(x)setTask(x)}
  async function validate(){const x=await act(()=>call("/tasks/"+task.task_id+"/validate","POST",actor,{}),"تم التحقق");if(x)setTask(x)}
  async function assign(){const x=await act(()=>call("/tasks/"+task.task_id+"/assign","POST",actor,{executor_id:roles.EXECUTOR.id}),"تم الإسناد");if(x)setTask({...task,status:"ASSIGNED"})}
  async function start(){const x=await act(()=>call("/executions/start","POST",roles.EXECUTOR.id,{task_id:task.task_id}),"بدأ التنفيذ");if(x){setExecution(x);refresh(x.execution_id)}}
  async function submitResult(){if(!execution)return;await act(()=>call("/executions/"+execution.execution_id+"/result","POST",roles.EXECUTOR.id,{result_status:result,result_data:resultData}),"تم حفظ النتيجة");refresh(execution.execution_id)}
  async function submitEvidence(){if(!execution)return;const x=await act(()=>call("/executions/"+execution.execution_id+"/evidence","POST",roles.EXECUTOR.id,{evidence_type:"TEXT",evidence_text:evidence}),"تم إرسال الدليل");if(x)refresh(execution.execution_id)}
  async function validateEvidence(){const ev=trace?.evidence?.find(v=>v.status==="SUBMITTED");if(!ev)return;await act(()=>call("/evidence/"+ev.evidence_id+"/validate","POST",actor,{}),"تم اعتماد الدليل");refresh(execution.execution_id)}
  async function complete(){if(!execution)return;const x=await act(()=>call("/executions/"+execution.execution_id+"/complete","POST",roles.EXECUTOR.id,{}),"اكتمل التنفيذ");if(x){setExecution(x);refresh(x.execution_id)}}
  async function recordEffort(){if(!execution)return;await act(()=>call("/executions/"+execution.execution_id+"/effort","POST",roles.EXECUTOR.id,{t_accounted_ns:Number(effort)}),"تم تسجيل T_accounted");refresh(execution.execution_id)}
  async function calcRt(){if(!execution)return;await act(()=>call("/executions/"+execution.execution_id+"/rt","POST",roles.EXECUTOR.id,{}),"تم حساب RT");refresh(execution.execution_id)}
  async function settle(){if(!execution)return;await act(()=>call("/executions/"+execution.execution_id+"/settlement","POST",roles.REQUESTER.id,{}),"تم إنشاء Settlement Record");refresh(execution.execution_id)}
  async function train(){if(!execution)return;await act(()=>call("/executions/"+execution.execution_id+"/training","POST",actor,{}),"تم تسجيل Training Record");refresh(execution.execution_id)}
  useEffect(()=>{if(tab==="trainer")act(()=>call("/training","GET",roles.TRAINER.id,{}),"تم تحميل بيانات التدريب").then(x=>x&&setTraining(x))},[tab]);

  const progress=useMemo(()=>[task?.status&&["CREATED","VALIDATED","ASSIGNED","IN_EXECUTION","COMPLETED"].includes(task.status),trace?.result,trace?.evidence?.some(v=>v.status==="VALIDATED"),trace?.effort,trace?.rt,trace?.settlement].filter(Boolean).length,[task,trace]);
  return <div className="app">
    <header><div><b>AQOOM Central Application</b><small>MVP · Central Execution Platform</small></div><select value={role} onChange={e=>setRole(e.target.value)}>{Object.entries(roles).map(([k,v])=><option key={k} value={k}>{v.label}</option>)}</select></header>
    <nav><button onClick={()=>setTab("dashboard")}>لوحة التشغيل</button><button onClick={()=>setTab("requester")}>Requester</button><button onClick={()=>setTab("executor")}>Executor</button><button onClick={()=>setTab("trace")}>Execution Trace</button><button onClick={()=>setTab("trainer")}>Trainer</button></nav>
    <main>
      {notice&&<div className="notice">{notice}</div>}
      <section className="hero"><div><span>PROJECT 1</span><h1>دورة تنفيذ واحدة، من الطلب إلى الدليل والـRT.</h1><p>واجهة MVP عربية RTL تحافظ على حدود المنتج: Settlement Record فقط وTraining Input فقط.</p></div><div className="rt"><b>1 RT</b><strong>30 ns</strong></div></section>
      <div className="metrics"><div><small>Progress</small><b>{progress}/6</b></div><div><small>Execution</small><b>{execution?.status||"READY"}</b></div><div><small>RT</small><b>{trace?.rt?trace.rt.rt_value+" RT":"—"}</b></div><div><small>Mode</small><b>{useDemo?"DEMO":"API"}</b></div></div>

      {tab==="dashboard"&&<section className="panel"><h2>المسار المركزي</h2><p>Task → Assignment → Execution → Result → Evidence → T_accounted → RT → Settlement → Training → Trace</p><div className="chain">{["Task","Assignment","Execution","Result","Evidence","Effort","RT","Settlement","Training","Trace"].map((x,i)=><span key={x}>{i+1}. {x}</span>)}</div><button className="primary" onClick={()=>setTab("requester")}>ابدأ دورة تنفيذ</button></section>}

      {tab==="requester"&&<section className="panel"><h2>Requester Workspace</h2><label>وصف المهمة<textarea value={desc} onChange={e=>setDesc(e.target.value)}/></label><div className="actions"><button className="primary" onClick={create}>1 إنشاء Task</button><button disabled={!task||task.status!=="CREATED"} onClick={validate}>2 Validation</button><button disabled={!task||task.status!=="VALIDATED"} onClick={assign}>3 Assignment</button></div>{task&&<pre>{JSON.stringify(task,null,2)}</pre>}</section>}

      {tab==="executor"&&<section className="panel"><h2>Executor Workspace</h2><button className="primary" disabled={!task||task.status!=="ASSIGNED"} onClick={start}>4 بدء Execution</button><label>النتيجة<select value={result} onChange={e=>setResult(e.target.value)}><option>SUCCESS</option><option>FAILED</option><option>INCOMPLETE</option><option>REJECTED</option></select></label><label>بيانات النتيجة<textarea value={resultData} onChange={e=>setResultData(e.target.value)}/></label><div className="actions"><button disabled={!execution} onClick={submitResult}>5 Result</button><button disabled={!execution} onClick={submitEvidence}>6 Evidence</button><button disabled={!trace?.evidence?.length} onClick={validateEvidence}>Validate Evidence</button><button disabled={!trace?.result||execution?.status!=="IN_EXECUTION"} onClick={complete}>Complete</button></div><label>Evidence<textarea value={evidence} onChange={e=>setEvidence(e.target.value)}/></label><label>T_accounted (ns)<input type="number" min="1" value={effort} onChange={e=>setEffort(e.target.value)}/></label><div className="actions"><button disabled={execution?.status!=="COMPLETED"} onClick={recordEffort}>7 Effort</button><button disabled={!trace?.effort} onClick={calcRt}>8 RT</button><button disabled={!trace?.rt} onClick={settle}>9 Settlement Record</button><button disabled={!trace?.settlement||!!trace?.training} onClick={train}>10 Training</button></div></section>}

      {tab==="trace"&&<section className="panel"><h2>Execution Trace</h2><button disabled={!execution} onClick={()=>refresh(execution.execution_id)}>تحديث</button><div className="chain">{["Task","Assignment","Execution","Result","Evidence","Effort","RT","Settlement","Training"].map(x=><span key={x}>{x}</span>)}</div>{trace?<pre>{JSON.stringify(trace,null,2)}</pre>:<p>ابدأ تنفيذًا ثم افتح الأثر.</p>}</section>}

      {tab==="trainer"&&<section className="panel"><h2>Trainer Workspace</h2><p>قراءة بيانات التدريب فقط. لا تعديل للقرار التشغيلي ولا للـRT.</p>{training.length?<pre>{JSON.stringify(training,null,2)}</pre>:<p>لا توجد Training Records.</p>}</section>}
    </main>
  </div>
}
createRoot(document.getElementById("root")).render(<App/>);
