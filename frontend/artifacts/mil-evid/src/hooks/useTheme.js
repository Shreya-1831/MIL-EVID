import { useEffect, useState } from 'react';

export function useTheme() {
  const [theme, setTheme] = useState(() => localStorage.getItem('mil-evid-theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'));
  useEffect(() => { document.documentElement.classList.toggle('dark', theme === 'dark'); localStorage.setItem('mil-evid-theme', theme); }, [theme]);
  return { theme, toggleTheme: () => setTheme((value) => value === 'dark' ? 'light' : 'dark') };
}