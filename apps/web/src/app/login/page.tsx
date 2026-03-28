'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import api from '@/lib/api';
import { TokenResponse } from '@/types/api';
import { Eye, EyeOff, Lock, Mail, BarChart3 } from 'lucide-react';

export default function LoginPage() {
  const router = useRouter();
  const { setAuth } = useAuthStore();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    if (!email || !password) {
      setError('Please enter both email and password.');
      return;
    }
    setLoading(true);
    setError('');

    try {
      console.log('Attempting login for:', email);
      const res = await api.post<TokenResponse>('/api/v1/auth/login', { email, password });
      const { access_token, refresh_token, user } = res.data;

      console.log('Login successful, role:', user.role);

      // Persist auth (also sets cookie-compatible localStorage for middleware)
      setAuth(user, access_token, refresh_token);

      // Set a cookie so middleware can check on server side (30 days max-age)
      document.cookie = `crm_token=${access_token}; path=/; max-age=2592000; SameSite=Lax${window.location.protocol === 'https:' ? '; Secure' : ''}`;

      // Role-based redirect
      if (user.role === 'Admin' || user.role === 'Client') {
        router.replace('/admin/dashboard');
      } else {
        setError('Access denied. This portal is for Admin and Client users only.');
        setAuth(user, '', '');
      }
    } catch (err: unknown) {
      console.error('Login error:', err);
      const axiosError = err as { response?: { data?: { detail?: any } } };
      const detail = axiosError?.response?.data?.detail;
      setError(
        (typeof detail === 'string' ? detail : JSON.stringify(detail)) ||
        'Login failed. Please check your credentials.'
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex bg-mesh-ultra font-sans selection:bg-indigo-500/30 overflow-hidden relative">
      {/* Background Aurora Glows - Indigo for RuixenUI */}
      <div className="absolute inset-0 z-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[-20%] left-[-10%] w-[60%] h-[60%] bg-indigo-600/[0.07] rounded-full blur-[160px]" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[70%] h-[70%] bg-zinc-800/[0.05] rounded-full blur-[180px]" />
        <div className="absolute inset-0 opacity-[0.03]" style={{ backgroundImage: 'radial-gradient(#ffffff 1px, transparent 1px)', backgroundSize: '40px 40px' }} />
      </div>

      <div className="flex w-full relative z-10">
        {/* Left Section: Branding & Vision */}
        <div className="hidden lg:flex flex-col justify-between w-[45%] p-20">
          <div className="animate-in fade-in slide-in-from-top-4 duration-700">
            <div className="flex items-center gap-4 mb-4">
              <div className="w-14 h-14 rounded-2xl flex items-center justify-center shadow-xl shadow-indigo-500/20"
                style={{ background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)' }}>
                <BarChart3 size={28} className="text-white" />
              </div>
              <span className="text-white font-black text-2xl tracking-tighter uppercase">TAC PMC</span>
            </div>
            <div className="h-[2px] w-14 bg-indigo-500/40 rounded-full" />
          </div>

          <div className="max-w-lg">
            <h1 className="text-6xl font-black text-white leading-[1.1] mb-8 tracking-tighter animate-in fade-in slide-in-from-left-6 duration-1000">
              Financial Integrity,<br />
              <span className="text-indigo-400 italic">Masterfully Built.</span>
            </h1>
            <p className="text-slate-400 text-xl leading-relaxed mb-16 opacity-80">
              Transforming construction finance with real-time analytics
              and immutable traceability at scale.
            </p>

            <div className="grid gap-5">
              {[
                { label: 'Real-time Analytics', icon: '01' },
                { label: 'Automated Reporting', icon: '02' },
                { label: 'Secure Architecture', icon: '03' },
              ].map((item, i) => (
                <div key={item.label}
                  className="glass-card rounded-[1.5rem] p-5 flex items-center gap-6 group hover:translate-x-2 transition-transform duration-500"
                  style={{ transitionDelay: `${i * 150}ms` }}>
                  <span className="text-xs font-black text-indigo-500/40 tracking-widest group-hover:text-indigo-500 transition-colors uppercase">{item.icon}</span>
                  <span className="text-white/90 font-bold text-base tracking-wide">{item.label}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-5 text-slate-600 text-xs font-black tracking-[0.3em] uppercase">
            <span className="opacity-40">Privacy Policy</span>
            <div className="w-1 h-1 rounded-full bg-slate-800" />
            <span className="opacity-40">Security Status</span>
            <div className="w-1 h-1 rounded-full bg-slate-800" />
            <span className="opacity-40 text-orange-500/40 italic">v4.2.0</span>
          </div>
        </div>

        {/* Right Section: Centered Login Terminal */}
        <div className="flex-1 flex items-center justify-center p-8 lg:p-20">
          <div className="w-full max-w-[540px] animate-in fade-in zoom-in-95 duration-1000">
            {/* Mobile Header */}
            <div className="flex flex-col items-center gap-4 mb-16 lg:hidden">
              <div className="w-16 h-16 rounded-[1.5rem] flex items-center justify-center shadow-2xl shadow-orange-500/20"
                style={{ background: 'linear-gradient(135deg, #F97316 0%, #ea6a0e 100%)' }}>
                <BarChart3 size={32} className="text-white" />
              </div>
              <span className="text-white font-bold text-3xl tracking-tighter uppercase">TAC-PMC</span>
            </div>

            <div className="glass-panel rounded-[3.5rem] p-12 md:p-20 relative group">
              {/* Gloss Sweep Effect */}
              <div className="absolute top-0 left-[-100%] w-full h-full bg-gradient-to-r from-transparent via-white/[0.04] to-transparent skew-x-[-25deg] transition-all duration-[1.5s] group-hover:left-[100%] pointer-events-none" />

              <div className="mb-14 relative z-10 text-center">
                <h2 className="text-5xl font-bold text-white mb-2 tracking-tight">Sign In</h2>
                <p className="text-slate-400 text-xs font-bold uppercase tracking-[0.2em] opacity-50">Enterprise Access Terminal</p>
              </div>

              <form onSubmit={handleLogin} className="space-y-10 relative z-10">
                <div className="space-y-3">
                  <label className="block text-slate-400 text-[10px] font-black uppercase tracking-[0.3em] ml-2">Identity</label>
                  <div className="relative group/input">
                    <Mail size={20} className="absolute left-8 top-1/2 -translate-y-1/2 text-zinc-500 group-focus-within/input:text-indigo-500 transition-colors z-20" />
                    <input
                      id="email"
                      type="email"
                      autoComplete="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="admin@tacpmc.com"
                      className="input-glass w-full pl-[5.5rem] pr-6 py-5 rounded-2xl text-white text-base placeholder:text-zinc-800 outline-none focus:ring-1 focus:ring-indigo-500/50"
                    />
                  </div>
                </div>

                <div className="space-y-3">
                  <div className="flex justify-between items-center px-2">
                    <label className="block text-slate-400 text-[10px] font-black uppercase tracking-[0.3em]">Security Key</label>
                    <a href="#" className="text-orange-500/60 hover:text-orange-400 text-[10px] font-bold uppercase tracking-widest transition-colors">Recovery</a>
                  </div>
                  <div className="relative group/input">
                    <Lock size={20} className="absolute left-8 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within/input:text-orange-500 transition-colors z-20" />
                    <input
                      id="password"
                      type={showPass ? 'text' : 'password'}
                      autoComplete="current-password"
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      className="input-glass w-full pl-[5.5rem] pr-16 py-5 rounded-2xl text-white text-base placeholder:text-slate-800 outline-none"
                    />
                    <button type="button" onClick={() => setShowPass(!showPass)} className="absolute right-8 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white transition-colors z-20">
                      {showPass ? <EyeOff size={22} /> : <Eye size={22} />}
                    </button>
                  </div>
                </div>



                {error && (
                  <div className="rounded-2xl px-6 py-4 text-xs font-bold flex items-center gap-4 bg-red-500/10 border border-red-500/20 text-red-400 animate-in fade-in zoom-in duration-200">
                    <div className="w-2 h-2 rounded-full bg-red-500 shadow-[0_0_10px_#ef4444]" />
                    {error}
                  </div>
                )}

                <button
                  id="login-btn"
                  type="submit"
                  disabled={loading}
                  className="w-full h-16 rounded-2xl font-bold text-white text-sm tracking-[0.3em] uppercase transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed shadow-2xl shadow-indigo-500/20 active:scale-[0.98] outline-none"
                  style={{ background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)' }}
                >
                  <span className="relative z-10 flex items-center justify-center gap-4">
                    {loading ? (
                      <><span className="w-4 h-4 border-[2px] border-white border-t-transparent rounded-full animate-spin" /> AUTHORIZING...</>
                    ) : (
                      <>ESTABLISH CONNECTION <BarChart3 size={18} className="opacity-60" /></>
                    )}
                  </span>
                </button>
              </form>
            </div>

            <div className="text-center mt-12 space-y-2 opacity-60">
              <p className="text-slate-200 text-xs font-bold tracking-[0.4em] uppercase">
                Authorized Access Only
              </p>
              <p className="text-slate-500 text-[10px] font-black tracking-[0.2em] uppercase">
                System Terminals Audited • ISO-27001 Verified
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
