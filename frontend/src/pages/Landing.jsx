import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Zap,
  ShieldCheck,
  BarChart3,
  Workflow,
  Search,
  FileText,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  ChevronRight,
  TrendingUp,
  Fingerprint,
  Network,
  Scale
} from 'lucide-react';

export default function Landing() {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    setIsVisible(true);
  }, []);

  return (
    <div className="flex flex-col min-h-screen bg-[#020608] overflow-hidden">
      {/* Background Decorative Elements */}
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none opacity-20">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-[#00d4aa] rounded-full blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[30%] h-[30%] bg-[#0099ff] rounded-full blur-[100px]" />
      </div>

      {/* Hero Section */}
      <header className="relative pt-24 pb-20 px-8 flex flex-col items-center text-center">
        <div className={`px-3 py-1 bg-[#111820] border border-[#1a2530] rounded-full flex items-center gap-2 mb-8 transition-all duration-1000 ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}>
          <span className="w-2 h-2 rounded-full bg-[#00d4aa] animate-pulse" />
          <span className="text-[10px] font-mono text-[#00d4aa] tracking-widest uppercase">Intelli-Credit v2.1 Advanced</span>
        </div>

        <h1 className={`font-syne text-6xl md:text-7xl font-bold text-[#e8f0f5] max-w-4xl tracking-tight leading-[1.1] mb-8 transition-all duration-1000 delay-100 ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
          The Institutional Standard for <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#00d4aa] to-[#0099ff]">AI Credit Appraisal</span>
        </h1>

        <p className={`text-lg text-[#4a6070] max-w-2xl mb-12 leading-relaxed transition-all duration-1000 delay-200 ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'}`}>
          Scale your lending operations with sub-30 minute appraisal cycles. Engineered for Risk Managers who demand precision, auditability, and bank-grade fraud detection.
        </p>

        <div className={`flex items-center gap-4 transition-all duration-1000 delay-300 ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}>
          <Link to="/appraisal/new" className="btn-primary flex items-center gap-2">
            Start New Appraisal <ArrowRight size={18} />
          </Link>
          <Link to="/dashboard" className="btn-secondary">
            View Analytics
          </Link>
        </div>
      </header>

      {/* Trust Metrics Bar */}
      <section className="px-8 mb-32">
        <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-1 px-1 bg-[#1a2530] rounded-2xl border border-[#1a2530] overflow-hidden">
          {[
            { label: 'Avg. Turnaround', value: '28m', sub: 'vs 15h Manual' },
            { label: 'Extraction Accuracy', value: '99.8%', sub: 'Financial parsing precision' },
            { label: 'Risk Parameters', value: '42', sub: 'Advanced multi-agent checks' },
          ].map((metric, i) => (
            <div key={i} className="bg-[#0a0f12] p-8 flex flex-col items-center text-center">
              <span className="text-[#4a6070] text-xs font-mono uppercase tracking-widest mb-1">{metric.label}</span>
              <span className="text-4xl font-syne font-bold text-[#e8f0f5] mb-1">{metric.value}</span>
              <span className="text-[#00d4aa] text-[10px] font-mono">{metric.sub}</span>
            </div>
          ))}
        </div>
      </section>

      {/* How It Works: The Agent Trio */}
      <section className="px-8 pb-32 pt-16 border-t border-[#1a2530]/30">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-20 animate-slide-up">
            <span className="text-[#00d4aa] font-mono text-xs tracking-widest uppercase mb-4 block">The Process</span>
            <h2 className="font-syne text-4xl font-bold text-[#e8f0f5]">Three Expert Agents, One Decision</h2>
            <p className="text-[#4a6070] mt-4 max-w-2xl mx-auto">We use three specialized AI agents that work together to confirm the accuracy of every application.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* Agent 1 */}
            <div className="card p-8 group hover:border-[#00d4aa]/30 transition-all animate-slide-up" style={{ animationDelay: '100ms' }}>
              <div className="w-12 h-12 rounded-xl bg-[#00d4aa]/10 flex items-center justify-center text-[#00d4aa] mb-6 group-hover:scale-110 transition-transform">
                <FileText size={24} />
              </div>
              <h3 className="font-syne text-xl font-bold text-[#e8f0f5] mb-4">1. Ingestor Agent</h3>
              <p className="text-sm text-[#4a6070] leading-relaxed mb-6">
                Our "Data Expert" pulls every number from your <b>ITR, GST returns, and Balance Sheets</b> using advanced extraction. It also runs a <b>Forgery Check</b> to make sure documents haven't been tampered with.
              </p>
              <ul className="space-y-2">
                {['GST vs Sales Check', 'ITR Verification', 'Auto-Data Extraction'].map((item, i) => (
                  <li key={i} className="flex items-center gap-2 text-[11px] font-mono text-[#00d4aa]">
                    <CheckCircle2 size={12} /> {item}
                  </li>
                ))}
              </ul>
            </div>

            {/* Agent 2 */}
            <div className="card p-8 group hover:border-[#0099ff]/30 transition-all animate-slide-up" style={{ animationDelay: '200ms' }}>
              <div className="w-12 h-12 rounded-xl bg-[#0099ff]/10 flex items-center justify-center text-[#0099ff] mb-6 group-hover:scale-110 transition-transform">
                <Search size={24} />
              </div>
              <h3 className="font-syne text-xl font-bold text-[#e8f0f5] mb-4">2. Research Agent</h3>
              <p className="text-sm text-[#4a6070] leading-relaxed mb-6">
                The "Background Checker" verifies if the business is real. It checks <b>EPFO records</b> for employee counts, maps <b>Director Networks</b> to find hidden risks, and scans the web for any legal defaults.
              </p>
              <ul className="space-y-2">
                {['EPFO Reality Check', 'Director Risk Map', 'Legal & News Scan'].map((item, i) => (
                  <li key={i} className="flex items-center gap-2 text-[11px] font-mono text-[#0099ff]">
                    <CheckCircle2 size={12} /> {item}
                  </li>
                ))}
              </ul>
            </div>

            {/* Agent 3 */}
            <div className="card p-8 group hover:border-[#ffd166]/30 transition-all animate-slide-up" style={{ animationDelay: '300ms' }}>
              <div className="w-12 h-12 rounded-xl bg-[#ffd166]/10 flex items-center justify-center text-[#ffd166] mb-6 group-hover:scale-110 transition-transform">
                <Scale size={24} />
              </div>
              <h3 className="font-syne text-xl font-bold text-[#e8f0f5] mb-4">3. Scorer Agent</h3>
              <p className="text-sm text-[#4a6070] leading-relaxed mb-6">
                The "Decision Maker" weighs all factors—including <b>Fixed Obligation Ratio (FOR)</b> and the 5Cs. It then writes a <b>Judge’s Walkthrough</b> in plain English so you know exactly why a loan was approved or flagged.
              </p>
              <ul className="space-y-2">
                {['FOR & 5C Scoring', 'Judge’s Walkthrough', 'Risk Flag Analysis'].map((item, i) => (
                  <li key={i} className="flex items-center gap-2 text-[11px] font-mono text-[#ffd166]">
                    <CheckCircle2 size={12} /> {item}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Feature Fact Section */}
      <section className="px-8 pb-32">
        <div className="max-w-6xl mx-auto">
          <div className="flex flex-col md:flex-row gap-16 items-center">
            <div className="flex-1">
              <span className="text-[#00d4aa] font-mono text-xs tracking-widest uppercase mb-4 block">Deep Financial Logic</span>
              <h2 className="font-syne text-4xl font-bold text-[#e8f0f5] mb-6 leading-tight">
                Accurate Data. <span className="text-[#00d4aa]">Smart Decisions.</span>
              </h2>
              <p className="text-[#4a6070] leading-relaxed mb-8">
                We use advanced AI to make sure you never miss a red flag. From checking simple tax filings to complex corporate networks, we take everything into account.
              </p>

              <div className="space-y-6">
                {[
                  { icon: <TrendingUp size={20} />, title: 'Real Revenue Check', desc: 'We compare your GST filings with bank statements to catch revenue inflation early.' },
                  { icon: <ShieldCheck size={20} />, title: 'Fraud Prevention', desc: 'Our first step is always checking for document forgery. We spot tampered PDFs instantly.' },
                  { icon: <Workflow size={20} />, title: 'Ability to Pay (FOR)', desc: 'We automatically calculate the Fixed Obligation Ratio (FOR) to ensure the borrower isn’t over-leveraged.' },
                ].map((item, i) => (
                  <div key={i} className="flex gap-4 p-4 rounded-xl border border-transparent hover:border-[#1a2530] hover:bg-[#0a0f12]/50 transition-all">
                    <div className="w-10 h-10 rounded-lg bg-[#111820] border border-[#1a2530] flex items-center justify-center text-[#00d4aa]">
                      {item.icon}
                    </div>
                    <div>
                      <h4 className="text-[#e8f0f5] font-semibold mb-1">{item.title}</h4>
                      <p className="text-xs text-[#4a6070] leading-normal">{item.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex-1 w-full max-w-md">
              <div className="card p-1 bg-gradient-to-br from-[#1a2530] to-[#0a0f12] overflow-hidden relative group">
                <div className="absolute inset-0 bg-[#00d4aa]/5 opacity-0 group-hover:opacity-100 transition-opacity" />
                <div className="p-8 relative bg-[#0a0f12] rounded-[9px]">
                  <h3 className="font-syne font-bold mb-6 text-[#e8f0f5] flex items-center justify-between">
                    The Scorer (5Cs) <span className="text-[10px] font-mono text-[#4a6070]">REAL-TIME LOGIC</span>
                  </h3>

                  <div className="space-y-4">
                    {[
                      { c: 'Character', val: 72, risk: 'LOW' },
                      { c: 'Capacity', val: 68, risk: 'MED' },
                      { c: 'Capital', val: 85, risk: 'LOW' },
                      { c: 'Collateral', val: 92, risk: 'LOW' },
                      { c: 'Conditions', val: 45, risk: 'HIGH' },
                    ].map((item, i) => (
                      <div key={i}>
                        <div className="flex justify-between text-[11px] font-mono mb-1.5">
                          <span className="text-[#4a6070]">{item.c}</span>
                          <span className={`${item.risk === 'HIGH' ? 'text-[#ef476f]' : item.val > 70 ? 'text-[#00d4aa]' : 'text-[#ffd166]'}`}>{item.val}/100</span>
                        </div>
                        <div className="h-1 bg-[#1a2530] rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all duration-1000`}
                            style={{
                              width: isVisible ? `${item.val}%` : '0%',
                              backgroundColor: item.risk === 'HIGH' ? '#ef476f' : item.val > 70 ? '#00d4aa' : '#ffd166',
                              transitionDelay: `${400 + (i * 100)}ms`
                            }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="mt-8 pt-6 border-t border-[#1a2530]">
                    <div className="flex items-center gap-3 text-[11px] text-[#4a6070] italic">
                      <Zap size={14} className="text-[#00d4aa]" />
                      "Dynamic weighting applied based on 42-parameter risk profile"
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Value Matrix */}
      <section className="bg-[#0a0f12] border-t border-b border-[#1a2530] py-24 px-8">
        <div className="max-w-6xl mx-auto text-center mb-16">
          <h2 className="font-syne text-3xl font-bold text-[#e8f0f5] mb-4">Competitive Superiority</h2>
          <p className="text-[#4a6070]">How standard manual appraisal compares to Intelli-Credit v2.1</p>
        </div>

        <div className="max-w-4xl mx-auto overflow-hidden border border-[#1a2530] rounded-xl font-mono text-[13px]">
          <div className="grid grid-cols-3 bg-[#111820] border-b border-[#1a2530] p-4 text-[#4a6070] font-bold">
            <div>PARAMETER</div>
            <div className="text-center">MANUAL PROCESS</div>
            <div className="text-right text-[#00d4aa]">INTELLI-CREDIT AI</div>
          </div>

          {[
            { p: 'Data Extraction', m: '12-15 Hours', a: 'Sub-90 Seconds' },
            { p: 'Fraud Screening', m: 'Sampling-based', a: '100% Comprehensive' },
            { p: 'Error Margin', m: '~18.5% Variance', a: '<0.5% Variance' },
            { p: 'Bias Control', m: 'Manager Subjectivity', a: 'Mathematic SHAP-Audit' },
            { p: 'Decision Memo', m: 'Human Authored', a: 'GenAI Narrative' },
          ].map((row, i) => (
            <div key={i} className={`grid grid-cols-3 p-4 border-b border-[#1a2530] last:border-0 ${i % 2 === 0 ? 'bg-[#0a0f12]' : 'bg-[#020608]'}`}>
              <div className="text-[#e8f0f5]">{row.p}</div>
              <div className="text-center text-[#4a6070]">{row.m}</div>
              <div className="text-right text-[#00d4aa] font-bold">{row.a}</div>
            </div>
          ))}
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-32 px-8 flex flex-col items-center text-center">
        <div className="w-16 h-16 rounded-2xl bg-[#00d4aa]/10 border border-[#00d4aa]/20 flex items-center justify-center text-[#00d4aa] mb-8">
          <Scale size={32} />
        </div>
        <h2 className="font-syne text-4xl font-bold text-[#e8f0f5] mb-6 tracking-tight">Ready to de-risk your portfolio?</h2>
        <p className="text-[#4a6070] max-w-xl mb-12">
          Join leading financial institutions that have automated 80% of their middle-office appraisal logic. No more "Wait & Watch" — just "Know & Decide".
        </p>
        <div className="flex gap-4">
          <Link to="/appraisal/new" className="btn-primary flex items-center gap-2">
            Launch Agent Pipeline <ChevronRight size={18} />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="mt-auto py-8 px-8 border-t border-[#1a2530] flex flex-col md:flex-row justify-between items-center gap-4">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded bg-[#00d4aa] flex items-center justify-center text-[10px] text-[#020608] font-bold font-syne">IC</div>
          <span className="text-xs text-[#4a6070] font-syne font-bold">Intelli-Credit System</span>
        </div>
        <div className="flex items-center gap-6 text-[10px] text-[#4a6070] font-mono uppercase tracking-widest">
          <span>Accuracy: 99.8%</span>
          <span>Latency: 28min Avg</span>
          <span>Compliance: RBI Standard v4</span>
        </div>
        <div className="text-[10px] text-[#4a6070]">© 2026 INTELLI-CREDIT AI LABORATORY</div>
      </footer>
    </div>
  );
}
