"use client";

import React, { useEffect, useMemo, useRef, useState, useContext, createContext } from "react";
import { Mic } from "lucide-react";

// ────────────────────────────────────────────────────────────────────────────────
// Ikoner (inline SVG)
const Svg = (p: any) => (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" {...p} />);
const IconPlay = (p: any) => (<Svg {...p}><polygon points="5 3 19 12 5 21 5 3" /></Svg>);
const IconSkipBack = (p: any) => (<Svg {...p}><polyline points="19 20 9 12 19 4" /><line x1="5" y1="19" x2="5" y2="5" /></Svg>);
const IconSkipForward = (p: any) => (<Svg {...p}><polyline points="5 4 15 12 5 20" /><line x1="19" y1="5" x2="19" y2="19" /></Svg>);
const IconThermometer = (p: any) => (<Svg {...p}><path d="M14 14.76V3a2 2 0 0 0-4 0v11.76" /><path d="M8 15a4 4 0 1 0 8 0" /></Svg>);
const IconCloudSun = (p: any) => (<Svg {...p}><circle cx="7" cy="7" r="3" /><path d="M12 3v2M12 19v2M4.22 4.22 5.64 5.64M18.36 18.36 19.78 19.78M1 12h2M21 12h2" /></Svg>);
const IconCpu = (p: any) => (<Svg {...p}><rect x="9" y="9" width="6" height="6" /><rect x="4" y="4" width="16" height="16" rx="2" /></Svg>);
const IconDrive = (p: any) => (<Svg {...p}><rect x="2" y="7" width="20" height="10" rx="2" /><circle cx="6.5" cy="12" r="1" /><circle cx="17.5" cy="12" r="1" /></Svg>);
const IconActivity = (p: any) => (<Svg {...p}><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" /></Svg>);
const IconMic = (p: any) => (<Svg {...p}><rect x="9" y="2" width="6" height="11" rx="3" /><path d="M12 13v6" /></Svg>);
const IconX = (p: any) => (<Svg {...p}><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></Svg>);
const IconCheck = (p: any) => (<Svg {...p}><polyline points="20 6 9 17 4 12" /></Svg>);
const IconClock = (p: any) => (<Svg {...p}><circle cx="12" cy="12" r="9" /><path d="M12 7v6h5" /></Svg>);
const IconSettings = (p: any) => (<Svg {...p}><circle cx="12" cy="12" r="3" /></Svg>);
const IconBell = (p: any) => (<Svg {...p}><path d="M6 8a6 6 0 1 1 12 0v6H6z" /></Svg>);
const IconSearch = (p: any) => (<Svg {...p}><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></Svg>);
const IconWifi = (p: any) => (<Svg {...p}><path d="M2 8c6-5 14-5 20 0" /><path d="M5 12c4-3 10-3 14 0" /><path d="M8.5 15.5c2-1.5 5-1.5 7 0" /><circle cx="12" cy="19" r="1" /></Svg>);
const IconBattery = (p: any) => (<Svg {...p}><rect x="2" y="7" width="18" height="10" rx="2" /><rect x="20" y="10" width="2" height="4" /></Svg>);
const IconGauge = (p: any) => (<Svg {...p}><circle cx="12" cy="12" r="9" /><line x1="12" y1="12" x2="18" y2="10" /></Svg>);

// ────────────────────────────────────────────────────────────────────────────────
// Utils
const safeUUID = () => `id-${Math.random().toString(36).slice(2)}-${Date.now()}`;
const clampPercent = (v: number) => Math.max(0, Math.min(100, Number.isFinite(v) ? v : 0));

// ────────────────────────────────────────────────────────────────────────────────
// HUD primitives
const GlowDot = ({ className }: { className?: string }) => (
  <span className={`relative inline-block ${className || ""}`}>
    <span className="absolute inset-0 rounded-full blur-[6px] bg-cyan-400/40" />
    <span className="absolute inset-0 rounded-full blur-[14px] bg-cyan-400/20" />
    <span className="relative block h-full w-full rounded-full bg-cyan-300" />
  </span>
);

const RingGauge = ({ size = 180, value, label, sublabel, icon, showValue = true }: {
  size?: number;
  value: number;
  label?: string;
  sublabel?: string;
  icon?: React.ReactNode;
  showValue?: boolean;
}) => {
  const pct = clampPercent(value);
  const r = size * 0.42;
  const c = 2 * Math.PI * r;
  const dash = (pct / 100) * c;
  return (
    <div className="relative grid place-items-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <defs>
          <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="0%"><stop offset="0%" stopColor="#22d3ee" /><stop offset="100%" stopColor="#38bdf8" /></linearGradient>
          <filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="4" result="coloredBlur" /><feMerge><feMergeNode in="coloredBlur" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
        </defs>
        <circle cx={size / 2} cy={size / 2} r={r} stroke="#0ea5b7" strokeOpacity="0.25" strokeWidth={10} fill="none" strokeDasharray={c} />
        <circle cx={size / 2} cy={size / 2} r={r} stroke="url(#grad)" strokeWidth={10} fill="none" strokeLinecap="round" strokeDasharray={`${dash} ${c - dash}`} style={{ transition: "stroke-dasharray .6s ease" }} filter="url(#glow)" />
      </svg>
      <div className="absolute inset-0 grid place-items-center">
        <div className="text-center">
          {(label || sublabel || showValue) && (
            <>
              <div className="flex items-center justify-center gap-2 text-cyan-300">{icon}{label && <span className="text-xs uppercase tracking-widest opacity-80">{label}</span>}</div>
              {showValue && (<div className="text-4xl font-semibold text-cyan-100">{Math.round(pct)}<span className="text-cyan-400 text-xl">%</span></div>)}
              {sublabel && <div className="text-xs text-cyan-300/80 mt-1">{sublabel}</div>}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

const Metric = ({ label, value, icon }: { label: string; value: number; icon: React.ReactNode }) => (
  <div className="text-center">
    <div className="flex items-center justify-center gap-2 text-xs text-cyan-300/80">{icon} {label}</div>
    <div className="text-2xl font-semibold text-cyan-100">{Math.round(value)}%</div>
  </div>
);

const Pane = ({ title, children, className, actions }: {
  title: string;
  children: React.ReactNode;
  className?: string;
  actions?: React.ReactNode;
}) => (
  <div className={`relative rounded-2xl border border-cyan-500/20 bg-cyan-950/20 p-4 shadow-[0_0_60px_-20px_rgba(34,211,238,.5)] ${className || ""}`}>
    <div className="flex items-center justify-between mb-3">
      <div className="flex items-center gap-2"><GlowDot className="h-2 w-2" /><h3 className="text-cyan-200/90 text-xs uppercase tracking-widest">{title}</h3></div>
      <div className="flex gap-2 text-cyan-300/70">{actions}</div>
    </div>
    {children}
    <div className="pointer-events-none absolute inset-0 rounded-2xl ring-1 ring-inset ring-cyan-300/10" />
  </div>
);

// ────────────────────────────────────────────────────────────────────────────────
// Hooks (simulerad data)
function useSystemMetrics() {
  const [cpu, setCpu] = useState(0);
  const [mem, setMem] = useState(0);
  const [net, setNet] = useState(0);
  useEffect(() => {
    // Set initial values on client
    setCpu(37);
    setMem(52);
    setNet(8);
    
    const id = setInterval(() => {
      setCpu((v) => clampPercent(v + (Math.random() * 10 - 5)));
      setMem((v) => clampPercent(v + (Math.random() * 6 - 3)));
      setNet((v) => clampPercent(v + (Math.random() * 14 - 7)));
    }, 1100);
    return () => clearInterval(id);
  }, []);
  return { cpu, mem, net };
}



function useWeatherStub() {
  const [w, setW] = useState({ temp: 0, desc: "Loading..." });
  useEffect(() => {
    // Set initial values on client
    setW({ temp: 21, desc: "Partly cloudy" });
    
    const id = setInterval(() => {
      setW({ temp: Math.round(18 + Math.random() * 10), desc: ["Sunny", "Cloudy", "Partly cloudy", "Light rain"][Math.floor(Math.random() * 4)] });
    }, 5000);
    return () => clearInterval(id);
  }, []);
  return w;
}

// ────────────────────────────────────────────────────────────────────────────────


// ────────────────────────────────────────────────────────────────────────────────
// Main HUD
export default function AliceHUD() {
  const { cpu, mem, net } = useSystemMetrics();
  const weather = useWeatherStub();
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState<Array<{role: 'user' | 'assistant', content: string}>>([
    { role: 'assistant', content: 'Hej! Jag är Alice. Hur kan jag hjälpa dig idag?' }
  ]);
  const [isTyping, setIsTyping] = useState(false);
  const [isListening, setIsListening] = useState(false);

  const [now, setNow] = useState("--:--");

  const sendMessage = () => {
    if (!query.trim()) return;
    
    // Lägg till användarens meddelande
    const userMessage = { role: 'user' as const, content: query.trim() };
    setMessages(prev => [...prev, userMessage]);
    setQuery('');
    
    // Simulera Alice svarar
    setIsTyping(true);
    setTimeout(() => {
      const responses = [
        "Intressant fråga! Låt mig tänka på det...",
        "Jag förstår vad du menar. Här är mitt svar...",
        "Bra fråga! Baserat på vad jag vet...",
        "Jag kan hjälpa dig med det. Låt mig förklara...",
        "Det är en utmaning. Här är vad jag tror..."
      ];
      const randomResponse = responses[Math.floor(Math.random() * responses.length)];
      setMessages(prev => [...prev, { role: 'assistant', content: randomResponse }]);
      setIsTyping(false);
    }, 1500);
  };

  const toggleVoice = () => {
    setIsListening(!isListening);
    if (!isListening) {
      // Simulera röstinspelning
      setTimeout(() => {
        setIsListening(false);
        const voiceMessage = { role: 'user' as const, content: 'Hej Alice, hur mår du?' };
        setMessages(prev => [...prev, voiceMessage]);
        setIsTyping(true);
        setTimeout(() => {
          setMessages(prev => [...prev, { role: 'assistant', content: 'Hej! Jag mår bra, tack! Hur kan jag hjälpa dig?' }]);
          setIsTyping(false);
        }, 1000);
      }, 3000);
    }
  };
  useEffect(() => {
    // Set initial time on client only
    setNow(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }));
    const id = setInterval(() => setNow(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })), 1000);
    return () => clearInterval(id);
  }, []);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    const chatContainer = document.querySelector('.overflow-y-auto');
    if (chatContainer) {
      chatContainer.scrollTop = chatContainer.scrollHeight;
    }
  }, [messages, isTyping]);

  // Update wave animation in real-time
  useEffect(() => {
    if (!isListening) return;
    
    const interval = setInterval(() => {
      // Force re-render to update wave heights
      setNow(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }));
    }, 50);
    
    return () => clearInterval(interval);
  }, [isListening]);

  return (
    <div className="relative min-h-screen w-full overflow-hidden bg-[#030b10] text-cyan-100">
      {/* Background effects */}
      <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/5 via-transparent to-blue-900/10" />
      <div className="pointer-events-none absolute inset-0 [background:radial-gradient(ellipse_at_top,rgba(13,148,136,.15),transparent_60%),radial-gradient(ellipse_at_bottom,rgba(3,105,161,.12),transparent_60%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(#0e7490_1px,transparent_1px),linear-gradient(90deg,#0e7490_1px,transparent_1px)] bg-[size:40px_40px] opacity-10" />

      <div className="mx-auto max-w-7xl px-6 pt-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 opacity-80">
            <IconWifi className="h-4 w-4" />
            <IconBattery className="h-4 w-4" />
            <IconBell className="h-4 w-4" />
          </div>
          <div className="flex items-center gap-2 text-cyan-300/80">
            <IconClock className="h-4 w-4" />
            <span className="tracking-widest text-xs uppercase">{now}</span>
          </div>
        </div>
      </div>

      <main className="mx-auto grid max-w-7xl grid-cols-1 gap-6 px-6 pb-24 pt-4 md:grid-cols-12">
                            <div className="md:col-span-3 space-y-6">
                      <Pane title="System" actions={<IconSettings className="h-4 w-4" />}>
                        <div className="grid grid-cols-3 gap-3">
                          <Metric label="CPU" value={cpu} icon={<IconCpu className="h-3 w-3" />} />
                          <Metric label="MEM" value={mem} icon={<IconDrive className="h-3 w-3" />} />
                          <Metric label="NET" value={net} icon={<IconActivity className="h-3 w-3" />} />
                        </div>
                        <div className="mt-4 grid grid-cols-3 gap-3">
                          <RingGauge size={80} value={cpu} icon={<IconCpu className="h-3 w-3" />} showValue={false} />
                          <RingGauge size={80} value={mem} icon={<IconDrive className="h-3 w-3" />} showValue={false} />
                          <RingGauge size={80} value={net} icon={<IconGauge className="h-3 w-3" />} showValue={false} />
                        </div>
                      </Pane>
                    </div>

                            <div className="md:col-span-6 space-y-6">
                      {/* Voice Indicator Panel */}
                      <Pane title="Voice Input">
                        <div 
                          className="relative h-32 overflow-hidden rounded-xl border border-cyan-500/20 bg-cyan-900/10 cursor-pointer hover:bg-cyan-900/20 transition-colors"
                          onClick={toggleVoice}
                        >
                          {/* Mic Icon in top-right corner */}
                          <div className="absolute top-3 right-3 z-10">
                            <Mic className={`h-5 w-5 transition-colors ${
                              isListening ? 'text-cyan-300' : 'text-cyan-300/60'
                            }`} />
                          </div>
                          
                          {/* Wave Animation - Full Width */}
                          <div className="absolute inset-0 flex items-center justify-center px-4">
                            <div className="flex items-end space-x-1 h-16 w-full">
                              {[...Array(20)].map((_, i) => (
                                <div
                                  key={i}
                                  className={`flex-1 bg-gradient-to-t from-cyan-400 to-cyan-300 rounded-full transition-all duration-300 ${
                                    isListening 
                                      ? 'animate-pulse' 
                                      : 'opacity-30'
                                  }`}
                                  style={{
                                    height: isListening 
                                      ? `${20 + Math.sin(Date.now() * 0.001 + i * 0.3) * 15}px`
                                      : '8px',
                                    animationDelay: `${i * 0.05}s`
                                  }}
                                />
                              ))}
                            </div>
                          </div>
                          
                          {/* Status Text */}
                          <div className="absolute bottom-3 left-3">
                            <div className="text-xs text-cyan-300/60">
                              {isListening ? 'Lyssnar...' : 'Klicka för att starta'}
                            </div>
                          </div>
                        </div>
                      </Pane>

                      {/* Chat Interface */}
                      <Pane title="Alice Core">
                        <div className="h-80 overflow-hidden rounded-xl border border-cyan-500/20 bg-cyan-900/10">
                          <div className="h-full flex flex-col">
                            {/* Chat Messages */}
                            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                              {messages.map((msg, index) => (
                                <div key={index} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                  <div className={`max-w-xs rounded-lg px-3 py-2 ${
                                    msg.role === 'user' 
                                      ? 'bg-cyan-400/20 text-cyan-100 border border-cyan-400/30' 
                                      : 'bg-cyan-900/20 text-cyan-200 border border-cyan-500/20'
                                  }`}>
                                    <div className="text-xs text-cyan-300/60 mb-1">
                                      {msg.role === 'user' ? 'Du' : 'Alice'}
                                    </div>
                                    <div className="text-sm">{msg.content}</div>
                                  </div>
                                </div>
                              ))}
                              {isTyping && (
                                <div className="flex justify-start">
                                  <div className="bg-cyan-900/20 text-cyan-200 border border-cyan-500/20 rounded-lg px-3 py-2">
                                    <div className="text-xs text-cyan-300/60 mb-1">Alice</div>
                                    <div className="flex space-x-1">
                                      <div className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce"></div>
                                      <div className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                                      <div className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                                    </div>
                                  </div>
                                </div>
                              )}
                            </div>
                            
                            {/* Input Area */}
                            <div className="border-t border-cyan-500/20 p-4">
                              <div className="flex gap-2">
                                <input
                                  value={query}
                                  onChange={(e) => setQuery(e.target.value)}
                                  onKeyDown={(e) => {
                                    if (e.key === 'Enter' && query.trim()) {
                                      sendMessage();
                                    }
                                  }}
                                  placeholder="Skriv ett meddelande..."
                                  className="flex-1 bg-transparent text-cyan-100 placeholder:text-cyan-300/40 focus:outline-none"
                                />
                                <button
                                  onClick={sendMessage}
                                  disabled={!query.trim()}
                                  className="rounded-lg border border-cyan-400/30 px-3 py-2 text-xs hover:bg-cyan-400/10 disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                  Skicka
                                </button>
                              </div>
                            </div>
                          </div>
                        </div>
                      </Pane>

          <Pane title="Media">
            <div className="flex items-center gap-4">
              <button className="rounded-full border border-cyan-400/30 p-2 hover:bg-cyan-400/10">
                <IconSkipBack className="h-4 w-4" />
              </button>
              <button className="rounded-full border border-cyan-400/30 p-3 hover:bg-cyan-400/10">
                <IconPlay className="h-5 w-5" />
              </button>
              <button className="rounded-full border border-cyan-400/30 p-2 hover:bg-cyan-400/10">
                <IconSkipForward className="h-4 w-4" />
              </button>
              <div className="ml-auto text-xs text-cyan-300/70">0:00 / 3:45</div>
            </div>
          </Pane>
        </div>

                            <div className="md:col-span-3 space-y-6">
                      <Pane title="Weather" actions={<IconCloudSun className="h-4 w-4" />}>
                        <div className="flex items-center gap-4">
                          <IconThermometer className="h-10 w-10 text-cyan-300" />
                          <div>
                            <div className="text-3xl font-semibold">{weather.temp}°C</div>
                            <div className="text-cyan-300/80 text-sm">{weather.desc}</div>
                          </div>
                        </div>
                      </Pane>
                    </div>
      </main>

      <footer className="pointer-events-none absolute inset-x-0 bottom-0 mx-auto max-w-7xl px-6 pb-8">
        <div className="grid grid-cols-5 gap-4 opacity-80">
          {["SYS", "NET", "AUX", "NAV", "CTRL"].map((t, i) => (
            <div key={i} className="relative h-14 overflow-hidden rounded-xl border border-cyan-500/20 bg-cyan-900/10">
              <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(34,211,238,.15),transparent_50%)]" />
              <div className="absolute inset-0 grid place-items-center text-xs tracking-[.35em] text-cyan-200/70">{t}</div>
              <div className="absolute bottom-0 h-[2px] w-full bg-gradient-to-r from-cyan-500/0 via-cyan-500/60 to-cyan-500/0" />
            </div>
          ))}
        </div>
      </footer>
    </div>
  );
}
