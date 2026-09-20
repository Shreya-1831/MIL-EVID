import { Search } from "lucide-react";
import Button from "./Button";

function EmptyState({ title, text, onReset }) {
  return (
    <div className="py-12 text-center">
      <div className="mx-auto grid h-10 w-10 place-items-center border border-border text-muted-foreground">
        <Search size={17} />
      </div>

      <h3 className="mt-4 text-sm font-medium">{title}</h3>

      <p className="mt-2 text-xs text-muted-foreground">{text}</p>

      {onReset && (
        <Button
          variant="outline"
          className="mt-5"
          onClick={onReset}
          data-testid="button-empty-reset"
        >
          Reset filters
        </Button>
      )}
    </div>
  );
}

export default EmptyState;