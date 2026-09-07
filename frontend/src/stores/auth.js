import { reactive } from "vue";
import { api, getToken, setToken } from "../api";
import { applyTheme } from "../theme";

export const auth = reactive({
  token: getToken(),
  user: null,
});

export async function loadMe() {
  if (!auth.token) {
    auth.user = null;
    return null;
  }
  try {
    auth.user = await api("/api/auth/me");
    if (auth.user && auth.user.organization) {
      applyTheme(auth.user.organization.theme, auth.user.organization.layout_key);
    }
    return auth.user;
  } catch {
    setToken("");
    auth.token = "";
    auth.user = null;
    return null;
  }
}

export async function login(email, password) {
  const data = await api("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setToken(data.token);
  auth.token = data.token;
  auth.user = data.user;
  if (data.user && data.user.organization) {
    applyTheme(data.user.organization.theme, data.user.organization.layout_key);
  }
  return data.user;
}

export async function register(payload) {
  const data = await api("/api/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  setToken(data.token);
  auth.token = data.token;
  auth.user = data.user;
  if (data.user && data.user.organization) {
    applyTheme(data.user.organization.theme, data.user.organization.layout_key);
  }
  return data.user;
}

export function logout() {
  setToken("");
  auth.token = "";
  auth.user = null;
}
