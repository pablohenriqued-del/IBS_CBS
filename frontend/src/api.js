import axios from "axios";

export const BACKEND = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND}/api`;

export const api = axios.create({
  baseURL: API,
  // Sem withCredentials — o ingress reescreve Access-Control-Allow-Origin para *,
  // o que quebra cookies cross-origin. Usamos Bearer token via localStorage.
  withCredentials: false,
});

// Bearer token fallback (para navegadores que bloqueiam cookies cross-site)
export function setAuthToken(token) {
  if (token) {
    api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
    localStorage.setItem("fc-token", token);
  } else {
    delete api.defaults.headers.common["Authorization"];
    localStorage.removeItem("fc-token");
  }
}

// Restaura o token na carga inicial
const saved = typeof window !== "undefined" ? localStorage.getItem("fc-token") : null;
if (saved) {
  api.defaults.headers.common["Authorization"] = `Bearer ${saved}`;
}

// Mensagens amigáveis para códigos de erro conhecidos do backend
const ERRO_CODIGO_PTBR = {
  documento_ja_importado: (d) =>
    `NF-e já importada anteriormente${d.chaveAcesso ? ` (chave …${String(d.chaveAcesso).slice(-8)})` : ""}`,
  sem_ruleset_vigente: (d) =>
    `Sem ruleset vigente${d.dataOperacao ? ` para a data ${d.dataOperacao}` : ""}`,
  cclasstrib_desconhecido: (d) =>
    `Código cClassTrib desconhecido no ruleset${d.codigo ? ` (${d.codigo})` : ""}`,
  validacao: (d) =>
    Array.isArray(d.detalhes)
      ? d.detalhes.map((x) => x.mensagem || `${x.campo}: ${x.codigo}`).join(" · ")
      : "Erro de validação",
  auditoria_nao_encontrada: () => "Registro de auditoria não encontrado",
};

export function formatApiError(err) {
  const detail = err?.response?.data?.detail;
  if (detail == null) return err?.message || "Erro desconhecido";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail
      .map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e)))
      .filter(Boolean)
      .join(" · ");
  if (detail && typeof detail === "object") {
    if (typeof detail.msg === "string") return detail.msg;
    if (typeof detail.erro === "string" && ERRO_CODIGO_PTBR[detail.erro]) {
      return ERRO_CODIGO_PTBR[detail.erro](detail);
    }
    if (typeof detail.erro === "string") return detail.erro;
    // Fallback amigável em vez de despejar JSON
    return "Erro do servidor — verifique os dados enviados";
  }
  return String(detail);
}
