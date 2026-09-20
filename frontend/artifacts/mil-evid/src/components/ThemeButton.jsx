import { Moon, Sun } from "lucide-react";
import { useTheme } from "../hooks/useTheme";

function ThemeButton() {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      className="grid h-9 w-9 place-items-center border border-border text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
      aria-label="Toggle theme"
      data-testid="button-theme-toggle"
    >
      {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
    </button>
  );
}

export default ThemeButton;