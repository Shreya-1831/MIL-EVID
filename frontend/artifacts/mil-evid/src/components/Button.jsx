const cn = (...items) => items.filter(Boolean).join(" ");

function Button({ children, variant = "primary", className, ...props }) {
  const variants = {
    primary: "bg-primary text-primary-foreground hover:opacity-90",
    outline: "border border-border bg-card text-foreground hover:bg-muted",
    copper: "bg-accent text-accent-foreground hover:opacity-90",
    ghost: "text-muted-foreground hover:bg-muted hover:text-foreground",
  };

  return (
    <button
      className={cn(
        "inline-flex min-h-10 items-center justify-center gap-2 px-4 text-sm font-medium transition-all disabled:cursor-not-allowed disabled:opacity-50",
        variants[variant],
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}

export default Button;