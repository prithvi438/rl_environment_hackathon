import React, { useState, useEffect, useRef } from 'react';
import { 
  Activity, 
  Terminal, 
  User, 
  Shield, 
  AlertTriangle, 
  CheckCircle2, 
  RefreshCw, 
  Play, 
  Cpu,
  Layers,
  Database,
  History,
  Info,
  ChevronRight,
  TrendingUp,
  Clock
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const ActionIcon = ({ type }) => {
  const icons = {
    lookup: <Database className="w-4 h-4" />,
    reply: <CheckCircle2 className="w-4 h-4" />,
    escalate: <AlertTriangle className="w-4 h-4 text-amber-500" />,
    close: <Shield className="w-4 h-4 text-emerald-500" />,
    refund: <Activity className="w-4 h-4 text-blue-500" />,
    update_ticket: <RefreshCw className="w-4 h-4" />,
    internal_note: <Terminal className="w-4 h-4" />
  };
  return icons[type?.toLowerCase()] || <Info className="w-4 h-4" />;
};

const Tag = ({ children, type = 'info' }) => {
  const colors = {
    success: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20',
    warning: 'bg-amber-500/10 text-amber-500 border-amber-500/20',
    danger: 'bg-rose-500/10 text-rose-500 border-rose-500/20',
    info: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
    neutral: 'bg-slate-500/10 text-slate-400 border-slate-500/20'
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wider border uppercase ${colors[type]}`}>
      {children}
    </span>
  );
};

export default function App() {
  const [state, setState] = useState(null);
  const [curriculum, setCurriculum] = useState(null);
  const [logs, setLogs] = useState('Awaiting inference deployment...');
  const [demoStatus, setDemoStatus] = useState('idle');
  const [demoMsg, setDemoMsg] = useState('');
  const [isResetting, setIsResetting] = useState(false);
  const [isDemoStarting, setIsDemoStarting] = useState(false);
  
  const actionFeedRef = useRef(null);
  const logsRef = useRef(null);
  const episodeIdRef = useRef(null);

  const fetchData = async () => {
    try {
      const [stateRes, currRes, logRes, statusRes] = await Promise.all([
        fetch('/state'),
        fetch('/curriculum'),
        fetch('/agent-logs'),
        fetch('/demo-status')
      ]);

      if (stateRes.ok) {
        const data = await stateRes.json();
        if (data.initialized) {
          setState(data.state);
          if (data.state.episode_id !== episodeIdRef.current) {
            episodeIdRef.current = data.state.episode_id;
          }
        }
      }

      if (currRes.ok) {
        const data = await currRes.json();
        setCurriculum(data.curriculum);
      }

      if (logRes.ok) {
        const data = await logRes.json();
        if (data.logs !== logs) {
          setLogs(data.logs);
        }
      }

      if (statusRes.ok) {
        const data = await statusRes.json();
        setDemoStatus(data.status);
      }
    } catch (err) {
      console.error('Fetch error:', err);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 1500);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (logsRef.current) {
      logsRef.current.scrollTop = logsRef.current.scrollHeight;
    }
  }, [logs]);

  const handleReset = async () => {
    setIsResetting(true);
    try {
      await fetch('/reset', { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      setTimeout(() => window.location.reload(), 500);
    } catch (err) {
      console.error(err);
      setIsResetting(false);
    }
  };

  const handleRunDemo = async () => {
    setIsDemoStarting(true);
    setDemoMsg('Starting agent...');
    try {
      const res = await fetch('/run-demo', { method: 'POST' });
      const data = await res.json();
      setDemoMsg(data.message);
    } catch (err) {
      setDemoMsg('Failed to launch agent.');
    } finally {
      setTimeout(() => setIsDemoStarting(false), 3000);
    }
  };

  const avgReward = curriculum?.avg_reward || 0;
  const totalEpisodes = curriculum?.episode_count || 0;
  const rewardProgress = Math.min(Math.max((avgReward / 1.0) * 100, 0), 100);

  return (
    <div className="flex h-screen bg-[#020617] text-slate-200 overflow-hidden font-sans selection:bg-blue-500/30">
      {/* Sidebar */}
      <aside className="w-80 border-r border-white/5 bg-slate-900/50 backdrop-blur-xl p-8 flex flex-col gap-8 z-10 shadow-2xl">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
            <Cpu className="text-white w-6 h-6" />
          </div>
          <span className="text-2xl font-bold tracking-tight bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
            OpenEnv
          </span>
        </div>

        <div className="space-y-4">
          <div className="p-5 rounded-2xl bg-white/5 border border-white/5 hover:border-blue-500/30 transition-all group overflow-hidden relative">
            <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:scale-110 transition-transform">
              <TrendingUp className="w-12 h-12" />
            </div>
            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">Avg Reward</p>
            <h3 className="text-3xl font-bold gradient-text">{(avgReward || 0).toFixed(4)}</h3>
          </div>

          <div className="p-5 rounded-2xl bg-white/5 border border-white/5 flex justify-between items-end">
            <div>
              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">Episodes</p>
              <h3 className="text-2xl font-bold">{totalEpisodes.toLocaleString()}</h3>
            </div>
            <Tag type="neutral">Live</Tag>
          </div>

          <div className="p-5 rounded-2xl bg-white/5 border border-white/5">
            <div className="flex justify-between items-center mb-3">
              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Difficulty</p>
              <Tag type={state?.difficulty === 'expert' ? 'danger' : 'warning'}>{state?.difficulty || 'Easy'}</Tag>
            </div>
            <div className="h-2 bg-black/40 rounded-full overflow-hidden shadow-inner">
              <motion.div 
                className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 shadow-[0_0_12px_rgba(59,130,246,0.5)]"
                initial={{ width: 0 }}
                animate={{ width: `${rewardProgress}%` }}
                transition={{ duration: 1, ease: "easeOut" }}
              />
            </div>
          </div>
        </div>

        <div className="mt-auto space-y-4">
          <div className="p-5 rounded-2xl bg-blue-500/5 border border-blue-500/10 space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-xs font-semibold text-blue-400">Agent Sandbox</span>
              <Tag type={demoStatus === 'running' ? 'success' : 'neutral'}>{demoStatus}</Tag>
            </div>
            <button 
              onClick={handleRunDemo}
              disabled={demoStatus === 'running' || isDemoStarting}
              className="w-full py-3 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold text-sm transition-all shadow-lg shadow-blue-500/20 active:scale-95 flex items-center justify-center gap-2"
            >
              {isDemoStarting ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              Run AI Agent Demo
            </button>
            {demoMsg && <p className="text-[10px] text-slate-500 text-center animate-pulse">{demoMsg}</p>}
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto p-12 space-y-8 relative">
        <header className="flex justify-between items-start">
          <div className="space-y-1">
            <h1 className="text-4xl font-bold tracking-tight capitalize">
              {state?.task_id?.replace(/_/g, ' ') || 'Waiting for Agent...'}
            </h1>
            <div className="flex items-center gap-4 text-slate-500 text-sm font-medium">
              <span className="flex items-center gap-1.5"><Clock className="w-4 h-4" /> Session: {state?.episode_id || '----'}</span>
              <span className="w-1 h-1 rounded-full bg-slate-700" />
              <span className="flex items-center gap-1.5 text-emerald-500/80"><Activity className="w-4 h-4" /> Pipeline Active</span>
            </div>
          </div>
          
          <div className="flex gap-4">
            <button 
              onClick={handleReset}
              disabled={isResetting}
              className="px-6 py-3 rounded-xl bg-white/10 hover:bg-white/15 border border-white/5 font-bold text-sm transition-all flex items-center gap-2"
            >
              <RefreshCw className={`w-4 h-4 ${isResetting ? 'animate-spin' : ''}`} />
              {isResetting ? 'Resetting...' : 'Force Reload'}
            </button>
          </div>
        </header>

        <div className="grid grid-cols-2 gap-8 h-[calc(100vh-270px)]">
          {/* Observation Matrix */}
          <div className="glass-panel rounded-[2rem] p-8 flex flex-col gap-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 rounded-lg bg-blue-500/10 text-blue-500">
                <Layers className="w-5 h-5" />
              </div>
              <h2 className="text-xl font-bold">Observation Matrix</h2>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              {[
                { label: 'Customer', value: state?.customer?.name || '---', icon: <User className="w-4 h-4" /> },
                { label: 'Tier', value: state?.customer?.account_tier || '---', icon: <Shield className="w-4 h-4" />, isTag: true },
                { label: 'Priority', value: state?.ticket?.priority || '---', icon: <AlertTriangle className="w-4 h-4" />, color: 'text-rose-500' },
                { label: 'Sentiment', value: state?.ticket?.sentiment || '---', icon: <Activity className="w-4 h-4" /> }
              ].map((item, i) => (
                <div key={i} className="p-4 rounded-2xl bg-white/[0.03] border border-white/5 flex flex-col gap-1">
                  <div className="flex items-center gap-2 text-slate-500">
                    {item.icon}
                    <span className="text-[10px] font-bold uppercase tracking-widest">{item.label}</span>
                  </div>
                  <div className={`text-sm font-bold truncate uppercase ${item.color || ''}`}>
                    {item.isTag ? <Tag type="info">{item.value}</Tag> : item.value}
                  </div>
                </div>
              ))}
            </div>

            <div className="flex-1 bg-black/40 border border-white/5 rounded-2xl p-6 relative overflow-hidden">
              <div className="absolute top-0 left-0 w-1 h-full bg-blue-500" />
              <div className="text-sm leading-relaxed text-slate-300 italic">
                {state?.conversation?.[state?.conversation?.length - 1]?.content || 'Awaiting initial customer input...'}
              </div>
            </div>
          </div>

          {/* Action Stream */}
          <div className="glass-panel rounded-[2rem] p-8 flex flex-col gap-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 rounded-lg bg-purple-500/10 text-purple-500">
                <Activity className="w-5 h-5" />
              </div>
              <h2 className="text-xl font-bold">Inference Stream</h2>
            </div>

            <div className="flex-1 overflow-y-auto pr-2 space-y-4 custom-scrollbar">
              <AnimatePresence initial={false}>
                {state?.actions_taken?.map((action, i) => (
                  <motion.div 
                    key={`${state.episode_id}-${i}`}
                    initial={{ opacity: 0, scale: 0.95, y: -20 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    className="p-5 rounded-2xl bg-white/[0.03] border border-white/5 flex flex-col gap-3 group"
                  >
                    <div className="flex justify-between items-center">
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-slate-800 text-slate-300 group-hover:bg-blue-500/20 group-hover:text-blue-400 transition-colors">
                          <ActionIcon type={action.type} />
                        </div>
                        <span className="text-xs font-bold uppercase tracking-widest text-slate-400">
                          {action.type?.replace(/_/g, ' ')}
                        </span>
                      </div>
                      <Tag type={(state?.step_scores?.[i] || 0) >= 80 ? 'success' : (state?.step_scores?.[i] || 0) >= 50 ? 'warning' : 'danger'}>
                        {state?.step_scores?.[i] || 0} pts
                      </Tag>
                    </div>
                    <p className="text-sm text-slate-400 line-clamp-2 leading-relaxed">
                      {action?.type === 'lookup' ? `Invoked ${action?.tool_name} for system verification` : 
                       action?.type === 'refund' ? `Processed refund for Order #${action?.tool_input?.order_id}` : 
                       action?.message || 'Processing command...'}
                    </p>
                  </motion.div>
                )).reverse()}
              </AnimatePresence>
              {!state?.actions_taken?.length && (
                <div className="h-full flex flex-col items-center justify-center text-slate-600 gap-4 opacity-50">
                  <Cpu className="w-12 h-12" />
                  <p className="text-xs font-bold uppercase tracking-widest">Awaiting Agent Logic</p>
                </div>
              )}
            </div>
          </div>

          {/* Reasoner Log & Tools Output */}
          <div className="col-span-2 grid grid-cols-2 gap-8 h-80">
            <div className="bg-slate-950/80 rounded-3xl border border-white/5 overflow-hidden flex flex-col shadow-inner">
              <div className="px-6 py-3 border-b border-white/5 bg-slate-900/50 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="flex gap-1.5 mr-2">
                    <div className="w-2.5 h-2.5 rounded-full bg-rose-500/50" />
                    <div className="w-2.5 h-2.5 rounded-full bg-amber-500/50" />
                    <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/50" />
                  </div>
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest flex items-center gap-2">
                    <History className="w-3 h-3" /> agent_inference.log
                  </span>
                </div>
              </div>
              <pre ref={logsRef} className="flex-1 p-6 font-mono text-[11px] text-slate-400 overflow-y-auto whitespace-pre-wrap leading-relaxed custom-scrollbar">
                {logs || 'Initializing system log...'}
              </pre>
            </div>

            <div className="bg-slate-950/80 rounded-3xl border border-white/5 overflow-hidden flex flex-col shadow-inner">
              <div className="px-6 py-3 border-b border-white/5 bg-slate-900/50 flex items-center justify-between">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest flex items-center gap-2">
                  <Terminal className="w-3 h-3" /> tools_output.json
                </span>
                <Tag type="neutral">RO</Tag>
              </div>
              <pre className="flex-1 p-6 font-mono text-[11px] text-blue-400 overflow-y-auto whitespace-pre-wrap leading-relaxed custom-scrollbar bg-blue-500/[0.02]">
                {JSON.stringify(state?.actions_taken?.[(state?.actions_taken?.length || 1) - 1]?.tool_input || { status: "standby" }, null, 2)}
              </pre>
            </div>
          </div>
        </div>

      </main>
    </div>
  );
}
