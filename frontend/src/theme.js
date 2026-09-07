export function applyTheme(theme, layoutKey) {
  const root = document.documentElement;
  if (!theme) return;
  const map = {
    primary: "--terra",
    secondary: "--ink",
    accent: "--gold",
    background: "--paper",
    surface: "--paper-2",
    text: "--ink",
    muted: "--ink-soft",
    border: "--line",
    success: "--sage",
    danger: "--danger",
    radius: "--radius",
    font: "--sans",
    heading: "--serif",
  };
  if (theme.primary) root.style.setProperty("--terra-dark", theme.primary);
  Object.entries(map).forEach(([k, css]) => {
    if (theme[k]) root.style.setProperty(css, theme[k]);
  });
  if (layoutKey) document.body.dataset.layout = layoutKey;
}
