import React, { useEffect, useState } from "react";
import { UserPlus, Users } from "lucide-react";
import { api, formatApiError } from "../api";

export function UsuariosPage() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ email: "", password: "", name: "", role: "fiscal" });
  const [msg, setMsg] = useState(null);

  const carregar = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/auth/users");
      setUsers(data.users);
    } catch (e) {
      setMsg({ type: "error", text: formatApiError(e) });
    } finally { setLoading(false); }
  };

  useEffect(() => { carregar(); }, []);

  const criar = async (e) => {
    e.preventDefault();
    setMsg(null);
    try {
      await api.post("/auth/register", form);
      setMsg({ type: "success", text: `✓ ${form.email} criado como ${form.role}` });
      setForm({ email: "", password: "", name: "", role: "fiscal" });
      carregar();
    } catch (err) {
      setMsg({ type: "error", text: formatApiError(err) });
    }
  };

  return (
    <div className="max-w-[1400px] mx-auto px-6 py-12">
      <div className="mb-8">
        <div className="text-[11px] font-mono uppercase tracking-[0.3em] text-muted mb-2">
          POST /api/auth/register · GET /api/auth/users
        </div>
        <h1 className="font-heading text-4xl tracking-tight text-strong mb-2">
          <span className="serif-italic text-accent">Usuários</span> &amp; papéis.
        </h1>
        <p className="text-muted max-w-2xl">
          <span className="text-text">Fiscal</span> importa docs e vê apurações.{" "}
          <span className="text-text">Auditoria</span> tem acesso somente-leitura à trilha
          imutável. <span className="text-text">Admin</span> gerencia usuários e regras.
        </p>
      </div>

      <div className="grid grid-cols-12 gap-6">
        <form onSubmit={criar} data-testid="user-form" className="col-span-12 lg:col-span-5 border border-border rounded-md bg-surface p-5 space-y-3">
          <div className="flex items-center gap-2 mb-2">
            <UserPlus className="w-4 h-4 text-accent" />
            <span className="text-[10px] uppercase tracking-[0.3em] text-accent">Criar usuário</span>
          </div>
          <label className="block">
            <span className="text-[10px] uppercase tracking-[0.25em] text-muted">Nome</span>
            <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="user-name"
              className="mt-1 w-full bg-bg border border-border rounded-md px-3 py-2 text-sm focus:border-accent focus:outline-none" />
          </label>
          <label className="block">
            <span className="text-[10px] uppercase tracking-[0.25em] text-muted">E-mail</span>
            <input required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} data-testid="user-email"
              className="mt-1 w-full bg-bg border border-border rounded-md px-3 py-2 text-sm font-mono focus:border-accent focus:outline-none" />
          </label>
          <label className="block">
            <span className="text-[10px] uppercase tracking-[0.25em] text-muted">Senha (mín 8)</span>
            <input required type="password" minLength={8} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} data-testid="user-password"
              className="mt-1 w-full bg-bg border border-border rounded-md px-3 py-2 text-sm font-mono focus:border-accent focus:outline-none" />
          </label>
          <label className="block">
            <span className="text-[10px] uppercase tracking-[0.25em] text-muted">Papel</span>
            <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} data-testid="user-role"
              className="mt-1 w-full bg-bg border border-border rounded-md px-3 py-2 text-sm focus:border-accent focus:outline-none">
              <option value="fiscal">fiscal</option>
              <option value="auditoria">auditoria</option>
              <option value="admin">admin</option>
            </select>
          </label>
          <button type="submit" data-testid="user-submit"
            className="w-full bg-accent text-bg font-semibold rounded-md py-2.5 flex items-center justify-center gap-2 hover:bg-accentHover">
            <UserPlus className="w-4 h-4" strokeWidth={2.5} /> Criar
          </button>
          {msg && (
            <div data-testid="user-msg" className={`text-[12px] font-mono rounded-md px-3 py-2 ${msg.type === "success" ? "text-success border border-success/30 bg-success/5" : "text-error border border-error/30 bg-error/5"}`}>
              {msg.text}
            </div>
          )}
        </form>

        <div className="col-span-12 lg:col-span-7 border border-border rounded-md overflow-hidden bg-surface">
          <div className="px-4 py-3 border-b border-border flex items-center gap-2">
            <Users className="w-4 h-4 text-muted" />
            <span className="text-[10px] uppercase tracking-[0.3em] text-muted">Usuários cadastrados</span>
            <span className="ml-auto text-[11px] font-mono text-muted">{loading ? "…" : `${users.length} total`}</span>
          </div>
          <div className="grid grid-cols-12 gap-3 px-4 py-2 border-b border-border text-[10px] uppercase tracking-[0.25em] text-muted">
            <div className="col-span-5">e-mail</div><div className="col-span-3">nome</div>
            <div className="col-span-2">papel</div><div className="col-span-2">criado</div>
          </div>
          {users.map((u) => (
            <div key={u.id} className="grid grid-cols-12 gap-3 px-4 py-2.5 border-b border-border/50 text-[12px] items-center">
              <div className="col-span-5 font-mono text-[11.5px] text-strong truncate">{u.email}</div>
              <div className="col-span-3 text-muted truncate">{u.name}</div>
              <div className="col-span-2"><span className="text-[9.5px] font-mono uppercase tracking-[0.2em] text-accent border border-accent/40 rounded px-1.5 py-0.5">{u.role}</span></div>
              <div className="col-span-2 font-mono text-[10.5px] text-muted">{u.created_at?.slice(0, 10)}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
